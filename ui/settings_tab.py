from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
)
from qfluentwidgets import (
    ScrollArea, SimpleCardWidget, LineEdit, PasswordLineEdit,
    ComboBox, Slider, TextEdit, PrimaryPushButton, PushButton,
    SubtitleLabel, BodyLabel, CaptionLabel, InfoBar, InfoBarPosition,
    FluentIcon as FIF, SwitchButton
)
from tts_engine import AVAILABLE_VOICES

class SettingsTab(ScrollArea):
    save_requested = Signal()
    voice_changed = Signal(str)                       # (voice_id)
    test_voice_requested = Signal(str, str, str, str) # (voice, rate, pitch, volume)
    test_ai_requested = Signal(str, str, str)         # (provider, key, model)
    sim_comment_requested = Signal(str, str)          # (username, comment)
    sim_join_requested = Signal(str)                  # (username)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self._init_ui()

    def _init_ui(self):
        self.setWidgetResizable(True)
        container = QWidget()
        self.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 20, 24, 20)

        # 1. PENGATURAN KECERDASAN BUATAN (AI PROVIDER)
        ai_card = SimpleCardWidget(container)
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(20, 16, 20, 16)
        ai_layout.setSpacing(14)

        ai_title = SubtitleLabel("Penyedia Kecerdasan Buatan (AI Engine)", ai_card)
        ai_layout.addWidget(ai_title)

        grid_ai = QGridLayout()
        grid_ai.setSpacing(12)

        # Provider Selector
        lbl_prov = BodyLabel("Layanan AI:", ai_card)
        self.combo_provider = ComboBox(ai_card)
        self.combo_provider.addItem("Google Gemini AI (Gratis & Cepat)", userData="gemini")
        self.combo_provider.addItem("Mode Cerdas Lokal (Tanpa API Key)", userData="smart_rules")

        curr_prov = self.config.get("ai_provider", "gemini")
        for i in range(self.combo_provider.count()):
            if self.combo_provider.itemData(i) == curr_prov:
                self.combo_provider.setCurrentIndex(i)
                break

        grid_ai.addWidget(lbl_prov, 0, 0)
        grid_ai.addWidget(self.combo_provider, 0, 1, 1, 2)

        # 1. Gemini API Key Input
        lbl_gemini = BodyLabel("Gemini API Key:", ai_card)
        self.input_gemini_key = PasswordLineEdit(ai_card)
        self.input_gemini_key.setPlaceholderText("Google Gemini API Key")
        self.input_gemini_key.setText(self.config.get("gemini_api_key", ""))
        self.input_gemini_key.setClearButtonEnabled(True)

        self.btn_test_gemini = PushButton(FIF.IOT, "Uji Gemini", ai_card)
        self.btn_test_gemini.clicked.connect(self._on_test_gemini_clicked)

        grid_ai.addWidget(lbl_gemini, 1, 0)
        grid_ai.addWidget(self.input_gemini_key, 1, 1)
        grid_ai.addWidget(self.btn_test_gemini, 1, 2)

        # 2. Gemini Model Selector
        lbl_model = BodyLabel("Model Gemini:", ai_card)
        self.combo_gemini_model = ComboBox(ai_card)
        self.combo_gemini_model.addItems(["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"])
        curr_model = self.config.get("gemini_model", "gemini-3.5-flash-lite")
        idx_m = self.combo_gemini_model.findText(curr_model)
        if idx_m >= 0:
            self.combo_gemini_model.setCurrentIndex(idx_m)

        grid_ai.addWidget(lbl_model, 2, 0)
        grid_ai.addWidget(self.combo_gemini_model, 2, 1, 1, 2)

        # 3. TikTok Session ID (untuk bypass WAF)
        lbl_session = BodyLabel("TikTok Session ID (Opsional):", ai_card)
        self.input_session_id = LineEdit(ai_card)
        self.input_session_id.setPlaceholderText("Kosongkan jika tidak diperlukan (lihat petunjuk di bawah)")
        self.input_session_id.setText(self.config.get("tiktok_session_id", ""))
        self.input_session_id.setClearButtonEnabled(True)

        grid_ai.addWidget(lbl_session, 3, 0)
        grid_ai.addWidget(self.input_session_id, 3, 1, 1, 2)

        session_hint = CaptionLabel(
            "Jika gagal konek live (WAF block), buka TikTok di browser → F12 → Application → Cookies → salin nilai 'sessionid'",
            ai_card
        )
        session_hint.setWordWrap(True)
        grid_ai.addWidget(session_hint, 4, 0, 1, 3)

        ai_layout.addLayout(grid_ai)

        # System Instruction / Persona
        lbl_prompt = BodyLabel("Instruksi Karakter / Persona AI:", ai_card)
        ai_layout.addWidget(lbl_prompt)

        self.input_prompt = TextEdit(ai_card)
        self.input_prompt.setPlainText(self.config.get("ai_system_prompt", ""))
        self.input_prompt.setMaximumHeight(85)
        ai_layout.addWidget(self.input_prompt)

        layout.addWidget(ai_card)

        # 2. PENGATURAN SUARA VOICE (MANUSIA ASLI & NATURAL)
        tts_card = SimpleCardWidget(container)
        tts_layout = QVBoxLayout(tts_card)
        tts_layout.setContentsMargins(20, 16, 20, 16)
        tts_layout.setSpacing(14)

        tts_title = SubtitleLabel("🎙️ Karakter Suara Voice AI (Manusia Asli)", tts_card)
        tts_layout.addWidget(tts_title)

        tts_hint = CaptionLabel(
            "Pilihan karakter bertanda 🌟 menghasilkan suara manusia asli super jernih & ekspresif (Gemini AI). Setiap kali Anda memilih karakter suara, pengaturannya otomatis langsung tersinkronisasi ke Live TikTok.",
            tts_card
        )
        tts_hint.setWordWrap(True)
        tts_layout.addWidget(tts_hint)

        grid_tts = QGridLayout()
        grid_tts.setSpacing(12)

        # Voice selection
        lbl_voice = BodyLabel("Pilihan Karakter Suara:", tts_card)
        self.combo_voice = ComboBox(tts_card)
        for v in AVAILABLE_VOICES:
            self.combo_voice.addItem(v["name"], userData=v["id"])

        curr_voice = self.config.get("tts_voice", "gemini_Kore")
        for i in range(self.combo_voice.count()):
            if self.combo_voice.itemData(i) == curr_voice:
                self.combo_voice.setCurrentIndex(i)
                break

        # Otomatis sinkron saat pilihan suara diubah
        self.combo_voice.currentIndexChanged.connect(self._on_voice_combo_changed)

        grid_tts.addWidget(lbl_voice, 0, 0)
        grid_tts.addWidget(self.combo_voice, 0, 1, 1, 2)

        # Rate / Kecepatan
        lbl_rate = BodyLabel("Kecepatan Suara:", tts_card)
        self.slider_rate = Slider(Qt.Orientation.Horizontal, tts_card)
        self.slider_rate.setRange(-50, 100)
        init_rate = self._parse_pct(self.config.get("tts_rate", "+0%"))
        self.slider_rate.setValue(init_rate)
        self.lbl_rate_val = CaptionLabel(f"{init_rate:+d}%", tts_card)
        self.slider_rate.valueChanged.connect(self._on_rate_slider_changed)

        grid_tts.addWidget(lbl_rate, 1, 0)
        grid_tts.addWidget(self.slider_rate, 1, 1)
        grid_tts.addWidget(self.lbl_rate_val, 1, 2)

        # Pitch / Nada
        lbl_pitch = BodyLabel("Nada Suara (Pitch):", tts_card)
        self.slider_pitch = Slider(Qt.Orientation.Horizontal, tts_card)
        self.slider_pitch.setRange(-50, 50)
        init_pitch = self._parse_hz(self.config.get("tts_pitch", "+0Hz"))
        self.slider_pitch.setValue(init_pitch)
        self.lbl_pitch_val = CaptionLabel(f"{init_pitch:+d}Hz", tts_card)
        self.slider_pitch.valueChanged.connect(self._on_pitch_slider_changed)

        grid_tts.addWidget(lbl_pitch, 2, 0)
        grid_tts.addWidget(self.slider_pitch, 2, 1)
        grid_tts.addWidget(self.lbl_pitch_val, 2, 2)

        tts_layout.addLayout(grid_tts)

        # Test Voice Button
        self.btn_test_voice = PushButton(FIF.PLAY, "Dengarkan Contoh Suara (Test Voice)", tts_card)
        self.btn_test_voice.clicked.connect(self._on_test_voice_clicked)
        tts_layout.addWidget(self.btn_test_voice)

        layout.addWidget(tts_card)

        # 3. PENGATURAN ANTREAN & KECEPATAN RESPON LIVE
        queue_card = SimpleCardWidget(container)
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(20, 16, 20, 16)
        queue_layout.setSpacing(14)

        queue_title = SubtitleLabel("⚡ Kecepatan Respon & Antrean Suara (Real-Time)", queue_card)
        queue_layout.addWidget(queue_title)

        queue_hint = CaptionLabel(
            "Sesuaikan pengaturan di bawah agar bot selalu membacakan komentar penonton yang paling baru dan tidak tertinggal saat chat sedang ramai.",
            queue_card
        )
        queue_hint.setWordWrap(True)
        queue_layout.addWidget(queue_hint)

        grid_queue = QGridLayout()
        grid_queue.setSpacing(12)

        # 1. Prioritaskan Komentar Terbaru
        lbl_prio = BodyLabel("Prioritaskan Komentar Terbaru:", queue_card)
        self.switch_prioritize_latest = SwitchButton(queue_card)
        self.switch_prioritize_latest.setOnText("Aktif (Auto-Catch Up)")
        self.switch_prioritize_latest.setOffText("Nonaktif (Antre Berurutan)")
        self.switch_prioritize_latest.setChecked(self.config.get("prioritize_latest", True))
        grid_queue.addWidget(lbl_prio, 0, 0)
        grid_queue.addWidget(self.switch_prioritize_latest, 0, 1, 1, 2)

        prio_desc = CaptionLabel("Saat komentar menumpuk, bot otomatis melewati antrean lama dan langsung membacakan komentar paling baru.", queue_card)
        prio_desc.setWordWrap(True)
        grid_queue.addWidget(prio_desc, 1, 0, 1, 3)

        # 2. Batas Maksimal Antrean (Max Queue Size)
        lbl_mq = BodyLabel("Batas Maksimal Antrean Suara:", queue_card)
        self.slider_max_queue = Slider(Qt.Orientation.Horizontal, queue_card)
        self.slider_max_queue.setRange(1, 10)
        init_mq = self.config.get("max_queue_size", 3)
        self.slider_max_queue.setValue(init_mq)
        self.lbl_max_queue_val = CaptionLabel(f"{init_mq} komentar", queue_card)
        self.slider_max_queue.valueChanged.connect(lambda v: self.lbl_max_queue_val.setText(f"{v} komentar"))
        grid_queue.addWidget(lbl_mq, 2, 0)
        grid_queue.addWidget(self.slider_max_queue, 2, 1)
        grid_queue.addWidget(self.lbl_max_queue_val, 2, 2)

        # 3. Batas Kedaluwarsa Komentar (TTL)
        lbl_ttl = BodyLabel("Batas Kedaluwarsa Komentar:", queue_card)
        self.slider_queue_ttl = Slider(Qt.Orientation.Horizontal, queue_card)
        self.slider_queue_ttl.setRange(10, 60)
        init_ttl = self.config.get("queue_ttl_sec", 20)
        self.slider_queue_ttl.setValue(init_ttl)
        self.lbl_queue_ttl_val = CaptionLabel(f"{init_ttl} detik", queue_card)
        self.slider_queue_ttl.valueChanged.connect(lambda v: self.lbl_queue_ttl_val.setText(f"{v} detik"))
        grid_queue.addWidget(lbl_ttl, 3, 0)
        grid_queue.addWidget(self.slider_queue_ttl, 3, 1)
        grid_queue.addWidget(self.lbl_queue_ttl_val, 3, 2)

        # 4. Jeda Antar Komentar Per Penonton
        lbl_cd = BodyLabel("Jeda Komentar Per Penonton (Anti-Spam):", queue_card)
        self.slider_user_cooldown = Slider(Qt.Orientation.Horizontal, queue_card)
        self.slider_user_cooldown.setRange(2, 30)
        init_cd = self.config.get("user_comment_cooldown_sec", 8)
        self.slider_user_cooldown.setValue(init_cd)
        self.lbl_user_cooldown_val = CaptionLabel(f"{init_cd} detik", queue_card)
        self.slider_user_cooldown.valueChanged.connect(lambda v: self.lbl_user_cooldown_val.setText(f"{v} detik"))
        grid_queue.addWidget(lbl_cd, 4, 0)
        grid_queue.addWidget(self.slider_user_cooldown, 4, 1)
        grid_queue.addWidget(self.lbl_user_cooldown_val, 4, 2)

        queue_layout.addLayout(grid_queue)
        layout.addWidget(queue_card)

        # 4. KARTU SIMULATOR UJI COBA RESPON AI & SUARA
        sim_card = SimpleCardWidget(container)
        sim_layout = QVBoxLayout(sim_card)
        sim_layout.setContentsMargins(20, 16, 20, 16)
        sim_layout.setSpacing(12)

        sim_title = SubtitleLabel("🧪 Simulator Pengujian Respon AI & Suara", sim_card)
        sim_layout.addWidget(sim_title)

        sim_caption = CaptionLabel(
            "Uji coba respon AI dan suara di sini sebelum memulai live TikTok. Balasan akan langsung disuarakan dan masuk ke tabel Live Monitor.",
            sim_card
        )
        sim_layout.addWidget(sim_caption)

        row_sim = QHBoxLayout()
        row_sim.setSpacing(10)

        self.sim_user = LineEdit(sim_card)
        self.sim_user.setPlaceholderText("Nama Penonton")
        self.sim_user.setText("Budi")
        self.sim_user.setMaximumWidth(140)

        self.sim_comment = LineEdit(sim_card)
        self.sim_comment.setPlaceholderText("Tulis komentar uji coba (contoh: kak mau beli bajunya)")
        self.sim_comment.setText("kak tolong spill baju hitamnya dong")

        self.btn_sim_comment = PushButton(FIF.SEND, "Kirim Komentar", sim_card)
        self.btn_sim_comment.clicked.connect(self._on_sim_comment_clicked)

        self.btn_sim_join = PushButton(FIF.ADD, "Simulasi Join", sim_card)
        self.btn_sim_join.clicked.connect(self._on_sim_join_clicked)

        row_sim.addWidget(self.sim_user)
        row_sim.addWidget(self.sim_comment, stretch=1)
        row_sim.addWidget(self.btn_sim_comment)
        row_sim.addWidget(self.btn_sim_join)
        sim_layout.addLayout(row_sim)

        layout.addWidget(sim_card)

        # 5. KARTU DATABASE MONGODB CLOUD
        db_card = SimpleCardWidget(container)
        db_layout = QVBoxLayout(db_card)
        db_layout.setContentsMargins(20, 16, 20, 16)
        db_layout.setSpacing(12)

        db_title = SubtitleLabel("☁️ Database Cloud (MongoDB Atlas)", db_card)
        db_layout.addWidget(db_title)

        is_mongo = getattr(self.config, "using_mongodb", False)
        status_txt = f"🟢 Terhubung ({self.config.db_name}.{self.config.collection_name})" if is_mongo else f"🔴 Terputus ({self.config.db_error or 'Periksa .env'})"
        self.lbl_mongo_status = CaptionLabel(
            f"Status Database: {status_txt}. Seluruh setup (AI, scope, prompt, filter kata kunci, suara, akun TikTok) disimpan 100% ke Cloud MongoDB Atlas tanpa ada file lokal.",
            db_card
        )
        self.lbl_mongo_status.setWordWrap(True)
        db_layout.addWidget(self.lbl_mongo_status)

        row_db = QHBoxLayout()
        row_db.setSpacing(10)

        self.btn_sync_to_db = PushButton(FIF.UP, "Unggah Setup ke MongoDB", db_card)
        self.btn_sync_to_db.clicked.connect(self._on_sync_to_db_clicked)

        self.btn_sync_from_db = PushButton(FIF.DOWNLOAD, "Muat Ulang dari MongoDB", db_card)
        self.btn_sync_from_db.clicked.connect(self._on_sync_from_db_clicked)

        row_db.addWidget(self.btn_sync_to_db)
        row_db.addWidget(self.btn_sync_from_db)
        row_db.addStretch()
        db_layout.addLayout(row_db)

        layout.addWidget(db_card)

        # 6. TOMBOL SIMPAN PENGATURAN
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.btn_save = PrimaryPushButton(FIF.SAVE, "Simpan Semua Pengaturan", container)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_save.setMinimumWidth(220)
        bottom_layout.addWidget(self.btn_save)

        layout.addLayout(bottom_layout)
        layout.addStretch()



    def _parse_pct(self, val_str: str) -> int:
        try:
            return int(val_str.replace("%", "").replace("+", ""))
        except Exception:
            return 0

    def _parse_hz(self, val_str: str) -> int:
        try:
            return int(val_str.replace("Hz", "").replace("+", ""))
        except Exception:
            return 0



    def _on_voice_combo_changed(self, index: int):
        voice_id = self.combo_voice.itemData(index)
        if voice_id:
            self.config.set("tts_voice", voice_id)
            self.config.save()
            self.voice_changed.emit(voice_id)

    def _on_rate_slider_changed(self, v: int):
        self.lbl_rate_val.setText(f"{v:+d}%")
        self.config.set("tts_rate", f"{v:+d}%")

    def _on_pitch_slider_changed(self, v: int):
        self.lbl_pitch_val.setText(f"{v:+d}Hz")
        self.config.set("tts_pitch", f"{v:+d}Hz")

    def _on_test_gemini_clicked(self):
        key = self.input_gemini_key.text().strip()
        model = self.combo_gemini_model.currentText()
        if not key:
            InfoBar.warning(
                title="Gemini Key Kosong",
                content="Masukkan Gemini API Key terlebih dahulu.",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        self.test_ai_requested.emit("gemini", key, model)

    def _on_test_voice_clicked(self):
        voice_id = self.combo_voice.currentData()
        rate = f"{self.slider_rate.value():+d}%"
        pitch = f"{self.slider_pitch.value():+d}Hz"
        volume = "+0%"
        self.test_voice_requested.emit(voice_id, rate, pitch, volume)

    def _on_save_clicked(self):
        self.config.set("ai_provider", self.combo_provider.currentData())
        self.config.set("gemini_api_key", self.input_gemini_key.text().strip())
        self.config.set("gemini_model", self.combo_gemini_model.currentText())
        self.config.set("ai_system_prompt", self.input_prompt.toPlainText().strip())
        self.config.set("tiktok_session_id", self.input_session_id.text().strip())
        self.config.set("tts_voice", self.combo_voice.currentData())
        self.config.set("tts_rate", f"{self.slider_rate.value():+d}%")
        self.config.set("tts_pitch", f"{self.slider_pitch.value():+d}Hz")
        self.config.set("max_queue_size", self.slider_max_queue.value())
        self.config.set("prioritize_latest", self.switch_prioritize_latest.isChecked())
        self.config.set("queue_ttl_sec", self.slider_queue_ttl.value())
        self.config.set("user_comment_cooldown_sec", self.slider_user_cooldown.value())
        self.config.save()

        if getattr(self.config, "using_mongodb", False):
            save_msg = f"Pengaturan berhasil disimpan 100% ke Cloud Database MongoDB ({self.config.db_name}.{self.config.collection_name})."
            self.lbl_mongo_status.setText(f"Status Database: 🟢 Terhubung ({self.config.db_name}.{self.config.collection_name}). Setup tersimpan di Cloud MongoDB.")
        else:
            save_msg = f"Gagal menyimpan ke Cloud: {self.config.db_error or 'Periksa .env'}"

        if getattr(self.config, "using_mongodb", False):
            InfoBar.success(
                title="Tersimpan di Cloud",
                content=save_msg,
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=3500,
                parent=self
            )
        else:
            InfoBar.error(
                title="Gagal Simpan Cloud",
                content=save_msg,
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
        self.save_requested.emit()

    def _on_sync_to_db_clicked(self):
        # Update settings from UI
        self.config.set("ai_provider", self.combo_provider.currentData())
        self.config.set("gemini_api_key", self.input_gemini_key.text().strip())
        self.config.set("gemini_model", self.combo_gemini_model.currentText())
        self.config.set("ai_system_prompt", self.input_prompt.toPlainText().strip())
        self.config.set("tiktok_session_id", self.input_session_id.text().strip())
        self.config.set("tts_voice", self.combo_voice.currentData())
        self.config.set("tts_rate", f"{self.slider_rate.value():+d}%")
        self.config.set("tts_pitch", f"{self.slider_pitch.value():+d}Hz")
        self.config.set("max_queue_size", self.slider_max_queue.value())
        self.config.set("prioritize_latest", self.switch_prioritize_latest.isChecked())
        self.config.set("queue_ttl_sec", self.slider_queue_ttl.value())
        self.config.set("user_comment_cooldown_sec", self.slider_user_cooldown.value())

        ok, msg = self.config.sync_to_mongodb()
        if ok:
            InfoBar.success(
                title="Sinkronisasi Berhasil",
                content=msg,
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=3500,
                parent=self
            )
            self.lbl_mongo_status.setText(f"Status Database: 🟢 Terhubung ({self.config.db_name}.{self.config.collection_name}). Setup tersimpan di Cloud MongoDB.")
        else:
            InfoBar.error(
                title="Sinkronisasi Gagal",
                content=msg,
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )

    def _on_sync_from_db_clicked(self):
        ok, msg = self.config.sync_from_mongodb()
        if ok:
            self.input_gemini_key.setText(self.config.get("gemini_api_key", ""))
            self.input_prompt.setPlainText(self.config.get("ai_system_prompt", ""))
            self.input_session_id.setText(self.config.get("tiktok_session_id", ""))
            curr_prov = self.config.get("ai_provider", "gemini")
            for i in range(self.combo_provider.count()):
                if self.combo_provider.itemData(i) == curr_prov:
                    self.combo_provider.setCurrentIndex(i)
                    break
            curr_voice = self.config.get("tts_voice", "gemini_Kore")
            for i in range(self.combo_voice.count()):
                if self.combo_voice.itemData(i) == curr_voice:
                    self.combo_voice.setCurrentIndex(i)
                    break
            self.slider_rate.setValue(self._parse_pct(self.config.get("tts_rate", "+0%")))
            self.slider_pitch.setValue(self._parse_hz(self.config.get("tts_pitch", "+0Hz")))
            self.slider_max_queue.setValue(self.config.get("max_queue_size", 3))
            self.switch_prioritize_latest.setChecked(self.config.get("prioritize_latest", True))
            self.slider_queue_ttl.setValue(self.config.get("queue_ttl_sec", 20))
            self.slider_user_cooldown.setValue(self.config.get("user_comment_cooldown_sec", 8))

            InfoBar.success(
                title="Berhasil Dimuat",
                content=msg,
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=3500,
                parent=self
            )
            self.lbl_mongo_status.setText(f"Status Database: 🟢 Terhubung ({self.config.db_name}.{self.config.collection_name}). Setup terbaru dimuat dari Cloud.")
            self.save_requested.emit()
        else:
            InfoBar.error(
                title="Gagal Memuat dari MongoDB",
                content=msg,
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )

    def _on_sim_comment_clicked(self):
        user = self.sim_user.text().strip() or "Penonton"
        comment = self.sim_comment.text().strip()
        if not comment:
            InfoBar.warning(
                title="Komentar Kosong",
                content="Masukkan teks komentar uji coba terlebih dahulu.",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self
            )
            return
        self.sim_comment_requested.emit(user, comment)

    def _on_sim_join_clicked(self):
        user = self.sim_user.text().strip() or "Penonton"
        self.sim_join_requested.emit(user)
