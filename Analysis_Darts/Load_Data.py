import os
import logging
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd

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

    # 데이터 리턴
    return df_3y
