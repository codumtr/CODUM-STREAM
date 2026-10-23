"""
StreamDub Health Monitor & Auto-Recovery Engine - CODUM Production
Canlı yayın sırasında tüm boru hattını (STT, Çeviri, TTS, OBS bağlantısı) milisaniye düzeyinde izler.
Gecikme birikmesi durumunda eski cümleleri otomatik temizler (queue drop),
servis çökmelerinde yedek motora geçer (circuit breaker / auto-failover)
ve yayıncıya anlaşılır insan dilinde tanılama bildirimleri sunar.
"""

import time
from typing import List, Dict, Optional

class SystemHealthEvent:
    def __init__(self, level: str, message: str, details: str = ""):
        self.timestamp = time.strftime("%H:%M:%S")
        self.level = level # "INFO", "WARNING", "ERROR", "RECOVERY"
        self.message = message
        self.details = details

    def to_dict(self):
        return {
            "time": self.timestamp,
            "level": self.level,
            "message": self.message,
            "details": self.details
        }

class HealthMonitor:
    def __init__(self, max_allowed_latency_ms: int = 3500):
        self.max_allowed_latency_ms = max_allowed_latency_ms
        self.events: List[SystemHealthEvent] = []
        
        # Anlık Gecikme Metrikleri (Son işlenen cümle)
        self.last_stt_ms = 0
        self.last_llm_ms = 0
        self.last_tts_ms = 0
        self.last_total_ms = 0
        self.audio_queue_depth = 0
        
        # Servis Sağlık Durumları (Circuit Breakers)
        self.stt_status = "HEALTHY" # "HEALTHY", "DEGRADED", "FAILED"
        self.llm_status = "HEALTHY"
        self.tts_status = "HEALTHY"
        self.active_stt_provider = "Groq Whisper"
        self.active_llm_provider = "Gemini Flash / LLaMA"
        self.active_tts_provider = "ElevenLabs / Cartesia"

        # İstatistikler
        self.dropped_stale_sentences = 0
        self.auto_failover_count = 0

        self.log_event("INFO", "Sistem Sağlık İzleyici başlatıldı. Tüm servisler nominal.")

    def log_event(self, level: str, message: str, details: str = ""):
        event = SystemHealthEvent(level, message, details)
        self.events.insert(0, event)
        if len(self.events) > 60:
            self.events.pop()
        print(f"[{level}] [HealthMonitor {event.timestamp}]: {message}")

    def record_pipeline_metrics(self, stt_ms: float, llm_ms: float, tts_ms: float):
        self.last_stt_ms = int(stt_ms)
        self.last_llm_ms = int(llm_ms)
        self.last_tts_ms = int(tts_ms)
        self.last_total_ms = self.last_stt_ms + self.last_llm_ms + self.last_tts_ms

        if self.last_total_ms > self.max_allowed_latency_ms:
            self.log_event(
                "WARNING",
                f"Yüksek Gecikme Tespit Edildi ({self.last_total_ms}ms)",
                "İzleyici senkronu için gecikme tamponu devrede."
            )

    def check_and_drop_stale_queue(self, queue_age_ms: float) -> bool:
        """
        1. Tehlike Çözümü: Aşırı gecikmede eski cümleleri atla.
        Yayıncı çoktan başka konuya geçmişken 5 saniye önceki cümlenin dublajını yapıp
        sesleri üst üste bindirmemek için eski cümleyi sessizce eler.
        """
        if queue_age_ms > self.max_allowed_latency_ms:
            self.dropped_stale_sentences += 1
            self.log_event(
                "RECOVERY",
                "Eski Cümle Atlandı (Akıllı Gecikme Koruması)",
                f"Konuşma {int(queue_age_ms)}ms geciktiği için seslerin üst üste binmesi engellendi."
            )
            return True # Drop this chunk!
        return False

    def trigger_failover(self, service: str, failed_provider: str, backup_provider: str, reason: str = ""):
        """
        3. Tehlike Çözümü: Çeviri/TTS servisi çökerse yayın ortasında durma, yedeğe geç!
        """
        self.auto_failover_count += 1
        if service == "LLM":
            self.llm_status = "DEGRADED"
            self.active_llm_provider = backup_provider
        elif service == "TTS":
            self.tts_status = "DEGRADED"
            self.active_tts_provider = backup_provider
        elif service == "STT":
            self.stt_status = "DEGRADED"
            self.active_stt_provider = backup_provider

        self.log_event(
            "RECOVERY",
            f"{service} Sağlayıcısı ({failed_provider}) Yanıt Vermedi!",
            f"Sistem durdurulmadı; kesintisiz olarak yedek motor ({backup_provider}) devreye alındı. Neden: {reason}"
        )

    def get_health_report(self, obs_connected: bool = True) -> dict:
        """Dashboard'a canlı yansıtılan teşhis raporu"""
        # Genel durum değerlendirmesi
        overall = "EXCELLENT"
        if self.last_total_ms > 3000 or self.llm_status != "HEALTHY" or self.tts_status != "HEALTHY":
            overall = "WARNING"
        if not obs_connected:
            overall = "OBS_DISCONNECTED"

        return {
            "overall_health": overall,
            "latency": {
                "stt_ms": self.last_stt_ms,
                "llm_ms": self.last_llm_ms,
                "tts_ms": self.last_tts_ms,
                "total_ms": self.last_total_ms,
                "target_max_ms": self.max_allowed_latency_ms
            },
            "services": {
                "stt": {"status": self.stt_status, "provider": self.active_stt_provider},
                "llm": {"status": self.llm_status, "provider": self.active_llm_provider},
                "tts": {"status": self.tts_status, "provider": self.active_tts_provider},
                "obs_socket": {"status": "HEALTHY" if obs_connected else "NOT_CONNECTED"}
            },
            "stats": {
                "dropped_stale": self.dropped_stale_sentences,
                "auto_failovers": self.auto_failover_count
            },
            "recent_events": [e.to_dict() for e in self.events[:15]]
        }
