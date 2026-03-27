from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QGridLayout, QMessageBox, QVBoxLayout
import finplot as fplt

import os
import subprocess
import pandas as pd
import numpy as np
from lightweight_charts.widgets import QtChart

from ui.ChartWidget2 import Ui_ChartWidget2
from pygooglenews import GoogleNews
from dateutil import parser
from dateutil import tz
from settings import settings


class ChartWidget2(QWidget):
    # [중요] 반드시 __init__ 밖, 클래스 바로 아래에 선언하세요.
    closed = Signal(object)

    def __init__(self, ticker, name, parent=None):
        super().__init__(parent)
        
        # 현재 티켓
        self.stock_ticker = ticker
        self.stock_name = name

        # ui 로딩
        self.ui = Ui_ChartWidget2()
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

        # 데이터를 불러온다.
        self.stock_dir = os.path.join(settings.data_folder, 'stocks')
        self.stock_file = os.path.join(self.stock_dir, f'{self.stock_ticker}_{self.stock_name}.parquet')
        if not os.path.exists(self.stock_file):
            QMessageBox.information(self, '알림', f'{self.stock_ticker}_{self.stock_name} 데이터가 없습니다.')
            return

        self.df_stock = pd.read_parquet(self.stock_file)
        self.df_candle = self.df_stock[['Time', 'Open', 'Close', 'High', 'Low', 'Volume']]
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

        # QGraphicsView에 finplot 넣기
        self.chart_layout = QVBoxLayout(self.ui.widget_container)
        self.ui.widget_container.setLayout(self.chart_layout)

        # 차트 생성
        self.chart = QtChart(self, inner_height=0.5)
        self.chart_layout.addWidget(self.chart.get_webview())
        self.chart.set(self.df_candle)

        # 캔들 스타일
        self.chart.candle_style(
            up_color='#FF0000',  # 빨강
            down_color='#0000FF',  # 파랑
            border_up_color='#FF0000',
            border_down_color='#0000FF',
            wick_up_color='#FF0000',
            wick_down_color='#0000FF'
        )

        # 거래량 패널(아래) 비율/색상
        self.chart.volume_config(
            scale_margin_top=0.8,  # 위 80% 캔들, 아래 20% 거래량[web:30]
            scale_margin_bottom=0.0,
            up_color="rgba(255,0,0,0.5)",
            down_color="rgba(0,0,255,0.5)",
        )

        # 이평 그리기
        # sma_settings = [
        #     {'color': '#FFD700', 'name': 'SMA_5'},  # 골드
        #     {'color': '#FF00FF', 'name': 'SMA_20'},  # 핑크
        #     {'color': '#00FF00', 'name': 'SMA_60'},  # 녹색
        #     {'color': '#00FFFF', 'name': 'SMA_120'},  # 하늘색
        #     {'color': '#FFFFFF', 'name': 'SMA_200'}  # 흰색
        # ]
        # for sma in sma_settings:
        #     line = self.chart.create_line(name=sma['name'], color=sma['color'], width=1)
        #     line.set(self.df_stock[['Time', sma['name']]])

        # 볼린져 밴드 그리기
        # 상단선 (Upper Band)
        self.bb_upper = self.chart.create_line(name='BBU_20_2.0', color='rgba(255, 0, 0, 0.5)', width=1)
        # 중단선 (Basis/SMA)
        self.bb_basis = self.chart.create_line(name='BBM_20_2.0', color='rgba(255, 255, 255, 0.3)', width=1, style='dotted')
        # 하단선 (Lower Band)
        self.bb_lower = self.chart.create_line(name='BBL_20_2.0', color='rgba(0, 0, 255, 0.5)', width=1)
        # 3. 데이터 구성 및 세팅 (컬럼명은 time, value 필수)
        self.bb_upper.set(self.df_stock[['Time', 'BBU_20_2.0']])
        self.bb_basis.set(self.df_stock[['Time', 'BBM_20_2.0']])
        self.bb_lower.set(self.df_stock[['Time', 'BBL_20_2.0']])

        # 2) 서브차트 생성 (아래 20%)
        rsi_chart = self.chart.create_subchart(width=1, height=0.5, sync=True)  # 시간축 동기화
        # 3) RSI 선 추가
        rsi_line = rsi_chart.create_line(name="RSI_14", color="#FF9800", width=1)
        rsi_line.set(self.df_stock[['Time', 'RSI_14']])
        # RSI 기준선 (30/50/70)
        rsi_chart.horizontal_line(price=70, color="#FF0000", width=2, style="dashed")
        rsi_chart.horizontal_line(price=30, color="#00FF00", width=2, style="dashed")
        rsi_chart.horizontal_line(price=50, color="#808080", width=1, style="solid")

        self.chart.layout()

    def closeEvent(self, event):
        # 창이 닫힐 때 closed 시그널 발생
        self.closed.emit(self)
        event.accept()

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

