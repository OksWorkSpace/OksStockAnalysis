import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np
import pandas as pd
import sys
import logging
from Load_Data import load_data
from Model_LightGBM import run_LightGBM
from Model_RegressionEnsemble import run_RegressionEnsembleModel
from Model_TFT import run_TFTModel
from Model_XGB import run_XGBModel


# 기본 설정: 레벨을 DEBUG로 낮추고 출력 포맷 지정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# 로거 가져오기
logger = logging.getLogger(__name__)


# 주식 예측 함수
def process_darts(model, stock_dir, stock_list):
    # 자식 프로세스용 로그 차단
    import logging, warnings
    logging.getLogger("darts").setLevel(logging.ERROR)
    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore")  # 자식 프로세스 경고 차단

    for stock in stock_list:
        # 파일 경로
        file_path = os.path.join(stock_dir, f"{stock}.parquet")

        # 데이터 로딩
        data_df = load_data(file_path)

        # 마지막 종가 데이터 (딕셔너리 형태)
        last_close_data = {
            'Time': data_df['Time'].iloc[-1].strftime('%Y-%m-%d'),
            'Predicted_Log_Return': 0.0,
            'Predicted_Close': data_df['Close'].iloc[-1]
        }

        # 모델 실행
        predic_df = None
        if model == 'LGBM':
            predic_df = run_LightGBM(data_df)
        elif model == 'TFT':
            predic_df = run_TFTModel(data_df)
        elif model == 'XGB':
            predic_df = run_XGBModel(data_df)
        elif model == 'RE':
            predic_df = run_RegressionEnsembleModel(data_df)
        else:
            logger.error(f"모델 입력 오류! [LGBM, TFT, XGB, RE] - {stock}")
            continue

        # 마지막 종가 데이터 추가 및 정렬
        predic_df = pd.concat([predic_df, pd.DataFrame([last_close_data])], ignore_index=True)
        # Time 컬럼이 문자열이라면 datetime으로 변환 후 정렬하는 것이 정확합니다.
        predic_df['Time'] = pd.to_datetime(predic_df['Time'])
        predic_df = predic_df.sort_values(by='Time').reset_index(drop=True)

        logger.info("=== 미래 5일 예측 결과 ===")
        logger.info(predic_df.to_string(index=False))

        # model, date, D0, D1, D2, D3, D4, D5
        close_values = predic_df['Predicted_Close'].values
        save_df = pd.DataFrame(
            {
                'model': model,
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
    if len(sys.argv) < 4:
        logger.error("사용법: python Analysis_NP.py <모델:LGBM, TFT, XGB, RE> <주식 폴더> <[주식 리스트]>")
        sys.exit(1)

    # 데이터 파일 경로
    data_model = sys.argv[1]
    data_dir = sys.argv[2]
    data_list = []
    try:
        data_list = json.loads(sys.argv[3])
        logger.info(f"주식 리스트 : {data_list}")
    except json.JSONDecodeError:
        logger.error("주식 리스트 JSON 파싱 에러! 문자열 형식을 확인하세요.")
        sys.exit(1)
    # data_model = 'LGBM'
    # data_dir = 'D:\\WorkSpace\\Python\\OksStockAnalysis\\data\\stocks'
    # data_list = ['000660_SK하이닉스', '005930_삼성전자', '005935_삼성전자우']

    # 프로세스 실행 개수
    num_workers = 2

    # 데이터를 4개 그룹으로 분할 (numpy 활용 시 간편)
    chunks = np.array_split(data_list, num_workers)

    # partial로 고정 인자 채움
    func = partial(process_darts, data_model, data_dir)

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


