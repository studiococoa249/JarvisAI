import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "tiktok_username": "",
    "ai_provider": "gemini",  # "gemini", "smart_rules"
    "gemini_api_key": "",
    "gemini_model": "gemini-3.5-flash-lite",
    "scope_topic": "Jualan & Spill Produk (Keranjang Kuning)",
    "scope_store_info": "",
    "scope_max_words": 15,
    "scope_strict_dm": True,
    "scope_strict_topic": True,
    "scope_no_emoji": True,
    "scope_custom_rules": "",
    "ai_system_prompt": (
        "Kamu asisten host live streaming TikTok yang ramah, santai, dan cerdas. "
        "Balas komentar penonton sesuai persis dengan apa yang mereka ketik secara relevan dan nyambung. "
        "ATURAN: 1. Balaslah nyambung sesuai topik yang diketik penonton. "
        "2. HANYA tawarkan jajan lewat DM JIKA penonton secara jelas bertanya ingin membeli, memesan, atau menanyakan harga barang. "
        "3. JANGAN tawarkan jajan atau DM jika penonton hanya menyapa atau mengetik kata singkat seperti aku, alu, ka, halo, kenal deh. Balaslah santai (contoh: 'Iya halo kak, kenapa nih?'). "
        "4. Jangan baca tanda garis bawah (_) atau huruf berulang pada username. "
        "5. Maksimal 1 kalimat singkat (di bawah 15 kata), bahasa Indonesia natural tanpa emoji."
    ),
    "tts_voice": "child_girl_caca",
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
    "max_queue_size": 15
}

class ConfigManager:
    def __init__(self, filepath=CONFIG_FILE):
        self.filepath = filepath
        self.config = self.load()

    def load(self):
        merged = DEFAULT_CONFIG.copy()
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged.update(data)
            except Exception as e:
                print(f"[ConfigManager] Gagal membaca config: {e}")

        # Hapus kunci RapidAPI lama jika ada di file config pengguna
        for old_k in ["rapidapi_key", "rapidapi_keys", "selected_rapidapi_key_name", "rapidapi_model", "enable_aitohuman"]:
            merged.pop(old_k, None)

        if merged.get("ai_provider") == "rapidapi":
            merged["ai_provider"] = "gemini"

        # Perbaiki model jika lama
        if merged.get("gemini_model") in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            merged["gemini_model"] = "gemini-3.5-flash-lite"

        return merged

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager] Gagal menyimpan config: {e}")
            return False

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()
