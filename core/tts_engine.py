"""
Voice DNA & Neural Voice Cloning Engine - CODUM Production
Yayıncının ses örneğini analiz edip profil oluşturur ve ElevenLabs / Cartesia / Edge-TTS
üzerinden ticari lisanslı, tını korumalı dublaj sesi üretir.
"""

import io
import os
import json
import aiohttp
from pathlib import Path
from config import engine_config

class VoiceCloningEngine:
    def __init__(self, streamer_id: str = "default", backend: str = None):
        self.streamer_id = streamer_id
        self.backend = backend or engine_config.TTS_BACKEND
        self.profile_path = Path("profiles") / f"{streamer_id}.json"
        self.profile = self._load_profile()

    def _load_profile(self) -> dict:
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "display_name": "Streamer",
            "voice_id": os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            "voice_characteristics": {
                "stability": 0.35,
                "similarity_boost": 0.85,
                "speed_multiplier": 1.05
            }
        }

    async def create_voice_clone(self, sample_audio_bytes: bytes, voice_name: str) -> dict:
        """
        Yayıncının yüklediği veya mikrofondan kaydettiği 30 saniyelik ses kaydından
        otomatik Voice DNA çıkarıp API üzerinde gerçek ses klonu oluşturur.
        """
        api_key = os.getenv("ELEVENLABS_API_KEY", "").strip() or engine_config.ELEVENLABS_API_KEY
        if not api_key:
            # ElevenLabs anahtarı henüz girilmemişse yerel profil simülasyonu
            voice_id = f"simulated_{self.streamer_id}"
            self.profile["voice_id"] = voice_id
            self.profile["display_name"] = voice_name
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=2, ensure_ascii=False)
            return {
                "status": "success",
                "voice_id": voice_id,
                "mode": "local_preview",
                "message": "ElevenLabs anahtarı girilmediği için ses profili yerel olarak kaydedildi (Yerel test sesi kullanılacak)."
            }

        url = "https://api.elevenlabs.io/v1/voices/add"
        headers = {"xi-api-key": api_key}
        data = aiohttp.FormData()
        data.add_field("name", f"CODUM_{voice_name}_{self.streamer_id}")
        data.add_field("files", sample_audio_bytes, filename="voice_dna_sample.wav", content_type="audio/wav")
        data.add_field("description", f"CODUM.TR STREAM Voice DNA clone for {voice_name}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        cloned_id = res.get("voice_id")
                        self.profile["voice_id"] = cloned_id
                        self.profile["display_name"] = voice_name
                        with open(self.profile_path, "w", encoding="utf-8") as f:
                            json.dump(self.profile, f, indent=2, ensure_ascii=False)
                        print(f"✅ [Voice DNA] Yeni ses klonu üretildi: {cloned_id}")
                        return {"status": "success", "voice_id": cloned_id}
                    else:
                        err = await resp.text()
                        print(f"❌ ElevenLabs Clone Hatası: {err}")
                        return {"status": "error", "message": err}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def synthesize(self, text: str, target_lang: str = "en", is_high_energy: bool = False, health_monitor = None) -> tuple[bytes, str, int]:
        """
        Metni seslendirir.
        Duygu Yönetimi: Yayıncı bağırıyorsa (is_high_energy) TTS motoru fısıldamaz;
        yüksek duygu ve stil çarpanıyla enerjik ses üretir.
        Otomatik Failover: Birincil sağlayıcı çökerse yedek motora geçer.
        """
        if not text or not text.strip():
            return b"", "audio/mp3", 0

        char_count = len(text)

        # 1. ElevenLabs Klonlanmış Ses
        eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip() or engine_config.ELEVENLABS_API_KEY
        if eleven_key:
            audio_bytes = await self._synthesize_elevenlabs(text, is_high_energy, eleven_key)
            if audio_bytes:
                return audio_bytes, "audio/mp3", char_count
            elif health_monitor:
                health_monitor.trigger_failover("TTS", "ElevenLabs Turbo", "Cartesia Sonic", "API zaman aşımı")

        # 2. Cartesia Sonic
        cartesia_key = os.getenv("CARTESIA_API_KEY", "").strip()
        if cartesia_key:
            audio_bytes = await self._synthesize_cartesia(text, cartesia_key)
            if audio_bytes:
                return audio_bytes, "audio/pcm", char_count
            elif health_monitor:
                health_monitor.trigger_failover("TTS", "Cartesia Sonic", "Edge-TTS (Yedek)", "API hatası")

        # 3. Test & Yedek Motor: Edge TTS (Yayın asla sessiz kalmaz)
        audio_bytes = await self._synthesize_edge(text, target_lang, is_high_energy)
        return audio_bytes, "audio/mp3", char_count

    async def _synthesize_elevenlabs(self, text: str, is_high_energy: bool = False, api_key: str = None) -> bytes:
        api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "").strip() or engine_config.ELEVENLABS_API_KEY
        voice_id = self.profile.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # Duygu ve Enerji Dengesi
        stability = 0.20 if is_high_energy else 0.40
        style = 0.80 if is_high_energy else 0.50

        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": 0.85,
                "style": style
            }
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=3.5)) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            print(f"❌ ElevenLabs Sentez Hatası: {e}")
        return b""

    async def _synthesize_cartesia(self, text: str, api_key: str) -> bytes:
        url = "https://api.cartesia.ai/tts/bytes"
        headers = {
            "X-API-Key": api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        }
        payload = {
            "model_id": "sonic-english",
            "transcript": text,
            "voice": {"mode": "id", "id": os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")},
            "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000}
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=3.0)) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            print(f"❌ Cartesia Sentez Hatası: {e}")
        return b""

    async def _synthesize_edge(self, text: str, target_lang: str, is_high_energy: bool = False) -> bytes:
        """Kullanıcının ekstra ücret ödemeden canlı ses çıktısını duyması için test motoru"""
        try:
            import edge_tts
            voice = "en-US-ChristopherNeural" if target_lang == "en" else "tr-TR-AhmetNeural"
            rate = "+12%" if is_high_energy else "+6%"
            pitch = "+2Hz" if is_high_energy else "-2Hz"
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
            return bytes(audio_data)
        except Exception:
            return b""
