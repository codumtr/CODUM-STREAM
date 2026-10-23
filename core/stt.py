"""
Speech-to-Text (STT) Engine
Yayıncının Türkçe sesini milisaniye hızında metne döker.
Yerel Faster-Whisper ve Ultra-düşük gecikmeli Groq Whisper API seçeneklerini destekler.
Oyun/yayın jargonu (Kick, drop, ping, ban, clutch, vb.) için model prompt conditioning içerir.
"""

import io
import wave
import aiohttp
import numpy as np
from config import engine_config

class STTEngine:
    def __init__(self, backend: str = None):
        self.backend = backend or engine_config.STT_BACKEND
        self.local_model = None

        # Modelin yayıncı jargonuyla yönlendirilmesi için başlangıç ipucu
        self.prompt_hints = "Kick, chat, abi, aga, valla, drop, clutch, loot, push, ping, gg."

        if self.backend == "faster-whisper":
            try:
                from faster_whisper import WhisperModel
                # CTranslate2 tabanlı hızlı model
                self.local_model = WhisperModel("small", device="cuda" if self._has_cuda() else "cpu", compute_type="float16" if self._has_cuda() else "int8")
            except ImportError:
                print("⚠️ faster-whisper yüklü değil, Groq/API moduna geçiliyor.")
                self.backend = "groq"

    def _has_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False

    def pcm16_to_wav_bytes(self, pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
        """Ham PCM16 baytlarını bellek içi WAV formatına çevirir."""
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return wav_io.getvalue()

    async def transcribe(self, pcm_bytes: bytes, language: str = "tr") -> str:
        """PCM ses öbeğini metne dönüştürür."""
        if not pcm_bytes or len(pcm_bytes) < 3200: # ~100ms'den azsa geç
            return ""

        groq_key = os.getenv("GROQ_API_KEY", "").strip() or engine_config.GROQ_API_KEY
        if self.backend == "groq" and groq_key:
            return await self._transcribe_groq(pcm_bytes, language, groq_key)
        elif self.backend == "faster-whisper" and self.local_model:
            return self._transcribe_local(pcm_bytes)
        else:
            # API anahtarı girilmediğinde test/simülasyon yanıtı üretir
            print("ℹ️ [Test Modu]: API anahtarı tanımlanmadığı için simülasyon cümlesi üretiliyor.")
            return "Aga vallahi patladık ya, chat baksana şuna oğlum böyle bir şey olamaz!"

    async def _transcribe_groq(self, pcm_bytes: bytes, language: str = "tr", api_key: str = None) -> str:
        """Groq Cloud üzerinden Whisper Large v3 (~120ms ultra hızlı STT)"""
        groq_key = api_key or os.getenv("GROQ_API_KEY", "").strip() or engine_config.GROQ_API_KEY
        wav_data = self.pcm16_to_wav_bytes(pcm_bytes)
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}"}

        data = aiohttp.FormData()
        data.add_field("file", wav_data, filename="speech.wav", content_type="audio/wav")
        data.add_field("model", "whisper-large-v3")
        data.add_field("language", language)
        data.add_field("prompt", self.prompt_hints)
        data.add_field("temperature", "0.0")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        return res.get("text", "").strip()
                    else:
                        err = await resp.text()
                        print(f"❌ Groq STT Hatası [{resp.status}]: {err}")
                        return ""
        except Exception as e:
            print(f"❌ STT İstek Hatası: {e}")
            return ""

    def _transcribe_local(self, pcm_bytes: bytes) -> str:
        """Yerel Faster-Whisper motoru ile çözümleme"""
        audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self.local_model.transcribe(
            audio_np,
            language="tr",
            initial_prompt=self.prompt_hints,
            beam_size=1
        )
        text = " ".join([seg.text for seg in segments]).strip()
        return text
