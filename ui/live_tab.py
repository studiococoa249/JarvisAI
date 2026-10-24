import time
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidgetItem, QHeaderView
)
from qfluentwidgets import (
    CardWidget, SimpleCardWidget, PrimaryPushButton, PushButton,
    LineEdit, TableWidget, SubtitleLabel, CaptionLabel,
    BodyLabel, InfoBar, InfoBarPosition, FluentIcon as FIF,
    SwitchButton
)

class LiveTab(QWidget):
    connect_requested = Signal(str)   # username
    disconnect_requested = Signal()
    skip_speech_requested = Signal()
    clear_queue_requested = Signal()
    mute_toggled = Signal(bool)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.is_connected = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # 1. KONTROL KONEKSI LIVE
        conn_card = SimpleCardWidget(self)
        conn_layout = QHBoxLayout(conn_card)
        conn_layout.setContentsMargins(16, 12, 16, 12)
        conn_layout.setSpacing(12)

        lbl_user = BodyLabel("Username TikTok Live:", self)
        self.input_username = LineEdit(self)
        self.input_username.setPlaceholderText("Contoh: @toko_online / streamer123")
        self.input_username.setText(self.config.get("tiktok_username", ""))
        self.input_username.setClearButtonEnabled(True)
        self.input_username.setMinimumWidth(240)

        self.btn_connect = PrimaryPushButton(FIF.PLAY, "Hubungkan Live", self)
        self.btn_connect.clicked.connect(self._on_connect_clicked)

        self.lbl_status = CaptionLabel("Status: Offline", self)
        self.lbl_status.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px;")

        conn_layout.addWidget(lbl_user)
        conn_layout.addWidget(self.input_username)
        conn_layout.addWidget(self.btn_connect)
        conn_layout.addSpacing(10)
        conn_layout.addWidget(self.lbl_status)
        conn_layout.addStretch()

        # Status Badge AI
        self.lbl_ai_mode = CaptionLabel("", self)
        self.update_ai_mode_badge()
        conn_layout.addWidget(self.lbl_ai_mode)

        layout.addWidget(conn_card)

        # 2. STATUS SUARA & ANTREAN AUDIO
        voice_card = SimpleCardWidget(self)
        voice_layout = QHBoxLayout(voice_card)
        voice_layout.setContentsMargins(16, 12, 16, 12)
        voice_layout.setSpacing(16)

        left_voice = QVBoxLayout()
        self.lbl_now_speaking = SubtitleLabel("Suara: Menunggu...", self)
        self.lbl_now_speaking.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.lbl_speaking_detail = CaptionLabel("Belum ada komentar yang sedang dibacakan.", self)
        left_voice.addWidget(self.lbl_now_speaking)
        left_voice.addWidget(self.lbl_speaking_detail)
        voice_layout.addLayout(left_voice, stretch=1)

        self.lbl_queue_count = CaptionLabel("Antrean: 0", self)
        self.lbl_queue_count.setStyleSheet("font-weight: bold; font-size: 13px; color: #3498db;")
        voice_layout.addWidget(self.lbl_queue_count)

        self.btn_skip = PushButton(FIF.CHEVRON_RIGHT_MED, "Skip Suara", self)
        self.btn_skip.clicked.connect(self.skip_speech_requested.emit)
        voice_layout.addWidget(self.btn_skip)

        self.btn_clear_queue = PushButton(FIF.DELETE, "Kosongkan Antrean", self)
        self.btn_clear_queue.clicked.connect(self.clear_queue_requested.emit)
        voice_layout.addWidget(self.btn_clear_queue)

        self.switch_mute = SwitchButton(self)
        self.switch_mute.setOnText("Mute")
        self.switch_mute.setOffText("Bersuara")
        self.switch_mute.checkedChanged.connect(self.mute_toggled.emit)
        voice_layout.addWidget(self.switch_mute)

        layout.addWidget(voice_card)

        # 3. TABEL FEED REAL-TIME LIVE
        feed_header_layout = QHBoxLayout()
        feed_title = SubtitleLabel("Aktivitas Live TikTok Real-Time", self)
        feed_header_layout.addWidget(feed_title)
        feed_header_layout.addStretch()

        self.btn_clear_table = PushButton(FIF.DELETE, "Bersihkan Tabel", self)
        self.btn_clear_table.clicked.connect(self._clear_table)
        feed_header_layout.addWidget(self.btn_clear_table)
        layout.addLayout(feed_header_layout)

        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Waktu", "Tipe", "Penonton", "Pesan / Aktivitas", "Balasan Voice AI", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setWordWrap(True)

        layout.addWidget(self.table, stretch=1)

    def update_ai_mode_badge(self):
        provider = self.config.get("ai_provider", "gemini")
        if provider == "gemini":
            key = self.config.get("gemini_api_key", "").strip()
            if key:
                model = self.config.get("gemini_model", "gemini-3.5-flash-lite")
                self.lbl_ai_mode.setText(f"🤖 AI: Google Gemini ({model}) Aktif")
                self.lbl_ai_mode.setStyleSheet("color: #27ae60; font-weight: bold; background: rgba(39, 174, 96, 0.1); padding: 4px 8px; border-radius: 4px;")
                return
        self.lbl_ai_mode.setText("⚡ Mode Cerdas (Smart Rules)")
        self.lbl_ai_mode.setStyleSheet("color: #d35400; font-weight: bold; background: rgba(211, 84, 0, 0.1); padding: 4px 8px; border-radius: 4px;")

    def _on_connect_clicked(self):
        if not self.is_connected:
            username = self.input_username.text().strip()
            if not username:
                InfoBar.warning(
                    title="Username Kosong",
                    content="Silakan masukkan username TikTok Live terlebih dahulu.",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            self.config.set("tiktok_username", username)
            self.connect_requested.emit(username)
        else:
            self.disconnect_requested.emit()

    def set_connected_state(self, connected: bool, username: str = "", status_detail: str = ""):
        self.is_connected = connected
        if connected:
            self.btn_connect.setText("Putuskan Live")
            self.btn_connect.setIcon(FIF.PAUSE)
            self.lbl_status.setText(f"Status: Terhubung ke @{username}")
            self.lbl_status.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 13px;")
            self.input_username.setEnabled(False)
        else:
            self.btn_connect.setText("Hubungkan Live")
            self.btn_connect.setIcon(FIF.PLAY)
            self.lbl_status.setText(status_detail or "Status: Offline")
            self.lbl_status.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px;")
            self.input_username.setEnabled(True)

    def set_reconnecting_state(self, message: str):
        self.lbl_status.setText(f"Status: {message}")
        self.lbl_status.setStyleSheet("color: #f39c12; font-weight: bold; font-size: 13px;")

    def set_speaking_status(self, username: str, text: str):
        if text:
            self.lbl_now_speaking.setText(f"Sedang Berbicara (Untuk: {username})")
            self.lbl_speaking_detail.setText(f"\"{text}\"")
        else:
            self.lbl_now_speaking.setText("Suara: Menunggu...")
            self.lbl_speaking_detail.setText("Tidak ada audio yang sedang diputar.")

    def update_queue_count(self, count: int):
        self.lbl_queue_count.setText(f"Antrean: {count}")

    def add_event_row(self, event_type: str, username: str, message: str, reply: str, will_speak: bool):
        now_str = time.strftime("%H:%M:%S")
        row = 0
        self.table.insertRow(row)

        item_time = QTableWidgetItem(now_str)
        item_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        item_type = QTableWidgetItem(event_type)
        item_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        item_user = QTableWidgetItem(username)
        item_msg = QTableWidgetItem(message)
        item_reply = QTableWidgetItem(reply)

        status_text = "Bersuara" if will_speak else "Dilewati"
        item_status = QTableWidgetItem(status_text)
        item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        if will_speak:
            item_status.setForeground(Qt.GlobalColor.darkGreen)
        else:
            item_status.setForeground(Qt.GlobalColor.gray)

        self.table.setItem(row, 0, item_time)
        self.table.setItem(row, 1, item_type)
        self.table.setItem(row, 2, item_user)
        self.table.setItem(row, 3, item_msg)
        self.table.setItem(row, 4, item_reply)
        self.table.setItem(row, 5, item_status)

        # Batasi jumlah baris maksimal 200
        if self.table.rowCount() > 200:
            self.table.removeRow(self.table.rowCount() - 1)

    def _clear_table(self):
        self.table.setRowCount(0)
