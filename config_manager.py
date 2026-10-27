import os
from dotenv import load_dotenv

# Muat file .env dari direktori proyek
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

try:
    from pymongo import MongoClient
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False

CONFIG_DOC_ID = "main_config"

DEFAULT_SCOPE_TEXT = (
    "FOKUS & TOPIK LIVE:\n"
    "- Jualan & Spill Produk di Keranjang Kuning\n"
    "- Fashion Pria & Wanita (Pakaian, Jaket, Celana, Aksesoris)\n\n"
    "INFORMASI TOKO & PRODUK:\n"
    "- Produk etalase No 1 sampai 10 ready stok dan siap dikirim\n"
    "- Bisa bayar COD ke seluruh Indonesia\n"
    "- Pengiriman setiap hari kerja jam 4 sore\n\n"
    "ATURAN BALASAN & BATASAN (SCOPE):\n"
    "1. Balaslah SESUAI PERSIS dengan apa yang diketik penonton agar nyambung.\n"
    "2. Maksimal 1 kalimat singkat (di bawah 15 kata), bahasa Indonesia natural santai.\n"
    "3. HANYA tawarkan jajan lewat DM JIKA penonton secara jelas bertanya mau beli, harga, order, atau pesan barang.\n"
    "4. JANGAN PERNAH menawarkan jajan atau DM jika komentar bukan tentang pembelian (misal cuma 'aku', 'alu', 'ka', 'halo', 'kenal deh')!\n"
    "5. DILARANG menggunakan emoji, simbol, atau markdown formatting (**bold**, dsb.) agar suara TTS jernih.\n"
    "6. Jika penonton berkomentar di luar konteks live, tanggapi dengan sopan dan ajak kembali ke topik live streaming."
)

DEFAULT_REMINDER_ITEMS = [
    {
        "id": "1",
        "enabled": True,
        "title": "Tap-Tap & Follow Akun",
        "message": "Halo teman-teman yang baru bergabung, jangan lupa bantu tap tap layar dan follow akun kita ya! Terima kasih banyak dukungannya."
    },
    {
        "id": "2",
        "enabled": True,
        "title": "Cek & Checkout Keranjang Kuning",
        "message": "Jangan lupa kepoin etalase di keranjang kuning ya kak! Semua produk ready stock dan siap dikirim, langsung di-checkout sebelum kehabisan promo."
    },
    {
        "id": "3",
        "enabled": True,
        "title": "Info COD & Jam Pengiriman",
        "message": "Pengiriman kita setiap hari jam 4 sore ya kak, dan bisa bayar COD ke seluruh Indonesia. Yuk segera klaim voucher diskonnya sekarang!"
    },
    {
        "id": "4",
        "enabled": True,
        "title": "Spill & Tanya Produk",
        "message": "Kalau ada barang yang mau dispill atau ditanyakan, langsung ketik nomor etalasenya di kolom komentar ya kak, nanti mimin bantu jelaskan!"
    }
]

DEFAULT_CONFIG = {
    "tiktok_username": "",
    "tiktok_session_id": "",
    "ai_provider": "gemini",  # "gemini", "smart_rules"
    "gemini_api_key": "",
    "gemini_model": "gemini-3.5-flash-lite",
    "scope_ai_text": DEFAULT_SCOPE_TEXT,
    "ai_system_prompt": (
        "Kamu asisten host live streaming TikTok yang ramah, santai, dan cerdas. "
        "Balas komentar penonton sesuai persis dengan apa yang mereka ketik secara relevan dan nyambung. "
        "ATURAN: 1. Balaslah nyambung sesuai topik yang diketik penonton. "
        "2. HANYA tawarkan jajan lewat DM JIKA penonton secara jelas bertanya ingin membeli, memesan, atau menanyakan harga barang. "
        "3. JANGAN tawarkan jajan atau DM jika penonton hanya menyapa atau mengetik kata singkat seperti aku, alu, ka, halo, kenal deh. Balaslah santai (contoh: 'Iya halo kak, kenapa nih?'). "
        "4. Jangan baca tanda garis bawah (_) atau huruf berulang pada username. "
        "5. Maksimal 1 kalimat singkat (di bawah 15 kata), bahasa Indonesia natural tanpa emoji."
    ),
    "tts_voice": "gemini_Kore",
    "tts_rate": "+0%",
    "tts_pitch": "+0Hz",
    "tts_volume": "+0%",
    "enable_comments": True,
    "enable_greetings": True,
    "greeting_cooldown_sec": 5,
    "greeting_template": "Halo kak {username}, selamat datang di live!",
    "greeting_use_ai": False,
    "reply_mode": "all",  # "all", "keywords"
    "whitelist_keywords": ["halo", "harga", "spill", "cara", "promo", "diskon", "keranjang", "stok", "beli"],
    "blacklist_keywords": ["kontol", "memek", "anjing", "babi", "bangsat", "tolol", "scam", "bodoh"],
    "custom_triggers": [
      {"keyword": "harga", "response": "Untuk cek harga dan diskon spesial, langsung tap keranjang kuning di bawah ya kak!"},
      {"keyword": "spill", "response": "Siap kak, produknya segera di-spill, jangan lupa tap-tap layar dan follow ya!"},
      {"keyword": "keranjang", "response": "Keranjang kuningnya sudah siap kak, silakan di-checkout sebelum kehabisan promo!"}
    ],
    "max_queue_size": 3,
    "prioritize_latest": True,
    "queue_ttl_sec": 20,
    "user_comment_cooldown_sec": 8,
    # Fitur Reminder Otomatis Berkala
    "enable_reminder": True,
    "reminder_interval_min": 3,
    "reminder_mode": "list_rotate",  # "list_rotate", "list_random", "scope_summary"
    "reminder_items": DEFAULT_REMINDER_ITEMS,
    "reminder_avoid_interrupt": True,
    "reminder_only_when_live": False,
    # Metadata Fitur Otak, Nalar, Responsive, & Daya Ingat
    "enable_ai_brain": True,
    "enable_reasoning": True,
    "enable_conversation_memory": True,
    "enable_slang_translator": True,
    "enable_smart_pricing_calc": True,
    "max_user_history_turns": 5,
    "max_room_history_turns": 8,
    "memory_ttl_minutes": 15,
    "ceramah_mode_threshold": 2,
    "max_reply_words": 14,
    "ai_temperature": 0.4,
    "ai_max_tokens": 85
}

class ConfigManager:
    """
    Manager konfigurasi 100% Cloud (MongoDB Atlas).
    Tidak ada file konfigurasi yang disimpan ke disk lokal.
    """
    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.using_mongodb = False
        self.db_error = ""
        self.db_name = os.getenv("MONGODB_DB_NAME", "tiktok_live_ai")
        self.collection_name = os.getenv("MONGODB_COLLECTION", "app_config")
        self.mongo_uri = os.getenv("MONGODB_URI", "").strip()

        self._init_mongodb()
        self.config = self.load()

    def _init_mongodb(self) -> bool:
        """Menghubungkan ke MongoDB Atlas."""
        if not HAS_PYMONGO:
            self.using_mongodb = False
            self.db_error = "Library pymongo belum terpasang."
            print(f"[ConfigManager] {self.db_error}")
            return False

        if not self.mongo_uri:
            self.using_mongodb = False
            self.db_error = "MONGODB_URI belum diatur di file .env."
            print(f"[ConfigManager] {self.db_error}")
            return False

        try:
            self.mongo_client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000
            )
            # Uji koneksi ke MongoDB cluster
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.using_mongodb = True
            self.db_error = ""
            print(f"[ConfigManager] Terhubung ke Cloud MongoDB Atlas ({self.db_name}.{self.collection_name}).")
            return True
        except Exception as e:
            self.using_mongodb = False
            self.db_error = str(e)
            print(f"[ConfigManager] Gagal terhubung ke MongoDB Atlas: {e}")
            return False

    def load(self) -> dict:
        """Memuat seluruh konfigurasi secara eksklusif dari MongoDB Cloud."""
        merged = DEFAULT_CONFIG.copy()

        if not self.using_mongodb:
            self._init_mongodb()

        if self.using_mongodb and self.collection is not None:
            try:
                doc = self.collection.find_one({"_id": CONFIG_DOC_ID})
                if doc:
                    doc.pop("_id", None)
                    merged.update(doc)
                    print(f"[ConfigManager] Konfigurasi berhasil diambil dari Cloud MongoDB Atlas.")
                else:
                    # Inisialisasi dokumen baru di Cloud jika belum ada
                    save_doc = merged.copy()
                    save_doc["_id"] = CONFIG_DOC_ID
                    self.collection.replace_one({"_id": CONFIG_DOC_ID}, save_doc, upsert=True)
                    print(f"[ConfigManager] Inisialisasi konfigurasi awal ke Cloud MongoDB Atlas.")
            except Exception as e:
                self.db_error = str(e)
                print(f"[ConfigManager] Gagal memuat dari Cloud MongoDB Atlas: {e}")

        # Bersihkan kunci lama jika ada
        for old_k in ["rapidapi_key", "rapidapi_keys", "selected_rapidapi_key_name", "rapidapi_model", "enable_aitohuman"]:
            merged.pop(old_k, None)

        if merged.get("ai_provider") == "rapidapi":
            merged["ai_provider"] = "gemini"

        if merged.get("gemini_model") in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]:
            merged["gemini_model"] = "gemini-3.5-flash-lite"

        if "reminder_items" not in merged or not isinstance(merged["reminder_items"], list) or len(merged["reminder_items"]) == 0:
            merged["reminder_items"] = [dict(it) for it in DEFAULT_REMINDER_ITEMS]

        return merged

    def save(self) -> bool:
        """Menyimpan seluruh konfigurasi langsung ke MongoDB Atlas (100% Cloud, tanpa file lokal)."""
        if not self.using_mongodb:
            if not self._init_mongodb():
                return False

        if self.using_mongodb and self.collection is not None:
            try:
                save_doc = self.config.copy()
                save_doc["_id"] = CONFIG_DOC_ID
                self.collection.replace_one({"_id": CONFIG_DOC_ID}, save_doc, upsert=True)
                print(f"[ConfigManager] Setup berhasil disimpan ke Cloud MongoDB Atlas ({self.db_name}.{self.collection_name}).")
                return True
            except Exception as e:
                self.db_error = str(e)
                print(f"[ConfigManager] Gagal menyimpan ke Cloud MongoDB Atlas: {e}")
                return False
        return False

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def sync_to_mongodb(self) -> tuple[bool, str]:
        """Menyimpan seluruh konfigurasi aktif ke MongoDB Cloud."""
        if not self.using_mongodb:
            if not self._init_mongodb():
                return False, f"Gagal terhubung ke Cloud MongoDB: {self.db_error}"
        try:
            save_doc = self.config.copy()
            save_doc["_id"] = CONFIG_DOC_ID
            self.collection.replace_one({"_id": CONFIG_DOC_ID}, save_doc, upsert=True)
            return True, f"Setup berhasil disimpan ke Cloud MongoDB Atlas ({self.db_name}.{self.collection_name})"
        except Exception as e:
            self.db_error = str(e)
            return False, f"Gagal menyimpan ke Cloud MongoDB Atlas: {e}"

    def sync_from_mongodb(self) -> tuple[bool, str]:
        """Memuat ulang seluruh konfigurasi langsung dari MongoDB Cloud."""
        if not self.using_mongodb:
            if not self._init_mongodb():
                return False, f"Gagal terhubung ke Cloud MongoDB: {self.db_error}"
        try:
            doc = self.collection.find_one({"_id": CONFIG_DOC_ID})
            if doc:
                doc.pop("_id", None)
                self.config.update(doc)
                return True, f"Setup terbaru berhasil dimuat dari Cloud MongoDB Atlas ({self.db_name}.{self.collection_name})"
            else:
                return False, "Dokumen konfigurasi belum ditemukan di Cloud MongoDB."
        except Exception as e:
            self.db_error = str(e)
            return False, f"Gagal membaca dari Cloud MongoDB: {e}"
