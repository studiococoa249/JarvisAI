# 📘 SCOPE PROYEK: TikTok Live AI Voice Assistant

> Dokumen ini adalah panduan lengkap yang WAJIB dipelajari oleh AI untuk memahami seluruh alur kerja
> aplikasi **TikTok Live AI Voice & Comment Assistant** — mulai dari cara membaca komentar TikTok
> secara real-time, memproses komentar dengan kecerdasan buatan, hingga membalas dengan suara (Voice AI / TTS).

---

## 1. GAMBARAN UMUM APLIKASI

**Tujuan**: Aplikasi desktop berbasis Python + PySide6 (Qt) yang secara otomatis:
1. Terhubung ke siaran **TikTok Live** streamer manapun
2. Membaca **komentar penonton** secara real-time
3. Mengevaluasi setiap komentar (filter blacklist, whitelist, trigger kata kunci)
4. Membalas komentar menggunakan **AI** (Google Gemini atau Mode Cerdas Lokal)
5. Mengucapkan balasan dengan **suara (TTS)** — pilihan suara dewasa maupun anak-anak
6. Menyapa penonton yang baru bergabung (JoinEvent)

**Teknologi Utama**:
- `PySide6` + `qfluentwidgets` — UI Framework
- `TikTokLive` v7.0.1 — Koneksi websocket ke live streaming TikTok
- `Google Gemini API` — AI Provider utama
- `edge-tts` + `ffmpeg` — Text-to-Speech lokal (suara dewasa & anak-anak)
- `Qt Multimedia` (QMediaPlayer) — Pemutaran audio

---

## 2. STRUKTUR FILE PROYEK

```
d:\python\tiktokvoice\
│
├── live.py                  # Entry point utama (jalankan: python live.py)
├── config.json              # Konfigurasi pengguna (AI prompt, voice, filter, dll.)
│
├── config_manager.py        # Manajemen konfigurasi
├── ai_engine.py             # Otak AI: evaluasi komentar, generate balasan, panggil Gemini API
├── tts_engine.py            # Mesin suara: Edge-TTS & Gemini Voice
├── tiktok_worker.py         # Worker thread: koneksi TikTok Live, baca komentar real-time
│
└── ui/
    ├── __init__.py
    ├── main_window.py       # Jendela utama, penghubung semua komponen
    ├── live_tab.py           # Tab "Live Monitor" — kontrol koneksi, tabel feed real-time
    ├── settings_tab.py       # Tab "AI & Voice (TTS)" — pengaturan AI, suara, simulasi
    ├── filter_tab.py         # Tab "Filter & Kata Kunci" — whitelist, blacklist, custom trigger
    └── log_tab.py            # Tab "Log Sistem" — catatan aktivitas
```

---

## 3. ALUR KERJA (PIPELINE) LENGKAP

### 3.1 Koneksi ke TikTok Live
```
User memasukkan username → LiveTab._on_connect_clicked()
  → MainWindow._start_tiktok_stream(username)
    → TikTokWorker(username, ai_engine, config_manager)
      → sanitize_tiktok_username()  # Bersihkan @, URL, spasi
      → TikTokLiveClient(unique_id, web_kwargs={headers})
      → client.run(process_connect_events=False)  # Abaikan backlog lama
        → on_connect → emit connected signal → UI: "Terhubung"
```

### 3.2 Komentar Masuk → AI Memproses → Suara Keluar
```
TikTok WebSocket → CommentEvent
  │
  ├─ [FILTER WAKTU] Cek create_time/screen_time:
  │   • Komentar > 5 menit lalu? → LEWATI (kadaluarsa)
  │   • Komentar sebelum bot tersambung? → LEWATI
  │
  ├─ [FILTER BLACKLIST] Kata terlarang? → LEWATI
  │
  ├─ [FILTER WHITELIST] Mode "keywords" & tidak ada kata kunci? → LEWATI
  │
  ├─ [CUSTOM TRIGGER] Komentar cocok dengan kata kunci trigger?
  │   • Hanya 1-2 kata (misal "bang") → Balas instan dengan template
  │   • 3+ kata (misal "bang spill baju") → AI_ASSIST (AI memproses + info trigger)
  │
  ├─ [AI GENERATE REPLY]
  │   ├─ Google Gemini API
  │   └─ Smart Fallback (tanpa API) → Deteksi konteks komentar lokal
  │
  └─ [TTS ENGINE]
      ├─ Edge-TTS (id-ID-GadisNeural / id-ID-ArdiNeural)
      ├─ Edge-TTS + Formant Shift (suara anak-anak via ffmpeg)
      └─ Gemini Voice (Kore, Puck)
        → QMediaPlayer memutar audio → Lanjut ke antrean berikutnya
```

### 3.3 Penonton Bergabung (JoinEvent)
```
TikTok WebSocket → JoinEvent
  │
  ├─ Cek enable_greetings → aktif?
  ├─ Cek duplikat user (sudah pernah disapa?)
  ├─ Cek cooldown (jeda antar sapaan)
  │
  └─ generate_greeting(username)
      ├─ AI Greeting (jika greeting_use_ai=true)
      └─ Template Greeting (default)
        → TTS → Ucapkan sapaan
```

---

## 4. KOMPONEN INTI YANG HARUS DIPAHAMI AI

### 4.1 `ai_engine.py` — Otak Kecerdasan Buatan

#### Metode Evaluasi Komentar: `should_reply(comment)`
```python
Returns: (should_reply: bool, reason: str, direct_reply: str)
```
- **Langkah 1**: Cek **blacklist** → kata terlarang → tolak
- **Langkah 2**: Cek **custom_triggers** → cocokkan kata kunci → simpan trigger
- **Langkah 3**: Cek **mode whitelist** → jika mode "keywords", wajib ada kata whitelist
- **Langkah 4**: Evaluasi trigger:
  - Komentar HANYA berisi kata kunci (≤ kata kunci + 1 kata): **Balas instan** dengan template
  - Komentar mengandung pertanyaan lanjutan (3+ kata): **AI_ASSIST** — AI mengambil alih

#### Metode Generate Balasan: `generate_reply(username, comment, direct_reply)`
```python
1. Trigger instan → langsung balas template (ganti {username})
2. AI_ASSIST → kirim ke API dengan konteks tambahan
3. Google Gemini (Gratis & Cepat) → Smart Rules Lokal
4. Smart fallback lokal (generate_smart_fallback)
```

#### System Prompt Bawaan (Persona AI):
```
"Kamu asisten host live streaming TikTok yang ramah, santai, dan cerdas.
Balas komentar penonton sesuai persis dengan apa yang mereka ketik secara relevan dan nyambung.
ATURAN:
1. Balaslah nyambung sesuai topik yang diketik penonton.
2. HANYA tawarkan jajan lewat DM JIKA penonton secara jelas bertanya ingin membeli/memesan/harga.
3. JANGAN tawarkan jajan atau DM jika penonton hanya menyapa (aku, alu, ka, halo, kenal deh).
4. Jangan baca tanda garis bawah (_) atau huruf berulang pada username.
5. Maksimal 1 kalimat singkat (di bawah 15 kata), bahasa Indonesia natural tanpa emoji."
```

#### Pembersihan Username: `clean_username_for_speech(username)`
- Hapus pengulangan huruf (`nadiraaaaaaa` → `nadira`)
- Hapus underscore, dash, titik
- Hapus angka di akhir (`user068` → `user`)
- Ambil maksimal 2 kata pertama
- Title case

### 4.2 `tiktok_worker.py` — Koneksi Real-Time TikTok

**Fitur Utama**:
- **Patch API Route (`aid=1988`)**: TikTok mewajibkan parameter `aid=1988` pada `/api-live/user/room/` agar tidak ditolak dengan `params_error`.
- **Bypass `fetch_live_check=False`**: Melewati pengecekan `check_alive` bawaan TikTokLive yang sering salah mengembalikan status offline.
- **Patch HTML Parser**: Fallback membaca struktur data modern `__UNIVERSAL_DATA_FOR_REHYDRATION__` dan regex `roomId`.
- **Browser Headers**: User-Agent mobile Android agar tidak diblokir WAF TikTok
- **Sanitasi Username & Link**: `sanitize_tiktok_username()` mendukung username (`@user`), URL standar, link pendek (`vt.tiktok.com`), maupun Room ID langsung.
- **Filter Real-Time**: Komentar > 5 menit atau sebelum bot tersambung → dilewati
- **`process_connect_events=False`**: Tidak memproses event backlog lama saat pertama join room

### 4.3 `tts_engine.py` — Mesin Suara (Text-to-Speech)

**Pilihan Suara**:

| ID | Nama | Tipe | Engine |
|---|---|---|---|
| `id-ID-GadisNeural` | Gadis | Wanita Dewasa | Edge-TTS |
| `id-ID-ArdiNeural` | Ardi | Pria Dewasa | Edge-TTS |
| `gemini_Kore` | Kore | Wanita Dewasa | Gemini Voice |
| `gemini_Puck` | Puck | Pria Dewasa | Gemini Voice |
| `child_girl_caca` | Caca | Balita Perempuan 2-3 thn | Edge + Formant Shift 1.40 |
| `child_girl_mia` | Mia | Anak Perempuan 4-5 thn | Edge + Formant Shift 1.32 |
| `child_boy_nino` | Nino | Anak Laki-Laki 3-4 thn | Edge + Formant Shift 1.34 |

**Antrean Audio**:
- Prioritas: Komentar > Sapaan
- Batas antrean: `max_queue_size` (default 15)
- Item > 5 menit otomatis dihapus dari antrean
- Skip & mute tersedia di UI

### 4.4 `config_manager.py` — Manajemen Konfigurasi

**File `config.json`** menyimpan seluruh pengaturan:
- `ai_provider` — `"gemini"` | `"smart_rules"`
- `ai_system_prompt` — Persona/instruksi AI
- `tts_voice` — ID suara yang dipilih
- `tts_rate`, `tts_pitch`, `tts_volume` — Pengaturan suara
- `enable_comments` — Aktifkan/nonaktifkan balas komentar
- `enable_greetings` — Aktifkan/nonaktifkan sapaan
- `greeting_cooldown_sec` — Jeda antar sapaan (detik)
- `greeting_use_ai` — Sapaan dihasilkan AI atau template
- `reply_mode` — `"all"` | `"keywords"`
- `whitelist_keywords` — Kata kunci wajib (jika mode keywords)
- `blacklist_keywords` — Kata terlarang yang diabaikan
- `custom_triggers` — Daftar `{keyword, response}` untuk respons otomatis

---

## 5. PENYEDIA AI & VOICE

- **Google Gemini API**: Menghasilkan balasan percakapan kontekstual secara real-time.
- **Edge-TTS**: Menghasilkan ucapan audio natural (Dewasa & Anak-anak dengan formant shift ffmpeg).
- **Mode Cerdas Lokal (Smart Rules)**: Respon otomatis berdasarkan kata kunci dan template balasan tanpa memerlukan koneksi AI.

---

## 6. UI APLIKASI (4 TAB)

### Tab 1: Live Monitor (`live_tab.py`)
- Input username TikTok + tombol Hubungkan/Putuskan
- Status koneksi (Offline / Terhubung / Error detail)
- Badge AI mode aktif
- Kontrol suara: Skip, Kosongkan Antrean, Mute
- Tabel feed real-time: Waktu, Tipe, Penonton, Pesan, Balasan Voice AI, Status

### Tab 2: Filter & Kata Kunci (`filter_tab.py`)
- Toggle balas komentar otomatis
- Mode penyaringan: Balas semua / Hanya kata kunci whitelist
- Daftar whitelist & blacklist (pisahkan dengan koma)
- Tabel custom triggers: Kata kunci → Respons otomatis

### Tab 3: AI & Voice TTS (`settings_tab.py`)
- Pilihan provider AI: Gemini / Mode Cerdas Lokal
- Gemini API Key & model selector
- System prompt (instruksi persona AI)
- **Kartu Scope & Aturan AI (AI Scope)**:
  - Topik / Fokus Live Streaming
  - Batasan maksimal kata per balasan (SpinBox)
  - Saklar aturan ketat Jajan/DM
  - Saklar fokus tetap pada topik live
  - Saklar larangan emoji & markdown
  - Input teks aturan tambahan / larangan khusus (Custom Rules)
- Pilihan suara TTS + pengaturan rate/pitch/volume
- Simulasi uji komentar & join

### Tab 4: Log Sistem (`log_tab.py`)
- Catatan semua aktivitas: koneksi, komentar, sapaan, error

---

## 7. ATURAN PENTING UNTUK AI SAAT MEMBALAS KOMENTAR

1. **SELALU balas SESUAI apa yang diketik penonton** — jangan jawab melenceng
2. **Maksimal 1 kalimat (< 15 kata)** — bahasa Indonesia natural
3. **JANGAN tawarkan jajan/DM** kecuali penonton jelas bertanya harga/beli/order
4. **Sapaan singkat** (halo, hai, ka, aku) → balas santai, BUKAN arahkan ke keranjang
5. **Username dibersihkan** sebelum diucapkan (hapus _, angka berulang, dll.)
6. **Tanpa emoji, markdown, atau tanda kutip** di output
7. **Komentar > 5 menit** → tidak diproses sama sekali
8. **Komentar sebelum bot tersambung** → tidak diproses
9. **Kata blacklist** → komentar langsung diabaikan
10. **Custom trigger cocok** → balas cepat; trigger + pertanyaan lanjutan → AI memproses

---

## 8. CONTOH SKENARIO BALASAN AI

| Komentar Penonton | Evaluasi | Balasan yang Benar |
|---|---|---|
| `halo` | Sapaan singkat | `Halo juga kak Nadira, selamat datang di live ya!` |
| `aku` | Kata singkat ambigu | `Iya halo kak Budi, kenapa nih?` |
| `bang` | Trigger "bang" cocok | `Halo, halo, Rizky ada apa?` |
| `bang spill baju hitam` | Trigger "bang" + pertanyaan → AI_ASSIST | AI menjawab tentang produk baju hitam |
| `berapa harganya` | Pertanyaan harga | `Untuk info harga terbarunya, langsung cek di keranjang kuning ya kak!` |
| `beli` | Trigger "beli" cocok | `Bang Andi DM aja kalo mau jajan` |
| `kenal deh` | Sapaan santai | `Halo kak Sari, mungkin kita pernah ketemu di live sebelumnya ya!` |
| `kontol` | Blacklist | *(Dilewati — kata terlarang)* |

---

## 9. CATATAN TEKNIS PENTING

- **Fallback Berlapis**: Gemini → Smart Fallback Lokal (selalu ada jawaban)
- **Suara Anak**: Menggunakan Edge-TTS dewasa + formant shift via `ffmpeg` (asetrate + aresample + atempo)
- **Windows Console**: Emoji/unicode di komentar TikTok bisa crash cp1252 console → print disanitasi
- **TikTok WAF**: Halaman HTML tiktok.com diblokir tanpa header browser → pakai User-Agent Android mobile
- **SIGI_STATE Deprecated**: TikTok kini pakai `__UNIVERSAL_DATA_FOR_REHYDRATION__` → parser dipatch
- **Antrean TTS**: Item kadaluarsa (> 5 menit) otomatis dihapus sebelum diproses
