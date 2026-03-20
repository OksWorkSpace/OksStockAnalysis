import os
import sys
import logging
from typing import cast
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd
import pickle
from darts import TimeSeries
from darts.models import ExponentialSmoothing
from darts.models import LightGBMModel
from darts.utils.missing_values import fill_missing_values
from darts.dataprocessing.transformers import Scaler
from darts.metrics import mape
from darts.models import TFTModel
from pytorch_lightning.callbacks.early_stopping import EarlyStopping
from darts.models import AutoARIMA
from darts.models import XGBModel
from darts.models import RegressionModel
from sklearn.ensemble import RandomForestRegressor
from darts.models import TiDEModel, DLinearModel
from darts.models import RegressionEnsembleModel
from sklearn.linear_model import Ridge
import matplotlib.pyplot as plt
import warnings


# 데이터 저장 폴더
DATA_DIR = "../data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

warnings.filterwarnings("ignore", message="X does not have valid feature names")


def analysis_ExponentialSmoothing(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 컬럼명을 맞추어 준다.
    df.reset_index()
    df.dropna()

    # Darts TimeSeries 객체로 변환 (시간 컬럼과 예측할 값 컬럼 지정)
    series = TimeSeries.from_dataframe(df, time_col='Time', value_cols='Close', fill_missing_dates=True, freq='D')

    # TimeSeries로 변환하면 주말데이터가 Nan이 나오므로 채워줘야 한다.
    # 전방 채우기 (Forward Fill) - 가장 추천
    # Darts 내장 함수로 결측치 채우기 (가장 최근값으로 채움)
    series = fill_missing_values(series)

    # 3. 데이터 분할 (학습용과 검증용)
    train, val = series.split_before(0.85)  # 앞의 85%를 학습용으로 사용

    # 통계 모델 (ExponentialSmoothing)
    model = ExponentialSmoothing()
    model.fit(train)
    prediction = model.predict(len(val))  # 검증 데이터 길이만큼 예측
    print(prediction.tail())

    # 머신러닝 모델 (LightGBM)
    model = LightGBMModel(lags=30)  # 과거 30일 데이터를 참고
    model.fit(train)
    prediction = model.predict(len(val))
    file_path = os.path.join(DATA_DIR, f"{ticker}_ExponentialSmoothing.csv")
    prediction.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(prediction.tail())


def find_BestModel_LightGBM(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 컬럼명을 맞추어 준다.
    df.reset_index()
    df.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df, time_col='Time', value_cols='Close', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD + BB)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_10', 'SMA_20', 'SMA_60', 'SMA_200',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    'BBU_20_2.0_2.0', 'BBL_20_2.0_2.0'  # 볼린저 밴드 상단/하단]
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

    # 4. 데이터 분할
    train_target, val_target = series_target_scaled.split_before(0.85)
    train_covar, val_covar = series_covar_scaled.split_before(0.85)

    # 1. 테스트하고 싶은 파라미터 후보군 정의 (딕셔너리 형태)
    parameters = {
        "lags": [20, 40, 60],  # 과거 1달, 2달, 3달치 중 무엇이 좋을까?
        "lags_past_covariates": [5, 10],  # 보조지표는 1주, 2주치 중 무엇이 좋을까?
        "output_chunk_length": [1, 5],  # 1일씩 예측 vs 5일 묶음 예측
        "learning_rate": [0.01, 0.1],  # 학습 속도 조절
        "n_estimators": [100, 500]  # 트리 개수
    }

    # 2. GridSearch 실행
    # series: 전체 데이터, past_covariates: 보조지표 데이터
    # start: 전체 데이터의 어느 지점(예: 0.8 = 80%)부터 검증을 시작할지 결정
    # last_points_only=False: 모든 시점에서 검증 수행 (더 정확하지만 느림)
    best_model, best_params, best_score = LightGBMModel.gridsearch(
        parameters=parameters,
        series=series_target_scaled,
        past_covariates=series_covar_scaled,
        forecast_horizon=5,  # 5일 뒤를 잘 맞추는 모델 찾기
        stride=5,  # 검증 시 이동 간격
        metric=mape,  # 오차 측정 기준 (MAPE가 낮을수록 좋음)
        start=0.8,  # 데이터의 뒤쪽 20%로 테스트
        verbose=True  # 진행 상황 출력
    )

    # 3. 결과 확인
    print(f"최적의 파라미터: {best_params}")
    print(f"최저 MAPE 오차: {best_score:.2f}%")

    # 4. 최적의 모델로 다시 전체 학습 후 예측
    final_model = LightGBMModel(**best_params)
    final_model.fit(series_target_scaled, past_covariates=series_covar_scaled)
    prediction_scaled = final_model.predict(n=5, series=series_target_scaled, past_covariates=series_covar_scaled)


# 모든 데이터를 넣고 학습 후 5일 주가 예측
def analysis_LightGBM(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 컬럼명을 맞추어 준다.
    df.reset_index()
    df.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df, time_col='Time', value_cols='Close', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
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

    # 4. 데이터 분할
    train_target, val_target = series_target_scaled.split_before(0.85)
    train_covar, val_covar = series_covar_scaled.split_before(0.85)

    # LightGBM 실전 권장 파라미터 (고정값)
    model = LightGBMModel(
        lags=30,  # 한 달치(영업일 기준) 데이터 참고
        lags_past_covariates=7,  # 보조지표는 최근 1주일 패턴이 중요
        output_chunk_length=5,  # 1일씩 차근차근 예측 (정밀도 우선)
        n_estimators=500,  # 너무 많으면 느리고 과적합됨, 500이 적당
        learning_rate=0.05,  # 0.1은 너무 빠르고 0.01은 너무 느림
        num_leaves=31,  # 기본값 유지 (트리 복잡도)
        max_depth=10,  # 너무 깊게 파지 않도록 제한
        random_state=42
    )

    # 학습 시 보조지표 함께 전달
    # model.fit(series=train_target, past_covariates=train_covar)
    model.fit(series=series_target_scaled, past_covariates=series_covar_scaled)

    # 예측 시에도 현재까지의 보조지표 데이터가 필요함
    # prediction_scaled = model.predict(n=5, series=train_target, past_covariates=train_covar)
    prediction_scaled = model.predict(n=5, series=series_target_scaled, past_covariates=series_covar_scaled)

    # [중요] 5. 원래 주가 단위로 복원
    prediction_final = scaler_target.inverse_transform(prediction_scaled)
    file_path = os.path.join(DATA_DIR, f"{ticker}_LightGBM.csv")
    prediction_final.to_csv(file_path, encoding='utf-8-sig')
    result_df = prediction_final.to_dataframe()
    print("\n🚀 analysis_LightGBM - 향후 5일 예측 결과:")
    print(result_df)

    # # 1. 데이터를 Pandas로 변환
    # df_actual = series_target.to_dataframe()
    # df_forecast = prediction_final.to_dataframe()
    #
    # # 2. 그래프 그리기
    # plt.figure(figsize=(12, 6))
    # plt.plot(df_actual.index[-50:], df_actual['Close'][-50:], label='Actual', marker='o')  # 최근 50일만
    # plt.plot(df_forecast.index, df_forecast['Close'], label='Forecast', marker='x', linestyle='--')
    #
    # plt.xlabel('Date')
    # plt.ylabel('Price')
    # plt.title('Samsung Electronics Prediction')
    # plt.grid(True)
    # plt.legend()
    # plt.show()


def training_LightGBM(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Close', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4. 데이터 분할
    # 데이터를 80%는 학습, 20%는 검증으로 나눔
    train_target, val_target = series_target_scaled.split_before(0.80)
    train_covar, val_covar = series_covar_scaled.split_before(0.80)

    # LightGBM 실전 권장 파라미터 (고정값)
    model = LightGBMModel(
        lags=30,  # 한 달치(영업일 기준) 데이터 참고
        lags_past_covariates=7,  # 보조지표는 최근 1주일 패턴이 중요
        output_chunk_length=5,  # 1일씩 차근차근 예측 (정밀도 우선)
        n_estimators=500,  # 너무 많으면 느리고 과적합됨, 500이 적당
        learning_rate=0.05,  # 0.1은 너무 빠르고 0.01은 너무 느림
        num_leaves=31,  # 기본값 유지 (트리 복잡도)
        max_depth=10,  # 너무 깊게 파지 않도록 제한
        random_state=42
    )

    # 학습하기
    model.fit(
        series=train_target,
        past_covariates=train_covar,
        val_series=val_target,
        val_past_covariates=val_covar,
        verbose=True
    )

    # 예측 하기
    prediction_scaled = model.predict(n=5, series=series_target_scaled, past_covariates=series_covar_scaled)
    prediction_final = scaler_target.inverse_transform(prediction_scaled)
    result_df = prediction_final.to_dataframe()
    print("\n🚀 training_LightGBM - 향후 5일 예측 결과:")
    print(result_df)

    # 모델 저장하기
    model_path = os.path.join(DATA_DIR, f"{ticker}_lgbm_model.pth")
    model.save(model_path)

    # 3. Scaler 저장 (이게 없으면 주가 복원이 불가능함)
    # Target용과 Covariate용 각각 저장
    with open(os.path.join(DATA_DIR, f"{ticker}_lgbm_target_scaler.pkl"), "wb") as f:
        pickle.dump(scaler_target, f)  # type: ignore

    with open(os.path.join(DATA_DIR, f"{ticker}_lgbm_covar_scaler.pkl"), "wb") as f:
        pickle.dump(scaler_covar, f)  # type: ignore

    print(f" LightGBM 모델과 스케일러가 저장되었습니다.")


def run_LightGBM(ticker):
    # 1. 저장된 모델 로드
    model_path = os.path.join(DATA_DIR, f"{ticker}_lgbm_model.pth")
    if not os.path.exists(model_path):
        print("저장된 모델 파일이 없습니다.")
        return

    loaded_model = cast(LightGBMModel, LightGBMModel.load(model_path))

    # 2. 저장된 스케일러 로드
    with open(os.path.join(DATA_DIR, f"{ticker}_lgbm_target_scaler.pkl"), "rb") as f:
        loaded_target_scaler = pickle.load(f)
    with open(os.path.join(DATA_DIR, f"{ticker}_lgbm_covar_scaler.pkl"), "rb") as f:
        loaded_covar_scaler = pickle.load(f)

    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Close', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 4. 불러온 스케일러로 최신 데이터 변환 (fit 없이 transform만!)
    target_scaled = loaded_target_scaler.transform(series_target)
    covar_scaled = loaded_covar_scaler.transform(series_covar)

    # 5. 예측 수행
    pred_scaled = loaded_model.predict(n=5, series=target_scaled, past_covariates=covar_scaled)

    # 6. 불러온 스케일러로 실제 주가 복원
    prediction_final = loaded_target_scaler.inverse_transform(pred_scaled)

    # 7. 결과 출력 (Pandas DataFrame)
    result_df = prediction_final.to_dataframe()
    print("\n🚀 run_LightGBM - 향후 5일 예측 결과:")
    print(result_df)


def analysis_TFTModel(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    print(f"데이터 범위: {df_3y['Time'].min()} ~ {df_3y['Time'].max()}")
    print(f"남은 데이터 개수: {len(df_3y)}")

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Close', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4. 데이터 분할
    # 데이터를 80%는 학습, 20%는 검증으로 나눔
    train_target, val_target = series_target_scaled.split_before(0.80)
    train_covar, val_covar = series_covar_scaled.split_before(0.80)

    # 1. EarlyStopping 설정 (과적합 방지)
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

    # 3. 학습 실행
    # TFT는 검증 데이터(val_series)를 넣어주는 것이 성능에 훨씬 좋습니다.
    # 성능 체크가 필요하면 학습과 검증 데이터를 반드시 분리하세요.
    # model_tft.fit(
    #     series=train_target,
    #     past_covariates=train_covar,
    #     val_series=val_target,
    #     val_past_covariates=val_covar,
    #     verbose=True
    # )
    # 실제 내일 주가 예측이 목적이면 전체 데이터로 학습하되, 검증셋은 비워두는 것이 정석입니다.
    model_tft.fit(
        series=series_target_scaled,  # 100% 데이터
        past_covariates=series_covar_scaled,
        verbose=True
        # val_series 인자를 아예 생략함
    )

    # 예측 시에도 현재까지의 보조지표 데이터가 필요함
    pred_tft = model_tft.predict(n=5, series=series_target_scaled, past_covariates=series_covar_scaled)
    pred_tft_final = scaler_target.inverse_transform(pred_tft)

    # [중요] 5. 원래 주가 단위로 복원
    file_path = os.path.join(DATA_DIR, f"{ticker}_TFTModel.csv")
    pred_tft_final.to_csv(file_path, encoding='utf-8-sig')
    print(pred_tft_final)


# 로그 등락률 사용
def analysis2_LightGBM(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 컬럼명을 맞추어 준다.
    df.reset_index()
    df.dropna()

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4. 데이터 분할
    train_target, val_target = series_target_scaled.split_before(0.85)
    train_covar, val_covar = series_covar_scaled.split_before(0.85)

    # LightGBM 실전 권장 파라미터 (고정값)
    model = LightGBMModel(
        lags=30,  # 한 달치(영업일 기준) 데이터 참고
        lags_past_covariates=7,  # 보조지표는 최근 1주일 패턴이 중요
        output_chunk_length=5,  # 1일씩 차근차근 예측 (정밀도 우선)
        n_estimators=500,  # 너무 많으면 느리고 과적합됨, 500이 적당
        learning_rate=0.05,  # 0.1은 너무 빠르고 0.01은 너무 느림
        num_leaves=31,  # 기본값 유지 (트리 복잡도)
        max_depth=10,  # 너무 깊게 파지 않도록 제한
        random_state=42
    )

    # 학습 시 보조지표 함께 전달
    # model.fit(series=train_target, past_covariates=train_covar)
    model.fit(series=series_target_scaled, past_covariates=series_covar_scaled)

    # 예측 시에도 현재까지의 보조지표 데이터가 필요함
    # prediction_scaled = model.predict(n=5, series=train_target, past_covariates=train_covar)
    prediction_scaled = model.predict(n=5, series=series_target_scaled, past_covariates=series_covar_scaled)
    prediction_final = scaler_target.inverse_transform(prediction_scaled)

    # 3. 실제 주가로 환산 (마지막 종가 기준)
    pred_return_values = prediction_final.univariate_values()  # numpy 배열로 추출
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


# 보조지표 추가
def analysis3_LightGBM(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 컬럼명을 맞추어 준다.
    df.reset_index()
    df.dropna()

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    'VWAP_D', 'OBV', 'ATRe_14'
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4. 데이터 분할
    train_target, val_target = series_target_scaled.split_before(0.85)
    train_covar, val_covar = series_covar_scaled.split_before(0.85)

    # LightGBM 실전 권장 파라미터 (고정값)
    model = LightGBMModel(
        lags=30,  # 한 달치(영업일 기준) 데이터 참고
        lags_past_covariates=7,  # 보조지표는 최근 1주일 패턴이 중요
        output_chunk_length=5,  # 1일씩 차근차근 예측 (정밀도 우선)
        n_estimators=500,  # 너무 많으면 느리고 과적합됨, 500이 적당
        learning_rate=0.05,  # 0.1은 너무 빠르고 0.01은 너무 느림
        num_leaves=31,  # 기본값 유지 (트리 복잡도)
        max_depth=10,  # 너무 깊게 파지 않도록 제한
        random_state=42
    )

    # 학습 시 보조지표 함께 전달
    # model.fit(series=train_target, past_covariates=train_covar)
    model.fit(series=series_target_scaled, past_covariates=series_covar_scaled)

    # 예측 시에도 현재까지의 보조지표 데이터가 필요함
    # prediction_scaled = model.predict(n=5, series=train_target, past_covariates=train_covar)
    prediction_scaled = model.predict(n=5, series=series_target_scaled, past_covariates=series_covar_scaled)
    prediction_final = scaler_target.inverse_transform(prediction_scaled)

    # 3. 실제 주가로 환산 (마지막 종가 기준)
    pred_return_values = prediction_final.univariate_values()  # numpy 배열로 추출
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


# 로그 등락률 사용
def analysis_OHLC_LightGBM(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 1. 로그 수익률 계산 (상대적 변환)
    # 종가: 전일 종가 대비 수익률
    df['Close_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
    # 시가: 전일 종가 대비 시가 수익률 (갭상승/하락 포착)
    df['Open_Ret'] = np.log(df['Open'] / df['Close'].shift(1))
    # 고가: 당일 시가 대비 고가 수익률 (장중 상승폭)
    df['High_Ret'] = np.log(df['High'] / df['Open'])
    # 저가: 당일 시가 대비 저가 수익률 (장중 하락폭)
    df['Low_Ret'] = np.log(df['Low'] / df['Open'])

    # 컬럼명을 맞추어 준다.
    df.reset_index()
    df.dropna()

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    # 2. 다변량 타겟 데이터셋 생성 (Target)
    target_cols = ['Open_Ret', 'High_Ret', 'Low_Ret', 'Close_Ret']
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=target_cols, freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4. 데이터 분할
    train_target, val_target = series_target_scaled.split_before(0.85)
    train_covar, val_covar = series_covar_scaled.split_before(0.85)

    # LightGBM 실전 권장 파라미터 (고정값)
    model = LightGBMModel(
        lags=30,  # 한 달치(영업일 기준) 데이터 참고
        lags_past_covariates=7,  # 보조지표는 최근 1주일 패턴이 중요
        output_chunk_length=5,  # 1일씩 차근차근 예측 (정밀도 우선)
        n_estimators=500,  # 너무 많으면 느리고 과적합됨, 500이 적당
        learning_rate=0.05,  # 0.1은 너무 빠르고 0.01은 너무 느림
        num_leaves=31,  # 기본값 유지 (트리 복잡도)
        max_depth=10,  # 너무 깊게 파지 않도록 제한
        random_state=42
    )

    # 학습 시 보조지표 함께 전달
    model.fit(series=series_target_scaled, past_covariates=series_covar_scaled)

    # 예측 시에도 현재까지의 보조지표 데이터가 필요함
    prediction_scaled = model.predict(n=5, series=series_target_scaled, past_covariates=series_covar_scaled)
    prediction_final = scaler_target.inverse_transform(prediction_scaled)

    # 6. 실제 주가 환산 (마지막 영업일 가격 기준 누적 곱)
    last_prices = df_3y[['Open', 'High', 'Low', 'Close']].iloc[-1].values  # 마지막 [Open, High, Low, Close]
    pred_ret_values = prediction_final.values()  # (5, 4) 형태의 numpy 배열

    predicted_ohlc = []
    current_prices = last_prices

    for ret_row in pred_ret_values:
        # 각 컬럼별로 exp(로그수익률) 적용
        next_prices = current_prices * np.exp(ret_row)
        predicted_ohlc.append(next_prices)
        current_prices = next_prices

    # 1. 보정된 결과를 담을 리스트
    corrected_ohlc = []

    # 2. 각 날짜별 예측 행(Open, High, Low, Close) 순회
    for row in predicted_ohlc:
        o, h, l, c = row

        # [규칙 1] 고가(High)는 당일 모든 가격 중 가장 높아야 함
        h_corrected = max(o, h, l, c)

        # [규칙 2] 저가(Low)는 당일 모든 가격 중 가장 낮아야 함
        l_corrected = min(o, h, l, c)

        # [규칙 3] 시가와 종가는 고가와 저가 사이에 위치해야 함
        # (이미 위에서 h/l을 max/min으로 잡았으므로 자동 만족되지만 명시적 확인)
        o_corrected = np.clip(o, l_corrected, h_corrected)
        c_corrected = np.clip(c, l_corrected, h_corrected)

        corrected_ohlc.append([o_corrected, h_corrected, l_corrected, c_corrected])

    # 3. 보정된 데이터로 데이터프레임 생성
    forecast_df = pd.DataFrame(
        corrected_ohlc,
        columns=['Open', 'High', 'Low', 'Close'],
        index=prediction_final.time_index
    ).round(0).astype(int)

    print("=== 보정된 향후 5일 OHLC 예측 결과 ===")
    print(forecast_df)


def analysis2_TFTModel(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    print(f"데이터 범위: {df_3y['Time'].min()} ~ {df_3y['Time'].max()}")
    print(f"남은 데이터 개수: {len(df_3y)}")

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4. 데이터 분할
    # 데이터를 80%는 학습, 20%는 검증으로 나눔
    train_target, val_target = series_target_scaled.split_before(0.80)
    train_covar, val_covar = series_covar_scaled.split_before(0.80)

    # 1. EarlyStopping 설정 (과적합 방지)
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

    # 3. 학습 실행
    # TFT는 검증 데이터(val_series)를 넣어주는 것이 성능에 훨씬 좋습니다.
    # 성능 체크가 필요하면 학습과 검증 데이터를 반드시 분리하세요.
    # model_tft.fit(
    #     series=train_target,
    #     past_covariates=train_covar,
    #     val_series=val_target,
    #     val_past_covariates=val_covar,
    #     verbose=True
    # )
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
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


def analysis_ARIMA(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    print(f"데이터 범위: {df_3y['Time'].min()} ~ {df_3y['Time'].max()}")
    print(f"남은 데이터 개수: {len(df_3y)}")

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 2. AutoARIMA 모델 학습 및 예측
    # AutoARIMA는 최적의 p, d, q 값을 자동으로 탐색합니다.
    model = AutoARIMA()
    # 이 모델은 future_covariates만 지원하므로 과거 보조지표는 못씀
    # 보조지표 데이터를 강제로 넣어주어야 해서 안쓰는게 좋을 듯
    # model.fit(series_target_scaled, future_covariates=series_covar_scaled)
    model.fit(series_target_scaled)

    # 향후 5일 예측
    prediction_scaled = model.predict(n=5)
    prediction_final = scaler_target.inverse_transform(prediction_scaled)

    # 3. 실제 주가로 환산 (마지막 종가 기준)
    pred_return_values = prediction_final.univariate_values()
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


def analysis_XGBModel(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    print(f"데이터 범위: {df_3y['Time'].min()} ~ {df_3y['Time'].max()}")
    print(f"남은 데이터 개수: {len(df_3y)}")

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
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
    model = RegressionModel(
        model=RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42),
        lags=20,  # 과거 수익률 20일치 참고
        lags_past_covariates=12  # 과거 보조지표 12일치 참고
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
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


def analysis_RegressionModel(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    print(f"데이터 범위: {df_3y['Time'].min()} ~ {df_3y['Time'].max()}")
    print(f"남은 데이터 개수: {len(df_3y)}")

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4. XGBModel 정의 및 학습
    # lags: 타겟의 과거 관측치 사용량
    # lags_past_covariates: 보조지표의 과거 관측치 사용량
    model = XGBModel(
        lags=20,
        lags_past_covariates=12,
        output_chunk_length=5,
        n_estimators=100,
        max_depth=6
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
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


def analysis_TiDEModel(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    print(f"데이터 범위: {df_3y['Time'].min()} ~ {df_3y['Time'].max()}")
    print(f"남은 데이터 개수: {len(df_3y)}")

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4-1. TiDEModel 정의 (MLP 기반의 최신 고성능 모델)
    model = TiDEModel(
        input_chunk_length=20,  # 과거 20일 데이터 입력
        output_chunk_length=5,  # 미래 5일 예측
        num_encoder_layers=2,
        num_decoder_layers=2,
        n_epochs=50,  # 데이터 양에 따라 조절
        random_state=42
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
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


def analysis_DLinearModel(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    print(f"데이터 범위: {df_3y['Time'].min()} ~ {df_3y['Time'].max()}")
    print(f"남은 데이터 개수: {len(df_3y)}")

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 4-2. DLinearModel 정의 (시계열을 트렌드/잔차로 분해하여 학습)
    model = DLinearModel(
        input_chunk_length=20,
        output_chunk_length=5,
        n_epochs=50,
        random_state=42
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
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


def analysis_RegressionEnsembleModel(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 로그 등락률 계산 (전날 대비 몇 % 변동했는지)
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df['Time'] = pd.to_datetime(df['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df[df['Time'] >= three_years_ago].copy()

    print(f"데이터 범위: {df_3y['Time'].min()} ~ {df_3y['Time'].max()}")
    print(f"남은 데이터 개수: {len(df_3y)}")

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y.dropna()

    # 예측 대상 (종가)
    series_target = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols='Log_Return', freq='D')
    series_target = fill_missing_values(series_target)
    check_nans(series_target)

    # 보조지표 묶음 (거래량 + MA + RSI + MACD)
    feature_cols = ['Volume',
                    'SMA_5', 'SMA_20', 'SMA_60',
                    'RSI_14',
                    'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
                    ]
    series_covar = TimeSeries.from_dataframe(df_3y, time_col='Time', value_cols=feature_cols, freq='D')
    series_covar = fill_missing_values(series_covar)
    check_nans(series_covar)

    # 3. Scaler 적용 (0~1 사이 값으로 정규화)
    # 주가와 거래량은 단위가 완전히 다르므로 각각 스케일링하는 것이 성능에 좋습니다.
    scaler_target = Scaler()
    scaler_covar = Scaler()

    series_target_scaled = scaler_target.fit_transform(series_target)
    series_covar_scaled = scaler_covar.fit_transform(series_covar)

    # 3. 개별 모델(Base Models) 정의
    # 타겟 과거 20일, 보조지표 과거 12일을 참고하여 미래 5일을 예측하도록 통일
    input_len = 20
    output_len = 5

    model_tide = TiDEModel(
        input_chunk_length=input_len, output_chunk_length=output_len,
        n_epochs=50, random_state=42
    )
    model_dlinear = DLinearModel(
        input_chunk_length=input_len, output_chunk_length=output_len,
        n_epochs=50, random_state=42
    )
    model_lgbm = LightGBMModel(
        lags=input_len, lags_past_covariates=12,
        output_chunk_length=output_len, random_state=42
    )

    # 4. 앙상블 모델 정의 (최종 결합: Ridge 회귀)
    # 3년치 데이터 기준, 앙상블 학습용으로 150 포인트를 할당
    ensemble_model = RegressionEnsembleModel(
        forecasting_models=[model_tide, model_dlinear, model_lgbm],
        regression_train_n_points=150,
        regression_model=Ridge(alpha=1.0)
    )

    # 5. 통합 학습 및 예측
    # 모든 모델이 past_covariates를 지원하므로 함께 전달
    ensemble_model.fit(series_target_scaled, past_covariates=series_covar_scaled)

    prediction_scaled = ensemble_model.predict(
        n=output_len,
        series=series_target_scaled,
        past_covariates=series_covar_scaled
    )
    prediction_final = scaler_target.inverse_transform(prediction_scaled)

    # 3. 실제 주가로 환산 (마지막 종가 기준)
    pred_return_values = prediction_final.univariate_values()
    last_close = df_3y['Close'].iloc[-1]
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

    print("🚀 향후 5일 주가 예측 리포트")
    print(forecast_df.to_string(index=False))


def check_nans(series):
    df = series.to_dataframe()
    nans = df.isna().sum()
    total = nans.sum()
    print("컬럼별 NaN:", nans)
    print(f"총 NaN: {total}")
    return total == 0


def main():
    # analysis_ExponentialSmoothing("005930")
    # analysis_LightGBM("005930")
    # training_LightGBM("005930")
    # run_LightGBM("005930")
    # analysis_TFTModel("005930")
    # analysis2_LightGBM("005930")
    # analysis2_TFTModel("005930")
    # analysis_ARIMA("005930")
    # analysis_XGBModel("005930")
    # analysis_RegressionModel("005930")
    # analysis_TiDEModel("005930")
    # analysis_DLinearModel("005930")
    # analysis_RegressionEnsembleModel("005930")
    # 다변량 예측하기(OHLC)
    # analysis_OHLC_LightGBM("005930")
    # 보조지표 추가
    analysis3_LightGBM("005930")

