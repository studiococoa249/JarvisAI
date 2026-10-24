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
from PySide6.QtCore import QThread, Signal
from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    ConnectEvent,
    DisconnectEvent,
    CommentEvent,
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

# === 1. PATCH TIKTOK API ROUTE (TAMBAH aid=1988 & SAFE JSON DECODING) ===
# TikTok mewajibkan parameter aid=1988 pada endpoint /api-live/user/room/.
# Tanpa aid=1988, TikTok akan menolak dengan pesan 'params_error'.
# Jika TikTok memberikan HTTP 429 atau HTML WAF, jangan biarkan JSONDecodeError meledak.
_orig_fetch_user_room_data = FetchRoomIdAPIRoute.fetch_user_room_data

async def patched_fetch_user_room_data(cls, web, unique_id: str):
    try:
        response = await web.get(
            url="https://www.tiktok.com/api-live/user/room/",
            extra_params={"uniqueId": unique_id, "sourceType": 54, "aid": 1988}
        )
        if response.status_code == 429:
            raise TikTokLiveError("TikTok membatasi akses API (HTTP 429 Too Many Requests).")
        try:
            d = response.json()
        except Exception:
            raise TikTokLiveError("Respons TikTok API bukan format JSON yang valid (kemungkinan diblokir WAF/Rate limit).")
            
        if d.get("message") == "user_not_found":
            raise UserNotFoundError(unique_id, f"Username '{unique_id}' tidak ditemukan di TikTok.")
        return d
    except (UserNotFoundError, TikTokLiveError, UserOfflineError):
        raise
    except Exception as e:
        raise TikTokLiveError(f"Gagal mengambil data live dari TikTok: {e}")

FetchRoomIdAPIRoute.fetch_user_room_data = classmethod(patched_fetch_user_room_data)

# === 2. PATCH TIKTOK HTML ROUTE UNTUK RESOLUSI ROOM ID MODERN & PROFIL TIKTOK ===
_orig_parse_room_id = FetchRoomIdLiveHTMLRoute.parse_room_id

def patched_parse_room_id(cls, html: str) -> str:
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

    # 2. Cek pola regex roomId langsung di HTML
    m_rid = re.search(r'\"roomId\":\"(\d+)\"', html)
    if m_rid:
        return m_rid.group(1)

    # 3. Fallback ke parser bawaan TikTokLive (SIGI_STATE)
    try:
        return _orig_parse_room_id(html)
    except Exception:
        raise UserOfflineError("Streamer TikTok sedang offline atau room tidak ditemukan.")

FetchRoomIdLiveHTMLRoute.parse_room_id = classmethod(patched_parse_room_id)

async def patched_fetch_room_id_live_html_call(self, unique_id: str) -> str:
    """Resolusi Room ID yang sangat handal dengan memeriksa live page, profile page, dan status webcast."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
        "Referer": "https://www.tiktok.com/"
    }

    # Langkah 1: Coba ambil dari halaman live (@unique_id/live)
    live_url = f"https://www.tiktok.com/@{unique_id}/live"
    try:
        resp = await self._web.get(url=live_url, base_params=False, extra_headers=headers)
        html = resp.text
        m_univ = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html)
        if m_univ:
            d = json.loads(m_univ.group(1))
            scope = d.get('__DEFAULT_SCOPE__', {})
            live_detail = scope.get('webapp.live-detail', {})
            live_room = live_detail.get('liveRoom', {})
            if live_room:
                if live_room.get('status') == 4:
                    raise UserOfflineError(f"Streamer @{unique_id} sedang offline.")
                rid = live_room.get('roomId')
                if rid:
                    return str(rid)
        m_rid = re.search(r'\"roomId\":\"(\d+)\"', html)
        if m_rid:
            return m_rid.group(1)
    except UserOfflineError:
        raise
    except Exception as e:
        print(f"[TikTokWorker] Notice live HTML check: {e}")

    # Langkah 2: Coba ambil dari halaman profil (@unique_id)
    # TikTok seringkali menyimpan roomId siaran yang sedang berjalan di profil pengguna
    profile_url = f"https://www.tiktok.com/@{unique_id}"
    try:
        resp_prof = await self._web.get(url=profile_url, base_params=False, extra_headers=headers)
        html_prof = resp_prof.text
        m_prof = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html_prof)
        if m_prof:
            d_prof = json.loads(m_prof.group(1))
            scope_prof = d_prof.get('__DEFAULT_SCOPE__', {})
            user_detail = scope_prof.get('webapp.user-detail')
            if user_detail:
                user_info = user_detail.get('userInfo', {})
                user = user_info.get('user', {})
                rid = user.get('roomId')
                if rid and str(rid).isdigit() and int(rid) > 0:
                    # Validasi apakah siaran live aktif via webcast check_alive
                    check_resp = await self._web.get(
                        url="https://webcast.tiktok.com/webcast/room/check_alive/",
                        extra_params={"room_ids": str(rid)}
                    )
                    check_json = check_resp.json()
                    data_list = check_json.get("data", [])
                    if data_list and data_list[0].get("alive"):
                        return str(rid)
                    else:
                        raise UserOfflineError(f"Streamer @{unique_id} sedang offline (tidak sedang siaran live).")
    except UserOfflineError:
        raise
    except Exception as e:
        print(f"[TikTokWorker] Notice profile HTML check: {e}")

    # Langkah 3: Jika tidak ditemukan sama sekali, tandai offline
    raise UserOfflineError(f"Streamer @{unique_id} sedang offline atau siaran live tidak aktif.")

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
        self.last_error_message = None

    def stop(self):
        self._is_running = False
        if self.client:
            try:
                loop = getattr(self.client, "_loop", None)
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.client.disconnect(), loop)
            except Exception as e:
                print(f"[TikTokWorker] Error disconnect: {e}")

    def run(self):
        if not self.username:
            self.error_occurred.emit("Username TikTok kosong atau format tidak valid.")
            self.status_changed.emit("Offline (Username tidak valid)")
            self.disconnected.emit()
            return

        self.last_error_message = None
        self.status_changed.emit(f"Menghubungkan ke live @{self.username}...")

        # Browser headers untuk mencegah WAF bot-blocking TikTok
        custom_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.tiktok.com/"
        }

        try:
            self.client = TikTokLiveClient(
                unique_id=self.username,
                web_kwargs={"httpx_kwargs": {"headers": custom_headers}}
            )

            @self.client.on(ConnectEvent)
            async def on_connect(event: ConnectEvent):
                self.connect_time = time.time()
                self.connected.emit(self.username)
                self.status_changed.emit(f"Terkoneksi ke live @{self.username}")
                print(f"[TikTokWorker] Berhasil tersambung ke live @{self.username} pada epoch {self.connect_time}")

            @self.client.on(DisconnectEvent)
            async def on_disconnect(event: DisconnectEvent):
                self.disconnected.emit()
                self.status_changed.emit("Koneksi live terputus")

            @self.client.on(LiveEndEvent)
            async def on_live_end(event: LiveEndEvent):
                self.status_changed.emit(f"Live streaming @{self.username} telah berakhir")
                self.disconnected.emit()

            @self.client.on(CommentEvent)
            async def on_comment(event: CommentEvent):
                if not self._is_running:
                    return

                try:
                    user_obj = getattr(event, "user", None)
                    username = "Penonton"
                    if user_obj:
                        username = (
                            getattr(user_obj, "nick_name", None) or
                            getattr(user_obj, "nickname", None) or
                            getattr(user_obj, "unique_id", None) or
                            "Penonton"
                        )

                    comment_text = getattr(event, "comment", None) or getattr(event, "content", "") or ""
                    comment_text = str(comment_text).strip()

                    if not comment_text:
                        return

                    # === FILTER REAL-TIME: KOMENTAR > 5 MENIT JANGAN DIAMBIL & DIBALAS ===
                    now = time.time()
                    comment_timestamp = None

                    # 1. Ambil waktu pembuatan dari common protobuf
                    common = getattr(event, "common", None)
                    if common:
                        raw_ts = getattr(common, "create_time", 0) or getattr(common, "client_send_time", 0)
                        if raw_ts and raw_ts > 0:
                            comment_timestamp = (raw_ts / 1000.0) if raw_ts > 1e11 else float(raw_ts)

                    # 2. Ambil dari screen_time jika belum didapat
                    if not comment_timestamp:
                        s_time = getattr(event, "screen_time", 0)
                        if s_time and s_time > 0:
                            comment_timestamp = (s_time / 1000.0) if s_time > 1e11 else float(s_time)

                    # Evaluasi selisih waktu
                    if comment_timestamp and comment_timestamp > 0:
                        age_sec = now - comment_timestamp
                        # Lewat minimal 5 menit (300 detik)
                        if age_sec > 300:
                            print(f"[TikTokWorker] Komentar kadaluarsa ({int(age_sec)}s lalu) dilewati: '{comment_text}' dari {username}")
                            self.comment_received.emit(username, comment_text, f"(Dilewati: Komentar usang > 5 menit lalu)", False)
                            return

                        # Jika komentar terjadi jauh sebelum bot tersambung (> 30 detik sebelum connect)
                        if self.connect_time > 0 and comment_timestamp < (self.connect_time - 30):
                            print(f"[TikTokWorker] Komentar sebelum bot online dilewati: '{comment_text}' dari {username}")
                            self.comment_received.emit(username, comment_text, f"(Dilewati: Komentar sebelum bot terhubung)", False)
                            return

                    if not self.config.get("enable_comments", True):
                        self.comment_received.emit(username, comment_text, "(Fitur balas komentar dinonaktifkan)", False)
                        return

                    # Evaluasi komentar oleh AI Engine
                    should_reply, reason, direct_reply = self.ai.should_reply(comment_text)

                    if should_reply:
                        reply_text = self.ai.generate_reply(username, comment_text, direct_reply)
                        self.comment_received.emit(username, comment_text, reply_text, True)
                    else:
                        self.comment_received.emit(username, comment_text, f"(Dilewati: {reason})", False)
                except Exception as ex:
                    print(f"[TikTokWorker] Error processing comment: {ex}")

            @self.client.on(JoinEvent)
            async def on_join(event: JoinEvent):
                if not self._is_running:
                    return

                try:
                    user_obj = getattr(event, "user", None)
                    username = "Kawan"
                    if user_obj:
                        username = (
                            getattr(user_obj, "nick_name", None) or
                            getattr(user_obj, "nickname", None) or
                            getattr(user_obj, "unique_id", None) or
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

            # Jalankan client TikTok:
            # - process_connect_events=False: agar tidak memproses event backlog lama saat join
            # - fetch_live_check=False: lewati check_alive TikTok yang sering bug mengembalikan status offline
            run_kwargs = {
                "process_connect_events": False,
                "fetch_live_check": False
            }
            if self.username.isdigit():
                run_kwargs["room_id"] = int(self.username)
            self.client.run(**run_kwargs)

        except UserOfflineError:
            self.last_error_message = f"Pengguna @{self.username} sedang tidak melakukan live streaming (Offline)."
            self.error_occurred.emit(self.last_error_message)
        except UserNotFoundError:
            self.last_error_message = f"Username @{self.username} tidak ditemukan di TikTok."
            self.error_occurred.emit(self.last_error_message)
        except TikTokLiveError as e:
            self.last_error_message = f"Kesalahan TikTokLive: {str(e)}"
            self.error_occurred.emit(self.last_error_message)
        except Exception as e:
            err_str = str(e)
            if "UserOfflineError" in err_str or "offline" in err_str.lower():
                self.last_error_message = f"Pengguna @{self.username} sedang tidak live (Offline)."
            elif isinstance(e, json.JSONDecodeError) or "Expecting value" in err_str:
                self.last_error_message = f"TikTok membatasi akses sementara (Rate limit / WAF). Coba beberapa saat lagi atau masukkan Room ID langsung."
            else:
                self.last_error_message = f"Gagal koneksi live @{self.username}: {err_str}"
            self.error_occurred.emit(self.last_error_message)
        finally:
            self.disconnected.emit()
            if self.last_error_message:
                self.status_changed.emit(f"Offline ({self.last_error_message})")
            else:
                self.status_changed.emit("Status: Offline")
