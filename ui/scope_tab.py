from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
)
from qfluentwidgets import (
    ScrollArea, SimpleCardWidget, LineEdit, TextEdit,
    SpinBox, SwitchButton, PrimaryPushButton,
    SubtitleLabel, BodyLabel, CaptionLabel, InfoBar, InfoBarPosition,
    FluentIcon as FIF
)

class ScopeTab(ScrollArea):
    save_requested = Signal()

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

        # 1. KARTU TOPIK & INFORMASI PRODUK LIVE
        topic_card = SimpleCardWidget(container)
        topic_layout = QVBoxLayout(topic_card)
        topic_layout.setContentsMargins(20, 16, 20, 16)
        topic_layout.setSpacing(14)

        topic_title = SubtitleLabel("🎯 Ruang Lingkup & Fokus Live (Live Scope)", topic_card)
        topic_layout.addWidget(topic_title)

        topic_caption = CaptionLabel(
            "Tentukan tema live streaming dan informasi produk agar AI memiliki pengetahuan lengkap tentang apa yang Anda tawarkan.",
            topic_card
        )
        topic_layout.addWidget(topic_caption)

        grid_topic = QGridLayout()
        grid_topic.setSpacing(12)

        # Topik Live
        lbl_topic = BodyLabel("Fokus / Topik Siaran:", topic_card)
        self.input_scope_topic = LineEdit(topic_card)
        self.input_scope_topic.setPlaceholderText("Contoh: Jualan & Spill Produk Keranjang Kuning, Fashion Pria/Wanita")
        self.input_scope_topic.setText(self.config.get("scope_topic", "Jualan & Spill Produk (Keranjang Kuning)"))
        self.input_scope_topic.setClearButtonEnabled(True)

        grid_topic.addWidget(lbl_topic, 0, 0)
        grid_topic.addWidget(self.input_scope_topic, 0, 1, 1, 2)

        # Maksimal Kata
        lbl_max_words = BodyLabel("Maksimal Kata per Balasan:", topic_card)
        self.spin_max_words = SpinBox(topic_card)
        self.spin_max_words.setRange(5, 50)
        self.spin_max_words.setValue(int(self.config.get("scope_max_words", 15)))
        self.spin_max_words.setSuffix(" kata")
        lbl_words_hint = CaptionLabel("Rekomendasi 10 - 15 kata agar respon cepat dibacakan oleh suara TTS", topic_card)

        grid_topic.addWidget(lbl_max_words, 1, 0)
        grid_topic.addWidget(self.spin_max_words, 1, 1)
        grid_topic.addWidget(lbl_words_hint, 1, 2)

        topic_layout.addLayout(grid_topic)

        # Informasi Produk Toko (Knowledge Base)
        lbl_store = BodyLabel("Katalog & Detail Produk yang Dijual (Knowledge Toko):", topic_card)
        topic_layout.addWidget(lbl_store)

        self.input_store_info = TextEdit(topic_card)
        self.input_store_info.setPlaceholderText(
            "Tuliskan informasi produk yang sedang dijual di live ini. Contoh:\n"
            "- Produk 1: Kemeja Flanel Katun Premium (No 1 di etalase, harga promo Rp89.000, ukuran M-XXL)\n"
            "- Produk 2: Celana Chino Slim Fit (No 2 di etalase, harga Rp110.000, warna hitam & abu)\n"
            "- Pengiriman setiap hari jam 4 sore, bisa bayar COD ke seluruh Indonesia\n"
            "- Ada diskon voucher 10% jika tap keranjang kuning sekarang"
        )
        self.input_store_info.setPlainText(self.config.get("scope_store_info", ""))
        self.input_store_info.setMaximumHeight(110)
        topic_layout.addWidget(self.input_store_info)

        layout.addWidget(topic_card)

        # 2. KARTU BATASAN & ATURAN KETAT (STRICT CONSTRAINTS)
        rules_card = SimpleCardWidget(container)
        rules_layout = QVBoxLayout(rules_card)
        rules_layout.setContentsMargins(20, 16, 20, 16)
        rules_layout.setSpacing(14)

        rules_title = SubtitleLabel("🛡️ Batasan & Aturan Ketat Balasan (Strict Rules)", rules_card)
        rules_layout.addWidget(rules_title)

        rules_caption = CaptionLabel(
            "Pastikan AI tidak melenceng, tidak agresif mempromosikan jualan di waktu yang salah, dan tetap profesional.",
            rules_card
        )
        rules_layout.addWidget(rules_caption)

        # Switch 1: Strict DM
        row_strict_dm = QHBoxLayout()
        row_strict_dm.setContentsMargins(4, 2, 4, 2)
        self.switch_strict_dm = SwitchButton(rules_card)
        self.switch_strict_dm.setChecked(self.config.get("scope_strict_dm", True))
        lbl_dm_text = BodyLabel("Aturan Ketat Jajan / DM", rules_card)
        lbl_dm_cap = CaptionLabel("(HANYA tawarkan order/beli jika penonton jelas bertanya harga/cara order. Jangan tawarkan saat penonton menyapa biasa)", rules_card)
        row_strict_dm.addWidget(self.switch_strict_dm)
        row_strict_dm.addSpacing(8)
        row_strict_dm.addWidget(lbl_dm_text)
        row_strict_dm.addWidget(lbl_dm_cap)
        row_strict_dm.addStretch()
        rules_layout.addLayout(row_strict_dm)

        # Switch 2: Strict Topic
        row_strict_topic = QHBoxLayout()
        row_strict_topic.setContentsMargins(4, 2, 4, 2)
        self.switch_strict_topic = SwitchButton(rules_card)
        self.switch_strict_topic.setChecked(self.config.get("scope_strict_topic", True))
        lbl_topic_text = BodyLabel("Fokus Pada Topik Live", rules_card)
        lbl_topic_cap = CaptionLabel("(Arahkan kembali secara sopan jika penonton bertanya hal yang di luar konteks siaran live)", rules_card)
        row_strict_topic.addWidget(self.switch_strict_topic)
        row_strict_topic.addSpacing(8)
        row_strict_topic.addWidget(lbl_topic_text)
        row_strict_topic.addWidget(lbl_topic_cap)
        row_strict_topic.addStretch()
        rules_layout.addLayout(row_strict_topic)

        # Switch 3: No Emoji / Markdown
        row_no_emoji = QHBoxLayout()
        row_no_emoji.setContentsMargins(4, 2, 4, 2)
        self.switch_no_emoji = SwitchButton(rules_card)
        self.switch_no_emoji.setChecked(self.config.get("scope_no_emoji", True))
        lbl_emoji_text = BodyLabel("Larangan Emoji & Markdown", rules_card)
        lbl_emoji_cap = CaptionLabel("(Mencegah AI memunculkan emoji, tanda bintang, atau format markdown agar suara TTS jernih)", rules_card)
        row_no_emoji.addWidget(self.switch_no_emoji)
        row_no_emoji.addSpacing(8)
        row_no_emoji.addWidget(lbl_emoji_text)
        row_no_emoji.addWidget(lbl_emoji_cap)
        row_no_emoji.addStretch()
        rules_layout.addLayout(row_no_emoji)

        layout.addWidget(rules_card)

        # 3. KARTU ATURAN KHUSUS & LARANGAN TAMBAHAN
        custom_card = SimpleCardWidget(container)
        custom_layout = QVBoxLayout(custom_card)
        custom_layout.setContentsMargins(20, 16, 20, 16)
        custom_layout.setSpacing(12)

        custom_title = SubtitleLabel("📝 Aturan Tambahan & Larangan Khusus (Custom Rules)", custom_card)
        custom_layout.addWidget(custom_title)

        custom_caption = CaptionLabel(
            "Tuliskan aturan perilaku atau larangan spesifik yang WAJIB ditaati AI saat menjawab pertanyaan penonton.",
            custom_card
        )
        custom_layout.addWidget(custom_caption)

        self.input_scope_custom_rules = TextEdit(custom_card)
        self.input_scope_custom_rules.setPlaceholderText(
            "Tuliskan aturan tambahan Anda di sini. Contoh:\n"
            "- Selalu panggil penonton dengan sebutan 'Kakak'\n"
            "- Dilarang menyebut atau membandingkan produk dengan merk lain\n"
            "- Jika ditanya diskon, infokan voucher potongan 20 ribu ada di profil toko\n"
            "- Respon selalu dengan nada ramah, bersemangat, dan tidak kaku"
        )
        self.input_scope_custom_rules.setPlainText(self.config.get("scope_custom_rules", ""))
        self.input_scope_custom_rules.setMaximumHeight(100)
        custom_layout.addWidget(self.input_scope_custom_rules)

        layout.addWidget(custom_card)

        # 4. TOMBOL SIMPAN
        bottom_layout = QHBoxLayout()
        self.btn_save = PrimaryPushButton(FIF.SAVE, "Simpan Pengaturan Scope AI", container)
        self.btn_save.setFixedHeight(40)
        self.btn_save.clicked.connect(self._on_save_clicked)
        bottom_layout.addWidget(self.btn_save)

        layout.addLayout(bottom_layout)
        layout.addStretch()

    def _on_save_clicked(self):
        self.config.set("scope_topic", self.input_scope_topic.text().strip())
        self.config.set("scope_store_info", self.input_store_info.toPlainText().strip())
        self.config.set("scope_max_words", self.spin_max_words.value())
        self.config.set("scope_strict_dm", self.switch_strict_dm.isChecked())
        self.config.set("scope_strict_topic", self.switch_strict_topic.isChecked())
        self.config.set("scope_no_emoji", self.switch_no_emoji.isChecked())
        self.config.set("scope_custom_rules", self.input_scope_custom_rules.toPlainText().strip())
        self.config.save()

        InfoBar.success(
            title="Scope AI Berhasil Disimpan",
            content="Batasan ruang lingkup dan aturan AI live streaming berhasil diperbarui.",
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        self.save_requested.emit()
