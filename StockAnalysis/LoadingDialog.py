from PySide6.QtGui import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar


class LoadingDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        # 1. 창 설정 (제목 표시줄 제거, 항상 위에 표시)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowTitleHint | Qt.WindowType.CustomizeWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)  # 창이 떠 있는 동안 메인창 클릭 불가
        self.setWindowTitle(title)
        self.setFixedSize(300, 100)

        layout = QVBoxLayout(self)

        # 2. 메시지 레이블
        self.label = QLabel(message, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        # 3. 진행바 설정 (핵심: Range를 0, 0으로 설정)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)  # 최소/최대값이 0이면 무한 왕복 애니메이션이 됩니다.
        self.progress.setTextVisible(False)  # 숫자(%) 숨기기
        layout.addWidget(self.progress)
