import os
import logging
import pandas as pd
import pandas_ta_classic
import numpy as np
from dateutil.relativedelta import relativedelta
from neuralprophet import NeuralProphet

# 데이터 저장 폴더
DATA_DIR = "../data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 로거 가져오기
logger = logging.getLogger(__name__)


def analysis_neuralprophet(ticker):
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

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y = df_3y.rename(columns={'Time': 'ds', 'Close': 'y'})

    # [중요] NeuralProphet이 허용하지 않는 'index' 또는 불필요한 컬럼 삭제
    if 'index' in df_3y.columns:
        df_3y = df_3y.drop(columns=['index'])
    df_3y = df_3y.dropna()

    # 모델 설정 및 학습
    # n_forecasts: 예측할 기간, n_lags: 과거 몇 일 데이터를 참고할지 (자기회귀 설정)
    model = NeuralProphet(
        # 주기성 설정
        yearly_seasonality=True,  # 연간 패턴 학습 (3년치이므로 효과적)
        weekly_seasonality=True,  # 요일별 패턴 학습
        daily_seasonality=False,  # 일간(시간단위)은 주식 데이터에 불필요

        # 트렌드 및 변화점 설정
        n_changepoints=30,  # 변화 지점을 충분히 확보
        changepoints_range=0.9,  # 최근 10% 구간까지 트렌드 변화 감지
        trend_reg=0.5,  # 너무 급격한 트렌드 변화 억제 (과적합 방지)

        # AR 모델 설정 (과거 데이터를 얼마나 볼 것인가)
        n_lags=20,  # 과거 20일치 데이터를 학습에 사용
        ar_layers=[64, 64],  # 비선형 패턴 학습을 위한 은닉층 구성

        n_forecasts=5,  # 5일 예측

        # 학습 관련
        epochs=100,  # 반복 학습 횟수
        learning_rate=0.03  # 학습률

        # epochs=200,  # 충분한 학습
        # learning_rate=0.03,  # 빠른 수렴
        # batch_size=64,  # 메모리 효율
        # n_lags=30,  # 30일 과거 패턴
        # n_forecasts=5,  # 5일 예측
        # yearly_seasonality=True,
        # weekly_seasonality=True
    )
    model.add_country_holidays(country_name='KR')  # 한국 공휴일 기준

    lagged_regressors = [
        'Volume',
        'SMA_5', 'SMA_10', 'SMA_20', 'SMA_60', 'SMA_200',
        'RSI_14',
        'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
        'BBU_20_2.0', 'BBL_20_2.0'  # 볼린저 밴드 상단/하단
    ]

    # 모델 학습 시 필요한 컬럼만 필터링 (가장 확실한 방법)
    # ds, y 그리고 등록한 lagged_regressors 리스트에 있는 컬럼만 남깁니다.
    final_cols = ['ds', 'y'] + lagged_regressors
    df_3y = df_3y[final_cols]

    # 기술적 지표 컬럼들 등록
    for regressor in lagged_regressors:
        model.add_lagged_regressor(names=regressor)

    # 학습 실행 (epochs 조절을 통해 과적합 방지)
    metrics = model.fit(df_3y, freq='D')

    # 3. 미래 예측
    future = model.make_future_dataframe(df_3y, periods=5, n_historic_predictions=len(df_3y))
    forecast = model.predict(future)
    file_path = os.path.join(DATA_DIR, f"{ticker}_neuralprophet.csv")
    forecast.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(forecast[['ds', 'y', 'yhat1']].tail())

    # 4. 결과 시각화
    # fig_forecast = model.plot(forecast)
    # fig_components = model.plot_components(forecast)  # 추세, 계절성 분석
    # fig_forecast = model.plot(forecast, plotting_backend='matplotlib')
    # fig_components = model.plot_components(forecast, plotting_backend='matplotlib')

    # plt.title("Stock Price Forecast")  # 그래프 제목 추가 가능

    # 3. 화면에 출력 (이 함수를 호출해야 팝업 창이 뜹니다)
    # plt.show()


def analysis2_neuralprophet(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 1. 날짜 인덱스 생성 (시작일부터 종료일까지 빠짐없이)
    all_dates = pd.date_range(start=df['Time'].min(), end=df['Time'].max(), freq='D')
    df_full = df.set_index('Time').reindex(all_dates)

    # 1. 일단 종가(Close)만 먼저 ffill로 채웁니다.
    df_full['Close'] = df_full['Close'].ffill()

    # 2. 나머지 가격(시/고/저)의 빈칸(NaN)을 채워진 '종가' 값으로 똑같이 복사합니다.
    # fillna를 사용하면 NaN인 부분만 Close 값으로 채워집니다.
    df_full['Open'] = df_full['Open'].fillna(df_full['Close'])
    df_full['High'] = df_full['High'].fillna(df_full['Close'])
    df_full['Low'] = df_full['Low'].fillna(df_full['Close'])

    # 3. 거래량은 반드시 0으로 채웁니다.
    df_full['Volume'] = df_full['Volume'].fillna(0)
    df_full['Rate'] = df_full['Rate'].fillna(0)

    # 지표 새로 계산
    df_full = add_stocks_indicators(df_full)

    # VWAP_D는 거래량 가중 평균 가격 이므로 직전 값으로 채운다.
    df_full['VWAP_D'] = df_full['VWAP_D'].ffill()

    # 4. 인덱스 초기화 (필요시)
    df_full = df_full.reset_index().rename(columns={'index': 'Time'})

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df_full['Time'] = pd.to_datetime(df_full['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df_full['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df_full[df_full['Time'] >= three_years_ago].copy()

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y = df_3y.rename(columns={'Time': 'ds', 'Close': 'y'})

    # [중요] NeuralProphet이 허용하지 않는 'index' 또는 불필요한 컬럼 삭제
    # if 'index' in df_3y.columns:
    #     df_3y = df_3y.drop(columns=['index'])
    # df_3y = df_3y.dropna()

    # 모델 설정 및 학습
    # n_forecasts: 예측할 기간, n_lags: 과거 몇 일 데이터를 참고할지 (자기회귀 설정)
    model = NeuralProphet(
        # 주기성 설정
        yearly_seasonality=True,  # 연간 패턴 학습 (3년치이므로 효과적)
        weekly_seasonality=True,  # 요일별 패턴 학습
        daily_seasonality=False,  # 일간(시간단위)은 주식 데이터에 불필요

        # 트렌드 및 변화점 설정
        n_changepoints=30,  # 변화 지점을 충분히 확보
        changepoints_range=0.9,  # 최근 10% 구간까지 트렌드 변화 감지
        trend_reg=0.5,  # 너무 급격한 트렌드 변화 억제 (과적합 방지)

        # AR 모델 설정 (과거 데이터를 얼마나 볼 것인가)
        n_lags=24,  # 과거 20일치 데이터를 학습에 사용
        ar_layers=[64, 64],  # 비선형 패턴 학습을 위한 은닉층 구성

        quantiles=[0.1, 0.9],  # 10%~90% = 80% 신뢰구간 (필수!)

        n_forecasts=5,  # 5일 예측

        # 학습 관련
        epochs=100,  # 반복 학습 횟수
        learning_rate=0.03  # 학습률

        # epochs=200,  # 충분한 학습
        # learning_rate=0.03,  # 빠른 수렴
        # batch_size=64,  # 메모리 효율
        # n_lags=30,  # 30일 과거 패턴
        # n_forecasts=5,  # 5일 예측
        # yearly_seasonality=True,
        # weekly_seasonality=True
    )
    model.add_country_holidays(country_name='KR')  # 한국 공휴일 기준

    lagged_regressors = [
        'Volume',
        'SMA_5', 'SMA_20', 'SMA_60', 'SMA_200',
        'RSI_14',
        'MACD_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
        'BBU_20_2.0', 'BBL_20_2.0'  # 볼린저 밴드 상단/하단
    ]

    # 모델 학습 시 필요한 컬럼만 필터링 (가장 확실한 방법)
    # ds, y 그리고 등록한 lagged_regressors 리스트에 있는 컬럼만 남깁니다.
    final_cols = ['ds', 'y'] + lagged_regressors
    df_3y = df_3y[final_cols]

    # 기술적 지표 컬럼들 등록
    for regressor in lagged_regressors:
        model.add_lagged_regressor(names=regressor)

    # 학습 실행 (epochs 조절을 통해 과적합 방지)
    metrics = model.fit(df_3y, freq='D')

    # 3. 미래 예측
    future = model.make_future_dataframe(df_3y, periods=5, n_historic_predictions=len(df_3y))
    forecast = model.predict(future)

    # 각 날짜의 "1일 후 예측값"만 모으기 (가장 정확)
    future_forecast = forecast[forecast['y'].isna()]  # 미래 데이터만

    # 각 행의 yhat1 값을 가져오기
    predicted_prices = [future_forecast['yhat1'].iloc[0], future_forecast['yhat2'].iloc[0],
                        future_forecast['yhat3'].iloc[0], future_forecast['yhat4'].iloc[0],
                        future_forecast['yhat5'].iloc[0]]

    # 예측 날짜 생성 (첫 미래 날짜부터 5일)
    first_future_date = future_forecast['ds'].iloc[0]
    pred_dates = pd.date_range(start=first_future_date, periods=5, freq='D')

    # 깔끔한 DataFrame 생성
    result_df = pd.DataFrame({
        'Time': pred_dates,
        'yhat1': [round(x, 0) for x in predicted_prices]
    })

    print("=== 미래 5일 예측 결과 ===")
    print(result_df.to_string(index=False))

    # file_path = os.path.join(DATA_DIR, f"{ticker}_neuralprophet.csv")
    # forecast.to_csv(file_path, index=False, encoding='utf-8-sig')
    # print(forecast[['ds', 'y', 'yhat1']].tail())

    # 4. 결과 시각화
    # fig_forecast = model.plot(forecast)
    # fig_components = model.plot_components(forecast)  # 추세, 계절성 분석
    # fig_forecast = model.plot(forecast, plotting_backend='matplotlib')
    # fig_components = model.plot_components(forecast, plotting_backend='matplotlib')

    # plt.title("Stock Price Forecast")  # 그래프 제목 추가 가능

    # 3. 화면에 출력 (이 함수를 호출해야 팝업 창이 뜹니다)
    # plt.show()


def analysis3_neuralprophet(ticker):
    # 데이터 읽어오기
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    df = pd.read_parquet(file_path)
    if df is None or df.empty:
        print(f"{ticker} 데이터가 없습니다.")
        return

    # 1. 날짜 인덱스 생성 (시작일부터 종료일까지 빠짐없이)
    all_dates = pd.date_range(start=df['Time'].min(), end=df['Time'].max(), freq='D')
    df_full = df.set_index('Time').reindex(all_dates)

    # 1. 일단 종가(Close)만 먼저 ffill로 채웁니다.
    df_full['Close'] = df_full['Close'].ffill()

    # 2. 나머지 가격(시/고/저)의 빈칸(NaN)을 채워진 '종가' 값으로 똑같이 복사합니다.
    # fillna를 사용하면 NaN인 부분만 Close 값으로 채워집니다.
    df_full['Open'] = df_full['Open'].fillna(df_full['Close'])
    df_full['High'] = df_full['High'].fillna(df_full['Close'])
    df_full['Low'] = df_full['Low'].fillna(df_full['Close'])

    # 3. 거래량은 반드시 0으로 채웁니다.
    df_full['Volume'] = df_full['Volume'].fillna(0)
    df_full['Rate'] = df_full['Rate'].fillna(0)

    # 지표 새로 계산
    df_full = add_stocks_indicators(df_full)

    # VWAP_D는 거래량 가중 평균 가격 이므로 직전 값으로 채운다.
    # 거래량이 0이면 zero 나누기이므로 계산이 안됨.
    df_full['VWAP_D'] = df_full['VWAP_D'].ffill()

    # 로그 등락률 계산 (Log Return)
    # 공식: log(현재가 / 이전가)
    df_full['Log_Return'] = np.log(df_full['Close'] / df_full['Close'].shift(1))

    # 4. 인덱스 초기화 (필요시)
    df_full = df_full.reset_index().rename(columns={'index': 'Time'})

    # 마지막 데이터의 이전 3년치 데이터만 학습에 사용한다.
    df_full['Time'] = pd.to_datetime(df_full['Time'])

    # 데이터의 마지막 날짜 확인
    last_date = df_full['Time'].max()

    # 3년 전 날짜 계산 (정확한 년 단위 계산을 위해 relativedelta 사용)
    three_years_ago = last_date - relativedelta(years=3)

    # 필터링 (최근 3년치만 남기기)
    df_3y = df_full[df_full['Time'] >= three_years_ago].copy()

    # 컬럼명을 맞추어 준다.
    df_3y.reset_index()
    df_3y = df_3y.rename(columns={'Time': 'ds', 'Log_Return': 'y'})

    # # [중요] NeuralProphet이 허용하지 않는 'index' 또는 불필요한 컬럼 삭제
    # if 'index' in df_3y.columns:
    #     df_3y = df_3y.drop(columns=['index'])
    # df_3y = df_3y.dropna()  # 여기서 0으로 채운 데이터가 날라감.

    # 모델 설정 및 학습
    # n_forecasts: 예측할 기간, n_lags: 과거 몇 일 데이터를 참고할지 (자기회귀 설정)
    model = NeuralProphet(
        # 주기성 설정
        yearly_seasonality=True,  # 연간 패턴 학습 (3년치이므로 효과적)
        weekly_seasonality=True,  # 요일별 패턴 학습
        daily_seasonality=False,  # 일간(시간단위)은 주식 데이터에 불필요

        # 트렌드 및 변화점 설정
        n_changepoints=30,  # 변화 지점을 충분히 확보
        changepoints_range=0.9,  # 최근 10% 구간까지 트렌드 변화 감지
        trend_reg=0.5,  # 너무 급격한 트렌드 변화 억제 (과적합 방지)

        # AR 모델 설정 (과거 데이터를 얼마나 볼 것인가)
        n_lags=24,  # 과거 20일치 데이터를 학습에 사용
        ar_layers=[64, 64],  # 비선형 패턴 학습을 위한 은닉층 구성

        quantiles=[0.1, 0.9],  # 10%~90% = 80% 신뢰구간 (필수!)

        n_forecasts=5,  # 5일 예측

        # 학습 관련
        epochs=100,  # 반복 학습 횟수
        learning_rate=0.03  # 학습률

        # epochs=200,  # 충분한 학습
        # learning_rate=0.03,  # 빠른 수렴
        # batch_size=64,  # 메모리 효율
        # n_lags=30,  # 30일 과거 패턴
        # n_forecasts=5,  # 5일 예측
        # yearly_seasonality=True,
        # weekly_seasonality=True
    )
    # model.add_country_holidays(country_name='KR')  # 한국 공휴일 기준

    lagged_regressors = [
        'Volume',
        'SMA_5', 'SMA_20', 'SMA_60',
        'RSI_14',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',  # MACD 선과 시그널 선
        'VWAP_D', 'OBV', 'ATRe_14'
    ]

    # 모델 학습 시 필요한 컬럼만 필터링 (가장 확실한 방법)
    # ds, y 그리고 등록한 lagged_regressors 리스트에 있는 컬럼만 남깁니다.
    final_cols = ['ds', 'y'] + lagged_regressors
    df_3y = df_3y[final_cols]
    check_nans(df_3y)

    # 기술적 지표 컬럼들 등록
    for regressor in lagged_regressors:
        model.add_lagged_regressor(names=regressor)

    # 학습 실행 (epochs 조절을 통해 과적합 방지)
    metrics = model.fit(df_3y, freq='D')

    # 3. 미래 예측
    future = model.make_future_dataframe(df_3y, periods=5, n_historic_predictions=True)
    forecast = model.predict(future)

    # 각 날짜의 "1일 후 예측값"만 모으기 (가장 정확)
    future_forecast = forecast[forecast['y'].isna()]  # 미래 데이터만

    # 각 행의 yhat 값을 가져오기
    predicted_log_returns = [future_forecast['yhat1'].iloc[0], future_forecast['yhat2'].iloc[0],
                             future_forecast['yhat3'].iloc[0], future_forecast['yhat4'].iloc[0],
                             future_forecast['yhat5'].iloc[0]]

    # 실제 주가로 환산 루프
    predicted_prices = []
    current_price = df['Close'].iloc[-1]

    for log_r in predicted_log_returns:
        # 역산 공식: 현재가 * exp(로그수익률)
        next_price = current_price * np.exp(log_r)
        predicted_prices.append(next_price)
        current_price = next_price  # 다음 날 예측을 위해 갱신

    # 4. 결과 데이터프레임 생성
    forecast_df = pd.DataFrame({
        'Time': future_forecast['ds'],
        'Predicted_Log_Return': [round(x, 4) for x in predicted_log_returns],
        'Predicted_Close': np.array(predicted_prices).astype(int)
    })

    print("=== 미래 5일 예측 결과 ===")
    print(forecast_df.to_string(index=False))

    # file_path = os.path.join(DATA_DIR, f"{ticker}_neuralprophet.csv")
    # forecast.to_csv(file_path, index=False, encoding='utf-8-sig')
    # print(forecast[['ds', 'y', 'yhat1']].tail())

    # 4. 결과 시각화
    # fig_forecast = model.plot(forecast)
    # fig_components = model.plot_components(forecast)  # 추세, 계절성 분석
    # fig_forecast = model.plot(forecast, plotting_backend='matplotlib')
    # fig_components = model.plot_components(forecast, plotting_backend='matplotlib')

    # plt.title("Stock Price Forecast")  # 그래프 제목 추가 가능

    # 3. 화면에 출력 (이 함수를 호출해야 팝업 창이 뜹니다)
    # plt.show()


def add_stocks_indicators(df):
    # 이평계산
    df.ta.sma(length=5, append=True)
    df.ta.sma(length=10, append=True)
    df.ta.sma(length=20, append=True)
    df.ta.sma(length=60, append=True)
    df.ta.sma(length=200, append=True)

    # 볼린져 밴드
    df.ta.bbands(length=20, std=1.0, closed=True, append=True)
    df.ta.bbands(length=20, std=2.0, closed=True, append=True)
    df.ta.bbands(length=20, std=3.0, closed=True, append=True)

    # RSI
    df.ta.rsi(length=14, append=True)

    # MACD
    df.ta.macd(close="Close", fast=12, slow=26, signal=9, append=True)

    # VWAP(Volume Weighted Average Price, 거래량 가중 평균 가격)
    # 기관/대형 투자자들이 실제로 얼마에 매수했는지를 보여줌
    df.ta.vwap(append=True)

    # OBV(On Balance Volume)
    # 거래량의 누적 흐름을 통해 수급의 신뢰도를 판단
    df.ta.obv(append=True)

    # ATR 계산 (기본 length=14, SMA 기반)
    df.ta.atr(length=14,  # 기본 14, 기간 조정 가능
              mamode="ema",  # 기본 "rma"일 수 있음, 필요시 "sma" 또는 "ema" 지정
              append=True  # 기존 df에 ATR 컬럼 추가
              )

    # 캔들패턴 분석
    patterns_df = df.ta.cdl_pattern(name="all")
    df['candle_pattern'] = patterns_df.apply(lambda x: ", ".join([c.replace('CDL_', '') for c in x[x != 0].index]), axis=1)

    # 두 신호가 동시에 뜨면 0으로 상쇄하거나 별도 처리하고 싶을 때
    def combine_signals(x):
        has_bull = any(x > 0)
        has_bear = any(x < 0)
        if has_bull and has_bear:
            return 0  # 혹은 혼조세 신호로 정의
        if has_bull:
            return 1
        if has_bear:
            return -1
        return 0

    df['candle_signal'] = patterns_df.apply(combine_signals, axis=1)

    return df


def check_nans(df):
    nans = df.isna().sum()
    total = nans.sum()
    print("컬럼별 NaN:", nans)
    print(f"총 NaN: {total}")
    return total == 0
