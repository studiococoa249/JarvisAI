import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication
from qfluentwidgets import (
    TextEdit, PushButton, SubtitleLabel, CaptionLabel,
    FluentIcon as FIF, InfoBar, InfoBarPosition
)

class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QHBoxLayout()
        title = SubtitleLabel("Log Aktivitas & Sistem", self)
        header.addWidget(title)
        header.addStretch()

        self.btn_copy = PushButton(FIF.COPY, "Salin Log", self)
        self.btn_copy.clicked.connect(self._copy_log)
        header.addWidget(self.btn_copy)

        self.btn_clear = PushButton(FIF.DELETE, "Bersihkan", self)
        self.btn_clear.clicked.connect(self._clear_log)
        header.addWidget(self.btn_clear)

        layout.addLayout(header)

        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 12px;")
        layout.addWidget(self.log_text, stretch=1)

    def log(self, level: str, message: str):
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{now_str}] [{level.upper()}] {message}"
        self.log_text.append(line)

    def _clear_log(self):
        self.log_text.clear()

    def _copy_log(self):
        text = self.log_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            InfoBar.success(
                title="Tersalin",
                content="Log aktivitas berhasil disalin ke clipboard.",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
