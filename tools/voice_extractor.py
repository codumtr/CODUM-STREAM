"""
Streamer Voice Analyzer & Profile Generator
Yayıncıların ses kayıtlarından temiz vokal örneği çıkarır,
temel frekans (F0 - pitch), konuşma temposu, rezonans ve ses karakteristiğini analiz ederek
ses klonlama profili (profile.json) üretir.
"""

import os
import sys
import json
import wave
import struct
import math
import numpy as np
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

class VoiceExtractor:
    def __init__(self, output_dir: str = "profiles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_audio_wave(self, wav_path: str) -> dict:
        """
        WAV dosyasını okuyup temel akustik metrikleri (RMS enerji, tahmini pitch/F0, tempo) hesaplar.
        """
        if not os.path.exists(wav_path):
            return {
                "error": f"Dosya bulunamadı: {wav_path}",
                "mean_pitch_hz": 120.0,
                "dynamic_range_db": 35.0,
                "speech_rate": "fast_energetic"
            }

        with wave.open(wav_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            audio_bytes = wf.readframes(n_frames)

        # 16-bit PCM varsayımı
        if sampwidth == 2:
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        else:
            samples = np.frombuffer(audio_bytes, dtype=np.int8).astype(np.float32)

        if n_channels > 1:
            samples = samples[::n_channels]

        # RMS Enerji
        rms = np.sqrt(np.mean(samples**2)) if len(samples) > 0 else 0
        db = 20 * math.log10(rms + 1e-9)

        # Temel Frekans (F0) tahmini - Autocorrelation
        corr = np.correlate(samples[:min(len(samples), framerate * 2)], samples[:min(len(samples), framerate * 2)], mode='full')
        corr = corr[len(corr)//2:]
        d = np.diff(corr)
        start = np.where(d > 0)[0]
        pitch_hz = 125.0
        if len(start) > 0:
            peak = np.argmax(corr[start[0]:]) + start[0]
            if peak > 0:
                pitch_hz = framerate / peak
                # Erkek ses aralığı filtresi (80Hz - 240Hz)
                if pitch_hz < 70 or pitch_hz > 300:
                    pitch_hz = 120.0  # Karakteristik tok erkek sesi için tipik medyan

        return {
            "duration_sec": round(n_frames / framerate, 2),
            "sample_rate": framerate,
            "mean_pitch_hz": round(pitch_hz, 1),
            "approx_energy_db": round(db, 2),
            "timbre": "deep_raspy_resonant" if pitch_hz < 135 else "standard_male"
        }

    def generate_streamer_profile(
        self,
        streamer_id: str,
        name: str,
        reference_audio_path: str,
        sample_quotes: list[str] = None,
        slang_dictionary: dict = None,
        energy_level: str = "high_dynamic"
    ) -> dict:
        """
        Yayıncıya özel tam konfigürasyonlu profil dosyası üretir.
        """
        acoustic_stats = self.analyze_audio_wave(reference_audio_path)

        profile = {
            "streamer_id": streamer_id,
            "display_name": name,
            "reference_audio": reference_audio_path,
            "voice_characteristics": {
                "pitch_hz": acoustic_stats.get("mean_pitch_hz", 118.0),
                "timbre": acoustic_stats.get("timbre", "deep_raspy_resonant"),
                "speed_multiplier": 1.05,  # Hızlı ve dinamik konuşma
                "pitch_shift": -1.2,       # Tokluğu korumak için hafif bas dengesi
                "energy_level": energy_level,
                "emotion_stability": 0.35, # Düşük stabilite = yüksek duygusal ifade ve kahkahalar
            },
            "llm_persona_prompt": (
                f"You are the real-time live English dubber for the popular Turkish streamer {name}. "
                "Maintain their authentic high energy, humorous reactions, banter, sarcasm, and streamer vibe. "
                "Never sound like a formal corporate interpreter! Translate Turkish slang into punchy, "
                "natural Gen-Z / Twitch streamer English slang."
            ),
            "slang_dictionary": slang_dictionary or {
                "aga": "bro",
                "kanka": "dude",
                "dayı": "man",
                "valla": "I swear",
                "yemin ederim": "on god / for real",
                "patladık": "we're so cooked",
                "sıctık": "we're done for",
                "kafayı yersin": "unbelievable / that's insane",
                "hadi bakayım": "let's get it",
                "yapıştır": "send it",
                "harbi mi": "really bro?",
                "oğlum ne yapıyorsun": "bro what are you doing",
                "yok artık": "no shot"
            },
            "sample_quotes": sample_quotes or [
                "Aga yemin ederim böyle bir şey görmedim ya!",
                "Patladık oğlum patladık, kaçın kaçın!",
                "Dayı vallahi helal olsun adama, nasıl vurdu öyle?"
            ]
        }

        profile_path = self.output_dir / f"{streamer_id}.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

        print(f"✅ Profil başarıyla oluşturuldu: {profile_path}")
        return profile


if __name__ == "__main__":
    extractor = VoiceExtractor()
    # Örnek Yayıncı profili oluştur
    extractor.generate_streamer_profile(
        streamer_id="default",
        name="Streamer Pro",
        reference_audio_path="profiles/default_sample.wav",
        energy_level="high_dynamic"
    )
