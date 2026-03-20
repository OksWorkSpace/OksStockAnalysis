import sys
import pandas as pd
import numpy as np
from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtGui import QFont, QColor, QBrush


class StockTableViewModel(QAbstractTableModel):
    def __init__(self, dataframe):
        super().__init__()
        # 데이터 프레임 정리
        self._dataframe = dataframe.copy()  # 원본 보호를 위해 복사본 생성 권장
        self._dataframe.replace(["nan", "NaN", "None"], "", inplace=True)
        # inf 값을 NaN으로 변환 후 전체를 빈 문자열로 채움
        self._dataframe.replace([np.inf, -np.inf], np.nan, inplace=True)
        self._dataframe.fillna("", inplace=True)
        # 등락률 색상
        self.RED_BRUSH = QBrush(QColor(255, 230, 230))
        self.BLUE_BRUSH = QBrush(QColor(230, 230, 255))
        self.RED_TEXT = QColor(200, 0, 0)
        self.BLUE_TEXT = QColor(0, 0, 200)

    def rowCount(self, parent=None):
        return len(self._dataframe)

    def columnCount(self, parent=None):
        return len(self._dataframe.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        value = self._dataframe.iloc[index.row(), index.column()]
        col_name = self._dataframe.columns[index.column()]

        # 1. 표시 텍스트
        if role == Qt.ItemDataRole.DisplayRole:
            if col_name in ['현재가', '전일대비', '시가', '고가', '저가', '거래량', '거래대금', '시가총액', '상장주식수']:
                return f"{value:,}"
            elif col_name == '등락률':  # 등락률은 %로 표시
                return f"{value:.2f}%"
            return str(value)
        elif role == Qt.ItemDataRole.EditRole:
            return value  # 원본 값 (편집용)

        # 2. 정렬
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col_name in ['현재가', '변동코드', '전일대비', '등락률', '시가', '고가', '저가', '거래량', '거래대금', '시가총액', '상장주식수']:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        # 4. 등락률 색상 (핵심!)
        if role == Qt.ItemDataRole.BackgroundRole and col_name == '등락률':
            if value > 0:  # 상승: 연한 빨강 배경
                return self.RED_BRUSH
            else:  # 급락: 연한 파랑 배경
                return self.BLUE_BRUSH

        if role == Qt.ItemDataRole.ForegroundRole and col_name == '등락률':
            if value > 0:  # 상승: 진한 빨강 글씨
                return self.RED_TEXT
            else:  # 하락: 진한 파랑 글씨
                return self.BLUE_TEXT

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            # 가로 헤더가 아닌 '세로 헤더(Vertical)'일 때
            if orientation == Qt.Orientation.Vertical:
                # section은 현재 화면에 보이는 행의 순서(0부터 시작)입니다.
                # 여기에 1을 더하면 정렬 후에도 위에서부터 1, 2, 3... 순서가 유지됩니다.
                return str(section + 1)
            # 가로 헤더(컬럼명) 처리 (예시)
            if orientation == Qt.Orientation.Horizontal:
                return str(self._dataframe.columns[section])
        return super().headerData(section, orientation, role)

    def flags(self, index):
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    """헤더 클릭 시 호출되는 메서드"""
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        self.layoutAboutToBeChanged.emit()  # 변경 시작 알림

        col_name = self._dataframe.columns[column]
        ascending = (order == Qt.SortOrder.AscendingOrder)

        # 실제 정렬 (Pandas는 매우 빠름)
        self._dataframe.sort_values(by=col_name, ascending=ascending, inplace=True)
        # 인덱스 초기화를 해줘야 이후 iloc 접근 시 혼선이 없습니다.
        self._dataframe.reset_index(drop=True, inplace=True)

        self.layoutChanged.emit()  # 변경 완료 알림

    # 🔥 전체 DataFrame 교체용 메서드
    def update(self, new_df):
        self.beginResetModel()
        # 데이터 프레임 정리
        self._dataframe = new_df.copy()  # 원본 보호를 위해 복사본 생성 권장
        self._dataframe.replace(["nan", "NaN", "None"], "", inplace=True)
        # inf 값을 NaN으로 변환 후 전체를 빈 문자열로 채움
        self._dataframe.replace([np.inf, -np.inf], np.nan, inplace=True)
        self._dataframe.fillna("", inplace=True)
        self.endResetModel()

    # row의 컬럼 값 가져오기
    def get_data_by_name(self, row, column_name):
        try:
            # Pandas Index 객체에서 열 이름으로 위치(숫자) 찾기
            col_idx = self._dataframe.columns.get_loc(column_name)
            return self.index(row, col_idx).data()
        except KeyError:
            # 컬럼 이름이 없을 경우 예외 처리
            print(f"Error: '{column_name}' 컬럼을 찾을 수 없습니다.")
            return None
