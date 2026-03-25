import logging

import numpy as np
import pandas as pd
from darts import TimeSeries
from darts.utils.missing_values import fill_missing_values
from darts.dataprocessing.transformers import Scaler
from darts.models import SKLearnModel
from sklearn.ensemble import RandomForestRegressor
import warnings

warnings.filterwarnings("ignore", message="X does not have valid feature names")

# 로거 가져오기
logger = logging.getLogger(__name__)


def run_XGBModel(df):
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

    # 4. RegressionModel 정의 및 학습
    # sklearn의 모델을 model 파라미터에 넣습니다.
    model = SKLearnModel(
        model=RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42),
        lags=20,  # 과거 수익률 20일치 참고
        lags_past_covariates=12,  # 과거 보조지표 12일치 참고
        output_chunk_length=5
    )

    model.fit(series_target_scaled, past_covariates=series_covar_scaled)

    # 5. 예측
    prediction_scaled = model.predict(
        n=5,
        series=series_target_scaled,
        past_covariates=series_covar_scaled
    )
    prediction_final = scaler_target.inverse_transform(prediction_scaled)

    # 3. 실제 주가로 환산 (마지막 종가 기준)
    pred_return_values = prediction_final.univariate_values()
    last_close = df['Close'].iloc[-1]
    predicted_prices = []

    current_price = last_close
    for r in pred_return_values:
        # 로그 수익률 역산: 현재가 * exp(로그수익률)
        next_price = current_price * np.exp(r)
        predicted_prices.append(next_price)
        current_price = next_price

    # 4. 결과 데이터프레임 생성
    forecast_df = pd.DataFrame({
        'Time': prediction_final.time_index,
        'Predicted_Log_Return': pred_return_values.round(4),
        'Predicted_Close': np.array(predicted_prices).astype(int)
    })

    return forecast_df


def check_nans(series):
    # 1. 데이터프레임 변환 (시리즈인 경우 그대로 사용하거나 변환)
    df = series.to_dataframe()

    # 2. 각 컬럼별 NaN 개수 계산
    nans = df.isna().sum()

    # 3. NaN이 1개라도 있는 항목만 필터링
    nans_only = nans[nans > 0]
    total = nans_only.sum()

    # 4. 결측치가 있을 때만 출력
    if total > 0:
        # 인자를 콤마(,)로 구분하지 말고 f-string 하나로 합치세요
        logger.info(f"결측치 발견 항목:\n{nans_only}")
        logger.info(f"총 NaN 개수: {total}")

    # 5. 결측치가 없으면 True 반환 (학습 진행 가능)
    return total == 0
