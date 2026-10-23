"""
Voice Activity Detection (VAD) Engine - CODUM Production
Yayıncının konuşma ve sessizlik anlarını ses örnekleri (sample count) üzerinden
kesin ve deterministik olarak hesaplar. Ağ gecikmesi veya buffer kuyruklarından etkilenmez.
"""

import time
import numpy as np
from typing import Callable, Optional

class StreamingVAD:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        silence_threshold_ms: int = 400,
        energy_threshold: float = 0.015,
        on_speech_chunk_ready: Optional[Callable[[bytes], None]] = None
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * (frame_duration_ms / 1000.0))
        self.silence_threshold_ms = silence_threshold_ms
        self.energy_threshold = energy_threshold
        self.on_speech_chunk_ready = on_speech_chunk_ready

        self.buffer = bytearray()
        self.current_speech = bytearray()
        self.is_speaking = False
        
        # Kritik Düzeltme: Sistem saati (wall-clock) yerine ses örneklerinden kare sayacı
        self.silent_frames_count = 0
        self.min_speech_frames = int(200 / frame_duration_ms) # En az 200ms konuşma
        self.speech_frames_count = 0

    def set_parameters(self, energy_threshold: float = None, silence_threshold_ms: int = None):
        """Panelden canlı olarak hassasiyet ve sessizlik süresi güncellenebilir."""
        if energy_threshold is not None:
            self.energy_threshold = max(0.001, min(0.2, float(energy_threshold)))
        if silence_threshold_ms is not None:
            self.silence_threshold_ms = max(150, min(2000, int(silence_threshold_ms)))

    def _calc_frame_energy(self, frame_bytes: bytes) -> float:
        """Kare başına normalize edilmiş RMS enerji seviyesi"""
        samples = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if len(samples) == 0:
            return 0.0
        return float(np.sqrt(np.mean(samples ** 2)))

    def process_audio_chunk(self, chunk_bytes: bytes):
        """Gelen PCM16 ses akışını kareler halinde inceler."""
        self.buffer.extend(chunk_bytes)
        bytes_per_frame = self.frame_size * 2  # 16-bit = 2 bytes

        while len(self.buffer) >= bytes_per_frame:
            frame = bytes(self.buffer[:bytes_per_frame])
            del self.buffer[:bytes_per_frame]

            energy = self._calc_frame_energy(frame)

            if energy > self.energy_threshold:
                # Konuşma tespit edildi
                self.is_speaking = True
                self.silent_frames_count = 0
                self.speech_frames_count += 1
                self.current_speech.extend(frame)
            else:
                # Sessizlik karesi
                if self.is_speaking:
                    self.current_speech.extend(frame)
                    self.silent_frames_count += 1
                    
                    # Örnek sayımı tabanlı sessizlik süresi (Network jitter ve buffering'e karşı bağışık)
                    elapsed_silence_ms = self.silent_frames_count * self.frame_duration_ms
                    if elapsed_silence_ms >= self.silence_threshold_ms:
                        self._emit_speech()

    def _emit_speech(self):
        """Konuşma öbeğini STT kuyruğuna gönderir."""
        if self.speech_frames_count >= self.min_speech_frames:
            ready_audio = bytes(self.current_speech)
            if self.on_speech_chunk_ready:
                self.on_speech_chunk_ready(ready_audio)
        self.current_speech.clear()
        self.is_speaking = False
        self.silent_frames_count = 0
        self.speech_frames_count = 0

    def flush(self):
        """Oturum durdurulduğunda tamponda kalan sesi fırlatır."""
        if len(self.current_speech) > 0:
            self._emit_speech()
