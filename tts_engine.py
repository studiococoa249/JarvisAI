import os
import uuid
import wave
import asyncio
import subprocess
import tempfile
import edge_tts
from PySide6.QtCore import QObject, Signal, QUrl, Slot
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from google import genai
from google.genai import types

AVAILABLE_VOICES = [
    # === SUARA DEWASA (ADULT VOICES) ===
    {
        "id": "id-ID-GadisNeural",
        "name": "👩 Gadis (Wanita Dewasa - Indonesia Alami)",
        "category": "dewasa",
        "engine": "edge",
        "voice_base": "id-ID-GadisNeural",
        "formant_shift": None,
        "gender": "Female"
    },
    {
        "id": "id-ID-ArdiNeural",
        "name": "👨 Ardi (Pria Dewasa - Indonesia Alami)",
        "category": "dewasa",
        "engine": "edge",
        "voice_base": "id-ID-ArdiNeural",
        "formant_shift": None,
        "gender": "Male"
    },
    {
        "id": "gemini_Kore",
        "name": "🌟 Kore (Wanita Dewasa - Gemini Real Human)",
        "category": "dewasa",
        "engine": "gemini",
        "voice_preset": "Kore",
        "formant_shift": None,
        "prompt_style": "Ucapkan dengan sangat ramah, hangat, dan natural seperti wanita dewasa host live streaming: ",
        "gender": "Female"
    },
    {
        "id": "gemini_Puck",
        "name": "🌟 Puck (Pria Dewasa - Gemini Real Human)",
        "category": "dewasa",
        "engine": "gemini",
        "voice_preset": "Puck",
        "formant_shift": None,
        "prompt_style": "Ucapkan dengan santai, asyik, dan ramah seperti pria dewasa host live streaming: ",
        "gender": "Male"
    },

    # === SUARA ANAK-ANAK (CHILDREN 2 - 5 TAHUN) ===
    {
        "id": "child_girl_caca",
        "name": "👶 Caca (Balita Perempuan 2-3 Tahun - Sangat Imut, Ceria & Polos)",
        "category": "anak",
        "engine": "edge_child",
        "voice_base": "id-ID-GadisNeural",
        "formant_shift": 1.40,
        "gender": "Female"
    },
    {
        "id": "child_girl_mia",
        "name": "👧 Mia (Anak Perempuan 4-5 Tahun - Ceria, Ramah & Manis)",
        "category": "anak",
        "engine": "edge_child",
        "voice_base": "id-ID-GadisNeural",
        "formant_shift": 1.32,
        "gender": "Female"
    },
    {
        "id": "child_boy_nino",
        "name": "👦 Nino (Anak Laki-Laki 3-4 Tahun - Lucu, Ceria & Gemas)",
        "category": "anak",
        "engine": "edge_child",
        "voice_base": "id-ID-ArdiNeural",
        "formant_shift": 1.34,
        "gender": "Male"
    }
]

VOICE_MAP = {v["id"]: v for v in AVAILABLE_VOICES}

class TTSEngine(QObject):
    started_speaking = Signal(str, str)   # (username, text)
    finished_speaking = Signal()
    queue_changed = Signal(int)           # queue count
    error_occurred = Signal(str)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.queue = []
        self.is_busy = False
        self.is_muted = False
        self.current_audio_file = None
        self._gemini_client = None
        self._cached_gemini_key = None

        # Setup temp dir
        self.temp_dir = os.path.join(tempfile.gettempdir(), "tiktokvoice_cache")
        os.makedirs(self.temp_dir, exist_ok=True)

        # Qt Media Player setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

    def _get_gemini_client(self):
        key = self.config.get("gemini_api_key", "").strip()
        if not key:
            return None
        if self._gemini_client is None or self._cached_gemini_key != key:
            self._gemini_client = genai.Client(api_key=key)
            self._cached_gemini_key = key
        return self._gemini_client

    def set_muted(self, muted: bool):
        self.is_muted = muted
        if muted and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()

    def add_to_queue(self, username: str, text: str, source: str = "Komentar", voice_id: str = None):
        """Menambahkan balasan/sapaan ke antrean pembacaan suara."""
        text = text.strip()
        if not text:
            return

        max_queue = self.config.get("max_queue_size", 15)
        if len(self.queue) >= max_queue:
            # Hapus item terlama (prioritaskan hapus sapaan jika ada)
            idx_to_remove = 0
            for i, it in enumerate(self.queue):
                if it.get("source") != "Komentar":
                    idx_to_remove = i
                    break
            self.queue.pop(idx_to_remove)

        actual_voice = voice_id or self.config.get("tts_voice", "id-ID-GadisNeural")

        new_item = {
            "username": username,
            "text": text,
            "source": source,
            "voice_id": actual_voice,
            "created_at": time.time()
        }

        # Komentar mendapat prioritas lebih tinggi daripada sapaan
        if source == "Komentar":
            insert_pos = len(self.queue)
            for i, it in enumerate(self.queue):
                if it.get("source") != "Komentar":
                    insert_pos = i
                    break
            self.queue.insert(insert_pos, new_item)
        else:
            self.queue.append(new_item)

        self.queue_changed.emit(len(self.queue))

        if not self.is_busy and not self.is_muted:
            self._process_next()

    def _apply_child_formant(self, input_path: str, output_path: str, shift_factor: float) -> bool:
        """Mengubah resonansi pita suara (vocal tract formant) & pitch menjadi suara anak kecil balita asli."""
        try:
            rate_calc = f"24000*{shift_factor}"
            tempo_calc = f"{1.0 / shift_factor:.4f}"
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-af", f"asetrate={rate_calc},aresample=24000,atempo={tempo_calc}",
                output_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return res.returncode == 0
        except Exception as e:
            print(f"[TTSEngine] Error shifting formant to child: {e}")
            return False

    def _generate_gemini_audio(self, text: str, voice_info: dict, filepath: str) -> bool:
        """Menghasilkan suara via Gemini AI."""
        client = self._get_gemini_client()
        if not client:
            return False

        voice_preset = voice_info.get("voice_preset", "Kore")
        prompt_style = voice_info.get("prompt_style", "Ucapkan dengan sangat ramah dan natural: ")
        full_prompt = f"{prompt_style}{text}"

        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_preset
                            )
                        )
                    )
                )
            )

            if resp.candidates and resp.candidates[0].content.parts:
                part = resp.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    audio_data = part.inline_data.data
                    with wave.open(filepath, "wb") as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(24000)
                        wav_file.writeframes(audio_data)
                    return True
        except Exception as e:
            print(f"[TTSEngine] Gemini Voice error: {e}")

        return False

    def _generate_edge_audio(self, text: str, voice_info: dict, filepath: str) -> bool:
        """Menghasilkan suara via Edge-TTS (Dewasa atau Anak-anak via Formant Shift)."""
        voice_base = voice_info.get("voice_base", "id-ID-GadisNeural")
        formant_shift = voice_info.get("formant_shift")

        rate = self.config.get("tts_rate", "+10%")
        pitch = self.config.get("tts_pitch", "+0Hz")
        volume = self.config.get("tts_volume", "+0%")

        try:
            if formant_shift:
                # 1. Hasilkan suara dasar Edge-TTS ke file sementara
                raw_temp = os.path.join(self.temp_dir, f"raw_edge_{uuid.uuid4().hex[:6]}.mp3")
                async def _speak():
                    comm = edge_tts.Communicate(text=text, voice=voice_base, rate="+10%")
                    await comm.save(raw_temp)

                asyncio.run(_speak())

                # 2. Terapkan formant shift anak-anak
                shifted = self._apply_child_formant(raw_temp, filepath, formant_shift)
                try:
                    os.remove(raw_temp)
                except Exception:
                    pass
                return shifted
            else:
                # Suara Dewasa normal (tanpa formant shift)
                async def _speak_adult():
                    comm = edge_tts.Communicate(text=text, voice=voice_base, rate=rate, pitch=pitch, volume=volume)
                    await comm.save(filepath)

                asyncio.run(_speak_adult())
                return True
        except Exception as e:
            print(f"[TTSEngine] Edge-TTS error: {e}")
            return False


    def _process_next(self):
        # Bersihkan antrean yang sudah kadaluarsa lebih dari 5 menit (300 detik)
        now = time.time()
        while self.queue:
            age = now - self.queue[0].get("created_at", now)
            if age > 300:
                expired = self.queue.pop(0)
                print(f"[TTSEngine] Melewati antrean suara kadaluarsa ({int(age)}s lalu): {expired.get('text')}")
            else:
                break

        if not self.queue:
            self.is_busy = False
            self.finished_speaking.emit()
            return

        if self.is_muted:
            self.is_busy = False
            return

        self.is_busy = True
        item = self.queue.pop(0)
        self.queue_changed.emit(len(self.queue))

        username = item["username"]
        text = item["text"]
        selected_voice_id = item.get("voice_id") or self.config.get("tts_voice", "id-ID-GadisNeural")
        voice_info = VOICE_MAP.get(selected_voice_id, VOICE_MAP["id-ID-GadisNeural"])

        self.started_speaking.emit(username, text)
        audio_success = False

        # 1. Gemini Voice jika dipilih
        if voice_info.get("engine") == "gemini":
            filename = f"voice_gemini_{uuid.uuid4().hex[:8]}.wav"
            filepath = os.path.join(self.temp_dir, filename)
            audio_success = self._generate_gemini_audio(text, voice_info, filepath)
            if audio_success:
                self.current_audio_file = filepath

        # 2. Edge-TTS (Dewasa atau Anak-anak)
        if not audio_success:
            ext = ".wav" if voice_info.get("formant_shift") else ".mp3"
            filename = f"voice_edge_{uuid.uuid4().hex[:8]}{ext}"
            filepath = os.path.join(self.temp_dir, filename)
            audio_success = self._generate_edge_audio(text, voice_info, filepath)
            if audio_success:
                self.current_audio_file = filepath
            else:
                self.error_occurred.emit("Gagal menghasilkan suara.")

        if audio_success and self.current_audio_file:
            self.player.setSource(QUrl.fromLocalFile(self.current_audio_file))
            self.player.play()
        else:
            self._cleanup_current_file()
            self._process_next()

    @Slot(QMediaPlayer.MediaStatus)
    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._cleanup_current_file()
            self._process_next()

    def skip_current(self):
        """Melewati audio yang sedang berbicara saat ini."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()
        self._cleanup_current_file()
        self._process_next()

    def clear_all(self):
        """Mengosongkan antrean dan menghentikan audio."""
        self.queue.clear()
        self.queue_changed.emit(0)
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()
        self._cleanup_current_file()
        self.is_busy = False
        self.finished_speaking.emit()

    def _cleanup_current_file(self):
        if self.current_audio_file and os.path.exists(self.current_audio_file):
            try:
                os.remove(self.current_audio_file)
            except Exception:
                pass
            self.current_audio_file = None
