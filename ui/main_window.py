import time
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon as FIF,
    InfoBar, InfoBarPosition, setTheme, Theme
)

from config_manager import ConfigManager
from ai_engine import AIEngine
from tts_engine import TTSEngine
from tiktok_worker import TikTokWorker
from ui.live_tab import LiveTab
from ui.scope_tab import ScopeTab
from ui.settings_tab import SettingsTab
from ui.filter_tab import FilterTab
from ui.log_tab import LogTab

class AIValidationThread(QThread):
    finished_check = Signal(bool, str, str)

    def __init__(self, ai_engine, provider: str, api_key: str, model: str, parent=None):
        super().__init__(parent)
        self.ai = ai_engine
        self.provider = provider
        self.api_key = api_key
        self.model = model

    def run(self):
        success, msg = self.ai.test_gemini(self.api_key, self.model)
        self.finished_check.emit(success, msg, self.provider)

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok Live AI Voice & Comment Assistant")
        self.resize(1100, 750)

        # Core Engines
        self.config_manager = ConfigManager()
        self.ai_engine = AIEngine(self.config_manager)
        self.tts_engine = TTSEngine(self.config_manager, self)
        self.tiktok_worker = None

        self._init_navigation()
        self._init_connections()

        self.log_tab.log("INFO", "Aplikasi TikTok Live Voice Assistant siap digunakan.")

    def _init_navigation(self):
        # 1. Tab Live Monitor
        self.live_tab = LiveTab(self.config_manager, self)
        self.live_tab.setObjectName("liveInterface")
        self.addSubInterface(self.live_tab, FIF.VIDEO, "Live Monitor")

        # 2. Tab Scope AI (Ruang Lingkup & Aturan)
        self.scope_tab = ScopeTab(self.config_manager, self)
        self.scope_tab.setObjectName("scopeInterface")
        self.addSubInterface(self.scope_tab, FIF.ROBOT, "Scope AI")

        # 3. Tab Filter & Kata Kunci
        self.filter_tab = FilterTab(self.config_manager, self)
        self.filter_tab.setObjectName("filterInterface")
        self.addSubInterface(self.filter_tab, FIF.FILTER, "Filter & Kata Kunci")

        # 4. Tab Pengaturan AI & Voice
        self.settings_tab = SettingsTab(self.config_manager, self)
        self.settings_tab.setObjectName("settingsInterface")
        self.addSubInterface(self.settings_tab, FIF.SETTING, "AI & Voice (TTS)")

        # 5. Tab Log
        self.log_tab = LogTab(self)
        self.log_tab.setObjectName("logInterface")
        self.addSubInterface(self.log_tab, FIF.DOCUMENT, "Log Sistem", NavigationItemPosition.BOTTOM)

    def _init_connections(self):
        # Live Tab signals
        self.live_tab.connect_requested.connect(self._start_tiktok_stream)
        self.live_tab.disconnect_requested.connect(self._stop_tiktok_stream)
        self.live_tab.skip_speech_requested.connect(self.tts_engine.skip_current)
        self.live_tab.clear_queue_requested.connect(self.tts_engine.clear_all)
        self.live_tab.mute_toggled.connect(self.tts_engine.set_muted)

        # TTS Engine signals
        self.tts_engine.started_speaking.connect(self._on_speech_started)
        self.tts_engine.finished_speaking.connect(self._on_speech_finished)
        self.tts_engine.queue_changed.connect(self.live_tab.update_queue_count)
        self.tts_engine.error_occurred.connect(lambda err: self.log_tab.log("ERROR", err))

        # Scope Tab signals
        self.scope_tab.save_requested.connect(self.live_tab.update_ai_mode_badge)

        # Settings Tab signals
        self.settings_tab.save_requested.connect(self.live_tab.update_ai_mode_badge)
        self.settings_tab.test_voice_requested.connect(self._test_voice)
        self.settings_tab.test_ai_requested.connect(self._test_ai_connection)
        self.settings_tab.sim_comment_requested.connect(self._handle_sim_comment)
        self.settings_tab.sim_join_requested.connect(self._handle_sim_join)

        # Filter Tab signals
        self.filter_tab.save_requested.connect(self.live_tab.update_ai_mode_badge)

    # --- TIKTOK STREAM CONNECTION ---
    def _start_tiktok_stream(self, username: str):
        if self.tiktok_worker and self.tiktok_worker.isRunning():
            self.tiktok_worker.stop()
            self.tiktok_worker.wait()

        self._was_connected = False
        self.log_tab.log("INFO", f"Mencoba menghubungkan ke live TikTok @{username}...")
        self.tiktok_worker = TikTokWorker(username, self.ai_engine, self.config_manager, self)
        self.tiktok_worker.connected.connect(self._on_worker_connected)
        self.tiktok_worker.disconnected.connect(self._on_worker_disconnected)
        self.tiktok_worker.status_changed.connect(self._on_worker_status_changed)
        self.tiktok_worker.comment_received.connect(self._on_comment_received)
        self.tiktok_worker.join_received.connect(self._on_join_received)
        self.tiktok_worker.error_occurred.connect(self._on_worker_error)

        self.tiktok_worker.start()

    def _stop_tiktok_stream(self):
        self._was_connected = False
        if self.tiktok_worker and self.tiktok_worker.isRunning():
            self.log_tab.log("INFO", "Menghentikan koneksi live streaming...")
            self.tiktok_worker.stop()
            self.tiktok_worker.wait(2000)
        self.live_tab.set_connected_state(False)

    def _on_worker_status_changed(self, msg: str):
        self.log_tab.log("INFO", msg)
        if "menyambungkan" in msg.lower() or "terputus" in msg.lower():
            self.live_tab.set_reconnecting_state(msg)

    def _on_worker_connected(self, username: str):
        first_time = not self._was_connected
        self._was_connected = True
        self.live_tab.set_connected_state(True, username)
        if first_time:
            self.log_tab.log("SUCCESS", f"Berhasil tersambung ke live @{username}")
            InfoBar.success(
                title="Tersambung",
                content=f"Berhasil terhubung ke live streaming TikTok @{username}",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=3500,
                parent=self.live_tab
            )
        else:
            self.log_tab.log("SUCCESS", f"Berhasil tersambung kembali (auto-reconnected) ke live @{username}")

    def _on_worker_disconnected(self):
        self._was_connected = False
        self.live_tab.set_connected_state(False)
        self.log_tab.log("INFO", "Koneksi live telah diputus.")

    def _on_worker_error(self, err_msg: str):
        self._was_connected = False
        self.live_tab.set_connected_state(False, status_detail=f"Offline: {err_msg}")
        self.log_tab.log("ERROR", err_msg)
        InfoBar.error(
            title="Gagal Terhubung Live",
            content=err_msg,
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.TOP,
            duration=5500,
            parent=self.live_tab
        )

    # --- EVENT HANDLERS ---
    def _on_comment_received(self, username: str, comment: str, reply: str, will_speak: bool):
        self.live_tab.add_event_row("Komentar", username, comment, reply, will_speak)
        log_msg = f"Komentar dari {username}: '{comment}' -> Balasan: '{reply}' (Bersuara: {will_speak})"
        self.log_tab.log("KOMENTAR", log_msg)

        if will_speak and reply:
            self.tts_engine.add_to_queue(username, reply, source="Komentar")

    def _on_join_received(self, username: str, greeting: str, will_speak: bool):
        self.live_tab.add_event_row("Gabung Live", username, "Bergabung ke live streaming", greeting, will_speak)
        self.log_tab.log("JOIN", f"{username} bergabung -> Sapaan: '{greeting}'")

        if will_speak and greeting:
            self.tts_engine.add_to_queue(username, greeting, source="Sapaan")

    def _on_speech_started(self, username: str, text: str):
        self.live_tab.set_speaking_status(username, text)
        self.log_tab.log("VOICE", f"Sedang membacakan: \"{text}\"")

    def _on_speech_finished(self):
        self.live_tab.set_speaking_status("", "")

    # --- SIMULATION (UJI COBA TANPA LIVE) ---
    def _handle_sim_comment(self, username: str, comment: str):
        self.log_tab.log("SIMULASI", f"Uji komentar dari {username}: '{comment}'")
        should_reply, reason, direct = self.ai_engine.should_reply(comment)

        if should_reply:
            reply = self.ai_engine.generate_reply(username, comment, direct)
            self._on_comment_received(username, comment, reply, True)
        else:
            self._on_comment_received(username, comment, f"(Dilewati: {reason})", False)

    def _handle_sim_join(self, username: str):
        self.log_tab.log("SIMULASI", f"Uji penonton bergabung: {username}")
        greeting = self.ai_engine.generate_greeting(username)
        self._on_join_received(username, greeting, True)

    # --- TESTING TOOLS ---
    def _test_voice(self, voice_id: str, rate: str, pitch: str, volume: str):
        # Sinkronkan pilihan suara dan slider ke config agar suara live PERSIS sama
        self.config.set("tts_voice", voice_id)
        self.config.set("tts_rate", rate)
        self.config.set("tts_pitch", pitch)
        self.config.set("tts_volume", volume)
        self.config.save()

        if "child" in voice_id or "toddler" in voice_id:
            sample_text = "Halo om dan tante! Selamat datang di live ya, jangan lupa tap-tap layar!"
        else:
            sample_text = "Halo semuanya! Selamat datang di siaran live streaming kami, selamat berbelanja ya!"
        self.log_tab.log("TEST", f"Menguji suara ({voice_id}) dengan kecepatan {rate} dan nada {pitch}...")
        self.tts_engine.add_to_queue("Preview", sample_text, source="Uji Suara", voice_id=voice_id)

    def _test_ai_connection(self, provider: str, api_key: str, model: str):
        label = f"Gemini ({model})"
        self.log_tab.log("INFO", f"Memeriksa koneksi {label}...")
        self.ai_thread = AIValidationThread(self.ai_engine, provider, api_key, model, self)
        self.ai_thread.finished_check.connect(self._on_ai_check_finished)
        self.ai_thread.start()

    def _on_ai_check_finished(self, success: bool, msg: str, provider: str = "gemini"):
        label = "Gemini API"
        if success:
            self.log_tab.log("SUCCESS", f"Koneksi {label} Valid: {msg}")
            InfoBar.success(
                title=f"Koneksi {label} Berhasil",
                content=f"Respon AI: \"{msg}\"",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self.settings_tab
            )
        else:
            self.log_tab.log("ERROR", f"Koneksi {label} Gagal: {msg}")
            InfoBar.error(
                title=f"Koneksi {label} Gagal",
                content=f"Detail: {msg}",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=5500,
                parent=self.settings_tab
            )

    def closeEvent(self, event):
        self._stop_tiktok_stream()
        self.tts_engine.clear_all()
        super().closeEvent(event)
