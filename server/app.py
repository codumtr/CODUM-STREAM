"""
StreamDub Server Hub - CODUM Production
Yayıncı mikrofon akışını karşılar, VAD -> STT -> Çeviri -> Voice DNA Ses Klonlama
zincirini asenkron olarak işletir ve izleyicilere + OBS ses/altyazı çıkışına dağıtır.
"""

import os
import sys
import json
import asyncio
import base64
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config import server_config, audio_config, engine_config
from server.room_manager import RoomManager
from server.kick_bot import kick_router
from core.vad import StreamingVAD
from core.stt import STTEngine
from core.translator import StreamerTranslator
from core.tts_engine import VoiceCloningEngine
from core.audio_validator import AudioQualityValidator
from core.health_monitor import HealthMonitor
from core.license_guard import verify_license_integrity, print_startup_banner

base_dir = os.path.dirname(os.path.dirname(__file__))

def get_settings_file_path() -> str:
    if getattr(sys, 'frozen', False):
        target_dir = os.path.dirname(sys.executable)
    else:
        target_dir = base_dir
    return os.path.join(target_dir, "user_settings.json")

def load_persistent_settings() -> dict:
    path = get_settings_file_path()
    defaults = {
        "setup_completed": False,
        "selected_mic": "",
        "target_language": "en",
        "slang_mode": "gamer_hype",
        "ai_engine": "auto",
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", ""),
        "cartesia_api_key": os.getenv("CARTESIA_API_KEY", ""),
        "voice_clone_id": "default",
        "obs_delay_ms": 0,
        "vad_sensitivity": 0.015,
        "silence_duration_ms": 400
    }
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
                for k in ["groq_api_key", "gemini_api_key", "elevenlabs_api_key", "cartesia_api_key"]:
                    if defaults.get(k):
                        env_key = k.upper()
                        os.environ[env_key] = defaults[k]
        except Exception as e:
            print(f"[UYARI] Ayar dosyası okunamadı: {e}")
    return defaults

def save_persistent_settings(settings: dict) -> bool:
    path = get_settings_file_path()
    try:
        current = load_persistent_settings()
        current.update(settings)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        for k in ["groq_api_key", "gemini_api_key", "elevenlabs_api_key", "cartesia_api_key"]:
            if k in settings and settings[k]:
                env_key = k.upper()
                os.environ[env_key] = settings[k]
        return True
    except Exception as e:
        print(f"[HATA] Ayar dosyası kaydedilemedi: {e}")
        return False

app = FastAPI(title="CODUM.TR STREAM Studio & Engine")

@app.on_event("startup")
async def startup_event():
    print_startup_banner()
    settings = load_persistent_settings()
    room = room_manager.get_or_create_room("streamer")
    room.target_language = settings.get("target_language", "en")
    room.slang_mode = settings.get("slang_mode", "gamer_hype")
    room.ai_engine = settings.get("ai_engine", "auto")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kick_router)

room_manager = RoomManager()
stt_engine = STTEngine()
audio_validator = AudioQualityValidator()
health_monitor = HealthMonitor()
sequence_counter = 0

base_dir = os.path.dirname(os.path.dirname(__file__))
overlay_dir = os.path.join(base_dir, "overlay")
dashboard_dir = os.path.join(base_dir, "streamer_dashboard")

if os.path.exists(overlay_dir):
    app.mount("/static/overlay", StaticFiles(directory=overlay_dir), name="overlay")

@app.get("/")
def index():
    return {
        "service": "CODUM.TR STREAM AI Hub",
        "status": "online",
        "supported_languages": engine_config.TARGET_LANGUAGES,
        "studio_url": "/dashboard",
        "obs_overlay_url": "/overlay"
    }

@app.get("/dashboard")
def serve_dashboard():
    dashboard_html = os.path.join(dashboard_dir, "index.html")
    if os.path.exists(dashboard_html):
        return FileResponse(dashboard_html)
    return HTMLResponse("<h3>Studio Dashboard bulunamadi</h3>")

@app.get("/overlay")
def serve_overlay(channel: str = "streamer"):
    overlay_html = os.path.join(overlay_dir, "index.html")
    if os.path.exists(overlay_html):
        return FileResponse(overlay_html)
    return HTMLResponse("<h3>Overlay dosyasi bulunamadi</h3>")

# --- REST API: Canlı Ayarlar & Metrikler ---

class SettingsPayload(BaseModel):
    target_language: str = "en"
    slang_mode: str = "gamer_hype"
    ai_engine: str = "auto" # "groq", "gemini", "auto"
    obs_delay_ms: int = 0
    vad_sensitivity: float = 0.015
    silence_duration_ms: int = 400
    custom_glossary: dict = {}

@app.get("/api/settings/{channel_id}")
def get_settings(channel_id: str):
    room = room_manager.get_or_create_room(channel_id)
    return {
        "channel_id": channel_id,
        "target_language": room.target_language,
        "slang_mode": room.slang_mode,
        "ai_engine": getattr(room, "ai_engine", "auto"),
        "is_panic_muted": room.is_panic_muted
    }

@app.post("/api/settings/{channel_id}")
def update_settings(channel_id: str, settings: SettingsPayload):
    room = room_manager.get_or_create_room(channel_id)
    room.target_language = settings.target_language
    room.slang_mode = settings.slang_mode
    room.ai_engine = settings.ai_engine
    health_monitor.active_llm_provider = f"Seçili: {settings.ai_engine.upper()}"
    return {"status": "success", "message": "Ayarlar ve AI Motoru güncellendi"}

@app.get("/api/user-settings")
def api_get_user_settings():
    """Tüm kaydedilmiş kullanıcı ayarlarını ve kurulum durumunu döndürür."""
    settings = load_persistent_settings()
    return settings

@app.post("/api/user-settings")
def api_save_user_settings(payload: dict):
    """Kurulum sihirbazı veya stüdyo panelinden gelen ayarları kalıcı olarak diske kaydeder."""
    success = save_persistent_settings(payload)
    room = room_manager.get_or_create_room("streamer")
    if "target_language" in payload:
        room.target_language = payload["target_language"]
    if "slang_mode" in payload:
        room.slang_mode = payload["slang_mode"]
    if "ai_engine" in payload:
        room.ai_engine = payload["ai_engine"]
    return {
        "status": "success" if success else "error",
        "message": "Ayarlar kalıcı olarak kaydedildi. Sonraki açılışlarda otomatik yüklenecektir.",
        "settings": load_persistent_settings()
    }

@app.get("/api/metrics/{channel_id}")
def get_metrics(channel_id: str):
    room = room_manager.get_or_create_room(channel_id)
    cost_info = room.metrics.calculate_actual_cost()
    return {
        "channel_id": channel_id,
        "metrics": cost_info
    }

@app.get("/api/health/{channel_id}")
def get_health(channel_id: str):
    room = room_manager.get_or_create_room(channel_id)
    obs_connected = len(room.overlay_clients) > 0
    return health_monitor.get_health_report(obs_connected=obs_connected)

@app.post("/api/panic_mute/{channel_id}")
async def toggle_panic_mute(channel_id: str, muted: bool = Query(...)):
    room = room_manager.get_or_create_room(channel_id)
    room.is_panic_muted = muted
    mute_msg = json.dumps({"type": "panic_mute", "muted": muted})
    for client in list(room.overlay_clients):
        await client.send_text(mute_msg)
    return {"status": "success", "muted": muted}

@app.post("/api/voice/validate")
async def validate_voice_sample(file: UploadFile = File(...)):
    """Yüklenen ses dosyasının kalitesini, gürültü ve clipping seviyesini analiz eder."""
    raw_bytes = await file.read()
    result = audio_validator.validate_wav_bytes(raw_bytes)
    return result

@app.post("/api/voice/clone/{channel_id}")
async def create_voice_clone_endpoint(
    channel_id: str,
    voice_name: str = Form("StreamerVoice"),
    file: UploadFile = File(...)
):
    """Voice DNA: Yayıncının yüklediği ses örneğinden gerçek ses klonu oluşturur."""
    audio_bytes = await file.read()
    
    # Önce kalite doğrulaması yap
    validation = audio_validator.validate_wav_bytes(audio_bytes)
    if not validation.get("valid", True) and validation.get("score", 100) < 40:
        return {
            "status": "warning",
            "message": "Ses kalitesi çok düşük!",
            "validation": validation
        }

    tts_engine = VoiceCloningEngine(streamer_id=channel_id)
    result = await tts_engine.create_voice_clone(audio_bytes, voice_name)
    result["validation"] = validation
    return result

# --- LİSANS & BYOK (BRING YOUR OWN KEY) YÖNETİMİ ---

@app.get("/api/license")
def get_license_info():
    """CODUM.TR STREAM dijital mühür ve lisans durumunu doğrular."""
    return verify_license_integrity()

class ApiKeysPayload(BaseModel):
    groq_api_key: str = ""
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    cartesia_api_key: str = ""

@app.get("/api/keys")
def get_api_keys_status():
    """Yayıncının girdiği API anahtarlarının durumunu maskeli olarak döndürür."""
    groq = os.getenv("GROQ_API_KEY", "")
    gemini = os.getenv("GEMINI_API_KEY", "")
    elevenlabs = os.getenv("ELEVENLABS_API_KEY", "")
    cartesia = os.getenv("CARTESIA_API_KEY", "")

    def mask(k: str):
        if not k or len(k) < 6:
            return ""
        return k[:4] + "••••••••" + k[-4:]

    return {
        "groq_configured": bool(groq),
        "groq_masked": mask(groq),
        "gemini_configured": bool(gemini),
        "gemini_masked": mask(gemini),
        "elevenlabs_configured": bool(elevenlabs),
        "elevenlabs_masked": mask(elevenlabs),
        "cartesia_configured": bool(cartesia),
        "cartesia_masked": mask(cartesia),
    }

@app.post("/api/keys")
def save_api_keys(payload: ApiKeysPayload):
    """Yayıncının girdiği API anahtarlarını .env dosyasına yazar ve anında hafızada günceller."""
    env_path = os.path.join(base_dir, ".env")
    existing_lines = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing_lines[k.strip()] = v.strip()

    if payload.groq_api_key.strip():
        existing_lines["GROQ_API_KEY"] = payload.groq_api_key.strip()
        os.environ["GROQ_API_KEY"] = payload.groq_api_key.strip()
    if payload.gemini_api_key.strip():
        existing_lines["GEMINI_API_KEY"] = payload.gemini_api_key.strip()
        os.environ["GEMINI_API_KEY"] = payload.gemini_api_key.strip()
    if payload.elevenlabs_api_key.strip():
        existing_lines["ELEVENLABS_API_KEY"] = payload.elevenlabs_api_key.strip()
        os.environ["ELEVENLABS_API_KEY"] = payload.elevenlabs_api_key.strip()
    if payload.cartesia_api_key.strip():
        existing_lines["CARTESIA_API_KEY"] = payload.cartesia_api_key.strip()
        os.environ["CARTESIA_API_KEY"] = payload.cartesia_api_key.strip()

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# CODUM.TR STREAM - Yerel Yapılandırma\n")
        for k, v in existing_lines.items():
            f.write(f"{k}={v}\n")

    return {"status": "success", "message": "API anahtarları başarıyla kaydedildi ve anında etkinleştirildi."}

# --- CANLI İŞLEME BORU HATTI ---

async def process_speech_pipeline(channel_id: str, speech_pcm: bytes):
    global sequence_counter
    sequence_counter += 1
    seq_id = sequence_counter

    start_time = time.time()
    room = room_manager.get_or_create_room(channel_id)
    selected_engine = getattr(room, "ai_engine", "auto")
    translator = StreamerTranslator(streamer_id=channel_id, backend=selected_engine)
    tts_engine = VoiceCloningEngine(streamer_id=channel_id)
    is_sandbox = getattr(room, "is_sandbox", False)

    # Ses Enerjisi / Duygu Tespiti: Yayıncı bağırıyor mu?
    try:
        import numpy as np
        pcm_arr = np.frombuffer(speech_pcm, dtype=np.int16)
        peak_val = np.max(np.abs(pcm_arr)) if len(pcm_arr) > 0 else 0
        is_high_energy = peak_val > 22000
    except Exception:
        is_high_energy = False

    # 1. Metrik: Konuşma süresi hesabı (16kHz, 16bit mono = 32000 bayt/sn)
    speech_duration_sec = len(speech_pcm) / 32000.0
    room.metrics.add_stt(speech_duration_sec)

    # 2. STT: Konuşmayı Metne Çevir
    t_stt_start = time.time()
    text_tr = await stt_engine.transcribe(speech_pcm, language="tr")
    stt_duration_ms = (time.time() - t_stt_start) * 1000.0

    if not text_tr or not text_tr.strip():
        return

    tag = "[SANDBOX]" if is_sandbox else "[LIVE]"
    hype_tag = "🔥 [YÜKSEK ENERJİ / BAĞIRIŞ]" if is_high_energy else ""
    print(f"{tag} {hype_tag} [{channel_id} TR #{seq_id}]: {text_tr}")

    sub_payload = json.dumps({
        "type": "subtitle",
        "seq": seq_id,
        "lang": "tr",
        "original": text_tr,
        "translated": None,
        "is_sandbox": is_sandbox,
        "is_high_energy": is_high_energy
    })

    if not is_sandbox:
        for client in list(room.overlay_clients):
            await client.send_text(sub_payload)

    if room.streamer_ws:
        try:
            await room.streamer_ws.send_text(sub_payload)
        except Exception:
            pass

    # 3. Çeviri (Hedef Dil & Duygu Eşleme & Failover)
    target_lang = room.target_language or "en"
    t_llm_start = time.time()
    text_translated, word_count = await translator.translate(
        text_tr,
        target_lang=target_lang,
        is_high_energy=is_high_energy,
        health_monitor=health_monitor
    )
    llm_duration_ms = (time.time() - t_llm_start) * 1000.0
    room.metrics.add_translation(word_count)

    if not text_translated or not text_translated.strip():
        return

    print(f"{tag} [{channel_id} -> {target_lang.upper()} #{seq_id}]: {text_translated}")

    # Gecikme Birikmesi Kontrolü (Aşırı Gecikmede Eski Cümleyi Düşür)
    current_elapsed_ms = (time.time() - start_time) * 1000.0
    if health_monitor.check_and_drop_stale_queue(current_elapsed_ms):
        return

    trans_sub = json.dumps({
        "type": "subtitle",
        "seq": seq_id,
        "lang": target_lang,
        "original": text_tr,
        "translated": text_translated,
        "is_sandbox": is_sandbox,
        "is_high_energy": is_high_energy
    })

    if not is_sandbox:
        for client in list(room.overlay_clients):
            await client.send_text(trans_sub)

    if room.streamer_ws:
        try:
            await room.streamer_ws.send_text(trans_sub)
        except Exception:
            pass

    # 4. Ses Klonlama / Dublaj Sentezi (Duygu Uyumlu TTS)
    t_tts_start = time.time()
    tts_duration_ms = 0.0

    if not room.is_panic_muted:
        audio_bytes, mime_type, char_count = await tts_engine.synthesize(
            text_translated,
            target_lang=target_lang,
            is_high_energy=is_high_energy,
            health_monitor=health_monitor
        )
        tts_duration_ms = (time.time() - t_tts_start) * 1000.0
        room.metrics.add_tts(char_count)

        # Health monitor metriklerini kaydet
        health_monitor.record_pipeline_metrics(stt_duration_ms, llm_duration_ms, tts_duration_ms)

        if audio_bytes and len(audio_bytes) > 0:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            audio_msg = json.dumps({
                "type": "dub_audio",
                "seq": seq_id,
                "lang": target_lang,
                "mime": mime_type,
                "text": text_translated,
                "audio": b64_audio,
                "is_sandbox": is_sandbox,
                "timestamp": time.time()
            })

            if is_sandbox:
                if room.streamer_ws:
                    try:
                        await room.streamer_ws.send_text(audio_msg)
                    except Exception:
                        pass
            else:
                for overlay_ws in list(room.overlay_clients):
                    try:
                        await overlay_ws.send_text(audio_msg)
                    except Exception:
                        room.remove_overlay(overlay_ws)

                if target_lang in room.viewer_clients:
                    for viewer_ws in list(room.viewer_clients[target_lang]):
                        try:
                            await viewer_ws.send_text(audio_msg)
                        except Exception:
                            room.remove_viewer(viewer_ws)

# --- WEBSOCKET UÇ NOKTASI ---

@app.websocket("/ws/stream/{channel_id}")
async def websocket_stream_endpoint(
    websocket: WebSocket,
    channel_id: str,
    role: str = Query("viewer"),
    lang: str = Query("en"),
    token: str = Query(None),
    sandbox: bool = Query(False)
):
    await websocket.accept()
    room = room_manager.get_or_create_room(channel_id)
    if role == "streamer":
        room.is_sandbox = sandbox
    loop = asyncio.get_event_loop()

    # Yayıncı Kimlik Doğrulaması (Security / Auth Check)
    if role == "streamer":
        # Güvenlik kontrolü: Token eşleşmeli veya geliştirme modunda olmalı
        if token and token != room.stream_key and token != "codum_live_key":
            await websocket.close(code=4001, reason="Geçersiz Yayın Anahtarı")
            return

        room.streamer_ws = websocket
        print(f"[STREAMER] Mikrofon bağlandı: {channel_id}")

        def on_speech_chunk(pcm_bytes: bytes):
            asyncio.run_coroutine_threadsafe(
                process_speech_pipeline(channel_id, pcm_bytes),
                loop
            )

        vad = StreamingVAD(
            sample_rate=audio_config.INPUT_SAMPLE_RATE,
            silence_threshold_ms=audio_config.VAD_SILENCE_THRESHOLD_MS,
            on_speech_chunk_ready=on_speech_chunk
        )

        try:
            while True:
                data = await websocket.receive_bytes()
                vad.process_audio_chunk(data)
        except WebSocketDisconnect:
            vad.flush()
            room_manager.remove_client(websocket)
            print(f"[DISCONNECT] Yayıncı bağlantısı kesildi: {channel_id}")

    elif role == "overlay":
        room.add_overlay(websocket)
        print(f"[OVERLAY] OBS Overlay bağlandı: {channel_id}")
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            room.remove_overlay(websocket)

    else:
        # İzleyici
        room.add_viewer(websocket, lang=lang)
        print(f"[VIEWER] İzleyici bağlandı [{lang}]: {channel_id}")
        try:
            while True:
                msg = await websocket.receive_text()
                payload = json.loads(msg)
                if payload.get("type") == "set_language":
                    new_lang = payload.get("lang", "en")
                    room.remove_viewer(websocket)
                    room.add_viewer(websocket, lang=new_lang)
                    await websocket.send_text(json.dumps({"type": "language_changed", "lang": new_lang}))
        except WebSocketDisconnect:
            room.remove_viewer(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host=server_config.HOST, port=server_config.PORT, reload=False)
