import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

# Fix Python 3.15 lazy import bug with concurrent.futures when Qt/PySide6 is loaded
import concurrent.futures.thread
import concurrent.futures.process
import concurrent.futures
concurrent.futures.ThreadPoolExecutor = concurrent.futures.thread.ThreadPoolExecutor
concurrent.futures.ProcessPoolExecutor = concurrent.futures.process.ProcessPoolExecutor

import subprocess
import importlib


REQUIRED_PACKAGES = {
    "PySide6": "PySide6",
    "qfluentwidgets": "PySide6-Fluent-Widgets",
    "TikTokLive": "TikTokLive",
    "edge_tts": "edge-tts",
    "google.genai": "google-genai",
    "pymongo": "pymongo",
    "dotenv": "python-dotenv",
}

def install_dependencies():
    missing = []
    for module_name, pkg_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pkg_name)
    
    if missing:
        print(f"[Setup] Library belum terinstall: {', '.join(missing)}")
        print("[Setup] Menginstall dependency via pip, mohon tunggu sebentar...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("[Setup] Instalasi library selesai!\n")
        except subprocess.CalledProcessError as e:
            print(f"[Error] Gagal menginstall library: {e}")
            sys.exit(1)

install_dependencies()

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
