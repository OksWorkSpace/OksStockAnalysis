import logging
import warnings

from neuralprophet import NeuralProphet

# 로거 가져오기
logger = logging.getLogger(__name__)

# 모든 경고 및 정보성 로그 차단
logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
logging.getLogger("neuralprophet").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")


def run_neuralprophet(df):
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
        learning_rate=0.03,  # 학습률
    )

    # 보조 지표 컬럼
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
    df = df[final_cols]

    # 기술적 지표 컬럼들 등록
    for regressor in lagged_regressors:
        model.add_lagged_regressor(names=regressor)

    # 학습 실행 (epochs 조절을 통해 과적합 방지)
    model.fit(df, freq='D', progress=None)

    # 3. 미래 예측
    future = model.make_future_dataframe(df, periods=5, n_historic_predictions=True)
    forecast = model.predict(future)

    # 결과 리턴
    return forecast

