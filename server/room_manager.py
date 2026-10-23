"""
Room & Connection Manager - CODUM Production
Yayın kanallarını, izleyicileri, OBS overlay bağlantılarını,
kimlik doğrulama anahtarlarını ve gerçek zamanlı maliyet metriklerini yönetir.
"""

import time
from typing import Dict, Set
from fastapi import WebSocket

class ChannelMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.total_audio_seconds = 0.0
        self.total_words_translated = 0
        self.total_tts_chars = 0
        self.total_utterances = 0

    def add_stt(self, duration_sec: float):
        self.total_audio_seconds += duration_sec
        self.total_utterances += 1

    def add_translation(self, words: int):
        self.total_words_translated += words

    def add_tts(self, chars: int):
        self.total_tts_chars += chars

    def calculate_actual_cost(self) -> dict:
        """Gerçek kullanım başına maliyet hesabı"""
        # Groq / Faster-Whisper: ~$0.0001 / sn ($0.006 / dk)
        stt_cost = (self.total_audio_seconds / 60.0) * 0.006
        # Gemini 2.0 Flash / LLaMA 3.3: ~$0.10 / 1M token (~$0.00013 / 1000 kelime)
        llm_cost = (self.total_words_translated / 1000.0) * 0.00015
        # ElevenLabs Turbo: ~$0.00003 / karakter (~$0.30 / 10K karakter)
        tts_cost = self.total_tts_chars * 0.00003

        total = stt_cost + llm_cost + tts_cost
        return {
            "total_cost_usd": round(total, 4),
            "stt_seconds": round(self.total_audio_seconds, 1),
            "words_translated": self.total_words_translated,
            "tts_chars": self.total_tts_chars,
            "utterances": self.total_utterances
        }

class ChannelRoom:
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.streamer_ws: WebSocket = None
        self.stream_key: str = "codum_live_key" # Varsayılan yayın anahtarı
        self.overlay_clients: Set[WebSocket] = set()
        self.viewer_clients: Dict[str, Set[WebSocket]] = {}
        self.metrics = ChannelMetrics()
        self.is_panic_muted = False
        self.target_language = "en"
        self.slang_mode = "gamer_hype"

    def add_viewer(self, ws: WebSocket, lang: str = "en"):
        if lang not in self.viewer_clients:
            self.viewer_clients[lang] = set()
        self.viewer_clients[lang].add(ws)

    def remove_viewer(self, ws: WebSocket):
        for lang_set in self.viewer_clients.values():
            lang_set.discard(ws)

    def add_overlay(self, ws: WebSocket):
        self.overlay_clients.add(ws)

    def remove_overlay(self, ws: WebSocket):
        self.overlay_clients.discard(ws)

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, ChannelRoom] = {}

    def get_or_create_room(self, channel_id: str) -> ChannelRoom:
        channel_id = channel_id.lower().strip()
        if channel_id not in self.rooms:
            self.rooms[channel_id] = ChannelRoom(channel_id)
        return self.rooms[channel_id]

    def remove_client(self, ws: WebSocket):
        for room in self.rooms.values():
            if room.streamer_ws == ws:
                room.streamer_ws = None
            room.remove_overlay(ws)
            room.remove_viewer(ws)
