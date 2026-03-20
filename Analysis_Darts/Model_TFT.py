import numpy as np
import pandas as pd
from darts import TimeSeries
from darts.utils.missing_values import fill_missing_values
from darts.dataprocessing.transformers import Scaler
from darts.models import TFTModel
from pytorch_lightning.callbacks.early_stopping import EarlyStopping
import warnings


warnings.filterwarnings("ignore", message="X does not have valid feature names")


def run_TFTModel(df):
    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = [
        'Volume',
        'SMA_5', 'SMA_20', 'SMA_60',
        'RSI_14',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
        'VWAP_D', 'OBV', 'ATRe_14'
    ]
    series_covar = TimeSeries.from_dataframe(df, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # EarlyStopping 설정 (과적합 방지)
    # 20번의 에포크 동안 손실(loss)이 줄어들지 않으면 학습 중단
    my_stopper = EarlyStopping(
        monitor="train_loss",
        patience=20,
        min_delta=0.001,
        mode="min"
    )

    # 2. 모델 정의
    model_tft = TFTModel(
        input_chunk_length=30,  # 과거 30일 데이터를 입력으로 사용
        output_chunk_length=5,  # 한 번에 5일치 미래를 예측
        hidden_size=64,  # 모델의 복잡도 (클수록 학습량 증가)
        lstm_layers=1,  # 내부 LSTM 계층 수
        num_attention_heads=4,  # 어텐션 헤드 수 (복잡한 패턴 인식)
        dropout=0.1,  # 과적합 방지용 노드 탈락 비율
        batch_size=64,
        n_epochs=50,  # 최대 학습 횟수
        add_relative_index=True,  # 시간 순서 정보를 모델에 제공 (TFT 핵심)
        optimizer_kwargs={"lr": 1e-3},  # 학습률 설정
        pl_trainer_kwargs={
            "callbacks": [my_stopper],
            "accelerator": "auto"  # GPU가 있으면 자동으로 GPU 사용
        },
        random_state=42
    )

    # 실제 내일 주가 예측이 목적이면 전체 데이터로 학습하되, 검증셋은 비워두는 것이 정석입니다.
    model_tft.fit(
        series=series_target_scaled,  # 100% 데이터
        past_covariates=series_covar_scaled,
        verbose=True
        # val_series 인자를 아예 생략함
    )

    # 예측 시에도 현재까지의 보조지표 데이터가 필요함
    prediction_scaled = model_tft.predict(n=5, series=series_target_scaled, past_covariates=series_covar_scaled)
    prediction_final = scaler_target.inverse_transform(prediction_scaled)

    # 3. 실제 주가로 환산 (마지막 종가 기준)
    pred_return_values = prediction_final.univariate_values()  # numpy 배열로 추출
    last_close = df['Close'].iloc[-1]
    predicted_prices = []

    current_price = last_close
    for r in pred_return_values:
        # 로그 수익률 역산: 현재가 * exp(로그수익률)
        next_price = current_price * np.exp(r)
        predicted_prices.append(next_price)
        current_price = next_price  # 누적 예측을 위해 갱신

    # 3. 데이터프레임 생성 (날짜 인덱스 포함)
    # pred_return(Darts 객체)에서 미래 날짜 인덱스를 그대로 가져옵니다.
    forecast_df = pd.DataFrame({
        'Time': prediction_final.time_index,
        'Predicted_Log_Return': pred_return_values.round(4),
        'Predicted_Close': np.array(predicted_prices).astype(int)
    })

    return forecast_df


def check_nans(series):
    df = series.to_dataframe()
    nans = df.isna().sum()
    total = nans.sum()
    print("컬럼별 NaN:", nans)
    print(f"총 NaN: {total}")
    return total == 0
