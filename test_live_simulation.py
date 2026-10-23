"""
Live Simulation Test
Sunucuya WebSocket üzerinden bağlanır:
1. Bir izleyici/overlay gibi altyazıları dinler
2. Yayıncı mikrofonundan geliyormuş gibi sentetik konuşma ses paketleri yollar
3. Gelen altyazı ve dublaj durumunu ekranda doğrular.
"""

import sys
import asyncio
import json
import websockets
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SERVER_WS = "ws://127.0.0.1:8765/ws/stream/testkanal"

async def overlay_listener():
    url = f"{SERVER_WS}?role=overlay"
    print("📺 [1. OBS Overlay Bağlandı] Altyazı ve Dublaj Sesi bekleniyor...")
    try:
        async with websockets.connect(url) as ws:
            sub_received = False
            audio_received = False
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("type") == "subtitle" and data.get("translated"):
                    print("\n" + "=" * 50)
                    print(f"🎯 [OBS ALTYAZISI GELDİ]:")
                    print(f"   🇹🇷 Orijinal  : {data.get('original')}")
                    print(f"   🇬🇧 İngilizce : {data.get('translated')}")
                    print("=" * 50)
                    sub_received = True

                if data.get("type") == "dub_audio":
                    audio_len = len(data.get("audio", ""))
                    print(f"🔊 [OBS DUBLAJ SESİ GELDİ]: Base64 Boyutu: {audio_len} karakter, Format: {data.get('mime')}")
                    audio_received = True

                if sub_received and audio_received:
                    print("✅ Hem OBS Altyazısı hem de OBS Dublaj Sesi başarıyla doğrulandı!\n")
                    break
    except Exception as e:
        print(f"Overlay dinleyici hatası: {e}")

async def streamer_sender():
    url = f"{SERVER_WS}?role=streamer&token=codum_live_key"
    await asyncio.sleep(1) # Overlay'in bağlanmasını bekle
    print("🎙️ [2. Yayıncı Mikrofonu Bağlandı] Simüle ses paketleri gönderiliyor...")

    try:
        async with websockets.connect(url) as ws:
            # 1.5 saniyelik konuşma enerjisi simülasyonu (440Hz sinüs tonu, konuşma eşiğini aşan enerji)
            sample_rate = 16000
            duration = 1.2
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = (np.sin(2 * np.pi * 300 * t) * 15000).astype(np.int16)
            pcm_bytes = tone.tobytes()

            # Parçalar halinde gönder
            chunk_size = 2048
            for i in range(0, len(pcm_bytes), chunk_size):
                await ws.send(pcm_bytes[i:i+chunk_size])
                await asyncio.sleep(0.03)

            # Ardından 400ms sessizlik gönder (VAD cümlenin bittiğini anlasın diye)
            silence = np.zeros(int(sample_rate * 0.4), dtype=np.int16).tobytes()
            for i in range(0, len(silence), chunk_size):
                await ws.send(silence[i:i+chunk_size])
                await asyncio.sleep(0.03)

            print("✅ Ses paketi ve sessizlik sinyali başarıyla iletildi.")
            await asyncio.sleep(2)
    except Exception as e:
        print(f"Yayıncı gönderici hatası: {e}")

async def main():
    print("🚀 Canlı Uçtan Uca Simülasyon Başlatılıyor...")
    await asyncio.gather(
        overlay_listener(),
        streamer_sender()
    )

if __name__ == "__main__":
    asyncio.run(main())
