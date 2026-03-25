import os
import logging
import pandas as pd
import pandas_ta_classic
import numpy as np
from dateutil.relativedelta import relativedelta

# 로거 가져오기
logger = logging.getLogger(__name__)


def load_data(file_path):
    # 데이터 읽어오기
    if not os.path.exists(file_path):
        logger.error(f"파일이 없습니다.({file_path})")
        return

    # 읽어올 컬럼 리스트 정의
    selected_cols = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume',
                     'SMA_5', 'SMA_20', 'SMA_60',
                     'RSI_14',
                     'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
                     'VWAP_D', 'OBV', 'ATRe_14']
    df = pd.read_parquet(file_path, columns=selected_cols)
    if df is None or df.empty:
        logger.error(f"데이터가 없습니다.({file_path})")
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
    # df_full['Change'] = df_full['Change'].fillna(0)

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
    check_nans(df_3y)

    # 데이터 프레임 리턴
    return df_3y


def add_stocks_indicators(df):
    # 이평계산
    df.ta.sma(length=5, append=True)
    # df.ta.sma(length=10, append=True)
    df.ta.sma(length=20, append=True)
    df.ta.sma(length=60, append=True)
    # df.ta.sma(length=120, append=True)
    # df.ta.sma(length=200, append=True)

    # 볼린져 밴드
    # df.ta.bbands(length=20, std=1.0, append=True)
    # df.ta.bbands(length=20, std=2.0, append=True)
    # df.ta.bbands(length=20, std=3.0, append=True)

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

    # # # 캔들패턴 분석
    # patterns_df = df.ta.cdl_pattern(name="all")
    # df['candle_pattern'] = patterns_df.apply(lambda x: ", ".join([c.replace('CDL_', '') for c in x[x != 0].index]), axis=1)
    #
    # # 두 신호가 동시에 뜨면 0으로 상쇄하거나 별도 처리하고 싶을 때
    # def combine_signals(x):
    #     has_bull = any(x > 0)
    #     has_bear = any(x < 0)
    #     if has_bull and has_bear:
    #         return 0  # 혹은 혼조세 신호로 정의
    #     if has_bull:
    #         return 1
    #     if has_bear:
    #         return -1
    #     return 0
    #
    # df['candle_signal'] = patterns_df.apply(combine_signals, axis=1)

    return df


def check_nans(df):
    # 각 컬럼별 NaN 개수 계산
    nans = df.isna().sum()
    # NaN이 1개라도 있는 컬럼만 필터링
    nans_only = nans[nans > 0]
    total = nans_only.sum()
    if total > 0:
        # 인자를 콤마(,)로 구분하지 말고 f-string 하나로 합치세요
        logger.info(f"결측치 발견 항목:\n{nans_only}")
        logger.info(f"총 NaN 개수: {total}")
    return total == 0
