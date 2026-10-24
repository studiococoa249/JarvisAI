from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout
)
from qfluentwidgets import (
    ScrollArea, SimpleCardWidget, TextEdit,
    PrimaryPushButton, PushButton,
    SubtitleLabel, CaptionLabel, InfoBar, InfoBarPosition,
    FluentIcon as FIF
)
from config_manager import DEFAULT_SCOPE_TEXT

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
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # KARTU FORM UTAMA SCOPE AI
        card = SimpleCardWidget(container)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(14)

        title = SubtitleLabel("🎯 Ruang Lingkup & Aturan AI (Scope AI)", card)
        card_layout.addWidget(title)

        caption = CaptionLabel(
            "Ketikkan seluruh panduan, informasi produk, dan batasan live streaming di form ini. "
            "Form ini adalah acuan tunggal bagi AI dalam membalas komentar penonton di live TikTok Anda.",
            card
        )
        card_layout.addWidget(caption)

        # Form Editor Teks Scope AI
        self.editor_scope = TextEdit(card)
        self.editor_scope.setPlaceholderText(
            "Tuliskan aturan, fokus live, dan informasi produk toko di sini...\n\n"
            "Contoh:\n"
            "FOKUS LIVE: Jualan hijab dan gamis crinkle\n"
            "HARGA: Rp85.000 promo beli 2 diskon 15%\n"
            "ATURAN: Balas maksimal 1 kalimat, ramah, jangan tawarkan DM jika penonton hanya menyapa."
        )
        current_text = self.config.get("scope_ai_text")
        if not current_text:
            current_text = DEFAULT_SCOPE_TEXT
        self.editor_scope.setPlainText(current_text)
        self.editor_scope.setMinimumHeight(420)
        card_layout.addWidget(self.editor_scope)

        # Tombol Aksi di Bawah Form
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_save = PrimaryPushButton(FIF.SAVE, "Simpan Scope AI", card)
        self.btn_save.setFixedHeight(40)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        self.btn_reset = PushButton(FIF.SYNC, "Muat Template Bawaan", card)
        self.btn_reset.setFixedHeight(40)
        self.btn_reset.clicked.connect(self._on_reset_clicked)
        btn_layout.addWidget(self.btn_reset)

        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)

        layout.addWidget(card)
        layout.addStretch()

    def _on_save_clicked(self):
        text = self.editor_scope.toPlainText().strip()
        self.config.set("scope_ai_text", text)
        self.config.save()

        InfoBar.success(
            title="Scope AI Berhasil Disimpan",
            content="Seluruh aturan dan ruang lingkup AI live streaming telah diperbarui.",
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        self.save_requested.emit()

    def _on_reset_clicked(self):
        self.editor_scope.setPlainText(DEFAULT_SCOPE_TEXT)
        InfoBar.info(
            title="Template Dimuat",
            content="Template bawaan Scope AI telah dimuat. Klik 'Simpan Scope AI' untuk menerapkannya.",
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self
        )
