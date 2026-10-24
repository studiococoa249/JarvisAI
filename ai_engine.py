import re
from google import genai
from google.genai import types

class AIEngine:
    def __init__(self, config_manager):
        self.config = config_manager
        self._gemini_client = None
        self._cached_gemini_key = None

    def get_active_provider_info(self) -> str:
        provider = self.config.get("ai_provider", "gemini")
        if provider == "gemini":
            key = self.config.get("gemini_api_key", "").strip()
            if key:
                model = self.config.get("gemini_model", "gemini-3.5-flash-lite")
                return f"Google Gemini ({model})"
        return "Mode Cerdas (Smart Rules)"

    def clean_text_for_voice(self, text: str) -> str:
        """Membersihkan markdown, karakter aneh, dan emoji agar suara natural saat diucapkan."""
        if not text:
            return ""
        # Hapus markdown formatting: **bold**, *italic*, # heading, `code`, dll.
        text = re.sub(r'[*_#`~]', '', text)
        # Hapus URL
        text = re.sub(r'https?://\S+', '', text)
        # Hapus tanda kutip luar jika ada
        text = text.strip('"\' ')
        # Rapikan spasi berlebih
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def should_reply(self, comment: str) -> tuple[bool, str, str]:
        """
        Mengecek apakah komentar harus dibalas.
        Returns:
            (should_reply: bool, reason: str, direct_reply: str)
            direct_reply bisa berupa teks jawaban langsung, atau 'AI_ASSIST:<panduan>' jika komentar kompleks.
        """
        comment_lower = comment.lower().strip()
        words = comment.strip().split()

        # 1. Cek Blacklist (menggunakan word boundary)
        blacklist = self.config.get("blacklist_keywords", [])
        for bad in blacklist:
            bad_clean = bad.strip().lower()
            if bad_clean:
                # Cocokkan kata utuh atau substring jika panjang kata > 3
                if re.search(r'\b' + re.escape(bad_clean) + r'\b', comment_lower) or (len(bad_clean) > 3 and bad_clean in comment_lower):
                    return False, f"Kata blacklist: '{bad}'", ""

        # 2. Cek Custom Triggers (Mendukung 1 kata maupun frasa beberapa kata)
        custom_triggers = self.config.get("custom_triggers", [])
        matched_triggers = []
        for item in custom_triggers:
            kw = item.get("keyword", "").lower().strip()
            resp = item.get("response", "").strip()
            if kw and resp:
                # Periksa apakah kata/frasa cocok dalam komentar
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, comment_lower) or kw in comment_lower:
                    matched_triggers.append((kw, resp))

        # 3. Cek Mode Balasan (Whitelist)
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
            if not has_whitelist and not matched_triggers:
                return False, "Tidak ada kata kunci whitelist", ""

        # Komentar terlalu pendek
        if len(comment.strip()) <= 1:
            return False, "Komentar terlalu singkat", ""

        # 4. Evaluasi Trigger yang Cocok:
        if matched_triggers:
            kw, direct_resp = matched_triggers[0]
            kw_words = len(kw.strip().split())
            total_words = len(words)

            # Jika komentar penonton HANYA berisi kata kunci tersebut (misal komentar cuma "bang" atau "halo bang"):
            # Maka cocok untuk respon instan cepat
            if total_words <= kw_words + 1:
                return True, f"Trigger instan cocok: '{kw}'", direct_resp
            else:
                # Jika komentar memiliki kata-kata/pertanyaan lanjutan (misal: "bang spill baju hitam"):
                # JANGAN dibatasi template kaku! AI mengambil alih untuk menjawab pertanyaan penonton secara tuntas!
                return True, f"Komentar memuat pertanyaan ('{kw}'), diproses AI", f"AI_ASSIST:{direct_resp}"

        return True, "Komentar valid untuk dibalas AI", ""

    def generate_smart_fallback(self, username: str, comment: str, assisted_context: str = "") -> str:
        """
        Balasan cerdas berbasis deteksi konteks komentar.
        """
        c = comment.lower()

        # Minta spill produk / lihat warna / ukuran
        if any(w in c for w in ["spill", "lihat", "tunjukin", "review", "coba", "pake", "pakai", "warna", "size", "ukuran"]):
            return f"Siap kak {username}, produknya segera kita spill, jangan lupa tap-tap layarnya ya!"

        # Tanya harga / ongkir / promo
        if any(w in c for w in ["harga", "berapa", "price", "ongkir", "biaya", "harganya", "rp", "diskon", "murah"]):
            return f"Untuk info harga dan promo terbarunya, langsung cek di keranjang kuning ya kak {username}!"

        # Tanya ketersediaan stok
        if any(w in c for w in ["ready", "stok", "masih ada", "habis", "ada gak", "tersedia"]):
            return f"Stoknya masih ready kak {username}, yuk langsung di-checkout sebelum kehabisan!"

        # Tanya pengiriman & COD
        if any(w in c for w in ["kirim", "dikirim", "dari mana", "cod", "bisa cod", "kapan sampai", "lokasi"]):
            return f"Bisa COD dan siap dikirim hari ini juga ya kak {username}!"

        # Jika ada panduan toko khusus dari trigger (bukan sekadar sapaan umum)
        if assisted_context and not any(w in assisted_context.lower() for w in ["ada apa", "halo, hai"]):
            return f"{assisted_context} ya kak {username}!"

        # Sapaan penonton
        if any(w in c for w in ["halo", "hai", "assalamu", "pagi", "siang", "sore", "malam", "hy", "hello", "hei"]):
            return f"Halo juga kak {username}, selamat bergabung di live streaming kami!"

        # Pujian
        if any(w in c for w in ["bagus", "keren", "cantik", "mantap", "suka", "lucu"]):
            return f"Terima kasih banyak pujiannya kak {username}, jangan sampai lolos promonya ya!"

        # Checkout / Beli
        if any(w in c for w in ["co", "checkout", "beli", "pesan", "order", "payment", "sudah co"]):
            return f"Terima kasih sudah checkout kak {username}, pesanan segera kami proses!"

        if assisted_context:
            return f"{assisted_context} kak {username}!"

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
        # Ambil maksimal 2 kata pertama agar sapaan ringkas
        parts = u.split()
        if len(parts) > 2:
            u = " ".join(parts[:2])
        return u.title()

    def generate_smart_fallback(self, username: str, comment: str, assisted_context: str = "") -> str:
        """
        Balasan cerdas berbasis deteksi konteks komentar jika AI offline/limit.
        """
        clean_user = self.clean_username_for_speech(username)
        c = comment.lower().strip()

        # Komentar singkat / ambigu (seperti yang sering diketik penonton TikTok)
        if c in ["aku", "gue", "gw", "sy", "saya"]:
            return f"Iya halo kak {clean_user}, kenapa nih?"
        if c in ["alu", "halo", "hai", "ka", "kak", "kakk", "hy", "hei"]:
            return f"Halo juga kak {clean_user}, selamat datang di live ya!"
        if "kenal" in c:
            return f"Halo kak {clean_user}, mungkin kita pernah ketemu di live sebelumnya ya!"

        # Minta spill produk / lihat warna / ukuran
        if any(w in c for w in ["spill", "lihat", "tunjukin", "review", "coba", "pake", "pakai", "warna", "size", "ukuran"]):
            return f"Siap kak {clean_user}, produknya segera kita spill, jangan lupa tap-tap layarnya ya!"

        # Tanya harga / ongkir / promo
        if any(w in c for w in ["harga", "berapa", "price", "ongkir", "biaya", "harganya", "rp", "diskon", "murah"]):
            return f"Untuk info harga dan promo terbarunya, langsung cek di keranjang kuning ya kak {clean_user}!"

        # Tanya ketersediaan stok
        if any(w in c for w in ["ready", "stok", "masih ada", "habis", "ada gak", "tersedia"]):
            return f"Stoknya masih ready kak {clean_user}, yuk langsung di-checkout sebelum kehabisan!"

        # Tanya pengiriman & COD
        if any(w in c for w in ["kirim", "dikirim", "dari mana", "cod", "bisa cod", "kapan sampai", "lokasi"]):
            return f"Bisa COD dan siap dikirim hari ini juga ya kak {clean_user}!"

        # Jika ada panduan toko khusus dari trigger (bukan sekadar sapaan umum)
        if assisted_context and not any(w in assisted_context.lower() for w in ["ada apa", "halo, hai"]):
            return f"{assisted_context} ya kak {clean_user}!"

        # Sapaan penonton
        if any(w in c for w in ["halo", "hai", "assalamu", "pagi", "siang", "sore", "malam"]):
            return f"Halo juga kak {clean_user}, selamat bergabung di live streaming kami!"

        # Pujian
        if any(w in c for w in ["bagus", "keren", "cantik", "mantap", "suka", "lucu"]):
            return f"Terima kasih banyak pujiannya kak {clean_user}, salam kenal ya!"

        # Checkout / Beli
        if any(w in c for w in ["co", "checkout", "beli", "pesan", "order", "payment", "sudah co"]):
            return f"Terima kasih sudah checkout kak {clean_user}, pesanan segera kami proses!"

        if assisted_context:
            return f"{assisted_context} kak {clean_user}!"

        # Umum
        return f"Halo kak {clean_user}, terima kasih sudah meramaikan live streaming kita ya!"


    def _call_gemini(self, username: str, comment: str, assisted_context: str = "") -> str:
        """Memanggil Google Gemini API."""
        api_key = self.config.get("gemini_api_key", "").strip()
        if not api_key:
            return ""

        if self._gemini_client is None or self._cached_gemini_key != api_key:
            self._gemini_client = genai.Client(api_key=api_key)
            self._cached_gemini_key = api_key

        clean_user = self.clean_username_for_speech(username)

        base_prompt = self.config.get(
            "ai_system_prompt",
            "Kamu adalah asisten host live streaming TikTok yang ramah, santai, dan cerdas."
        ).strip()

        scope_ai_text = self.config.get("scope_ai_text", "").strip()
        if scope_ai_text:
            system_instruction = f"{base_prompt}\n\nPANDUAN & RUANG LINGKUP LIVE (SCOPE AI):\n{scope_ai_text}"
        else:
            system_instruction = base_prompt

        extra_note = ""
        if assisted_context:
            extra_note = f"\nInformasi Penting Toko / Trigger: {assisted_context}\n"

        prompt = (
            f"Penonton TikTok Live bernama '{clean_user}' berkomentar: \"{comment}\"\n"
            f"{extra_note}"
            f"Tugas: Berikan 1 kalimat balasan langsung (maksimal 15 kata, bahasa Indonesia natural santai) sesuai Scope AI di atas tanpa awalan penjelasan."
        )

        models_to_try = [
            self.config.get("gemini_model", "gemini-3.5-flash-lite"),
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-flash-latest",
            "gemini-3.1-flash-lite"
        ]
        seen = set()
        clean_models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]
        max_tokens = 100
        for m_name in clean_models:
            try:
                response = self._gemini_client.models.generate_content(
                    model=m_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.5,
                        max_output_tokens=max_tokens,
                    )
                )
                raw_text = response.text or ""
                clean = self.clean_text_for_voice(raw_text)
                if clean:
                    return clean
            except Exception as e:
                print(f"[AIEngine] Gemini ({m_name}) error: {e}")

        return ""

    def generate_reply(self, username: str, comment: str, direct_reply: str = "") -> str:
        """
        Menghasilkan teks balasan cerdas.
        - Jika komentar singkat & cocok dengan trigger: langsung balas instan.
        - Jika komentar panjang (3+ kata): AI merespon dengan bantuan info trigger!
        """
        clean_user = self.clean_username_for_speech(username)

        # 1. Trigger Instan Langsung (Hanya jika bukan AI_ASSIST)
        if direct_reply and not direct_reply.startswith("AI_ASSIST:"):
            resp = direct_reply.replace("{username}", clean_user)
            return self.clean_text_for_voice(resp)

        # 2. Ekstrak panduan info jika ada AI_ASSIST
        assisted_context = ""
        if direct_reply and direct_reply.startswith("AI_ASSIST:"):
            assisted_context = direct_reply.replace("AI_ASSIST:", "").strip()

        provider = self.config.get("ai_provider", "gemini")
        reply = ""

        # 3. Coba panggil AI Provider terpilih (Google Gemini)
        if provider == "gemini":
            reply = self._call_gemini(clean_user, comment, assisted_context)

        # 4. Fallback Cerdas jika AI offline/timeout
        if not reply:
            reply = self.generate_smart_fallback(clean_user, comment, assisted_context)

        return reply

    def generate_greeting(self, username: str) -> str:
        """Menghasilkan sapaan penonton yang baru masuk."""
        clean_user = self.clean_username_for_speech(username)
        use_ai = self.config.get("greeting_use_ai", False)

        if use_ai:
            provider = self.config.get("ai_provider", "gemini")
            if provider == "gemini":
                greeting_prompt = f"Sapa dengan ramah penonton live bernama '{clean_user}' dalam 1 kalimat sangat singkat (maksimal 10 kata)."
                ai_greet = self._call_gemini(clean_user, greeting_prompt)
                if ai_greet:
                    return ai_greet

        template = self.config.get("greeting_template", "Halo kak {username}, selamat datang di live!")
        return template.replace("{username}", clean_user)


    def test_gemini(self, api_key: str, model_name: str = "gemini-3.5-flash-lite") -> tuple[bool, str]:
        """Uji koneksi Google Gemini API."""
        try:
            test_client = genai.Client(api_key=api_key.strip())
            resp = test_client.models.generate_content(
                model=model_name or "gemini-3.5-flash-lite",
                contents="Katakan 'API Gemini Berhasil Terhubung' secara singkat."
            )
            return True, resp.text.strip()
        except Exception as e:
            return False, str(e)
