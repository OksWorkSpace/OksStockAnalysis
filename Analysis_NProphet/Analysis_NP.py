import json
import multiprocessing
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import logging
import torch
import pandas as pd
import numpy as np
from neuralprophet.configure import Season
from Load_Data import load_data
from Model_NP import run_neuralprophet

# 기본 설정: 레벨을 DEBUG로 낮추고 출력 포맷 지정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# NeuralProphet 클래스 허용목록에 추가
torch.serialization.add_safe_globals([Season])

# logger 가져오기
logger = logging.getLogger(__name__)


# 주식 예측 함수
def process_np(stock_dir, stock_list):
    # 자식 프로세스 시작 시 외부 로그만 차단
    for log_name in ["NP", "pytorch_lightning", "matplotlib"]:
        target_logger = logging.getLogger(log_name)
        target_logger.setLevel(logging.ERROR)
        target_logger.propagate = False
    # 1. fsspec 및 관련 파일 시스템 로그 차단 (가장 효과적)
    logging.getLogger("fsspec").setLevel(logging.ERROR)
    logging.getLogger("fsspec.local").setLevel(logging.ERROR)

    for stock in stock_list:
        # 파일 경로
        file_path = os.path.join(stock_dir, f"{stock}.parquet")

        # 데이터 로딩
        df_data = load_data(file_path)

        # 마지막 종가 데이터 (딕셔너리 형태)
        last_close_data = {
            'Time': df_data['ds'].iloc[-1].strftime('%Y-%m-%d'),
            'Predicted_Log_Return': 0.0,
            'Predicted_Close': df_data['Close'].iloc[-1]
        }

        # 모델링 실행
        df_predic = run_neuralprophet(df_data)

        # 결과 출력
        # 각 날짜의 "1일 후 예측값"만 모으기 (가장 정확)
        future_forecast = df_predic[df_predic['y'].isna()]  # 미래 데이터만

        # 각 행의 yhat 값을 가져오기
        predicted_log_returns = [future_forecast['yhat1'].iloc[0], future_forecast['yhat2'].iloc[0],
                                 future_forecast['yhat3'].iloc[0], future_forecast['yhat4'].iloc[0],
                                 future_forecast['yhat5'].iloc[0]]

        # 실제 주가로 환산 루프
        predicted_prices = []
        current_price = df_data['Close'].iloc[-1]

        for log_r in predicted_log_returns:
            # 역산 공식: 현재가 * exp(로그수익률)
            next_price = current_price * np.exp(log_r)
            predicted_prices.append(next_price)
            current_price = next_price  # 다음 날 예측을 위해 갱신

        # 결과 데이터프레임 생성
        forecast_df = pd.DataFrame({
            'Time': future_forecast['ds'],
            'Predicted_Log_Return': [round(x, 4) for x in predicted_log_returns],
            'Predicted_Close': np.array(predicted_prices).astype(int)
        })

        # 마지막 종가 데이터 추가 및 정렬
        forecast_df = pd.concat([forecast_df, pd.DataFrame([last_close_data])], ignore_index=True)
        # Time 컬럼이 문자열이라면 datetime으로 변환 후 정렬하는 것이 정확합니다.
        forecast_df['Time'] = pd.to_datetime(forecast_df['Time'])
        forecast_df = forecast_df.sort_values(by='Time').reset_index(drop=True)

        logger.info("=== 미래 5일 예측 결과 ===")
        logger.info(forecast_df.to_string(index=False))

        # model, date, D0, D1, D2, D3, D4, D5
        close_values = forecast_df['Predicted_Close'].values
        save_df = pd.DataFrame(
            {
                'model': 'NP',
                'date': last_close_data['Time'],
                'D0': close_values[0],
                'D1': close_values[1],
                'D2': close_values[2],
                'D3': close_values[3],
                'D4': close_values[4],
                'D5': close_values[5],
            }, index=[0]
        )

        # 2. 파일이 없으면 헤더를 포함하고, 있으면 헤더 없이 데이터만 추가
        file_path = os.path.join(stock_dir, f"{stock}_fc.csv")
        header_condition = not os.path.exists(file_path)

        save_df.to_csv(file_path, mode='a', index=False, header=header_condition, encoding='utf-8-sig')


if __name__ == "__main__":
    # EXE 환경에서 멀티프로세싱을 지원하기 위해 반드시 최상단에 호출
    multiprocessing.freeze_support()

    # 전달 인자 검사
    if len(sys.argv) < 3:
        logger.error("사용법: Analysis_NP.exe <주식 폴더> <주식 리스트 문자열(json)>")
        sys.exit(1)

    # 데이터 파일 경로
    data_dir = sys.argv[1]
    data_list = []
    try:
        data_list = json.loads(sys.argv[2])
        logger.info(f"주식 리스트 : {data_list}")
    except json.JSONDecodeError:
        logger.error("주식 리스트 JSON 파싱 에러! 문자열 형식을 확인하세요.")
        sys.exit(1)
    # data_dir = 'D:\\WorkSpace\\Python\\OksStockAnalysis\\data\\stocks'
    # data_list = ['000660_SK하이닉스', '005930_삼성전자', '005935_삼성전자우']

    # 프로세스 실행 개수
    num_workers = 2

    # 데이터를 4개 그룹으로 분할 (numpy 활용 시 간편)
    chunks = np.array_split(data_list, num_workers)

    # partial로 고정 인자 채움
    func = partial(process_np, data_dir)

    # max_workers=4
    executor = ProcessPoolExecutor(max_workers=num_workers)
    try:
        # 예측 시작
        list(executor.map(func, chunks))
    except KeyboardInterrupt:
        logger.info("\n[중단 신호 포착] 모든 예측 작업을 즉시 중단합니다...")
        # cancel_futures=True: 아직 시작 안 한 작업들 모두 취소
        # wait=False: 현재 실행 중인 프로세스가 끝날 때까지 기다리지 않고 종료 시도
        executor.shutdown(wait=False, cancel_futures=True)
        # 윈도우 환경에서 자식 프로세스까지 완전히 강제 종료하기 위해 사용
        sys.exit(0)
    except Exception as e:
        print(f"오류 발생: {e}")
        executor.shutdown(wait=False)
