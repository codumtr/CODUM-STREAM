"""
Streamer Mic Isolated Audio Sender
Yayıncının YALNIZCA fiziksel mikrofonunu yakalar (oyun seslerini, Discord'u ve arka plan
müziğini dışlar). 16kHz mono 16-bit PCM akışı halinde doğrudan StreamDub sunucusuna iletir.
"""

import sys
import asyncio
import websockets
import numpy as np

# Konsol UTF-8 desteği
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024

async def stream_mic_audio(channel_id: str = "streamer", server_url: str = "ws://localhost:8765"):
    ws_url = f"{server_url}/ws/stream/{channel_id}?role=streamer"
    print(f"🎙️ Yayıncı Mikrofon İstemcisi Başlatılıyor...")
    print(f"🔗 Bağlanılan Sunucu: {ws_url}")

    try:
        import sounddevice as sd
    except ImportError:
        print("❌ 'sounddevice' kütüphanesi bulunamadı! 'pip install sounddevice' çalıştırın.")
        return

    # Kullanılabilir giriş cihazlarını listele
    devices = sd.query_devices()
    input_device = sd.default.device[0]
    print(f"🎤 Aktif Giriş Cihazı: {devices[input_device]['name']}")

    audio_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"⚠️ Ses uyarısı: {status}")
        # float32 -> int16 PCM dönüşümü
        pcm16 = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        loop.call_soon_threadsafe(audio_queue.put_nowait, pcm16)

    try:
        async with websockets.connect(ws_url) as ws:
            print(f"✅ Sunucuya bağlanıldı! Mikrofon akışı iletiliyor (Kanal: {channel_id})...")
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=CHUNK_SIZE,
                callback=audio_callback
            ):
                while True:
                    data = await audio_queue.get()
                    await ws.send(data)

    except ConnectionRefusedError:
        print("❌ Sunucuya bağlanılamadı. Lütfen önce 'server/app.py' sunucusunu başlatın.")
    except Exception as e:
        print(f"❌ Akış Hatası: {e}")

if __name__ == "__main__":
    channel = sys.argv[1] if len(sys.argv) > 1 else "streamer"
    asyncio.run(stream_mic_audio(channel_id=channel))
