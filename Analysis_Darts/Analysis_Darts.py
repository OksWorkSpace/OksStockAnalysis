import os

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


if __name__ == "__main__":
    # 전달 인자 검사
    # if len(sys.argv) < 3:
    #     logger.error("사용법: python Analysis_NP.py <모델[LGBM, TFT, XGB, RE(RegressionEnsemble)]> <데이터 파일경로>")
    #     sys.exit(1)
    #
    # # 데이터 파일 경로
    # model = sys.argv[1]
    # file_path = sys.argv[2]
    model = 'RE'
    file_path = 'D:\\WorkSpace\\Python\\OksStockAnalysis\\data\\stocks\\005930_삼성전자.parquet'

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
        logger.error("모델 입력 오류! [LGBM, TFT, XGB, RE(RegressionEnsemble)]")
        sys.exit(1)

    # 마지막 종가 데이터 추가 및 정렬
    predic_df = pd.concat([predic_df, pd.DataFrame([last_close_data])], ignore_index=True)
    # Time 컬럼이 문자열이라면 datetime으로 변환 후 정렬하는 것이 정확합니다.
    predic_df['Time'] = pd.to_datetime(predic_df['Time'])
    predic_df = predic_df.sort_values(by='Time').reset_index(drop=True)

    # csv로 저장
    # 디렉토리 경로, 파일명만 (경로 제외)
    directory = os.path.dirname(file_path)
    filename_ext = os.path.basename(file_path)
    filename_only = os.path.splitext(filename_ext)[0]

    if model == 'LGBM':
        predic_df.to_csv(os.path.join(directory, f"{filename_only}_lgbm.csv"), index=False)
    elif model == 'TFT':
        predic_df.to_csv(os.path.join(directory, f"{filename_only}_tft.csv"), index=False)
    elif model == 'XGB':
        predic_df.to_csv(os.path.join(directory, f"{filename_only}_xgb.csv"), index=False)
    elif model == 'RE':
        predic_df.to_csv(os.path.join(directory, f"{filename_only}_re.csv"), index=False)

    logger.info("=== 미래 5일 예측 결과 ===")
    logger.info(predic_df.to_string(index=False))
