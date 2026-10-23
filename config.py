import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class ServerConfig(BaseModel):
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8765"))
    WS_PATH: str = "/ws/stream"

class AudioConfig(BaseModel):
    INPUT_SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024
    OUTPUT_SAMPLE_RATE: int = 24000
    VAD_SILENCE_THRESHOLD_MS: int = 350  # Milisaniye cinsinden sessizlik eşiği
    MIN_SPEECH_DURATION_MS: int = 400

class EngineConfig(BaseModel):
    # STT Motoru: "faster-whisper", "groq", "openai"
    STT_BACKEND: str = os.getenv("STT_BACKEND", "groq")
    
    # Çeviri Motoru: "gemini", "groq-llama3", "deepl", "openai"
    TRANSLATOR_BACKEND: str = os.getenv("TRANSLATOR_BACKEND", "gemini")
    
    # TTS Motoru: "xtts", "kokoro", "elevenlabs", "edge-tts"
    TTS_BACKEND: str = os.getenv("TTS_BACKEND", "xtts")

    # API Anahtarları
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEEPL_API_KEY: str = os.getenv("DEEPL_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")

    # Varsayılan Yayıncı Profili
    DEFAULT_STREAMER: str = os.getenv("DEFAULT_STREAMER", "default")
    TARGET_LANGUAGES: list[str] = ["en", "es", "de", "ru"]

server_config = ServerConfig()
audio_config = AudioConfig()
engine_config = EngineConfig()
