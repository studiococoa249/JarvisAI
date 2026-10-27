import os
import sys
import time
import re
import json
import asyncio

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass
# Fix Python 3.15 lazy import bug with concurrent.futures when PySide6 is loaded
import concurrent.futures.thread
import concurrent.futures.process
import concurrent.futures
concurrent.futures.ThreadPoolExecutor = concurrent.futures.thread.ThreadPoolExecutor
concurrent.futures.ProcessPoolExecutor = concurrent.futures.process.ProcessPoolExecutor

from PySide6.QtCore import QThread, Signal
from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    ConnectEvent,
    DisconnectEvent,
    CommentEvent,
    EmoteChatEvent,
    JoinEvent,
    LiveEndEvent
)
from TikTokLive.client.errors import (
    UserOfflineError,
    UserNotFoundError,
    TikTokLiveError
)
from TikTokLive.client.web.routes.fetch_room_id_live_html import (
    FetchRoomIdLiveHTMLRoute,
    FailedParseRoomIdError
)
from TikTokLive.client.web.routes.fetch_room_id_api import FetchRoomIdAPIRoute
import TikTokLive.client.web.web_utils as web_utils

# Patch check_authenticated_session agar tidak melempar 'Target IDC must be passed when including a sessionId'
def safe_check_authenticated_session(session_id, tt_target_idc, session_required=False):
    if not session_id:
        if session_required:
            raise ValueError("Session ID required")
        return False
    if not os.getenv("WHITELIST_AUTHENTICATED_SESSION_ID_HOST"):
        os.environ["WHITELIST_AUTHENTICATED_SESSION_ID_HOST"] = "api.eulerstream.com"
    return True

web_utils.check_authenticated_session = safe_check_authenticated_session
os.environ["WHITELIST_AUTHENTICATED_SESSION_ID_HOST"] = "api.eulerstream.com"

# === HELPER: Deteksi apakah HTML dari TikTok adalah halaman WAF/challenge ===
def _is_waf_page(html: str) -> bool:
    """Cek apakah respons HTML TikTok adalah halaman WAF/Captcha (SlardarWAF) bukan konten asli."""
    if not html or len(html) < 2000:
        if "SlardarWAF" in html or "_wafchallengeid" in html or "Please wait..." in html:
            return True
    return False

# === 1. PATCH TIKTOK API ROUTE (TAMBAH aid=1988, RETRY PADA 429, SAFE JSON DECODING) ===
# TikTok mewajibkan parameter aid=1988 pada endpoint /api-live/user/room/.
# Tanpa aid=1988, TikTok akan menolak dengan pesan 'params_error'.
# Jika TikTok memberikan HTTP 429, retry dengan delay sebelum menyerah.
_orig_fetch_user_room_data = FetchRoomIdAPIRoute.fetch_user_room_data

async def patched_fetch_user_room_data(cls, web, unique_id: str):
    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            response = await web.get(
                url="https://www.tiktok.com/api-live/user/room/",
                extra_params={"uniqueId": unique_id, "sourceType": 54, "aid": 1988}
            )
            if response.status_code == 429:
                print(f"[TikTokWorker] API rate-limited (429), percobaan {attempt+1}/{max_retries}...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                raise TikTokLiveError(
                    "TikTok memblokir akses API (HTTP 429 Rate Limit). "
                    "Coba masukkan Room ID atau Link Share Live langsung di kolom username."
                )
            # Cek apakah respons HTML WAF
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type and _is_waf_page(response.text):
                print(f"[TikTokWorker] API mengembalikan WAF page, percobaan {attempt+1}/{max_retries}...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                raise TikTokLiveError(
                    "TikTok WAF memblokir pencarian Room ID dari API. "
                    "Coba masukkan Room ID atau Link Share Live langsung di kolom username."
                )
            try:
                d = response.json()
            except Exception:
                raise TikTokLiveError(
                    "Respons TikTok API bukan JSON valid (kemungkinan diblokir WAF). "
                    "Coba masukkan Room ID atau Link Share Live langsung di kolom username."
                )
            if d.get("message") == "user_not_found":
                raise UserNotFoundError(unique_id, f"Username '{unique_id}' tidak ditemukan di TikTok.")
            return d
        except (UserNotFoundError, TikTokLiveError, UserOfflineError):
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
    raise TikTokLiveError(f"Gagal mengambil data live dari TikTok setelah {max_retries} percobaan: {last_error}")

def patched_parse_api_room_id(cls, data: dict) -> str:
    """Ekstraksi Room ID dari data TikTok API dengan pengecekan status siaran yang akurat."""
    data_block = (data or {}).get("data") or {}
    live_room = data_block.get("liveRoom") or {}
    user_data = data_block.get("user") or {}

    # Status siaran: 4 = OFFLINE, 2 = LIVE
    status = live_room.get("status") if "status" in live_room else user_data.get("status")
    if status == 4:
        raise UserOfflineError("Streamer TikTok sedang offline (tidak sedang siaran live).")

    room_id = user_data.get("roomId") or live_room.get("roomId")
    if room_id:
        return str(room_id)

    raise FailedParseRoomIdError("Room ID tidak ditemukan pada data API TikTok.")

FetchRoomIdAPIRoute.fetch_user_room_data = classmethod(patched_fetch_user_room_data)
FetchRoomIdAPIRoute.parse_room_id = classmethod(patched_parse_api_room_id)

# === 2. PATCH TIKTOK HTML ROUTE UNTUK RESOLUSI ROOM ID MODERN & DESKTOP USER-AGENT ===
_orig_parse_room_id = FetchRoomIdLiveHTMLRoute.parse_room_id

DESKTOP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.tiktok.com/"
}

def extract_room_id_from_html(html: str) -> str:
    """Ekstraksi Room ID dari halaman web TikTok modern melalui JSON state atau regex HTML."""
    if not html:
        raise FailedParseRoomIdError("Halaman live TikTok kosong.")

    # 0. Deteksi WAF/Challenge page terlebih dahulu
    if _is_waf_page(html):
        raise FailedParseRoomIdError(
            "TikTok WAF/Captcha memblokir akses halaman live. "
            "Coba masukkan Room ID atau Link Share Live langsung."
        )

    # 1. Cek struktur JSON modern TikTok (__UNIVERSAL_DATA_FOR_REHYDRATION__)
    m_univ = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html)
    if m_univ:
        try:
            d = json.loads(m_univ.group(1))
            scope = d.get('__DEFAULT_SCOPE__', {})
            live_detail = scope.get('webapp.live-detail', {})
            live_room = live_detail.get('liveRoom', {})
            if live_room:
                status = live_room.get('status')
                if status == 4:
                    raise UserOfflineError("Streamer TikTok sedang offline (tidak sedang siaran live).")
                room_id = live_room.get('roomId')
                if room_id:
                    return str(room_id)
        except UserOfflineError:
            raise
        except Exception:
            pass

    # 2. Cek semua variasi atribut roomId / room_id di HTML (JSON state, props, atau window params)
    matches = (
        re.findall(r'["\']roomId["\']\s*:\s*["\']?(\d{15,22})["\']?', html) or
        re.findall(r'["\']room_id["\']\s*:\s*["\']?(\d{15,22})["\']?', html) or
        re.findall(r'room_id=(\d{15,22})', html)
    )
    if matches:
        return matches[0]

    # 3. Fallback ke parser bawaan SIGI_STATE
    try:
        return _orig_parse_room_id(html)
    except Exception:
        # Jangan raise UserOfflineError di sini — kita belum tahu pasti offline atau WAF
        raise FailedParseRoomIdError("Tidak dapat menemukan Room ID di halaman HTML TikTok.")

def patched_parse_room_id(cls, html: str) -> str:
    return extract_room_id_from_html(html)

FetchRoomIdLiveHTMLRoute.parse_room_id = classmethod(patched_parse_room_id)

async def patched_fetch_room_id_live_html_call(self, unique_id: str) -> str:
    """Resolusi Room ID yang sangat handal menggunakan Desktop Headers (mencegah redirect mobile)."""
    waf_detected = False

    req_headers = dict(DESKTOP_HEADERS)
    session_id = getattr(self, "_web", None) and self._web.cookies.get("sessionid")
    if session_id:
        req_headers["Cookie"] = f"sessionid={session_id}; sessionid_ss={session_id}; sid_tt={session_id}; tt-target-idc=useast1a"

    # Langkah 1: Coba ambil dari halaman live (@unique_id/live)
    live_url = f"https://www.tiktok.com/@{unique_id}/live"
    try:
        resp = await self._web.get(url=live_url, base_params=False, extra_headers=req_headers)
        if resp.status_code == 403:
            print(f"[TikTokWorker] HTTP 403 saat akses live page — TikTok memblokir akses.")
            waf_detected = True
        elif resp.status_code == 200:
            if _is_waf_page(resp.text):
                print(f"[TikTokWorker] WAF/Captcha terdeteksi pada halaman live @{unique_id}.")
                waf_detected = True
            else:
                rid = extract_room_id_from_html(resp.text)
                if rid:
                    return rid
    except UserOfflineError:
        raise  # Status == 4 dikonfirmasi dari JSON → benar-benar offline
    except FailedParseRoomIdError:
        waf_detected = True  # Mungkin WAF, biarkan API fallback mencoba
    except Exception as e:
        print(f"[TikTokWorker] Notice live HTML check: {e}")

    # Langkah 2: Coba ambil dari halaman profil (@unique_id)
    profile_url = f"https://www.tiktok.com/@{unique_id}"
    try:
        resp_prof = await self._web.get(url=profile_url, base_params=False, extra_headers=req_headers)
        if resp_prof.status_code == 200 and not _is_waf_page(resp_prof.text):
            html_prof = resp_prof.text
            m_prof_ids = (
                re.findall(r'["\']roomId["\']\s*:\s*["\']?(\d{15,22})["\']?', html_prof) or
                re.findall(r'["\']room_id["\']\s*:\s*["\']?(\d{15,22})["\']?', html_prof)
            )
            if m_prof_ids:
                return m_prof_ids[0]
        elif resp_prof.status_code == 403 or _is_waf_page(resp_prof.text):
            waf_detected = True
    except Exception as e:
        print(f"[TikTokWorker] Notice profile HTML check: {e}")

    # Langkah 3: Selalu coba via API endpoint sebelum menyerah!
    try:
        rid_api = await self._web.fetch_room_id_from_api(unique_id)
        if rid_api:
            return str(rid_api)
    except UserOfflineError:
        raise
    except Exception as api_err:
        print(f"[TikTokWorker] Notice API check fallback: {api_err}")

    # Langkah 4: Jika WAF terdeteksi, raise FailedParseRoomIdError
    if waf_detected:
        raise FailedParseRoomIdError(
            f"TikTok WAF memblokir pencarian Room ID untuk @{unique_id}."
        )

    # Langkah 5: Jika tidak ditemukan di mana pun
    raise UserOfflineError(f"Pengguna @{unique_id} sedang tidak melakukan live streaming (Offline).")

FetchRoomIdLiveHTMLRoute.__call__ = patched_fetch_room_id_live_html_call


def sanitize_tiktok_username(raw: str) -> str:
    """Membersihkan input username dari URL tiktok, share link (vt.tiktok.com), awalan @, maupun room_id."""
    raw = (raw or "").strip()
    if not raw:
        return ""

    # 1. Cek langsung jika input mengandung room_id angka (baik di query param maupun path)
    m_rid = re.search(r'room_id=(\d+)', raw) or re.search(r'/live/(\d+)', raw)
    if m_rid:
        return m_rid.group(1)

    # 2. Jika input berupa short link TikTok mobile (vt.tiktok.com atau vm.tiktok.com)
    if "vt.tiktok.com" in raw or "vm.tiktok.com" in raw:
        try:
            import urllib.request
            req = urllib.request.Request(
                raw,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                resolved_url = resp.geturl()
                m_rid2 = re.search(r'room_id=(\d+)', resolved_url) or re.search(r'/live/(\d+)', resolved_url)
                if m_rid2:
                    return m_rid2.group(1)
                m_user2 = re.search(r'@([a-zA-Z0-9_.-]+)', resolved_url)
                if m_user2:
                    return m_user2.group(1)
        except Exception as e:
            print(f"[sanitize_tiktok_username] Gagal resolve shortlink {raw}: {e}")

    # 3. Cek format URL standar https://www.tiktok.com/@username/live
    if "tiktok.com" in raw:
        m = re.search(r"@([a-zA-Z0-9_.-]+)", raw)
        if m:
            return m.group(1)
        m3 = re.search(r"/([a-zA-Z0-9_.-]+)/?$", raw.split("?")[0])
        if m3 and m3.group(1) != "live":
            return m3.group(1)

    # 4. Input langsung: bersihkan @ dan spasi
    return raw.lstrip("@").strip("/").strip()


class TikTokWorker(QThread):
    connected = Signal(str)             # username
    disconnected = Signal()
    status_changed = Signal(str)        # status message
    comment_received = Signal(str, str, str, bool) # (username, comment, reply, will_speak)
    join_received = Signal(str, str, bool)         # (username, greeting, will_speak)
    error_occurred = Signal(str)

    def __init__(self, username: str, ai_engine, config_manager, parent=None):
        super().__init__(parent)
        self.username = sanitize_tiktok_username(username)
        self.ai = ai_engine
        self.config = config_manager
        self.client = None
        self._is_running = True
        self.connect_time = 0.0
        self.last_greeting_time = 0.0
        self.greeted_users = set()
        self.seen_comments = {}             # {dedup_key: timestamp}
        self.user_last_comment_time = {}   # {username: timestamp}
        self.last_error_message = None

    def stop(self):
        self._is_running = False
        if self.client:
            try:
                loop = getattr(self.client, "_asyncio_loop", None) or getattr(self.client, "_loop", None)
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.client.disconnect(), loop)
            except Exception as e:
                print(f"[TikTokWorker] Error disconnect: {e}")

    async def _process_comment(self, event: CommentEvent):
        if not self._is_running:
            return

        try:
            user_obj = getattr(event, "user", None)
            username = "Penonton"
            if user_obj:
                username = (
                    getattr(user_obj, "nick_name", None) or
                    getattr(user_obj, "unique_id", None) or
                    getattr(user_obj, "nickname", None) or
                    getattr(user_obj, "username", None) or
                    "Penonton"
                )

            comment_text = getattr(event, "comment", None) or getattr(event, "content", "") or ""
            comment_text = str(comment_text).strip()

            if not comment_text:
                return

            # Deduplikasi komentar berbasis waktu (mencegah duplikat paket network)
            common = getattr(event, "common", None)
            msg_id = getattr(common, "msg_id", None) if common else None
            dedup_key = str(msg_id) if msg_id else f"{username}:{comment_text}"
            now = time.time()

            # Bersihkan cache deduplikasi jika sudah lama (> 60 detik)
            if len(self.seen_comments) > 300:
                self.seen_comments = {k: ts for k, ts in self.seen_comments.items() if (now - ts) < 60}

            if dedup_key in self.seen_comments and (now - self.seen_comments[dedup_key]) < 25:
                return
            self.seen_comments[dedup_key] = now

            # Evaluasi umur komentar: jika komentar sudah berumur > 25 detik saat tiba, lewati
            if common:
                raw_ts = getattr(common, "create_time", 0) or getattr(common, "client_send_time", 0)
                if raw_ts and raw_ts > 0:
                    comment_timestamp = (raw_ts / 1000.0) if raw_ts > 1e11 else float(raw_ts)
                    if comment_timestamp > 1.7e9:
                        age_sec = now - comment_timestamp
                        if age_sec > 25:
                            print(f"[TikTokWorker] Komentar lama ({int(age_sec)}s lalu) dilewati: '{comment_text}' dari {username}")
                            self.comment_received.emit(username, comment_text, "(Dilewati: Komentar lama > 25s)", False)
                            return

            if not self.config.get("enable_comments", True):
                self.comment_received.emit(username, comment_text, "(Fitur balas komentar dinonaktifkan)", False)
                return

            # Cooldown per penonton: cegah 1 user membanjiri antrean suara dan menenggelamkan penonton lain
            user_cooldown = self.config.get("user_comment_cooldown_sec", 8)
            last_comment_t = self.user_last_comment_time.get(username, 0)
            if (now - last_comment_t) < user_cooldown:
                print(f"[TikTokWorker] Penonton @{username} sedang jeda cooldown ({int(now - last_comment_t)}s < {user_cooldown}s)")
                self.comment_received.emit(username, comment_text, f"(Dilewati: Cooldown penonton {int(user_cooldown)}s)", False)
                return

            # Evaluasi komentar oleh AI Engine
            should_reply, reason, direct_reply = self.ai.should_reply(comment_text)

            if should_reply:
                self.user_last_comment_time[username] = now
                if len(self.user_last_comment_time) > 500:
                    self.user_last_comment_time.clear()

                # Jalankan AI di background thread agar WebSocket TikTok TIDAK PERNAH terblokir
                reply_text = await asyncio.to_thread(self.ai.generate_reply, username, comment_text, direct_reply)
                self.comment_received.emit(username, comment_text, reply_text, True)
            else:
                self.comment_received.emit(username, comment_text, f"(Dilewati: {reason})", False)
        except Exception as ex:
            print(f"[TikTokWorker] Error processing comment: {ex}")

    async def _process_join(self, event: JoinEvent):
        if not self._is_running:
            return

        try:
            user_obj = getattr(event, "user", None)
            username = "Kawan"
            if user_obj:
                username = (
                    getattr(user_obj, "nick_name", None) or
                    getattr(user_obj, "unique_id", None) or
                    getattr(user_obj, "nickname", None) or
                    getattr(user_obj, "username", None) or
                    "Kawan"
                )

            if not self.config.get("enable_greetings", True):
                return

            # Cek duplikat user
            if username in self.greeted_users:
                return

            # Cek jeda cooldown sapaan
            now = time.time()
            cooldown = self.config.get("greeting_cooldown_sec", 5)
            if (now - self.last_greeting_time) < cooldown:
                return

            self.last_greeting_time = now
            self.greeted_users.add(username)
            if len(self.greeted_users) > 500:
                self.greeted_users.clear()

            greeting_text = self.ai.generate_greeting(username)
            self.join_received.emit(username, greeting_text, True)
        except Exception as ex:
            print(f"[TikTokWorker] Error processing join: {ex}")

    def run(self):
        if not self.username:
            self.error_occurred.emit("Username TikTok kosong atau format tidak valid.")
            self.status_changed.emit("Offline (Username tidak valid)")
            self.disconnected.emit()
            return

        self._is_running = True
        self.last_error_message = None
        consecutive_failures = 0
        known_room_id = int(self.username) if self.username.isdigit() else None

        # Browser headers untuk mencegah WAF bot-blocking TikTok (gunakan Desktop Chrome)
        custom_headers = dict(DESKTOP_HEADERS)

        # === Ambil Session ID dari config untuk bypass WAF TikTok ===
        session_id = (self.config.get("tiktok_session_id", "") or "").strip()

        # === LOOP AUTO-RECONNECT OTOMATIS JIKA KONEKSI TIKTOK TERPUTUS SEMENTARA ===
        while self._is_running:
            self.status_changed.emit(f"Menghubungkan ke live @{self.username}...")
            is_live_ended = False

            try:
                self.client = TikTokLiveClient(
                    unique_id=self.username,
                    web_kwargs={"httpx_kwargs": {"headers": custom_headers}}
                )

                # Jika ada session ID, set cookie agar request terautentikasi (bypass WAF)
                if session_id:
                    print(f"[TikTokWorker] Menggunakan TikTok Session ID untuk bypass WAF...")
                    self.client.web.set_session(session_id, "useast1a")

                @self.client.on(ConnectEvent)
                async def on_connect(event: ConnectEvent):
                    nonlocal known_room_id, consecutive_failures
                    consecutive_failures = 0
                    self.connect_time = time.time()
                    if getattr(self.client, "room_id", None):
                        known_room_id = self.client.room_id
                    self.connected.emit(self.username)
                    self.status_changed.emit(f"Terkoneksi ke live @{self.username}")
                    print(f"[TikTokWorker] Berhasil tersambung ke live @{self.username} (Room ID: {getattr(self.client, 'room_id', known_room_id)})")

                @self.client.on(DisconnectEvent)
                async def on_disconnect(event: DisconnectEvent):
                    # Jika disconnect sementara dari server TikTok dan user tidak menekan stop, persiapkan auto-reconnect
                    if self._is_running and not is_live_ended:
                        print(f"[TikTokWorker] Sinyal Disconnect dari TikTok (reset koneksi). Mempersiapkan reconnect otomatis...")

                @self.client.on(LiveEndEvent)
                async def on_live_end(event: LiveEndEvent):
                    nonlocal is_live_ended
                    is_live_ended = True
                    self._is_running = False
                    self.status_changed.emit(f"Live streaming @{self.username} telah berakhir")
                    print(f"[TikTokWorker] Siaran live @{self.username} telah diakhiri oleh streamer.")

                @self.client.on(CommentEvent)
                async def on_comment(event: CommentEvent):
                    if not self._is_running:
                        return
                    # Jalankan pemrosesan di background task agar loop WebSocket TikTok TIDAK terblokir
                    asyncio.create_task(self._process_comment(event))

                @self.client.on(EmoteChatEvent)
                async def on_emote(event: EmoteChatEvent):
                    if not self._is_running:
                        return
                    asyncio.create_task(self._process_comment(event))

                @self.client.on(JoinEvent)
                async def on_join(event: JoinEvent):
                    if not self._is_running:
                        return
                    asyncio.create_task(self._process_join(event))

                # Jalankan client TikTok:
                # - process_connect_events=False: agar tidak memproses event backlog lama saat join
                # - fetch_live_check=False: lewati check_alive bawaan yang sering bug
                run_kwargs = {
                    "process_connect_events": False,
                    "fetch_live_check": False
                }
                if known_room_id:
                    run_kwargs["room_id"] = int(known_room_id)

                self.client.run(**run_kwargs)

            except UserOfflineError:
                if is_live_ended or not known_room_id:
                    self.last_error_message = (
                        f"Pengguna @{self.username} sedang tidak melakukan live streaming (Offline).\n"
                        "Jika sebenarnya sedang live, coba:\n"
                        "• Masukkan Room ID atau Link Share Live langsung di kolom username\n"
                        "• Atau isi Session ID TikTok di menu Pengaturan"
                    )
                    self.error_occurred.emit(self.last_error_message)
                    self._is_running = False
                    break
                else:
                    # Mungkin room_id sebelumnya telah berganti, coba cari ulang
                    known_room_id = None
            except UserNotFoundError:
                self.last_error_message = f"Username @{self.username} tidak ditemukan di TikTok."
                self.error_occurred.emit(self.last_error_message)
                self._is_running = False
                break
            except FailedParseRoomIdError as e:
                err_str = str(e)
                print(f"[TikTokWorker] FailedParseRoomIdError: {err_str}")
                # WAF memblokir HTML dan API, beri pesan yang jelas
                self.last_error_message = (
                    f"TikTok WAF memblokir koneksi otomatis ke @{self.username}.\n"
                    "Solusi:\n"
                    "• Di TikTok, tekan Share Live → Salin Link, lalu tempelkan di kolom username\n"
                    "• Atau isi Session ID TikTok di menu Pengaturan (AI & Voice)"
                )
                self.error_occurred.emit(self.last_error_message)
                self._is_running = False
                break
            except TikTokLiveError as e:
                err_str = str(e)
                print(f"[TikTokWorker] TikTokLive notice: {err_str}")
                # Cek apakah ini error WAF/rate-limit yang sudah kita tandai
                if "WAF" in err_str or "429" in err_str or "Room ID" in err_str:
                    self.last_error_message = (
                        f"TikTok memblokir pencarian Room ID untuk @{self.username}.\n"
                        "Solusi: Masukkan Room ID / Link Share Live langsung, "
                        "atau isi Session ID TikTok di Pengaturan."
                    )
                    self.error_occurred.emit(self.last_error_message)
                    self._is_running = False
                    break
            except Exception as e:
                err_str = str(e)
                print(f"[TikTokWorker] Runtime notice: {err_str}")
                if "Target IDC" in err_str:
                    self.last_error_message = (
                        f"Otentikasi Session ID gagal: {err_str}.\n"
                        "Kosongkan Session ID di Pengaturan jika tidak diperlukan."
                    )
                    self.error_occurred.emit(self.last_error_message)
                    self._is_running = False
                    break
                if "UserOfflineError" in err_str:
                    known_room_id = None

            # Jika live streaming diakhiri secara normal atau user menghentikan secara manual
            if is_live_ended or not self._is_running:
                break

            # AUTO-RECONNECT: Terputus sementara dari server TikTok, sambungkan ulang otomatis
            consecutive_failures += 1
            if consecutive_failures > 15:
                self.last_error_message = f"Koneksi ke live @{self.username} terputus berulang kali."
                self.error_occurred.emit(self.last_error_message)
                break

            retry_wait = min(2 * consecutive_failures, 8)
            self.status_changed.emit(f"Koneksi terputus. Menyambungkan kembali dalam {retry_wait}s ({consecutive_failures})...")
            print(f"[TikTokWorker] Mencoba menyambung kembali otomatis ke @{self.username} dalam {retry_wait}s (percobaan {consecutive_failures})...")

            for _ in range(int(retry_wait * 2)):
                if not self._is_running:
                    break
                time.sleep(0.5)

        # Keluar loop: proses live selesai sepenuhnya
        self.disconnected.emit()
        if self.last_error_message:
            self.status_changed.emit(f"Offline ({self.last_error_message})")
        else:
            self.status_changed.emit("Status: Offline")
