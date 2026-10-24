from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidgetItem, QHeaderView
)
from qfluentwidgets import (
    ScrollArea, SimpleCardWidget, LineEdit, TextEdit,
    ComboBox, Slider, SwitchButton, PrimaryPushButton, PushButton,
    SubtitleLabel, BodyLabel, CaptionLabel, InfoBar, InfoBarPosition,
    TableWidget, FluentIcon as FIF
)

class FilterTab(ScrollArea):
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

        # 1. PENGATURAN MODE BALAS KOMENTAR
        reply_card = SimpleCardWidget(container)
        reply_layout = QVBoxLayout(reply_card)
        reply_layout.setContentsMargins(20, 16, 20, 16)
        reply_layout.setSpacing(14)

        reply_title = SubtitleLabel("Aturan Deteksi & Balas Komentar", reply_card)
        reply_layout.addWidget(reply_title)

        # Toggle Balas Komentar
        row_toggle = QHBoxLayout()
        lbl_enable_reply = BodyLabel("Aktifkan Balas Komentar Otomatis:", reply_card)
        self.switch_enable_reply = SwitchButton(reply_card)
        self.switch_enable_reply.setChecked(self.config.get("enable_comments", True))
        row_toggle.addWidget(lbl_enable_reply)
        row_toggle.addWidget(self.switch_enable_reply)
        row_toggle.addStretch()
        reply_layout.addLayout(row_toggle)

        # Mode Balas
        row_mode = QHBoxLayout()
        lbl_mode = BodyLabel("Mode Penyaringan Komentar:", reply_card)
        self.combo_mode = ComboBox(reply_card)
        self.combo_mode.addItem("Balas Semua Komentar Valid", userData="all")
        self.combo_mode.addItem("Hanya Balas Jika Mengandung Kata Kunci Whitelist", userData="keywords")

        curr_mode = self.config.get("reply_mode", "all")
        for i in range(self.combo_mode.count()):
            if self.combo_mode.itemData(i) == curr_mode:
                self.combo_mode.setCurrentIndex(i)
                break

        row_mode.addWidget(lbl_mode)
        row_mode.addWidget(self.combo_mode)
        row_mode.addStretch()
        reply_layout.addLayout(row_mode)

        # Whitelist Keywords
        lbl_whitelist = BodyLabel("Kata Kunci Wajib (Whitelist) - Pisahkan dengan koma:", reply_card)
        reply_layout.addWidget(lbl_whitelist)

        self.input_whitelist = TextEdit(reply_card)
        whitelist_list = self.config.get("whitelist_keywords", [])
        self.input_whitelist.setPlainText(", ".join(whitelist_list))
        self.input_whitelist.setMaximumHeight(70)
        reply_layout.addWidget(self.input_whitelist)

        # Blacklist Keywords
        lbl_blacklist = BodyLabel("Kata Kunci Terlarang (Blacklist/Abaikan) - Pisahkan dengan koma:", reply_card)
        reply_layout.addWidget(lbl_blacklist)

        self.input_blacklist = TextEdit(reply_card)
        blacklist_list = self.config.get("blacklist_keywords", [])
        self.input_blacklist.setPlainText(", ".join(blacklist_list))
        self.input_blacklist.setMaximumHeight(70)
        reply_layout.addWidget(self.input_blacklist)

        layout.addWidget(reply_card)

        # 2. TRIGGER & BALASAN OTOMATIS KHUSUS (INSTAN)
        trigger_card = SimpleCardWidget(container)
        trigger_layout = QVBoxLayout(trigger_card)
        trigger_layout.setContentsMargins(20, 16, 20, 16)
        trigger_layout.setSpacing(14)

        trigger_title = SubtitleLabel("Respon Otomatis Berdasarkan Kata Kunci (Instan)", trigger_card)
        trigger_layout.addWidget(trigger_title)

        caption_trigger = CaptionLabel(
            "Bisa berupa 1 kata maupun frasa beberapa kata (misal: 'harga', 'bisa cod', 'spill baju hitam'). "
            "Jika komentar singkat, langsung dibalas instan. Jika komentar panjang/kompleks, AI otomatis menggunakan info ini untuk menjawab seluruh pertanyaan penonton!",
            trigger_card
        )
        trigger_layout.addWidget(caption_trigger)

        # Tabel Trigger
        self.table_triggers = TableWidget(trigger_card)
        self.table_triggers.setColumnCount(2)
        self.table_triggers.setHorizontalHeaderLabels(["Kata Kunci / Frasa", "Respon Otomatis / Panduan"])
        self.table_triggers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_triggers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_triggers.setMinimumHeight(150)
        self._load_triggers_to_table()
        trigger_layout.addWidget(self.table_triggers)

        # Input trigger baru
        new_trig_layout = QHBoxLayout()
        self.input_new_kw = LineEdit(trigger_card)
        self.input_new_kw.setPlaceholderText("Kata Kunci / Frasa (misal: bisa cod)")
        self.input_new_kw.setMinimumWidth(220)

        self.input_new_resp = LineEdit(trigger_card)
        self.input_new_resp.setPlaceholderText("Respon Otomatis (misal: Bisa COD dan gratis ongkir ya kak!)")

        self.btn_add_trigger = PushButton(FIF.ADD, "Tambah", trigger_card)
        self.btn_add_trigger.clicked.connect(self._add_trigger_row)

        self.btn_del_trigger = PushButton(FIF.DELETE, "Hapus Pilihan", trigger_card)
        self.btn_del_trigger.clicked.connect(self._del_trigger_row)

        new_trig_layout.addWidget(self.input_new_kw)
        new_trig_layout.addWidget(self.input_new_resp, stretch=1)
        new_trig_layout.addWidget(self.btn_add_trigger)
        new_trig_layout.addWidget(self.btn_del_trigger)
        trigger_layout.addLayout(new_trig_layout)

        layout.addWidget(trigger_card)

        # 3. PENGATURAN SAPAAN PENONTON MASUK (JOIN LIVE)
        greet_card = SimpleCardWidget(container)
        greet_layout = QVBoxLayout(greet_card)
        greet_layout.setContentsMargins(20, 16, 20, 16)
        greet_layout.setSpacing(14)

        greet_title = SubtitleLabel("Pengaturan Sapaan Penonton Masuk (Join Live)", greet_card)
        greet_layout.addWidget(greet_title)

        # Toggle Sapaan
        row_greet_toggle = QHBoxLayout()
        lbl_enable_greet = BodyLabel("Aktifkan Menyapa Penonton Baru Masuk:", greet_card)
        self.switch_enable_greet = SwitchButton(greet_card)
        self.switch_enable_greet.setChecked(self.config.get("enable_greetings", True))
        row_greet_toggle.addWidget(lbl_enable_greet)
        row_greet_toggle.addWidget(self.switch_enable_greet)
        row_greet_toggle.addStretch()
        greet_layout.addLayout(row_greet_toggle)

        # Template Sapaan
        lbl_template = BodyLabel("Template Sapaan (Gunakan {username} untuk nama penonton):", greet_card)
        greet_layout.addWidget(lbl_template)

        self.input_greet_template = LineEdit(greet_card)
        self.input_greet_template.setText(
            self.config.get("greeting_template", "Halo kak {username}, selamat datang di live!")
        )
        greet_layout.addWidget(self.input_greet_template)

        lbl_hint = CaptionLabel("Kalimat sapaan hanya akan menggunakan setup template di atas secara konsisten tanpa berubah-ubah.", greet_card)
        lbl_hint.setStyleSheet("color: #7f8c8d; font-style: italic;")
        greet_layout.addWidget(lbl_hint)

        # Cooldown Sapaan
        grid_cooldown = QGridLayout()
        lbl_cooldown = BodyLabel("Jeda Antar Sapaan (Cooldown Anti-Spam):", greet_card)
        self.slider_cooldown = Slider(Qt.Orientation.Horizontal, greet_card)
        self.slider_cooldown.setRange(1, 30)
        curr_cd = self.config.get("greeting_cooldown_sec", 5)
        self.slider_cooldown.setValue(curr_cd)
        self.lbl_cooldown_val = CaptionLabel(f"{curr_cd} detik", greet_card)
        self.slider_cooldown.valueChanged.connect(lambda v: self.lbl_cooldown_val.setText(f"{v} detik"))

        grid_cooldown.addWidget(lbl_cooldown, 0, 0)
        grid_cooldown.addWidget(self.slider_cooldown, 0, 1)
        grid_cooldown.addWidget(self.lbl_cooldown_val, 0, 2)
        greet_layout.addLayout(grid_cooldown)

        layout.addWidget(greet_card)

        # 4. TOMBOL SIMPAN
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.btn_save = PrimaryPushButton(FIF.SAVE, "Simpan Pengaturan Filter & Sapaan", container)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_save.setMinimumWidth(260)
        bottom_layout.addWidget(self.btn_save)

        layout.addLayout(bottom_layout)
        layout.addStretch()

    def _load_triggers_to_table(self):
        triggers = self.config.get("custom_triggers", [])
        self.table_triggers.setRowCount(0)
        for t in triggers:
            row = self.table_triggers.rowCount()
            self.table_triggers.insertRow(row)
            self.table_triggers.setItem(row, 0, QTableWidgetItem(t.get("keyword", "")))
            self.table_triggers.setItem(row, 1, QTableWidgetItem(t.get("response", "")))

    def _add_trigger_row(self):
        kw = self.input_new_kw.text().strip()
        resp = self.input_new_resp.text().strip()
        if not kw or not resp:
            InfoBar.warning(
                title="Input Kurang",
                content="Masukkan kata kunci dan respon otomatis.",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self
            )
            return

        row = self.table_triggers.rowCount()
        self.table_triggers.insertRow(row)
        self.table_triggers.setItem(row, 0, QTableWidgetItem(kw))
        self.table_triggers.setItem(row, 1, QTableWidgetItem(resp))
        self.input_new_kw.clear()
        self.input_new_resp.clear()

    def _del_trigger_row(self):
        curr_row = self.table_triggers.currentRow()
        if curr_row >= 0:
            self.table_triggers.removeRow(curr_row)

    def _on_save_clicked(self):
        # Whitelist
        raw_wl = self.input_whitelist.toPlainText()
        whitelist = [x.strip() for x in raw_wl.replace("\n", ",").split(",") if x.strip()]

        # Blacklist
        raw_bl = self.input_blacklist.toPlainText()
        blacklist = [x.strip() for x in raw_bl.replace("\n", ",").split(",") if x.strip()]

        # Triggers
        triggers = []
        for r in range(self.table_triggers.rowCount()):
            kw_item = self.table_triggers.item(r, 0)
            resp_item = self.table_triggers.item(r, 1)
            if kw_item and resp_item:
                kw = kw_item.text().strip()
                resp = resp_item.text().strip()
                if kw and resp:
                    triggers.append({"keyword": kw, "response": resp})

        self.config.set("enable_comments", self.switch_enable_reply.isChecked())
        self.config.set("reply_mode", self.combo_mode.currentData())
        self.config.set("whitelist_keywords", whitelist)
        self.config.set("blacklist_keywords", blacklist)
        self.config.set("custom_triggers", triggers)

        self.config.set("enable_greetings", self.switch_enable_greet.isChecked())
        self.config.set("greeting_use_ai", False)
        self.config.set("greeting_template", self.input_greet_template.text().strip())
        self.config.set("greeting_cooldown_sec", self.slider_cooldown.value())

        self.config.save()

        InfoBar.success(
            title="Berhasil Disimpan",
            content="Pengaturan filter kata kunci dan sapaan berhasil disimpan.",
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        self.save_requested.emit()
