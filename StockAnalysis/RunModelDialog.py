import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFileDialog, QDialog, QMessageBox, QApplication, QTableWidgetItem
from LoadingDialog import LoadingDialog
from StockAnalysisWorker import StockAnalysisWorker
from settings import settings
from ui.RunModelDialog import Ui_RunModelDialog
import os


class RunModelDialog(QDialog):
    def __init__(self, stocks, parent=None):
        super().__init__(parent)

        # 현재 주식 리스트
        self.stock_list = stocks

        # 주식 분석 쓰레드
        self.worker = None

        # ui 로딩
        self.ui = Ui_RunModelDialog()
        self.ui.setupUi(self)

        # np 모델 실행파일 경로
        self.ui.edit_np_path.setText(settings.np_path)
        self.ui.btn_np_path.clicked.connect(self.btnNpPathClicked)

        # darts 모델 실행파일 경로
        self.ui.edit_darts_path.setText(settings.darts_path)
        self.ui.btn_darts_path.clicked.connect(self.btnDartsPathClicked)

        # 초기 기본 모델링
        self.ui.check_np.setChecked(True)
        self.ui.check_lgbm.setChecked(True)
        self.ui.check_tft.setChecked(False)
        self.ui.check_xgb.setChecked(False)
        self.ui.check_re.setChecked(False)

        # 모델링 실행 버튼
        self.ui.btn_run_model.clicked.connect(self.btnRunModelClicked)

        # 중지 버튼
        self.ui.btn_stop_model.clicked.connect(self.btnStopModelClicked)

        # 로그화면 줄수 제한
        self.ui.text_output.setMaximumBlockCount(1000)

        # 테이블 위젯 컬럼 설정
        column_headers = ['종목코드_종목명', '날짜', '종가', 'D+1', 'D+2', 'D+3', 'D+4', 'D+5']
        self.ui.tableWidget.setColumnCount(len(column_headers))
        self.ui.tableWidget.setHorizontalHeaderLabels(column_headers)
        self.ui.tableWidget.setRowCount(len(self.stock_list))
        self.ui.tableWidget.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #F2F2F2; /* 엑셀 느낌의 연한 회색 */
                border: 1px solid #D8D8D8; /* 테두리 선 */
                font-weight: bold;         /* 글자 굵게 */
                height: 30px;              /* 헤더 높이 */
            }
        """)
        for row_idx, name in enumerate(self.stock_list):
            self.ui.tableWidget.setItem(row_idx, 0, QTableWidgetItem(name))

        self.update_tablewidget()

        # # 리스트 뷰 표시
        # self.ui.list_stocks.addItems(self.stock_list)
        # # 사용자의 클릭 입력을 막음 (프로그램 제어만 허용)
        # self.ui.list_stocks.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # # 하이라이트 스타일 정의 (선택된 항목의 색상 지정)
        # self.ui.list_stocks.setStyleSheet("""
        #     QListWidget::item:selected {
        #         background-color: palette(highlight);     /* 시스템 기본 선택 배경색 */
        #         color: palette(highlighted-text);        /* 시스템 기본 선택 글자색 */
        #         font-weight: bold;
        #     }
        # """)
        # self.ui.list_stocks.item(0).setSelected(True)

    def btnNpPathClicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "NP 실행 파일 선택",  # 창 제목
            "",  # 기본 경로 ("" = 현재 디렉토리)
            "Analysis_NP.exe (Analysis_NP.exe)"  # 필터
        )
        if file_path:
            self.ui.edit_np_path.setText(file_path)
            settings.np_path = file_path
            settings.save_settings()

    def btnDartsPathClicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Darts 실행 파일 선택",  # 창 제목
            "",  # 기본 경로 ("" = 현재 디렉토리)
            "Analysis_Darts.exe (Analysis_Darts.exe)"  # 필터
        )
        if file_path:
            self.ui.edit_darts_path.setText(file_path)
            settings.darts_path = file_path
            settings.save_settings()

    def btnRunModelClicked(self):
        models = []
        if self.ui.check_np.isChecked():
            models.append("NP")
        if self.ui.check_lgbm.isChecked():
            models.append("LGBM")
        if self.ui.check_tft.isChecked():
            models.append("TFT")
        if self.ui.check_xgb.isChecked():
            models.append("XGB")
        if self.ui.check_re.isChecked():
            models.append("RE")
        if self.worker is not None:
            QMessageBox.information(self, '알림', '주식 분석 작업이 진행 중입니다.')
            return
        if not models:
            QMessageBox.information(self, '알림', '종가 예측 모델을 선택해 주세요.')
            return
        # StockWorker 실행
        self.worker = StockAnalysisWorker(self.stock_list, models)
        self.worker.log_signal.connect(self.append_log)
        # 종료 시 처리 (순서 중요)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.cleanup_worker)
        self.worker.start()

    def cleanup_worker(self):
        print("쓰레드가 안전하게 종료되었습니다.")
        self.worker = None  # 여기서 변수를 비워줌
        # 작업이 종료되면 종가 예측 파일을 불러와서 테이블위젯 업데이트
        self.update_tablewidget()

    def update_tablewidget(self):
        # 1. 빈 데이터프레임 구조 생성
        columns = ['주식이름', '날짜', '종가', 'D1', 'D2', 'D3', 'D4', 'D5']
        df_result = pd.DataFrame(index=range(len(self.stock_list)), columns=columns)
        df_result['주식이름'] = self.stock_list
        # 모든 예측치의 평균을 넣는다.
        stock_dir = os.path.join(settings.data_folder, 'stocks')
        for i, stock in enumerate(self.stock_list):
            stock_file = os.path.join(stock_dir, f'{stock}_fc.csv')
            if not os.path.exists(stock_file):
                continue
            df_stock = pd.read_csv(stock_file)
            # 1. 날짜 컬럼을 datetime 형식으로 변환 (필요한 경우)
            df_stock['date'] = pd.to_datetime(df_stock['date'])
            # 2. 데이터프레임 내의 가장 최근(마지막) 날짜 찾기
            last_date = df_stock['date'].max()
            # 3. 해당 날짜에 해당하는 모든 종목 데이터 추출
            last_df = df_stock[df_stock['date'] == last_date]
            if last_df.empty:
                continue
            # 평균 계산 후 반올림하여 정수로 변환 (.round(0).astype(int))
            avg_values = last_df[['D1', 'D2', 'D3', 'D4', 'D5']].mean().round(0).astype(int)
            # 각 컬럼에 데이터 주입
            df_result.loc[i, '날짜'] = last_df['date'].iloc[0]
            df_result.loc[i, '종가'] = last_df['D0'].iloc[0].round(0).astype(int)
            # D0~D5 범위를 한 번에 정수 값으로 채움
            df_result.loc[i, 'D1':'D5'] = avg_values
        # 테이블위젯 업데이트
        self.ui.tableWidget.setUpdatesEnabled(False)  # 화면 업데이트 일시 중지
        # 기존 데이터와 행/열 설정 모두 지우기
        self.ui.tableWidget.setRowCount(0)
        # 데이터프레임 크기에 맞게 행/열 개수 재설정
        self.ui.tableWidget.setRowCount(len(self.stock_list))
        # 3. 데이터 다시 채우기
        for i in range(len(df_result)):
            for j in range(len(df_result.columns)):
                raw_val = df_result.iloc[i, j]
                try:
                    num_val = float(raw_val)
                    if pd.isna(num_val):
                        val = ""
                    else:
                        val = f"{int(num_val):,}"
                except (ValueError, TypeError):
                    val = str(raw_val)
                item = QTableWidgetItem(val)
                if val != "" and val.replace(",", "").isdigit():
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tableWidget.setItem(i, j, item)
        self.ui.tableWidget.setUpdatesEnabled(True)  # 다시 켜기

    def btnStopModelClicked(self):
        if self.worker is not None:
            self.worker.stop()
            dlg = LoadingDialog('알림', '정리중입니다.')
            dlg.show()
            while self.worker.isRunning():
                QApplication.processEvents()  # GUI가 멈추지 않게 이벤트 처리
                if self.worker.wait(500):  # 0.5초마다 체크
                    break
            dlg.close()

    def append_log(self, text):
        # 현재 작업 파일을 리스트에 표시
        # if "[작업]" in text:
        #     stock = text.split(" ")[1]
        #     list_items = self.ui.list_stocks.findItems(stock, Qt.MatchFlag.MatchExactly)
        #     if list_items:
        #         # 찾은 첫 번째 아이템의 행 번호(row) 가져오기
        #         row = self.ui.list_stocks.row(list_items[0])
        #         # 해당 행 선택 및 스크롤 이동
        #         self.ui.list_stocks.setCurrentRow(row)
        #         self.ui.list_stocks.scrollToItem(list_items[0])
        #     return
        # 일반 로그는 평소대로 다음 줄에 추가
        self.ui.text_output.appendPlainText(text)
        # 1. 현재 스크롤바 상태 확인
        scrollbar = self.ui.text_output.verticalScrollBar()
        # 현재 위치가 맨 아래인지 확인 (약간의 오차 허용을 위해 -5 정도 여유)
        at_bottom = scrollbar.value() >= (scrollbar.maximum() - 10)
        # 3. 사용자가 맨 아래에 있었다면, 새로 추가된 텍스트로 스크롤 이동
        if at_bottom:
            self.ui.text_output.moveCursor(QTextCursor.MoveOperation.End)

    def closeEvent(self, event):
        # 1. 쓰레드가 실행 중인지 확인
        if self.worker is not None and self.worker.isRunning():
            reply = QMessageBox.question(
                self, '알림', '주식 분석 작업이 진행 중입니다.\n강제종료 할까요?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                dlg = LoadingDialog('알림', '정리중입니다.')
                dlg.show()
                while self.worker.isRunning():
                    QApplication.processEvents()  # GUI가 멈추지 않게 이벤트 처리
                    if self.worker.wait(500):  # 0.5초마다 체크
                        break
                dlg.close()
        print("작업 쓰레드가 안전하게 정리되었습니다.")
        event.accept()  # 창 닫기 허용
