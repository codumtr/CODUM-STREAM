"""
CODUM.TR STREAM - Standalone Exe Giriş Noktası (Entrypoint)
Bu dosya PyInstaller ile derlendiğinde Python gerektirmeden tek tıkla çalışır.
Tüm hakları CODUM.TR STREAM'e aittir.
"""

import sys
import os
import webbrowser
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# PyInstaller paket dizinini algıla
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
    os.chdir(os.path.dirname(sys.executable))
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    os.chdir(application_path)

import uvicorn
from server.app import app

def open_browser():
    time.sleep(1.2)
    try:
        webbrowser.open("http://127.0.0.1:8765/dashboard")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 60)
    print("  CODUM.TR STREAM STUDIO (Stand-alone Sürüm)")
    print("  Telif Hakkı (c) 2026 CODUM.TR. Tüm Hakları Saklıdır.")
    print("  Kontrol Paneli : http://127.0.0.1:8765/dashboard")
    print("  OBS Browser URL: http://127.0.0.1:8765/overlay?channel=streamer")
    print("=" * 60)
    print("\n[BİLGİ] Tarayıcı otomatik açılıyor...")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
