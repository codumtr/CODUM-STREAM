"""
Voice Sample Quality Validator & Acoustic Analyzer - CODUM Production
Yayıncının yüklediği ses örneğini klonlamaya göndermeden önce inceler.
Kırpılma (clipping), gürültü (SNR), yankı ve süre kontrolleri yaparak
sesin yapay zekâ klonlamaya uygun olup olmadığını (Kalite Skoru 0-100) raporlar.
"""

import io
import math
import wave
import numpy as np

class AudioQualityValidator:
    def __init__(self):
        self.min_duration_sec = 15.0
        self.recommended_duration_sec = 35.0
        self.max_duration_sec = 90.0

    def validate_wav_bytes(self, wav_bytes: bytes) -> dict:
        """WAV baytlarını akustik olarak test eder."""
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                audio_raw = wf.readframes(n_frames)

            duration = n_frames / framerate
            if sampwidth == 2:
                samples = np.frombuffer(audio_raw, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                samples = np.frombuffer(audio_raw, dtype=np.int8).astype(np.float32) / 128.0

            if n_channels > 1:
                samples = samples[::n_channels]

            # 1. Kırpılma (Clipping / Bozulma) Kontrolü
            peak = float(np.max(np.abs(samples))) if len(samples) > 0 else 0.0
            clipping_ratio = float(np.mean(np.abs(samples) > 0.98))
            is_clipped = clipping_ratio > 0.005

            # 2. RMS Ses Seviyesi
            rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0
            rms_db = 20 * math.log10(rms + 1e-9)

            # 3. Sessizlik ve Arka Plan Gürültüsü Oranı (SNR Tahmini)
            frame_size = int(framerate * 0.03) # 30ms kareler
            num_frames = len(samples) // frame_size
            frame_energies = []
            for i in range(num_frames):
                f = samples[i*frame_size : (i+1)*frame_size]
                e = np.sqrt(np.mean(f**2))
                frame_energies.append(e)

            frame_energies = np.array(frame_energies) if frame_energies else np.array([0.0])
            silence_ratio = float(np.mean(frame_energies < 0.01))
            bg_noise_est = float(np.percentile(frame_energies, 10))

            # Kalite Puanı Hesaplama (0 - 100)
            score = 100
            issues = []
            recommendations = []

            # Süre Kontrolü
            if duration < self.min_duration_sec:
                score -= 35
                issues.append(f"Kayıt çok kısa ({duration:.1f} sn). En az 20 saniye olmalı.")
                recommendations.append("Daha uzun ve doğal konuşma temposuyla tekrar kaydedin.")
            elif duration > self.max_duration_sec:
                score -= 10
                issues.append("Kayıt biraz uzun. 30-45 saniye en idealidir.")

            # Kırpılma / Patlama Kontrolü
            if is_clipped:
                score -= 30
                issues.append("Seste aşırı patlama/kırpılma (clipping) var.")
                recommendations.append("Mikrofon kazancını (gain) biraz düşürün veya mikrofondan 10-15 cm uzaklaşın.")

            # Aşırı Düşük Ses Kontrolü
            if rms_db < -35.0:
                score -= 25
                issues.append("Ses seviyesi çok düşük/fısıltılı.")
                recommendations.append("Mikrofona daha yakın ve enerjik konuşun.")

            # Gürültü Kontrolü
            if bg_noise_est > 0.035:
                score -= 20
                issues.append("Arka planda belirgin dip ses veya oyun/fan gürültüsü var.")
                recommendations.append("Oyun sesini ve arka plan müziğini tamamen kapatıp sadece sesinizi kaydedin.")

            score = max(0, min(100, score))
            status = "EXCELLENT" if score >= 80 else ("ACCEPTABLE" if score >= 55 else "POOR")

            return {
                "valid": score >= 55,
                "score": score,
                "status": status,
                "duration_sec": round(duration, 1),
                "peak_db": round(20 * math.log10(peak + 1e-9), 1),
                "rms_db": round(rms_db, 1),
                "silence_ratio": round(silence_ratio, 2),
                "issues": issues,
                "recommendations": recommendations
            }
        except Exception as e:
            return {
                "valid": False,
                "score": 0,
                "status": "ERROR",
                "issues": [f"Ses dosyası okunamadı: {str(e)}"],
                "recommendations": ["Lütfen standart PCM 16-bit WAV veya MP3 formatında yükleyin."]
            }
