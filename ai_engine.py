import re
import time
from collections import deque
from google import genai
from google.genai import types
from tts_engine import normalize_text_for_speech

# =====================================================================
# 1. MODUL NALAR BAHASA & SLANG LIVE STREAMING (INDONESIAN SLANG PARSER)
# =====================================================================
SLANG_DICTIONARY = {
    r"\bbrp\b": "berapa",
    r"\bkpn\b": "kapan",
    r"\bknp\b": "kenapa",
    r"\bgmn\b": "gimana",
    r"\bgak\b|\bga\b|\bngga\b|\bgk\b": "tidak",
    r"\bsy\b|\bgw\b|\bgue\b|\bak\b|\baq\b": "aku",
    r"\blu\b|\belu\b": "kamu",
    r"\bspil\b|\bspill\b": "spill",
    r"\bpls\b|\bpliss\b|\bplis\b|\bplit\b": "tolong minta",
    r"\bcdm\b": "cek DM pesanan",
    r"\bdm\b": "direct message",
    r"\bgp\b": "game pass",
    r"\bacc\b": "aksesoris",
    r"\bmsh\b": "masih",
    r"\bjeti\b|\bjt\b": "juta cash",
    r"\bmin\b|\badm\b": "admin",
    r"\blol\b|\bwkwk+\b": "tertawa",
}

def expand_live_slang(text: str) -> str:
    """Mengembangkan singkatan dan bahasa gaul penonton live TikTok agar nalar AI dapat memahaminya secara presisi."""
    clean = text.lower()
    for pattern, replacement in SLANG_DICTIONARY.items():
        clean = re.sub(pattern, replacement, clean)
    return clean.strip()


# =====================================================================
# 2. SISTEM DAYA INGAT PEMBAHASAN (CONVERSATION & DISCUSSION MEMORY)
# =====================================================================
class ConversationMemory:
    """
    Sistem memori cerdas untuk mengingat alur percakapan per penonton (user memory)
    serta dinamika topik yang sedang aktif dibahas di ruang live (room memory).
    """
    def __init__(self, max_user_history=4, max_room_history=8, memory_ttl_sec=900):
        self.max_user_history = max_user_history
        self.max_room_history = max_room_history
        self.memory_ttl_sec = memory_ttl_sec
        # Riwayat per user: {username: [{"comment": str, "reply": str, "time": float, "topic": str}]}
        self.user_memories: dict[str, list[dict]] = {}
        # Riwayat global room: deque of {"user": str, "comment": str, "reply": str, "time": float}
        self.room_history = deque(maxlen=self.max_room_history)
        # Topik aktif yang dipelajari dari siaran live
        self.active_topics: list[str] = []
        self.last_discussed_items: list[str] = []

    def remember(self, username: str, comment: str, reply: str):
        """Menyimpan interaksi ke dalam memori penonton dan memori ruang siaran."""
        now = time.time()
        self._cleanup_stale(now)

        clean_user = username.strip().lower()
        if clean_user not in self.user_memories:
            self.user_memories[clean_user] = []

        interaction = {
            "comment": comment.strip(),
            "reply": reply.strip(),
            "time": now
        }
        self.user_memories[clean_user].append(interaction)
        if len(self.user_memories[clean_user]) > self.max_user_history:
            self.user_memories[clean_user].pop(0)

        # Simpan ke memori ruang live (room discussion)
        self.room_history.append({
            "user": username.strip(),
            "comment": comment.strip(),
            "reply": reply.strip(),
            "time": now
        })

        # Pelajari topik dan produk yang dibicarakan
        self._learn_from_interaction(comment, reply)

    def _learn_from_interaction(self, comment: str, reply: str):
        """Menganalisis topik dan produk untuk memperbarui daya nalar konteks siaran."""
        c_low = comment.lower()
        r_low = reply.lower()

        # Deteksi produk gamepass / cash dari percakapan
        known_products = [
            "police pass", "boombox", "painpass", "2x paycheck", "plate pass",
            "dragspec", "gp velg", "luxury", "aksesoris", "slot limit", "suspension",
            "cash", "jeti", "juta", "qris"
        ]
        for prod in known_products:
            if prod in c_low or prod in r_low:
                if prod not in self.last_discussed_items:
                    self.last_discussed_items.append(prod)
                if len(self.last_discussed_items) > 5:
                    self.last_discussed_items.pop(0)

        # Deteksi status topik live
        if any(w in c_low for w in ["kode", "code"]):
            if "kode server" not in self.active_topics:
                self.active_topics.append("kode server")
        if any(w in c_low for w in ["join", "server", "lock", "penuh", "full"]):
            if "akses server" not in self.active_topics:
                self.active_topics.append("akses server")
        if any(w in c_low for w in ["parkour", "ninja", "gameplay", "motor"]):
            if "gameplay parkour" not in self.active_topics:
                self.active_topics.append("gameplay parkour")

        if len(self.active_topics) > 4:
            self.active_topics.pop(0)

    def get_user_context(self, username: str) -> str:
        """Mengambil ringkasan ingatan percakapan sebelumnya dengan penonton tertentu."""
        clean_user = username.strip().lower()
        history = self.user_memories.get(clean_user, [])
        if not history:
            return ""

        lines = []
        for h in history[-3:]:
            lines.append(f"- Penonton ({username}): '{h['comment']}' -> Asisten: '{h['reply']}'")
        return "\n".join(lines)

    def get_room_context(self) -> str:
        """Mengambil rangkuman pembahasan yang sedang berlangsung di ruang live saat ini."""
        if not self.room_history:
            return ""
        
        recent_snippets = []
        for r in list(self.room_history)[-3:]:
            recent_snippets.append(f"@{r['user']}: \"{r['comment']}\"")
        
        context_str = "Komentar penonton lain baru-baru ini: " + " | ".join(recent_snippets)
        if self.last_discussed_items:
            context_str += f"\nProduk yang baru saja dibahas: {', '.join(self.last_discussed_items)}"
        if self.active_topics:
            context_str += f"\nFokus topik saat ini: {', '.join(self.active_topics)}"
        return context_str

    def get_user_repeat_freebie_count(self, username: str) -> int:
        """Mengecek berapa kali penonton meminta gratisan/hadiah berturut-turut untuk Mode Ceramah."""
        clean_user = username.strip().lower()
        history = self.user_memories.get(clean_user, [])
        count = 0
        for h in history:
            c = h["comment"].lower()
            if any(w in c for w in ["minta", "bagi", "gratis", "plis", "pls", "bagi dong", "gift"]):
                count += 1
        return count

    def _cleanup_stale(self, now: float):
        """Membersihkan memori penonton yang sudah lama tidak aktif (> 15 menit)."""
        expired_users = [
            u for u, hist in self.user_memories.items()
            if hist and (now - hist[-1]["time"]) > self.memory_ttl_sec
        ]
        for u in expired_users:
            del self.user_memories[u]


# =====================================================================
# 3. KELAS UTAMA AI ENGINE (BEROTAK, BERNALAR, DAYA INGAT, RESPONSIF)
# =====================================================================
class AIEngine:
    """
    Kecerdasan Buatan (AI Engine) live streaming TikTok berbasis Google Gemini & Smart Reasoning:
    - Otak & Nalar: Memahami maksud, konteks bertingkat, dan aturan logis dari database Scope AI.
    - Daya Ingat Pembahasan: Mengingat percakapan sebelumnya per penonton dan topik ruang siaran.
    - Responsif: Eksekusi kilat dengan token hemat dan bahasa Indonesia alami untuk TTS.
    - Sinkronisasi Cloud: 100% menggunakan data yang tersimpan di database MongoDB Atlas.
    """
    def __init__(self, config_manager):
        self.config = config_manager
        self._gemini_client = None
        self._cached_gemini_key = None
        # Muat konfigurasi terbaru dari database
        self.reload_config()
        # Inisialisasi sistem daya ingat percakapan menggunakan metadata dari database
        max_user_h = int(self.config.get("max_user_history_turns", 5))
        max_room_h = int(self.config.get("max_room_history_turns", 8))
        ttl_sec = int(self.config.get("memory_ttl_minutes", 15)) * 60
        self.memory = ConversationMemory(max_user_history=max_user_h, max_room_history=max_room_h, memory_ttl_sec=ttl_sec)

    def reload_config(self):
        """Memuat ulang konfigurasi engine terbaru dari database MongoDB."""
        if hasattr(self.config, "sync_from_mongodb"):
            self.config.sync_from_mongodb()
        elif hasattr(self.config, "load"):
            self.config.load()

    def get_active_provider_info(self) -> str:
        """Mengambil informasi engine aktif yang tersimpan di database."""
        provider = self.config.get("ai_provider", "gemini")
        if provider == "gemini":
            key = self.config.get("gemini_api_key", "").strip()
            if key:
                model = self.config.get("gemini_model", "gemini-3.5-flash-lite")
                return f"Google Gemini ({model}) [Memory & Nalar Aktif]"
        return "Mode Cerdas (Smart Rules) [Memory & Nalar Aktif]"

    def clean_text_for_voice(self, text: str) -> str:
        """Membersihkan markdown, karakter aneh, emoji, serta menormalkan istilah live streaming agar suara manusiawi."""
        return normalize_text_for_speech(text)

    def clean_username_for_speech(self, username: str) -> str:
        """Membersihkan username agar alami dan tidak membaca deretan huruf/simbol aneh."""
        if not username:
            return "Kak"
        # Hapus pengulangan karakter lebih dari 2x (misal: "nadiraaaaaaaaaaaaaaaa" -> "nadira")
        u = re.sub(r'([a-zA-Z0-9])\1{2,}', r'\1', username)
        # Hapus underscore, dash, titik berulang
        u = re.sub(r'[_.\-]+', ' ', u)
        # Hapus angka di akhir username (misal: "anuarothman068" -> "anuarothman")
        u = re.sub(r'\d+$', '', u)
        u = re.sub(r'\s+', ' ', u).strip()
        if not u:
            return "Kak"
        parts = u.split()
        if len(parts) > 2:
            u = " ".join(parts[:2])
        return u.title()

    def should_reply(self, comment: str) -> tuple[bool, str, str]:
        """
        Mengecek apakah komentar harus dibalas berdasarkan aturan dari database:
        - blacklist_keywords
        - custom_triggers
        - reply_mode & whitelist_keywords
        Returns:
            (should_reply: bool, reason: str, direct_reply: str)
        """
        comment_clean = comment.strip()
        comment_lower = comment_clean.lower()
        clean_text = re.sub(r'[^\w\s]', '', comment_lower).strip()
        words = clean_text.split()

        # 1. Cek Blacklist dari database
        blacklist = self.config.get("blacklist_keywords", [])
        for bad in blacklist:
            bad_clean = bad.strip().lower()
            if bad_clean:
                if re.search(r'\b' + re.escape(bad_clean) + r'\b', comment_lower) or (len(bad_clean) > 3 and bad_clean in comment_lower):
                    return False, f"Kata blacklist: '{bad}'", ""

        # 2. Cek Custom Triggers dari database
        custom_triggers = self.config.get("custom_triggers", [])
        for item in custom_triggers:
            kw = item.get("keyword", "").lower().strip()
            resp = item.get("response", "").strip()
            if kw and resp:
                kw_clean = re.sub(r'[^\w\s]', '', kw).strip()
                if kw_clean and (kw_clean in clean_text or kw_clean in comment_lower or clean_text == kw_clean or words == kw_clean.split()):
                    return True, f"Trigger instan cocok: '{kw}'", resp

        # 3. Cek Mode Balasan dari database
        reply_mode = self.config.get("reply_mode", "all")
        if reply_mode == "keywords":
            whitelist = self.config.get("whitelist_keywords", [])
            has_whitelist = False
            for w in whitelist:
                w_clean = w.strip().lower()
                if w_clean:
                    if re.search(r'\b' + re.escape(w_clean) + r'\b', comment_lower) or w_clean in comment_lower:
                        has_whitelist = True
                        break
            if not has_whitelist:
                return False, "Tidak ada kata kunci whitelist", ""

        # Komentar terlalu pendek / kosong (kurang dari 2 huruf dan bukan angka)
        if len(clean_text) < 2 and not clean_text.isdigit():
            return False, "Komentar terlalu singkat", ""

        return True, "Komentar valid untuk dibalas AI", ""

    def _call_gemini(self, username: str, comment: str, assisted_context: str = "") -> str:
        """
        Memanggil Google Gemini API dengan mengintegrasikan:
        1. Identitas, Persona & Scope AI resmi dari database MongoDB.
        2. Daya Ingat Percakapan sebelumnya dengan penonton ini (Multi-turn user context).
        3. Daya Ingat Ruang Siaran (Live room discussion context).
        4. Nalar Logika & Perhitungan (Price calculation, context connection, ceramah mode).
        """
        api_key = self.config.get("gemini_api_key", "").strip()
        if not api_key:
            print("[AIEngine] Gemini API Key kosong di database.")
            return ""

        # Inisialisasi atau re-use client
        if not self._gemini_client or self._cached_gemini_key != api_key:
            try:
                self._gemini_client = genai.Client(api_key=api_key, http_options={"timeout": 12000})
                self._cached_gemini_key = api_key
            except Exception as ce:
                print(f"[AIEngine] Gagal inisialisasi Gemini Client: {ce}")
                return ""

        client = self._gemini_client
        clean_user = self.clean_username_for_speech(username)

        # 1. Ambil System Prompt & Scope AI dari database
        base_prompt = self.config.get("ai_system_prompt", "").strip()
        scope_ai_text = self.config.get("scope_ai_text", "").strip()

        # 2. Ambil Ingatan Percakapan Pengguna & Ruang Live sesuai metadata database
        enable_memory = bool(self.config.get("enable_conversation_memory", True))
        user_memory_text = self.memory.get_user_context(username) if enable_memory else ""
        room_memory_text = self.memory.get_room_context() if enable_memory else ""
        repeat_freebie_count = self.memory.get_user_repeat_freebie_count(username) if enable_memory else 0
        ceramah_threshold = int(self.config.get("ceramah_mode_threshold", 2))
        max_words = int(self.config.get("max_reply_words", 14))
        enable_slang = bool(self.config.get("enable_slang_translator", True))

        # 3. Bentuk Instruksi Sistem Cerdas (Otak & Nalar Berbasis Scope Database)
        system_instruction_parts = []
        if base_prompt:
            system_instruction_parts.append(f"PERSONA HOST LIVE:\n{base_prompt}")
        if scope_ai_text:
            system_instruction_parts.append(f"RUANG LINGKUP & PANDUAN RESMI (SCOPE DATABASE):\n{scope_ai_text}")

        system_instruction_parts.append(
            "ATURAN NALAR & LOGIKA:\n"
            "1. Gunakan DAYA INGAT percakapan di bawah untuk memahami pertanyaan lanjutan (contoh: 'kalau tambah itu jadi berapa', 'totalnya berapa', 'bisa kurang gak', 'tadi itu'). Sambungkan jawaban dengan konteks sebelumnya.\n"
            "2. Lakukan perhitungan harga secara presisi & teliti menggunakan Pricelist di Scope AI.\n"
            "3. Jika penonton berulang kali meminta gratisan (Mode Ceramah), berikan teguran sopan dan motivasi sesuai aturan Scope AI.\n"
            f"4. Maksimal 1 kalimat singkat (di bawah {max_words} kata), wajib sebutkan username penonton, bahasa Indonesia alami santai tanpa emoji atau tanda format."
        )

        system_instruction = "\n\n".join(system_instruction_parts)

        # 4. Bangun Prompt Interaksi Cerdas
        prompt_parts = []
        if user_memory_text:
            prompt_parts.append(f"[DAYA INGAT PERCAKAPAN SEBELUMNYA DENGAN {clean_user}]:\n{user_memory_text}")
        if room_memory_text:
            prompt_parts.append(f"[KONTEKS PEMBAHASAN RUANG LIVE SAAT INI]:\n{room_memory_text}")
        if assisted_context and not any(w in assisted_context.lower() for w in ["ada apa", "halo, hai"]):
            prompt_parts.append(f"[INFORMASI PANDUAN KHUSUS]: {assisted_context}")
        if repeat_freebie_count >= ceramah_threshold:
            prompt_parts.append(f"[CATATAN NALAR]: Penonton {clean_user} sudah {repeat_freebie_count}x meminta hadiah/gratisan berturut-turut. Aktifkan Mode Ceramah!")

        # Normalisasi singkatan bahasa gaul penonton untuk membantu penalaran
        expanded_comment = expand_live_slang(comment) if enable_slang else comment
        prompt_parts.append(f"Penonton @{clean_user} baru saja berkomentar: \"{comment}\" (Maksud pesan: \"{expanded_comment}\")")
        prompt_parts.append(f"Tugas: Berikan 1 kalimat balasan langsung ringkas, cerdas, nyambung, dan to-the-point sesuai nalar & scope di atas.")

        final_prompt = "\n\n".join(prompt_parts)

        # 5. Pilihan Model Engine dari Database
        preferred_model = self.config.get("gemini_model", "gemini-3.5-flash-lite").strip()
        models_to_try = [preferred_model]
        for fallback_m in ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]:
            if fallback_m and fallback_m not in models_to_try:
                models_to_try.append(fallback_m)

        max_tokens = int(self.config.get("ai_max_tokens", 85))
        temperature = float(self.config.get("ai_temperature", 0.4))

        for m_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m_name,
                    contents=final_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    )
                )
                raw_text = response.text or ""
                clean = self.clean_text_for_voice(raw_text)
                if "{username}" in clean:
                    clean = clean.replace("{username}", clean_user)
                if clean:
                    return clean
            except Exception as e:
                print(f"[AIEngine] Gemini ({m_name}) error: {e}")

        return ""

    def generate_smart_fallback(self, username: str, comment: str, assisted_context: str = "") -> str:
        """
        Nalar cerdas fallback berbasis daya ingat dan Scope AI jika Gemini offline/timeout.
        """
        clean_user = self.clean_username_for_speech(username)
        c = comment.lower().strip()
        expanded_c = expand_live_slang(c)
        scope_text = self.config.get("scope_ai_text", "").lower()

        # 1. Cek Custom Trigger dari database
        custom_triggers = self.config.get("custom_triggers", [])
        for item in custom_triggers:
            kw = item.get("keyword", "").lower().strip()
            resp = item.get("response", "").strip()
            if kw and (kw in c or kw in expanded_c) and resp:
                return self.clean_text_for_voice(resp.replace("{username}", clean_user))

        # 2. Nalar Pertanyaan Lanjutan Menggunakan Daya Ingat User
        user_mem = self.memory.user_memories.get(username.strip().lower(), [])
        if user_mem:
            last_turn = user_mem[-1]
            last_comment = last_turn["comment"].lower()
            last_reply = last_turn["reply"].lower()

            # Jika penonton bertanya lanjutan seperti "kalau itu berapa", "tambah itu jadi berapa"
            if any(w in c for w in ["itu", "tadi", "total", "tambah", "dua-duanya", "semua"]):
                if "police pass" in last_comment or "police pass" in last_reply:
                    if "boombox" in c:
                        return f"Police Pass ditambah Boombox totalnya 27 ribu ya {clean_user}, silakan DM admin untuk jajan."
                if "boombox" in last_comment or "boombox" in last_reply:
                    if "police pass" in c:
                        return f"Boombox ditambah Police Pass jadi 27 ribu ya {clean_user}, silakan DM admin."

        # 3. Nalar Kategori Berdasarkan Scope Database
        if self.memory.get_user_repeat_freebie_count(username) >= 2:
            return f"{clean_user}, jangan sering meminta-minta ya, lebih baik berusaha dan tetap semangat!"

        if c in ["aku", "gue", "gw", "sy", "saya"]:
            return f"Iya halo kak {clean_user}, kenapa nih?"
        if c in ["alu", "halo", "hai", "ka", "kak", "kakk", "hy", "hei", "p", "halo bang", "bg", "bang"]:
            return f"Halo juga kak {clean_user}, selamat datang di live ya!"
        if "kenal" in c:
            return f"Halo kak {clean_user}, mungkin kita pernah ketemu di live sebelumnya ya!"

        if "kode" in expanded_c:
            if "tunggu" in scope_text or "perintah" in scope_text:
                return f"Tunggu dulu ya kak {clean_user}, cek sesuai perintah di live!"
            return f"Untuk kodenya sabar ya kak {clean_user}, segera diinfokan di live!"

        if any(w in expanded_c for w in ["sedang apa", "lagi apa", "main apa", "game apa"]):
            if "dds" in scope_text or "drag drive" in scope_text:
                return f"Sedang parkur di game DDS nih kak {clean_user}!"
            return f"Halo kak {clean_user}, lagi seru-seruan live streaming nih!"

        # Tanya beli / order / harga
        if any(w in expanded_c for w in ["beli", "harga", "berapa", "order", "jajan", "pesan"]):
            # Cek pricelist spesifik
            if "police" in expanded_c:
                return f"Police Pass 21 ribu ya {clean_user}, silakan DM admin kalau mau jajan."
            if "boombox" in expanded_c:
                return f"Boombox 6 ribu ya {clean_user}, silakan DM admin kalau mau jajan."
            if "painpass" in expanded_c:
                return f"Painpass 8 ribu ya {clean_user}, silakan DM admin."
            if "2x paycheck" in expanded_c or "paycheck" in expanded_c:
                return f"2x Paycheck 60 ribu ya {clean_user}, silakan DM admin."
            if "dm" in scope_text or "jajan" in scope_text:
                return f"Kalau mau jajan atau cek harga, silakan DM admin ya kak {clean_user}!"
            return f"Halo kak {clean_user}, untuk pembelian silakan hubungi admin ya!"

        # Tanya pembayaran
        if any(w in expanded_c for w in ["qris", "bayar", "transfer", "pembayaran"]):
            if "qris" in scope_text:
                return f"Jajan di sini pembayarannya cuma pakai QRIS ya kak {clean_user}!"
            return f"Untuk cara pembayaran bisa langsung tanyakan ke admin ya kak {clean_user}!"

        # Tanya server / join
        if any(w in expanded_c for w in ["join", "masuk", "cara join"]):
            return f"Untuk cara join, langsung cek dan ikuti petunjuk yang ada di live ya kak {clean_user}!"
        if any(w in expanded_c for w in ["server", "penuh", "full", "lock", "kunci"]):
            return f"Untuk info server silakan pantau live dan tunggu perintah ya kak {clean_user}!"

        # Minta gratis / minta hadiah
        if any(w in expanded_c for w in ["minta", "bagi", "plis", "pls"]):
            return f"Jangan suka meminta-minta ya kak {clean_user}, yuk main yang jujur dan semangat!"

        # Pujian
        if any(w in expanded_c for w in ["bagus", "keren", "mantap", "gg", "pro"]):
            return f"Terima kasih banyak kak {clean_user}, salam kenal ya!"

        if assisted_context and not any(w in assisted_context.lower() for w in ["ada apa", "halo, hai"]):
            return f"{assisted_context} ya kak {clean_user}!"

        return f"Halo kak {clean_user}, terima kasih sudah meramaikan live streaming kita ya!"

    def generate_reply(self, username: str, comment: str, direct_reply: str = "") -> str:
        """
        Menghasilkan teks balasan cerdas, berotak, dan berdaya ingat.
        Setiap interaksi otomatis disimpan ke sistem memori untuk pembelajaran konteks berkelanjutan.
        """
        clean_user = self.clean_username_for_speech(username)

        # 1. Trigger Instan Langsung dari database
        if direct_reply and not direct_reply.startswith("AI_ASSIST:"):
            resp = direct_reply.replace("{username}", clean_user)
            final_reply = self.clean_text_for_voice(resp)
            self.memory.remember(username, comment, final_reply)
            return final_reply

        # 2. Ekstrak panduan info jika ada AI_ASSIST
        assisted_context = ""
        if direct_reply and direct_reply.startswith("AI_ASSIST:"):
            assisted_context = direct_reply.replace("AI_ASSIST:", "").strip()

        # 3. Panggil Gemini dengan penalaran dan memori konteks
        provider = self.config.get("ai_provider", "gemini")
        reply = ""

        if provider == "gemini":
            reply = self._call_gemini(clean_user, comment, assisted_context)

        # 4. Fallback cerdas dengan daya ingat jika AI offline/limit
        if not reply:
            reply = self.generate_smart_fallback(clean_user, comment, assisted_context)

        # 5. Simpan ke sistem memori (Ingatan Pembahasan Pembicaraan)
        if reply:
            self.memory.remember(username, comment, reply)

        return reply

    def generate_greeting(self, username: str) -> str:
        """
        Menghasilkan sapaan penonton yang baru bergabung menggunakan konfigurasi greeting dari database.
        """
        clean_user = self.clean_username_for_speech(username)
        use_ai = bool(self.config.get("greeting_use_ai", False))
        provider = self.config.get("ai_provider", "gemini")

        # Jika opsi AI greeting diaktifkan di database dan Gemini siap
        if use_ai and provider == "gemini" and self.config.get("gemini_api_key"):
            try:
                room_context = self.memory.get_room_context()
                extra_note = f"\nKonteks Siaran: {room_context}" if room_context else ""
                greeting_ai = self._call_gemini(
                    clean_user,
                    "join live streaming",
                    assisted_context=f"Sapaan selamat datang ramah dan santai untuk penonton baru yang bergabung.{extra_note}"
                )
                if greeting_ai:
                    return greeting_ai
            except Exception as e:
                print(f"[AIEngine] Gagal generate greeting via AI: {e}")

        # Menggunakan template dari database
        template = self.config.get("greeting_template", "Halo kak {username}, selamat datang di live!").strip()
        if not template:
            template = "Halo kak {username}, selamat datang di live!"

        if "{username}" in template:
            return template.replace("{username}", clean_user)
        return f"{template} {clean_user}".strip()

    def test_gemini(self, api_key: str = "", model_name: str = "") -> tuple[bool, str]:
        """
        Uji koneksi Google Gemini API.
        Secara otomatis menggunakan API key dan model dari database jika parameter kosong.
        """
        key = (api_key or self.config.get("gemini_api_key", "")).strip()
        model = (model_name or self.config.get("gemini_model", "gemini-3.5-flash-lite")).strip()

        if not key:
            return False, "Gemini API Key belum diisi di database."

        try:
            test_client = genai.Client(api_key=key)
            resp = test_client.models.generate_content(
                model=model or "gemini-3.5-flash-lite",
                contents="Katakan 'API Gemini Berhasil Terhubung' secara singkat."
            )
            return True, resp.text.strip()
        except Exception as e:
            return False, str(e)
