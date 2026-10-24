from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
)
from qfluentwidgets import (
    ScrollArea, SimpleCardWidget, LineEdit, PasswordLineEdit,
    ComboBox, Slider, TextEdit, PrimaryPushButton, PushButton,
    SubtitleLabel, BodyLabel, CaptionLabel, InfoBar, InfoBarPosition,
    FluentIcon as FIF, SwitchButton, SpinBox
)
from tts_engine import AVAILABLE_VOICES

class SettingsTab(ScrollArea):
    save_requested = Signal()
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

        ai_layout.addLayout(grid_ai)

        # System Instruction / Persona
        lbl_prompt = BodyLabel("Instruksi Karakter / Persona AI:", ai_card)
        ai_layout.addWidget(lbl_prompt)

        self.input_prompt = TextEdit(ai_card)
        self.input_prompt.setPlainText(self.config.get("ai_system_prompt", ""))
        self.input_prompt.setMaximumHeight(85)
        ai_layout.addWidget(self.input_prompt)

        layout.addWidget(ai_card)

        # 2. RUANG LINGKUP & ATURAN KETAT AI (AI SCOPE)
        scope_card = SimpleCardWidget(container)
        scope_layout = QVBoxLayout(scope_card)
        scope_layout.setContentsMargins(20, 16, 20, 16)
        scope_layout.setSpacing(14)

        scope_title = SubtitleLabel("🎯 Ruang Lingkup & Aturan AI (AI Scope)", scope_card)
        scope_layout.addWidget(scope_title)

        scope_desc = CaptionLabel(
            "Tentukan fokus topik live streaming, batasan kata, dan aturan ketat agar AI membalas tepat sasaran dan tidak melenceng.",
            scope_card
        )
        scope_layout.addWidget(scope_desc)

        grid_scope = QGridLayout()
        grid_scope.setSpacing(12)

        # 1. Topik / Fokus Live Streaming
        lbl_topic = BodyLabel("Topik / Fokus Live:", scope_card)
        self.input_scope_topic = LineEdit(scope_card)
        self.input_scope_topic.setPlaceholderText("Contoh: Jualan & Spill Produk Keranjang Kuning, Fashion Pria/Wanita")
        self.input_scope_topic.setText(self.config.get("scope_topic", "Jualan & Spill Produk (Keranjang Kuning)"))
        self.input_scope_topic.setClearButtonEnabled(True)

        grid_scope.addWidget(lbl_topic, 0, 0)
        grid_scope.addWidget(self.input_scope_topic, 0, 1, 1, 2)

        # 2. Batasan Kata per Balasan
        lbl_max_words = BodyLabel("Maksimal Kata:", scope_card)
        self.spin_max_words = SpinBox(scope_card)
        self.spin_max_words.setRange(5, 50)
        self.spin_max_words.setValue(int(self.config.get("scope_max_words", 15)))
        self.spin_max_words.setSuffix(" kata")
        lbl_max_desc = CaptionLabel("Rekomendasi 10 - 15 kata agar suara TTS cepat dan tidak tertinggal percakapan", scope_card)

        grid_scope.addWidget(lbl_max_words, 1, 0)
        grid_scope.addWidget(self.spin_max_words, 1, 1)
        grid_scope.addWidget(lbl_max_desc, 1, 2)

        scope_layout.addLayout(grid_scope)

        # 3. Saklar Aturan Ketat (Switches)
        # Switch Strict DM
        row_strict_dm = QHBoxLayout()
        row_strict_dm.setContentsMargins(4, 2, 4, 2)
        self.switch_strict_dm = SwitchButton(scope_card)
        self.switch_strict_dm.setChecked(self.config.get("scope_strict_dm", True))
        lbl_dm_text = BodyLabel("Aturan Ketat Jajan/DM", scope_card)
        lbl_dm_cap = CaptionLabel("(Hanya tawarkan order/DM jika penonton bertanya harga/beli secara eksplisit)", scope_card)
        row_strict_dm.addWidget(self.switch_strict_dm)
        row_strict_dm.addSpacing(8)
        row_strict_dm.addWidget(lbl_dm_text)
        row_strict_dm.addWidget(lbl_dm_cap)
        row_strict_dm.addStretch()
        scope_layout.addLayout(row_strict_dm)

        # Switch Strict Topic
        row_strict_topic = QHBoxLayout()
        row_strict_topic.setContentsMargins(4, 2, 4, 2)
        self.switch_strict_topic = SwitchButton(scope_card)
        self.switch_strict_topic.setChecked(self.config.get("scope_strict_topic", True))
        lbl_topic_text = BodyLabel("Tetap Pada Topik Live", scope_card)
        lbl_topic_cap = CaptionLabel("(Arahkan kembali dengan sopan jika penonton berkomentar di luar konteks)", scope_card)
        row_strict_topic.addWidget(self.switch_strict_topic)
        row_strict_topic.addSpacing(8)
        row_strict_topic.addWidget(lbl_topic_text)
        row_strict_topic.addWidget(lbl_topic_cap)
        row_strict_topic.addStretch()
        scope_layout.addLayout(row_strict_topic)

        # Switch No Emoji/Markdown
        row_no_emoji = QHBoxLayout()
        row_no_emoji.setContentsMargins(4, 2, 4, 2)
        self.switch_no_emoji = SwitchButton(scope_card)
        self.switch_no_emoji.setChecked(self.config.get("scope_no_emoji", True))
        lbl_emoji_text = BodyLabel("Hapus Emoji & Markdown", scope_card)
        lbl_emoji_cap = CaptionLabel("(Cegah AI memunculkan emoji, simbol, dan markdown agar ucapan TTS jernih)", scope_card)
        row_no_emoji.addWidget(self.switch_no_emoji)
        row_no_emoji.addSpacing(8)
        row_no_emoji.addWidget(lbl_emoji_text)
        row_no_emoji.addWidget(lbl_emoji_cap)
        row_no_emoji.addStretch()
        scope_layout.addLayout(row_no_emoji)

        # 4. Aturan Kustom / Larangan Tambahan
        lbl_custom_rules = BodyLabel("Aturan Tambahan / Larangan Khusus (Custom Scope Rules):", scope_card)
        scope_layout.addWidget(lbl_custom_rules)

        self.input_scope_custom_rules = TextEdit(scope_card)
        self.input_scope_custom_rules.setPlaceholderText(
            "Tuliskan aturan tambahan untuk AI di sini. Contoh:\n"
            "- Pengiriman dilakukan dari Jakarta setiap jam 4 sore\n"
            "- Jangan menyebut atau membandingkan dengan merk lain\n"
            "- Selalu panggil penonton dengan sebutan Kakak\n"
            "- Voucher promo diskon 20% dapat diklaim di profil"
        )
        self.input_scope_custom_rules.setPlainText(self.config.get("scope_custom_rules", ""))
        self.input_scope_custom_rules.setMaximumHeight(85)
        scope_layout.addWidget(self.input_scope_custom_rules)

        layout.addWidget(scope_card)

        # 3. PENGATURAN SUARA VOICE (EDGE-TTS)
        tts_card = SimpleCardWidget(container)
        tts_layout = QVBoxLayout(tts_card)
        tts_layout.setContentsMargins(20, 16, 20, 16)
        tts_layout.setSpacing(14)

        tts_title = SubtitleLabel("Pengaturan Suara Voice AI (Edge-TTS Natural)", tts_card)
        tts_layout.addWidget(tts_title)

        grid_tts = QGridLayout()
        grid_tts.setSpacing(12)

        # Voice selection
        lbl_voice = BodyLabel("Pilihan Karakter Suara:", tts_card)
        self.combo_voice = ComboBox(tts_card)
        for v in AVAILABLE_VOICES:
            self.combo_voice.addItem(v["name"], userData=v["id"])

        curr_voice = self.config.get("tts_voice", "id-ID-GadisNeural")
        for i in range(self.combo_voice.count()):
            if self.combo_voice.itemData(i) == curr_voice:
                self.combo_voice.setCurrentIndex(i)
                break

        grid_tts.addWidget(lbl_voice, 0, 0)
        grid_tts.addWidget(self.combo_voice, 0, 1, 1, 2)

        # Rate / Kecepatan
        lbl_rate = BodyLabel("Kecepatan Suara:", tts_card)
        self.slider_rate = Slider(Qt.Orientation.Horizontal, tts_card)
        self.slider_rate.setRange(-50, 100)
        init_rate = self._parse_pct(self.config.get("tts_rate", "+0%"))
        self.slider_rate.setValue(init_rate)
        self.lbl_rate_val = CaptionLabel(f"{init_rate:+d}%", tts_card)
        self.slider_rate.valueChanged.connect(lambda v: self.lbl_rate_val.setText(f"{v:+d}%"))

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
        self.slider_pitch.valueChanged.connect(lambda v: self.lbl_pitch_val.setText(f"{v:+d}Hz"))

        grid_tts.addWidget(lbl_pitch, 2, 0)
        grid_tts.addWidget(self.slider_pitch, 2, 1)
        grid_tts.addWidget(self.lbl_pitch_val, 2, 2)

        tts_layout.addLayout(grid_tts)

        # Test Voice Button
        self.btn_test_voice = PushButton(FIF.PLAY, "Dengarkan Contoh Suara (Test Voice)", tts_card)
        self.btn_test_voice.clicked.connect(self._on_test_voice_clicked)
        tts_layout.addWidget(self.btn_test_voice)

        layout.addWidget(tts_card)

        # 3. KARTU SIMULATOR UJI COBA RESPON AI & SUARA
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

        # 4. TOMBOL SIMPAN PENGATURAN
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
        self.config.set("scope_topic", self.input_scope_topic.text().strip())
        self.config.set("scope_max_words", self.spin_max_words.value())
        self.config.set("scope_strict_dm", self.switch_strict_dm.isChecked())
        self.config.set("scope_strict_topic", self.switch_strict_topic.isChecked())
        self.config.set("scope_no_emoji", self.switch_no_emoji.isChecked())
        self.config.set("scope_custom_rules", self.input_scope_custom_rules.toPlainText().strip())
        self.config.set("tts_voice", self.combo_voice.currentData())
        self.config.set("tts_rate", f"{self.slider_rate.value():+d}%")
        self.config.set("tts_pitch", f"{self.slider_pitch.value():+d}Hz")
        self.config.save()

        InfoBar.success(
            title="Berhasil Disimpan",
            content="Pengaturan AI dan Voice berhasil diperbarui.",
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        self.save_requested.emit()

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
