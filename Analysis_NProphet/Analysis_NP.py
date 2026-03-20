import sys
import os
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


if __name__ == "__main__":

    # 전달 인자 검사
    if len(sys.argv) < 2:
        logger.error("사용법: python Analysis_NP.py <데이터 파일경로>")
        sys.exit(1)

    # 데이터 파일 경로
    file_path = sys.argv[1]
    # file_path = 'D:\\WorkSpace\\Python\\OksStockAnalysis\\data\\stocks\\005930_삼성전자.parquet'

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

    # csv로 저장
    # 디렉토리 경로, 파일명만 (경로 제외)
    directory = os.path.dirname(file_path)
    filename_ext = os.path.basename(file_path)
    filename_only = os.path.splitext(filename_ext)[0]

    forecast_df.to_csv(os.path.join(directory, f"{filename_only}_nprophet.csv"), index=False)

    logger.info("=== 미래 5일 예측 결과 ===")
    logger.info(forecast_df.to_string(index=False))
