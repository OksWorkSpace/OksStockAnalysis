from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QGridLayout, QMessageBox
import finplot as fplt

import os
import subprocess
import pandas as pd
from Fdr_Stock import fdr_update_stock
from ui.ChartWidget import Ui_ChartWidget
from pygooglenews import GoogleNews
from dateutil import parser
from dateutil import tz
from settings import settings


class ChartWidget(QWidget):
    # [중요] 반드시 __init__ 밖, 클래스 바로 아래에 선언하세요.
    closed = Signal(object)

    def __init__(self, ticker, name, parent=None):
        super().__init__(parent)
        
        # 현재 티켓
        self.stock_ticker = ticker
        self.stock_name = name

        # ui 로딩
        self.ui = Ui_ChartWidget()
        self.ui.setupUi(self)
        
        # 타이틀 설정
        self.setWindowTitle(f'{self.stock_ticker}_{self.stock_name}')

        # 뉴스 검색
        self.ui.textBrowser.setOpenExternalLinks(True)
        self.ui.btn_search_news.clicked.connect(self.btnSearchNews)

        # 초기 설정
        self.ui.check_candle.setChecked(True)
        self.ui.check_heikin.setChecked(False)

        self.ui.check_sma5.setChecked(True)
        self.ui.check_sma10.setChecked(True)
        self.ui.check_sma20.setChecked(True)
        self.ui.check_sma60.setChecked(True)
        self.ui.check_sma200.setChecked(True)

        self.ui.check_bb10.setChecked(False)
        self.ui.check_bb20.setChecked(True)
        self.ui.check_bb30.setChecked(False)

        # QGraphicsView에 finplot 넣기
        gridLayout = QGridLayout(self.ui.graphicsView)
        self.ui.graphicsView.setLayout(gridLayout)

        # 차트 생성 전 설정 (필수!)
        # fplt.background = '#CCCCCC'  # 회색 배경

        # 한국식 캔들 색상
        fplt.candle_bull_color = '#ff0000'  # 양봉: 빨강
        fplt.candle_bear_color = '#0000ff'  # 음봉: 파랑
        fplt.candle_bull_body_color = '#ff0000'
        fplt.candle_bear_body_color = '#0000ff'

        self.ax, self.ax_rsi, self.ax_macd = fplt.create_plot(init_zoom_periods=100, rows=3)
        self.ui.graphicsView.axs = [self.ax, self.ax_rsi, self.ax_macd]  # finplot requres this property
        self.ax_volume = self.ax.overlay()  # 거래량 챠트
        gridLayout.addWidget(self.ax.vb.win)

        fplt.show(qt_exec=False)  # prepares plots when they're all setup

        # 데이터를 불러온다.
        self.stock_dir = os.path.join(settings.data_folder, 'stocks')
        self.stock_file = os.path.join(self.stock_dir, f'{self.stock_ticker}_{self.stock_name}.parquet')
        if not os.path.exists(self.stock_file):
            QMessageBox.information(self, '알림', f'{self.stock_ticker}_{self.stock_name} 데이터가 없습니다.')
            return

        self.df_stock = pd.read_parquet(self.stock_file)
        self.df_candle = self.df_stock[['Time', 'Open', 'Close', 'High', 'Low']]
        # 하이킨아시 계산
        self.df_heikin = self.df_candle.copy()
        cols = ['Open', 'High', 'Low', 'Close']
        self.df_heikin[cols] = self.df_heikin[cols].astype(float)
        # 종가: (시+고+저+종) / 4
        self.df_heikin['Close'] = (self.df_heikin['Open'] + self.df_heikin['High'] + self.df_heikin['Low'] + self.df_heikin['Close']) / 4
        # 시가: (이전봉 시가 + 이전봉 종가) / 2
        # (첫 번째 봉은 원본 시가 사용, 이후는 반복 계산 필요)
        for i in range(1, len(self.df_heikin)):
            self.df_heikin.loc[self.df_heikin.index[i], 'Open'] = (self.df_heikin.loc[self.df_heikin.index[i - 1], 'Open'] +
                self.df_heikin.loc[self.df_heikin.index[i - 1], 'Close']) / 2
        # 고가: max(고가, 시가, 종가) / 저가: min(저가, 시가, 종가)
        self.df_heikin['High'] = self.df_heikin[['High', 'Open', 'Close']].max(axis=1)
        self.df_heikin['Low'] = self.df_heikin[['Low', 'Open', 'Close']].min(axis=1)

        # 챠트 업데이트
        self.updateChart()

        # # 초기 모델 선택
        # self.ui.check_np.setChecked(True)
        # self.ui.check_lgbm.setChecked(True)
        # self.ui.check_tft.setChecked(False)
        # self.ui.check_xgb.setChecked(False)
        # self.ui.check_re.setChecked(False)
        #
        # # 종가 예측 모델 실행
        # self.ui.btn_run_model.clicked.connect(self.btnRunModel)

    def closeEvent(self, event):
        # 창이 닫힐 때 closed 시그널 발생
        self.closed.emit(self)
        event.accept()

    def updateChart(self):
        # 차트 클리어
        self.ax.reset()  # remove previous plots
        self.ax_rsi.reset()
        self.ax_macd.reset()
        self.ax_volume.reset()

        # 캔들 + 거래량
        fplt.candlestick_ochl(self.df_candle, ax=self.ax)
        fplt.volume_ocv(self.df_stock[['Time', 'Open', 'Close', 'Volume']], ax=self.ax_volume)

        # 이평
        # fplt.plot(self.df_stock["SMA_5"], ax=self.ax, color="#EE0000", width=1, legend="SMA_5")
        # fplt.plot(self.df_stock["SMA_10"], ax=self.ax, color="#99FFFF", width=1, legend="SMA_10")
        # fplt.plot(self.df_stock["SMA_20"], ax=self.ax, color="#0000FF", width=1, legend="SMA_20")
        fplt.plot(self.df_stock["SMA_60"], ax=self.ax, color="#990099", width=1, legend="SMA_60")
        # fplt.plot(self.df_stock["SMA_120"], ax=self.ax, color="#0000FF", width=1, legend="SMA_120")
        # fplt.plot(self.df_stock["SMA_200"], ax=self.ax, color="#CC33FF", width=1, legend="SMA_200")

        # 볼린져 밴드
        fplt.plot(self.df_stock["BBU_20_1.0"], ax=self.ax, color="#FF99CC", width=1, legend="BBU_20_1.0")
        fplt.plot(self.df_stock["BBL_20_1.0"], ax=self.ax, color="#FF99CC", width=1, legend="BBL_20_1.0")
        fplt.plot(self.df_stock["BBU_20_2.0"], ax=self.ax, color="#FF66CC", width=1, legend="BBU_20_2.0")
        fplt.plot(self.df_stock["BBL_20_2.0"], ax=self.ax, color="#FF66CC", width=1, legend="BBL_20_2.0")
        fplt.plot(self.df_stock["BBU_20_3.0"], ax=self.ax, color="#FF33CC", width=1, legend="BBU_20_3.0")
        fplt.plot(self.df_stock["BBL_20_3.0"], ax=self.ax, color="#FF33CC", width=1, legend="BBL_20_3.0")

        # RSI 차트 (두 번째 행) ---
        fplt.plot(self.df_stock['RSI_14'], ax=self.ax_rsi, legend='RSI (14)', color='#9b59b6')
        # 과매수(70)/과매도(30) 기준선 추가
        fplt.add_band(30, 70, ax=self.ax_rsi)
        # Y축 고정
        # 해당 축의 자동 스케일링 기능을 완전히 끕니다.
        # 줌을 하거나 데이터를 이동해도 Y축이 변하지 않게 고정합니다.
        fplt.set_y_range(ymin=0, ymax=100, ax=self.ax_rsi)
        self.ax_rsi.vb.setYRange(0, 100)
        self.ax_rsi.vb.enableAutoRange(axis='y', enable=False)

        # MACD 선과 시그널 선
        fplt.plot(self.df_stock['MACD_12_26_9'], ax=self.ax_macd, legend='MACD', color='#3498db')
        fplt.plot(self.df_stock['MACDs_12_26_9'], ax=self.ax_macd, legend='Signal', color='#e74c3c')
        # MACD 히스토그램 (바 차트로 표현)
        colors = ['#26a69a' if v > 0 else '#ef5350' for v in self.df_stock['MACDh_12_26_9']]
        fplt.bar(self.df_stock['MACDh_12_26_9'], ax=self.ax_macd, color=colors, legend='Hist')

        # 상단 및 중간 차트의 X축(날짜) 숨기기
        self.ax.hideAxis('bottom')  # 메인 차트 날짜 숨김
        self.ax_rsi.hideAxis('bottom')  # RSI 차트 날짜 숨김

        # 핵심: 마지막에 모든 하단 차트의 X축을 메인 차트에 링크
        self.ax_rsi.setXLink(self.ax)
        self.ax_macd.setXLink(self.ax)

        # 3. RSI 결합 최종 판단 (시각화용 불리언 시리즈)
        # 상승신호(1) + RSI 35 이하 / 하락신호(-1) + RSI 65 이상
        buy_mask = (self.df_stock['candle_signal'] == 1) & (self.df_stock['RSI_14'] <= 35)
        sell_mask = (self.df_stock['candle_signal'] == -1) & (self.df_stock['RSI_14'] >= 65)

        # 매수 화살표 및 패턴명 표시
        for idx, row in self.df_stock[buy_mask].iterrows():
            fplt.plot(row['Time'], row['Low'] * 0.97, ax=self.ax, color='#00ff00', style='^', width=1)

        # 매도 화살표 및 패턴명 표시
        for idx, row in self.df_stock[sell_mask].iterrows():
            fplt.plot(row['Time'], row['High'] * 1.03, ax=self.ax, color='#ff0000', style='v', width=1)

        fplt.refresh()  # refresh autoscaling when all plots complete

    # # 종가 예측 모델 실행
    # def btnRunModel(self):
    #     stock_dir = os.path.join(settings.DATA_FOLDER, 'stocks')
    #     stock_file = os.path.join(stock_dir, f'{self.stock_ticker}_{self.stock_name}.parquet')
    #
    #     # 데이터 업데이트
    #     fdr_update_stock(self.stock_ticker, self.stock_name)
    #
    #     # 모델을 실행한다.
    #     if self.ui.check_np.isChecked():
    #         subprocess.run(
    #             ['D:\\WorkSpace\\Python\\OksStockAnalysis\\Analysis_NProphet\\dist\\Analysis_NP\\Analysis_NP.exe',
    #              stock_file])
    #     if self.ui.check_lgbm.isChecked():
    #         subprocess.run(
    #             ['D:\\WorkSpace\\Python\\OksStockAnalysis\\Analysis_Darts\\dist\\Analysis_Darts\\Analysis_Darts.exe',
    #              'LGBM', stock_file])
    #     if self.ui.check_tft.isChecked():
    #         subprocess.run(
    #             ['D:\\WorkSpace\\Python\\OksStockAnalysis\\Analysis_Darts\\dist\\Analysis_Darts\\Analysis_Darts.exe',
    #              'TFT', stock_file])
    #     if self.ui.check_xgb.isChecked():
    #         subprocess.run(
    #             ['D:\\WorkSpace\\Python\\OksStockAnalysis\\Analysis_Darts\\dist\\Analysis_Darts\\Analysis_Darts.exe',
    #              'XGB', stock_file])
    #     if self.ui.check_re.isChecked():
    #         subprocess.run(
    #             ['D:\\WorkSpace\\Python\\OksStockAnalysis\\Analysis_Darts\\dist\\Analysis_Darts\\Analysis_Darts.exe',
    #              'RE', stock_file])
    #
    #     # 모델명과 파일명 매핑 딕셔너리
    #     model_files = {
    #         'NP': f'{self.stock_ticker}_{self.stock_name}_np.csv',
    #         'LGBM': f'{self.stock_ticker}_{self.stock_name}_lgbm.csv',
    #         'TFT': f'{self.stock_ticker}_{self.stock_name}_tft.csv',
    #         'XGB': f'{self.stock_ticker}_{self.stock_name}_xgb.csv',
    #         'RE': f'{self.stock_ticker}_{self.stock_name}_re.csv'
    #     }
    #
    #     # 결과 행들을 담을 리스트
    #     all_rows = []
    #     cols = ['D+0', 'D+1', 'D+2', 'D+3', 'D+4', 'D+5']
    #
    #     # 딕셔너리 반복 처리
    #     for model_name, file_name in model_files.items():
    #         try:
    #             # 파일 읽기
    #             df = pd.read_csv(os.path.join(stock_dir, file_name))
    #
    #             # 첫 번째 날짜와 종가 리스트 추출 (6개 추출)
    #             base_date = df['Time'].iloc[0]
    #             prices = df['Predicted_Close'].tolist()[:6]
    #
    #             # 한 행 데이터 생성: [모델명, 날짜] + [가격들]
    #             new_row = [model_name, base_date] + prices
    #             all_rows.append(new_row)
    #
    #         except FileNotFoundError:
    #             print(f"경고: {file_name} 파일을 찾을 수 없습니다.")
    #
    #     # 최종 데이터프레임 생성
    #     result_df = pd.DataFrame(all_rows, columns=['model', '날짜'] + cols)
    #
    #     # CSV 저장 (인덱스 없이)
    #     result_df.to_csv(os.path.join(stock_dir, f'{self.stock_ticker}_{self.stock_name}_all.csv'),
    #                      index=False, encoding='utf-8-sig')

    # 뉴스 검색
    def btnSearchNews(self):
        # 한국 지역, 한국어 설정으로 초기화
        gn = GoogleNews(lang='ko', country='KR')

        # '삼성전자' 키워드로 검색 (최신순 정렬)
        # 검색어에 따옴표를 붙이면 정확히 해당 단어가 포함된 결과만 필터링합니다.
        search_result = gn.search(f'"{self.stock_name}"')

        # 검색 결과 중 상위 5개 출력
        print(f"--- '삼성전자' 최신 뉴스 검색 결과 ---")
        self.ui.textBrowser.clear()
        for entry in search_result['entries'][:10]:
            title = entry.title
            link = entry.link
            date = entry.published
            # 1. GMT 문자열을 datetime 객체로 변환
            gmt_date = parser.parse(entry.published)
            # 2. 한국 시간대로 변경
            kst_date = gmt_date.astimezone(tz.gettz('Asia/Seoul'))
            # 3. 원하는 형식으로 포맷팅 (예: 2026-03-18 15:30)
            formatted_date = kst_date.strftime('%Y-%m-%d %H:%M')

            # HTML 디자인 구성
            # pygooglenews의 link는 구글 리디렉션 주소이므로 클릭 시 실제 사이트로 이동함
            news_html = f"""
                        <div style='margin-bottom: 15px; border-bottom: 1px solid #ddd; padding-bottom: 10px;'>
                            <div style='color: #666; font-size: 9pt;'>🕒 {formatted_date}</div>
                            <div style='margin-top: 5px;'>
                                <a href='{link}' style='text-decoration: none; color: #1a0dab; font-size: 12pt; font-weight: bold;'>
                                    {title}
                                </a>
                            </div>
                            <div style='border-top: 1px dashed #cccccc; margin-top: 15px;'></div> <!-- 커스텀 구분선 -->
                        </div>
                        """
            self.ui.textBrowser.append(news_html)

