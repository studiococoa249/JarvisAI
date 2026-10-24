import sys
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme, setThemeColor

from ui.main_window import MainWindow

def main():
    # Mengaktifkan high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("TikTok Live AI Voice Assistant")

    # Set tema Fluent Design (Light / Dark)
    setTheme(Theme.AUTO)
    # Warna aksen modern biru toska / cyan
    setThemeColor("#0078d4")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
