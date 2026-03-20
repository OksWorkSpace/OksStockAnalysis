import os
from datetime import datetime
import FinanceDataReader as fdr
import pandas as pd
import pandas_ta_classic
from dateutil.relativedelta import relativedelta
from settings import settings


# 전체 증시 상황을 가져온다.
# market : KRX(코스피), KOSDAQ(코스닥)
def fdr_stocklist():
    # 상세 업종 정보 (Code, Sector, Industry 포함)
    df_desc = fdr.StockListing('KRX-DESC')
    df_desc = df_desc.drop(columns=['Unnamed: 0'], errors='ignore')
    # 기본 시세 정보 (Code, Name, Price 등)
    df_krx = fdr.StockListing('KRX')
    # 'Unnamed: 0' 컬럼이 있다면 삭제 (errors='ignore'로 설정하면 컬럼이 없어도 에러 안 남)
    df_krx = df_krx.drop(columns=['Unnamed: 0'], errors='ignore')
    print(df_krx.columns)
    # 'Code' 컬럼을 기준으로 합치기 (왼쪽 df_krx 기준)
    # 필요한 컬럼만 선택해서 합치는 것이 메모리 관리에 효율적입니다.
    df = pd.merge(df_krx, df_desc[['Code', 'Industry', 'Products']], on='Code', how='left')
    # 한글명 매핑 딕셔너리 생성
    mapper = {
        'Code': '종목코드',
        'ISU_CD': '표준코드',
        'Name': '종목명',
        'Market': '시장',
        'Dept': '소속부',
        'Close': '현재가',
        'ChangeCode': '변동코드',
        'Changes': '전일대비',
        'ChagesRatio': '등락률',
        'Open': '시가',
        'High': '고가',
        'Low': '저가',
        'Volume': '거래량',
        'Amount': '거래대금',
        'Marcap': '시가총액',
        'Stocks': '상장주식수',
        'MarketId': '시장ID'
    }
    # 컬럼명 변경 (inplace=True를 쓰면 원본이 바로 바뀜)
    df.rename(columns=mapper, inplace=True)
    # csv로 저장
    today = datetime.now().strftime('%Y%m%d')
    df.to_csv(os.path.join(settings.data_folder, f"{today}_KRX.csv"), index=False)

    return df


# 각 개별 종목의 데이터를 가져온다.
# 2015년 6월 15일 상하한가 +- 30%로 결정된 날이 시작날짜
def fdr_update_stock(ticker, name):
    # 데이터 저장 위치 설정
    stock_dir = os.path.join(settings.data_folder, "stocks")
    if not os.path.exists(stock_dir):
        os.makedirs(stock_dir)
    stock_file = os.path.join(stock_dir, f"{ticker}_{name}.parquet")

    # 조회 마지막날
    end_date = datetime.now() - relativedelta(days=1)

    # 시작 날짜 결정 (기존 파일 존재 여부 확인)
    if os.path.exists(stock_file):
        df_old = pd.read_parquet(stock_file)
        last_date = df_old['Time'].iloc[-1]
        start_date = last_date + pd.Timedelta(days=1)
    else:
        df_old = pd.DataFrame()
        start_date = datetime.strptime("20150615", "%Y%m%d")

    # 업데이트가 필요 없는 경우 스킵
    if start_date > end_date:
        print(f"[{ticker}] 이미 최신 상태입니다.")
        return df_old

    # 데이터 읽어오기
    try:
        df_new = fdr.DataReader(ticker, start_date, end_date)
        if df_new is None or df_new.empty:
            print(f"[{ticker}] 데이터가 비어있습니다.")
            return df_old
    except Exception as e:
        print(f"[{ticker}] 불러오기 실패: {e}")
        return df_old

    # 날짜 인덱스를 'Time' 컬럼으로
    df_new = df_new.reset_index().rename(columns={'Date': 'Time'})
    # 데이터 합치기
    df_updated = pd.concat([df_old, df_new], ignore_index=True)

    # 'Time' 기준 중복 제거 (index 대신 실제 날짜 컬럼 활용)
    # keep='last'를 통해 새로 가져온(all_new_data) 값을 남깁니다.
    df_updated = df_updated.drop_duplicates(subset=['Time'], keep='last')

    # 'Time' 기준으로 오름차순 정렬 (과거 -> 최신 순서 고정)
    df_updated = df_updated.sort_values(by='Time', ascending=True)

    # 인덱스 깔끔하게 정리
    df_updated = df_updated.reset_index(drop=True)

    # 여기서 지표 계산 함수(add_indicators)를 호출할 수 있습니다.
    # 지표 계산은 Time이 인덱스 이어야 함
    df_updated.set_index('Time', inplace=True)
    df_updated = add_stocks_indicators(df_updated)
    df_updated.reset_index(inplace=True)

    df_updated.to_parquet(stock_file, engine='pyarrow')
    print(f"[{ticker}_{name}] 최종 저장 완료.")

    return df_updated


def add_stocks_indicators(df):
    # 이평계산
    df.ta.sma(length=5, append=True)
    df.ta.sma(length=10, append=True)
    df.ta.sma(length=20, append=True)
    df.ta.sma(length=60, append=True)
    df.ta.sma(length=120, append=True)
    df.ta.sma(length=200, append=True)

    # 볼린져 밴드
    df.ta.bbands(length=20, std=1.0, append=True)
    df.ta.bbands(length=20, std=2.0, append=True)
    df.ta.bbands(length=20, std=3.0, append=True)

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
