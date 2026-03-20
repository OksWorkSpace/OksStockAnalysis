import sys
import pandas as pd
from PySide6.QtCore import Qt

import Fdr_Stock
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QHeaderView, QAbstractItemView, QTableView
from PySide6.QtWidgets import QMessageBox

from ChartWidget import ChartWidget
from Fdr_Stock import fdr_update_stock
from LoadingDialog import LoadingDialog
from RunModelDialog import RunModelDialog
from StockTreeView import StockTableViewModel
from ui.MainWindow import Ui_MainWindow
from pathlib import Path
from datetime import datetime
from settings import settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 로딩중 다이얼로그
        self.loading = None

        # UI 생성하기
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # 여러 차트를 표시하기 위한 리스트
        self.charts = []

        # 데이터 폴더 선택화면
        self.ui.edit_data_folder.setText(settings.data_folder)
        self.ui.btn_data_folder.clicked.connect(self.btnDataFolderClicked)

        # 일주가 불러오기 버튼
        self.ui.btn_krx_load.clicked.connect(self.btnKrxLoadClicked)

        # 시장 선택 체크
        self.ui.chk_kospi.setChecked(True)
        self.ui.chk_kospi.stateChanged.connect(self.chkMarketChanged)
        self.ui.chk_kosdaqg.setChecked(True)
        self.ui.chk_kosdaqg.stateChanged.connect(self.chkMarketChanged)
        self.ui.chk_kosdaq.setChecked(True)
        self.ui.chk_kosdaq.stateChanged.connect(self.chkMarketChanged)

        # AI 예측 모델 버튼
        self.ui.btn_run_model.clicked.connect(self.btnRunModelClicked)

        # 오늘날짜의 주식 데이터가 파일이 있는지 보고 초기화
        today = datetime.now()
        self.ui.groupBox_stock_day.setTitle(f'주식 현황({today.strftime('%Y년 %m월 %d일')})')
        file_path = Path(settings.data_folder) / f'{today.strftime('%Y%m%d')}_krx.csv'
        if file_path.exists():
            self.df_stock = pd.read_csv(file_path)
        else:
            self.df_stock = pd.DataFrame(
                columns=['종목코드', '표준코드', '종목명', '시장', '소속부', '현재가', '변동코드', '전일대비', '등락률', '시가',
                         '고가', '저가', '거래량', '거래대금', '시가총액', '상장주식수','시장ID', 'Industry', 'Products']
            )

        # 일주가 테이블뷰
        self.tableview_stock_model = StockTableViewModel(self.df_stock)
        self.ui.tableView_stock.setModel(self.tableview_stock_model)
        # 정렬 기능 활성화
        self.ui.tableView_stock.setSortingEnabled(True)
        # 엑셀 스타일 설정
        self.ui.tableView_stock.setStyleSheet("""
                    QHeaderView::section {
                        background-color: #F2F2F2;
                        color: #333333;
                        border: 1px solid #C0C0C0;
                    }
                """)
        header = self.ui.tableView_stock.horizontalHeader()
        header.setStretchLastSection(False)
        # 모든 열 자동 크기
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # 행 번호 표시
        self.ui.tableView_stock.verticalHeader().setVisible(True)
        # 내용에 맞춰 행 번호 칸 너비 조절 - 겁나 느려짐
        # self.ui.tableView_stock.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # 테이블 설정에서 편집 비활성화
        self.ui.tableView_stock.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        # 줄무늬
        # self.ui.tableView_stock.setAlternatingRowColors(True)
        # 행 단위 선택
        self.ui.tableView_stock.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Ctrl, Shift 키를 이용해 여러 개 선택 가능
        self.ui.tableView_stock.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # '시가총액' 기준 올림차순(DescendingOrder) 정렬
        column_idx = self.df_stock.columns.get_loc('시가총액')
        self.ui.tableView_stock.sortByColumn(column_idx, Qt.SortOrder.DescendingOrder)

    # def pushBtnClicked(self):
    #     chart = ChartWidget('005930', '삼성전자')
    #     chart.closed.connect(self.remove_chart_from_list)
    #     self.charts.append(chart)  # 리스트에 담아두면 메모리에서 삭제되지 않습니다.
    #     chart.show()
    #     # fdr_update_stock('005930', '삼성전자')

    def remove_chart_from_list(self, chart_obj):
        if chart_obj in self.charts:
            self.charts.remove(chart_obj)
            print(f"창 닫힘: 현재 남은 차트 수 {len(self.charts)}")

    # 데이터 저장폴더 버튼 이벤트
    def btnDataFolderClicked(self):
        folder_path = QFileDialog.getExistingDirectory(
            None,  # 부모 위젯
            "주식 데이터 저장 폴더 선택",  # 다이얼로그 제목
            settings.data_folder,  # 초기 디렉토리 경로
        )
        if folder_path:
            settings.data_folder = folder_path
            self.ui.edit_data_folder.setText(folder_path)
            settings.save_settings()

    # krx 데이터 불러오기 버튼 이벤트
    def btnKrxLoadClicked(self):
        file_path = Path(settings.data_folder) / f'{datetime.now().strftime('%Y%m%d')}_krx.csv'
        if file_path.exists():
            reply = QMessageBox.question(
                self, '알림', '오늘 날짜의 일일 주식 데이터가 있습니다.\n다시 불러올까요?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.df_stock = Fdr_Stock.fdr_stocklist()
            else:
                self.df_stock = pd.read_csv(file_path)
        else:
            self.df_stock = Fdr_Stock.fdr_stocklist()
        # 시세 정보 테이블 업데이트
        self.tableview_stock_model.update(self.df_stock)

    # kospi, kosdaq global, kosdaq 선택 체크박스 이벤트
    def chkMarketChanged(self):
        # 1. 신호를 보낸 위젯(체크박스) 찾기
        sender = self.sender()

    # AI 예측 모델 실행
    def btnRunModelClicked(self):
        # 선택 모델에서 선택된 인덱스들 가져오기
        selection_model = self.ui.tableView_stock.selectionModel()
        selected_indices = selection_model.selectedRows()  # 행 전체가 선택된 경우 유용
        if not selected_indices:
            QMessageBox.information(self, '알림', "선택 항목이 없습니다.")
            return
        selected_stock_list = []  # 결과를 담을 빈 리스트
        for index in selected_indices:
            row = index.row()
            item_code = self.tableview_stock_model.get_data_by_name(row, "종목코드")
            item_name = self.tableview_stock_model.get_data_by_name(row, "종목명")
            selected_stock_list.append(f'{item_code}_{item_name}')
        # 종가 예측 모델링 실행
        dialog = RunModelDialog(selected_stock_list)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec()
