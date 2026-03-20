from PySide6.QtCore import QThread, Signal, QProcess

from Fdr_Stock import fdr_update_stock
from settings import settings
import os


class StockAnalysisWorker(QThread):
    log_signal = Signal(str)  # 글자 전달용 시그널

    def __init__(self, stocks, models):
        super().__init__()
        # 주식 리스트
        self.stock_list = stocks
        # 실행 모델 리스트
        self.model_list = models

        # 중단 플래그
        self.is_killed = False

        # 모델 실행 프로세스
        self.process = None

    def run(self):
        # run 안에서 QProcess 생성
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)

        # 실제 작업 내용
        stock_dir = os.path.join(settings.data_folder, 'stocks')
        for stock in self.stock_list:
            # 중단 요청 시 루프 탈출
            if self.is_killed:
                break
            try:
                # 주식 데이터 업데이트
                ticker, name = stock.split("_")
                self.log_signal.emit(f"[작업] {stock}")
                self.log_signal.emit(f"[정보] {stock} 업데이트 시작 ...")
                fdr_update_stock(ticker, name)
                self.log_signal.emit(f"[정보] {stock} 업데이트 완료 ...\n")

                # 모델링 실행
                stock_file = os.path.join(stock_dir, f'{stock}.parquet')
                for model in self.model_list:
                    # 중단 요청 시 루프 탈출
                    if self.is_killed:
                        break
                    # 프로세스 시작
                    if model == "NP":
                        self.log_signal.emit(f"[정보] {stock} NP 모델링 실행 중...")
                        self.process.start(settings.np_path, [stock_file])
                    elif model == "LGBM":
                        self.log_signal.emit(f"[정보] {stock} LGBM 모델링 실행 중...")
                        self.process.start(settings.darts_path, ['LGBM', stock_file])
                    elif model == "TFT":
                        self.log_signal.emit(f"[정보] {stock} TFT 모델링 실행 중...")
                        self.process.start(settings.darts_path, ['TFT', stock_file])
                    elif model == "XGB":
                        self.log_signal.emit(f"[정보] {stock} XGB 모델링 실행 중...")
                        self.process.start(settings.darts_path, ['XGB', stock_file])
                    elif model == "RE":
                        self.log_signal.emit(f"[정보] {stock} RE 모델링 실행 중...")
                        self.process.start(settings.darts_path, ['RE', stock_file])
                    # 프로세스가 정상적으로 끝날 때까지 대기 (최대 10분 등 타임아웃 설정 가능)
                    # 만약 실패하거나 에러가 나도 다음으로 넘어가기 위해 체크
                    success = self.process.waitForFinished(-1)

                    # 에러 체크: 종료 코드가 0이 아니면 에러 발생으로 간주
                    if not success or self.process.exitCode() != 0:
                        self.log_signal.emit(f"[경고] {model}에서 에러 발생.")
                        self.process.kill()  # 확실히 종료 시킴
                        continue  # 다음 모델로 이동
                self.log_signal.emit(f"[정보] {stock} 종가 예측 모델링 완료\n")
            except Exception as e:
                # 예상치 못한 에러(파일 없음 등) 발생 시 종목 단위로 건너뛰기
                self.log_signal.emit(f"[에러] {stock} 처리 중 중단됨: {str(e)}")

    def handle_stdout(self):
        if self.process:
            data = self.process.readAllStandardOutput().data().decode("cp949", errors="ignore")
            self.log_signal.emit(data.strip())

    def handle_stderr(self):
        if self.process:
            data = self.process.readAllStandardError().data().decode("cp949", errors="ignore")
            # 에러 출력도 로그에 남기지만 중단하지는 않음
            self.log_signal.emit(f"[에러] {data.strip()}")

    def stop(self):
        self.is_killed = True
        # 실행 중인 외부 프로그램도 종료
        if self.process:
            self.process.kill()
        self.quit()
        self.wait()
