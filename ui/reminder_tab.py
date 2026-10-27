import random
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidgetItem, QHeaderView
)
from qfluentwidgets import (
    ScrollArea, SimpleCardWidget, CardWidget, LineEdit, TextEdit,
    SpinBox, ComboBox, SwitchButton, PrimaryPushButton, PushButton,
    SubtitleLabel, BodyLabel, CaptionLabel, InfoBar, InfoBarPosition,
    TableWidget, FluentIcon as FIF, CheckBox
)
from config_manager import DEFAULT_REMINDER_ITEMS

class ReminderTab(ScrollArea):
    """
    Tab Pengingat (Reminder) Otomatis Berkala untuk TikTok Live Streaming.
    Menyiarkan pesan informasi, promosi, dan edukasi penonton sesuai data yang tersimpan di setup.
    Waktu siaran dapat disesuaikan dan akan berulang secara otomatis.
    """
    save_requested = Signal()
    reminder_triggered = Signal(str, str)        # (message, title)
    test_reminder_requested = Signal(str, str)   # (message, title)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.is_live_connected = False
        self.current_rotate_index = 0

        # Inisialisasi waktu hitung mundur
        interval_min = int(self.config.get("reminder_interval_min", 3))
        self.seconds_left = max(1, interval_min) * 60

        self._init_ui()
        self._init_timer()
        self._load_config_to_ui()

    def _init_ui(self):
        self.setWidgetResizable(True)
        container = QWidget()
        self.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setSpacing(18)
        layout.setContentsMargins(24, 20, 24, 20)

        # =====================================================================
        # 1. KARTU STATUS & JADWAL PENGINGAT (INTERVAL & TIMER SETUP)
        # =====================================================================
        sched_card = SimpleCardWidget(container)
        sched_layout = QVBoxLayout(sched_card)
        sched_layout.setContentsMargins(20, 18, 20, 18)
        sched_layout.setSpacing(16)

        header_row = QHBoxLayout()
        title = SubtitleLabel("⏰ Pengingat Suara Otomatis (Periodic Reminder)", sched_card)
        header_row.addWidget(title)
        header_row.addStretch()

        self.lbl_status_badge = CaptionLabel("🟢 Berjalan (Aktif)", sched_card)
        self.lbl_status_badge.setStyleSheet(
            "padding: 4px 10px; border-radius: 6px; font-weight: bold; background: #27ae60; color: white;"
        )
        header_row.addWidget(self.lbl_status_badge)
        sched_layout.addLayout(header_row)

        desc = CaptionLabel(
            "Fitur ini akan menyiarkan informasi toko, ajakan interaksi penonton (tap-tap & follow), "
            "dan promosi produk secara berulang sesuai interval waktu yang Anda sesuaikan.",
            sched_card
        )
        sched_layout.addWidget(desc)

        # Baris Kontrol Utama: Sakelar Aktif & Hitung Mundur
        timer_display_box = CardWidget(sched_card)
        timer_box_layout = QHBoxLayout(timer_display_box)
        timer_box_layout.setContentsMargins(16, 12, 16, 12)
        timer_box_layout.setSpacing(20)

        # Switch Utama
        lbl_switch = BodyLabel("Status Pengingat Berkala:", timer_display_box)
        self.switch_enable = SwitchButton(timer_display_box)
        self.switch_enable.setOnText("Aktif")
        self.switch_enable.setOffText("Nonaktif")
        self.switch_enable.setChecked(bool(self.config.get("enable_reminder", True)))
        self.switch_enable.checkedChanged.connect(self._on_enable_toggled)

        timer_box_layout.addWidget(lbl_switch)
        timer_box_layout.addWidget(self.switch_enable)
        timer_box_layout.addSpacing(20)

        # Tampilan Countdown Realtime
        self.lbl_countdown = SubtitleLabel("⏳ Siaran Berikutnya Dalam: 03:00", timer_display_box)
        self.lbl_countdown.setStyleSheet("color: #0078d4; font-weight: bold; font-size: 16px;")
        timer_box_layout.addWidget(self.lbl_countdown)
        timer_box_layout.addStretch()

        # Tombol Aksi Cepat
        self.btn_trigger_now = PrimaryPushButton(FIF.MEGAPHONE, "Bunyikan Reminder Sekarang", timer_display_box)
        self.btn_trigger_now.setToolTip("Segera siarkan pesan pengingat saat ini tanpa menunggu interval timer habis")
        self.btn_trigger_now.clicked.connect(self._on_trigger_now_clicked)
        timer_box_layout.addWidget(self.btn_trigger_now)

        self.btn_reset_timer = PushButton(FIF.SYNC, "Reset Timer", timer_display_box)
        self.btn_reset_timer.clicked.connect(self._reset_countdown)
        timer_box_layout.addWidget(self.btn_reset_timer)

        sched_layout.addWidget(timer_display_box)

        # Grid Pengaturan Waktu & Mode
        grid_sched = QGridLayout()
        grid_sched.setHorizontalSpacing(16)
        grid_sched.setVerticalSpacing(12)

        # 1. Interval Waktu
        lbl_interval = BodyLabel("Waktu Pengingat Setiap (Interval):", sched_card)
        self.spin_interval = SpinBox(sched_card)
        self.spin_interval.setRange(1, 120)
        self.spin_interval.setSingleStep(1)
        curr_int = int(self.config.get("reminder_interval_min", 3))
        self.spin_interval.setValue(curr_int)
        self.spin_interval.valueChanged.connect(self._on_interval_changed)

        interval_unit = CaptionLabel("Menit sekali (Akan berulang terus)", sched_card)

        # Tombol Cepat Interval Preset
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(6)
        for min_val in [1, 2, 3, 5, 10, 15]:
            btn_p = PushButton(f"{min_val} Mnt", sched_card)
            btn_p.setFixedHeight(28)
            btn_p.clicked.connect(lambda _, v=min_val: self._set_preset_interval(v))
            preset_layout.addWidget(btn_p)

        grid_sched.addWidget(lbl_interval, 0, 0)
        grid_sched.addWidget(self.spin_interval, 0, 1)
        grid_sched.addWidget(interval_unit, 0, 2)
        grid_sched.addLayout(preset_layout, 0, 3)

        # 2. Mode Pemilihan Pesan Pengingat
        lbl_mode = BodyLabel("Metode Pemilihan Pesan:", sched_card)
        self.combo_mode = ComboBox(sched_card)
        self.combo_mode.addItem("Rotasi Berurutan (Pesan bergantian satu per satu)", userData="list_rotate")
        self.combo_mode.addItem("Acak (Pesan dipilih secara acak dari yang aktif)", userData="list_random")
        self.combo_mode.addItem("Ringkasan Info Toko dari Scope AI", userData="scope_summary")

        curr_mode = self.config.get("reminder_mode", "list_rotate")
        for i in range(self.combo_mode.count()):
            if self.combo_mode.itemData(i) == curr_mode:
                self.combo_mode.setCurrentIndex(i)
                break

        grid_sched.addWidget(lbl_mode, 1, 0)
        grid_sched.addWidget(self.combo_mode, 1, 1, 1, 3)

        # 3. Opsi Cerdas (Anti Interrupt & Syarat Live)
        self.switch_avoid_interrupt = SwitchButton(sched_card)
        self.switch_avoid_interrupt.setOnText("Ya")
        self.switch_avoid_interrupt.setOffText("Tidak")
        self.switch_avoid_interrupt.setChecked(bool(self.config.get("reminder_avoid_interrupt", True)))
        lbl_avoid = BodyLabel("Tunggu Komentar Selesai Dibacakan (Tidak memotong percakapan):", sched_card)

        grid_sched.addWidget(lbl_avoid, 2, 0, 1, 2)
        grid_sched.addWidget(self.switch_avoid_interrupt, 2, 2)

        self.switch_only_when_live = SwitchButton(sched_card)
        self.switch_only_when_live.setOnText("Ya")
        self.switch_only_when_live.setOffText("Tidak")
        self.switch_only_when_live.setChecked(bool(self.config.get("reminder_only_when_live", False)))
        self.switch_only_when_live.checkedChanged.connect(self._update_status_badge)
        lbl_only_live = BodyLabel("Hanya Bunyikan Saat Live Streaming Tersambung:", sched_card)

        grid_sched.addWidget(lbl_only_live, 3, 0, 1, 2)
        grid_sched.addWidget(self.switch_only_when_live, 3, 2)

        sched_layout.addLayout(grid_sched)
        layout.addWidget(sched_card)

        # =====================================================================
        # 2. KARTU MANAJEMEN DATA INFORMASI PENGINGAT (SETUP DATA)
        # =====================================================================
        data_card = SimpleCardWidget(container)
        data_layout = QVBoxLayout(data_card)
        data_layout.setContentsMargins(20, 18, 20, 18)
        data_layout.setSpacing(14)

        data_title = SubtitleLabel("📋 Data Informasi & Pesan Pengingat yang Disimpan", data_card)
        data_layout.addWidget(data_title)

        data_desc = CaptionLabel(
            "Berikut adalah data pengingat yang tersimpan di setup sistem. "
            "Pesan dengan status aktif akan disiarkan bergantian oleh suara AI sesuai waktu yang diatur di atas.",
            data_card
        )
        data_layout.addWidget(data_desc)

        # Tabel Pesan Reminder
        self.table_reminders = TableWidget(data_card)
        self.table_reminders.setColumnCount(4)
        self.table_reminders.setHorizontalHeaderLabels(["Aktif", "Judul Informasi", "Isi Pesan Suara", "Aksi"])
        self.table_reminders.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_reminders.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table_reminders.setColumnWidth(1, 210)
        self.table_reminders.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_reminders.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_reminders.setMinimumHeight(240)
        data_layout.addWidget(self.table_reminders)

        # Form Tambah Pesan Baru
        add_box = CardWidget(data_card)
        add_box_layout = QVBoxLayout(add_box)
        add_box_layout.setContentsMargins(14, 12, 14, 12)
        add_box_layout.setSpacing(10)

        add_label = BodyLabel("➕ Tambah Informasi Pengingat Baru:", add_box)
        add_box_layout.addWidget(add_label)

        add_input_row = QHBoxLayout()
        add_input_row.setSpacing(10)

        self.input_new_title = LineEdit(add_box)
        self.input_new_title.setPlaceholderText("Judul Pengingat (contoh: Promo Diskon 20%)")
        self.input_new_title.setMinimumWidth(210)

        self.input_new_msg = LineEdit(add_box)
        self.input_new_msg.setPlaceholderText("Isi Pesan Suara (contoh: Yuk kak checkout sekarang, ada diskon 20% khusus live!)")

        self.btn_add_item = PrimaryPushButton(FIF.ADD, "Tambah ke Setup", add_box)
        self.btn_add_item.clicked.connect(self._add_reminder_item)

        add_input_row.addWidget(self.input_new_title)
        add_input_row.addWidget(self.input_new_msg, stretch=1)
        add_input_row.addWidget(self.btn_add_item)
        add_box_layout.addLayout(add_input_row)

        data_layout.addWidget(add_box)

        # Tombol Simpan & Pulihkan Template
        btn_action_layout = QHBoxLayout()
        btn_action_layout.setSpacing(12)

        self.btn_load_defaults = PushButton(FIF.SYNC, "Muat Template Bawaan", data_card)
        self.btn_load_defaults.setFixedHeight(38)
        self.btn_load_defaults.clicked.connect(self._restore_default_items)
        btn_action_layout.addWidget(self.btn_load_defaults)

        btn_action_layout.addStretch()

        self.btn_save = PrimaryPushButton(FIF.SAVE, "Simpan Setup Pengingat", data_card)
        self.btn_save.setFixedHeight(38)
        self.btn_save.setMinimumWidth(220)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_action_layout.addWidget(self.btn_save)

        data_layout.addLayout(btn_action_layout)
        layout.addWidget(data_card)
        layout.addStretch()

    def _init_timer(self):
        """Inisialisasi QTimer detak 1 detik untuk menghitung mundur waktu siaran."""
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_second_tick)
        self._timer.start()
        self._update_status_badge()

    def _load_config_to_ui(self):
        """Memuat data item pengingat dari konfigurasi ke tabel UI."""
        items = self.config.get("reminder_items", DEFAULT_REMINDER_ITEMS)
        if not items:
            items = DEFAULT_REMINDER_ITEMS
        self._render_table_items(items)

    def _render_table_items(self, items: list[dict]):
        self.table_reminders.setRowCount(0)
        for idx, item in enumerate(items):
            row = self.table_reminders.rowCount()
            self.table_reminders.insertRow(row)

            # Kolom 0: Checkbox Aktif
            chk = CheckBox(self.table_reminders)
            chk.setChecked(bool(item.get("enabled", True)))
            chk.setStyleSheet("margin-left: 12px;")
            self.table_reminders.setCellWidget(row, 0, chk)

            # Kolom 1: Judul
            title_item = QTableWidgetItem(item.get("title", f"Pengingat #{idx+1}"))
            self.table_reminders.setItem(row, 1, title_item)

            # Kolom 2: Isi Pesan
            msg_item = QTableWidgetItem(item.get("message", ""))
            self.table_reminders.setItem(row, 2, msg_item)

            # Kolom 3: Aksi (Tombol Uji & Hapus)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)

            btn_test = PushButton(FIF.PLAY, "Uji", action_widget)
            btn_test.setFixedHeight(28)
            btn_test.clicked.connect(lambda _, r=row: self._test_single_row(r))

            btn_del = PushButton(FIF.DELETE, "Hapus", action_widget)
            btn_del.setFixedHeight(28)
            btn_del.clicked.connect(lambda _, r=row: self._delete_single_row(r))

            action_layout.addWidget(btn_test)
            action_layout.addWidget(btn_del)
            self.table_reminders.setCellWidget(row, 3, action_widget)

    def _add_reminder_item(self):
        title = self.input_new_title.text().strip()
        msg = self.input_new_msg.text().strip()
        if not msg:
            InfoBar.warning(
                title="Pesan Masih Kosong",
                content="Silakan ketikkan isi kalimat pesan pengingat yang akan disuarakan.",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return

        if not title:
            title = f"Pengingat #{self.table_reminders.rowCount() + 1}"

        current_items = self._get_items_from_table()
        new_item = {
            "id": str(len(current_items) + 1),
            "enabled": True,
            "title": title,
            "message": msg
        }
        current_items.append(new_item)
        self._render_table_items(current_items)

        self.input_new_title.clear()
        self.input_new_msg.clear()

        # Simpan otomatis ke konfigurasi
        self._on_save_clicked(show_infobar=False)
        InfoBar.success(
            title="Pesan Pengingat Ditambahkan",
            content=f"'{title}' berhasil ditambahkan ke daftar setup pengingat.",
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self
        )

    def _test_single_row(self, row_idx: int):
        if row_idx < 0 or row_idx >= self.table_reminders.rowCount():
            return
        title_item = self.table_reminders.item(row_idx, 1)
        msg_item = self.table_reminders.item(row_idx, 2)
        title = title_item.text().strip() if title_item else "Uji Pengingat"
        msg = msg_item.text().strip() if msg_item else ""
        if msg:
            self.test_reminder_requested.emit(msg, title)

    def _delete_single_row(self, row_idx: int):
        if row_idx < 0 or row_idx >= self.table_reminders.rowCount():
            return
        self.table_reminders.removeRow(row_idx)
        # Re-render action widgets to update row indices
        items = self._get_items_from_table()
        self._render_table_items(items)
        self._on_save_clicked(show_infobar=False)

    def _get_items_from_table(self) -> list[dict]:
        items = []
        for r in range(self.table_reminders.rowCount()):
            chk_widget = self.table_reminders.cellWidget(r, 0)
            enabled = chk_widget.isChecked() if isinstance(chk_widget, CheckBox) else True

            title_item = self.table_reminders.item(r, 1)
            title = title_item.text().strip() if title_item else f"Pengingat #{r+1}"

            msg_item = self.table_reminders.item(r, 2)
            msg = msg_item.text().strip() if msg_item else ""

            if msg:
                items.append({
                    "id": str(r + 1),
                    "enabled": enabled,
                    "title": title,
                    "message": msg
                })
        return items

    def _restore_default_items(self):
        self._render_table_items(DEFAULT_REMINDER_ITEMS)
        self._on_save_clicked(show_infobar=False)
        InfoBar.info(
            title="Template Dimuat",
            content="Template pesan pengingat bawaan telah dimuat kembali.",
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    # --- PENGATURAN WAKTU & HITUNG MUNDUR ---
    def _set_preset_interval(self, minutes: int):
        self.spin_interval.setValue(minutes)
        self._on_interval_changed(minutes)

    def _on_interval_changed(self, minutes: int):
        self.config.set("reminder_interval_min", minutes)
        self._reset_countdown()

    def _on_enable_toggled(self, is_checked: bool):
        self.config.set("enable_reminder", is_checked)
        self._update_status_badge()
        if is_checked:
            self._reset_countdown()

    def _reset_countdown(self):
        interval_min = int(self.spin_interval.value())
        self.seconds_left = max(1, interval_min) * 60
        self._update_countdown_label()

    def postpone(self, seconds: int = 10):
        """Menunda waktu siaran berikutnya (misal karena host/AI sedang sibuk membalas komentar)."""
        self.seconds_left = max(self.seconds_left, seconds)
        self.lbl_countdown.setText(f"⏳ Ditunda {seconds} dtk (Sedang membaca)")

    def set_live_connected(self, connected: bool):
        self.is_live_connected = connected
        self._update_status_badge()

    def _update_status_badge(self):
        is_enabled = self.switch_enable.isChecked()
        only_live = self.switch_only_when_live.isChecked()

        if not is_enabled:
            self.lbl_status_badge.setText("⚪ Nonaktif")
            self.lbl_status_badge.setStyleSheet(
                "padding: 4px 10px; border-radius: 6px; font-weight: bold; background: #7f8c8d; color: white;"
            )
            self.lbl_countdown.setText("⏳ Pengingat Dinonaktifkan")
        elif only_live and not self.is_live_connected:
            self.lbl_status_badge.setText("⏸️ Menunggu Live")
            self.lbl_status_badge.setStyleSheet(
                "padding: 4px 10px; border-radius: 6px; font-weight: bold; background: #e67e22; color: white;"
            )
            self.lbl_countdown.setText("⏳ Menunggu Live Tersambung")
        else:
            self.lbl_status_badge.setText("🟢 Berjalan (Aktif)")
            self.lbl_status_badge.setStyleSheet(
                "padding: 4px 10px; border-radius: 6px; font-weight: bold; background: #27ae60; color: white;"
            )
            self._update_countdown_label()

    def _update_countdown_label(self):
        is_enabled = self.switch_enable.isChecked()
        only_live = self.switch_only_when_live.isChecked()

        if not is_enabled or (only_live and not self.is_live_connected):
            return

        mins = self.seconds_left // 60
        secs = self.seconds_left % 60
        self.lbl_countdown.setText(f"⏳ Siaran Berikutnya Dalam: {mins:02d}:{secs:02d}")

    def _on_second_tick(self):
        """Dijalankan setiap 1 detik untuk menghitung mundur."""
        if not self.switch_enable.isChecked():
            return
        if self.switch_only_when_live.isChecked() and not self.is_live_connected:
            return

        self.seconds_left -= 1
        if self.seconds_left <= 0:
            # Waktu habis! Picu pengingat
            msg, title = self.get_next_reminder()
            if msg:
                self.reminder_triggered.emit(msg, title)
            # Reset countdown untuk putaran berikutnya (akan berulang sesuai waktu yang diatur)
            self._reset_countdown()
        else:
            self._update_countdown_label()

    def get_next_reminder(self) -> tuple[str, str]:
        """Mengambil pesan pengingat berikutnya berdasarkan metode pemilihan yang aktif."""
        mode = self.combo_mode.currentData() or "list_rotate"

        # Mode Scope AI Summary
        if mode == "scope_summary":
            scope_text = self.config.get("scope_ai_text", "").strip()
            if scope_text:
                # Ambil intisari baris pertama atau fokus
                lines = [l.strip("-* 1234567890.") for l in scope_text.splitlines() if l.strip() and not l.strip().endswith(":")]
                if lines:
                    summary = lines[0]
                    return f"Pengingat info live kita: {summary}. Yuk di-checkout sebelum promonya habis ya kak!", "Info Scope AI"

        # Ambil pesan aktif dari tabel
        items = self._get_items_from_table()
        active_items = [it for it in items if it.get("enabled", True)]
        if not active_items:
            active_items = items  # Fallback jika semua tidak dicentang

        if not active_items:
            return "", ""

        if mode == "list_random":
            chosen = random.choice(active_items)
            return chosen.get("message", ""), chosen.get("title", "Pengingat")
        else:
            # list_rotate (berurutan bergantian)
            if self.current_rotate_index >= len(active_items):
                self.current_rotate_index = 0
            chosen = active_items[self.current_rotate_index]
            self.current_rotate_index = (self.current_rotate_index + 1) % len(active_items)
            return chosen.get("message", ""), chosen.get("title", "Pengingat")

    def _on_trigger_now_clicked(self):
        msg, title = self.get_next_reminder()
        if not msg:
            InfoBar.warning(
                title="Pesan Kosong",
                content="Belum ada pesan pengingat aktif yang tersimpan di tabel.",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        self.test_reminder_requested.emit(msg, title)
        self._reset_countdown()

    def _on_save_clicked(self, show_infobar=True):
        items = self._get_items_from_table()
        self.config.set("enable_reminder", self.switch_enable.isChecked())
        self.config.set("reminder_interval_min", int(self.spin_interval.value()))
        self.config.set("reminder_mode", self.combo_mode.currentData() or "list_rotate")
        self.config.set("reminder_avoid_interrupt", self.switch_avoid_interrupt.isChecked())
        self.config.set("reminder_only_when_live", self.switch_only_when_live.isChecked())
        self.config.set("reminder_items", items)
        self.config.save()

        self._update_status_badge()
        self.save_requested.emit()

        if show_infobar:
            InfoBar.success(
                title="Setup Pengingat Disimpan",
                content="Pengaturan dan seluruh pesan pengingat berhasil disimpan ke Cloud Database.",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
