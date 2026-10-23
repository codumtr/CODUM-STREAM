"""
CODUM.TR STREAM - Standalone Masaüstü Uygulaması (Native Desktop GUI)
Bu uygulama çift tıklandığında tarayıcı sekmesi yerine bağımsız, modern bir
masaüstü program penceresi açar (Discord / OBS / Streamlabs tarzında).
Tüm hakları CODUM.TR STREAM'e aittir.
"""

import sys
import os
import time
import socket
import threading
import urllib.request
import webbrowser

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

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(start_port: int = 8765) -> int:
    port = start_port
    while port < start_port + 20:
        if not is_port_in_use(port):
            return port
        port += 1
    return start_port

def start_server_daemon(port: int):
    try:
        import uvicorn
        from server.app import app
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    except Exception as e:
        print(f"Sunucu hatası: {e}")

def main():
    target_port = 8765
    server_needed = True

    if is_port_in_use(target_port):
        # Zaten sunucu çalışıyor mu?
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{target_port}/", headers={"User-Agent": "CODUM-Checker"})
            with urllib.request.urlopen(req, timeout=0.8) as res:
                content = res.read().decode('utf-8', errors='ignore')
                if "CODUM.TR" in content:
                    server_needed = False
        except Exception:
            # Başka bir servis meşgul ediyorsa boş port bul
            target_port = find_available_port(8766)

    if server_needed:
        server_thread = threading.Thread(target=start_server_daemon, args=(target_port,), daemon=True)
        server_thread.start()
        time.sleep(0.8)

    app_url = f"http://127.0.0.1:{target_port}/dashboard"

    # Modern Masaüstü Program Penceresini Başlat
    try:
        import webview
        window = webview.create_window(
            title="CODUM.TR STREAM PRO STUDIO",
            url=app_url,
            width=1280,
            height=820,
            min_size=(960, 620),
            background_color='#0b0f19',
            text_select=True
        )
        webview.start(gui="edgechromium")
    except Exception as e:
        # Fallback: Herhangi bir GUI sürücüsü eksikse tarayıcıda aç
        print(f"Masaüstü penceresi fallback moduna geçti: {e}")
        webbrowser.open(app_url)
        try:
            input("\nProgram çalışıyor. Kapatmak için Enter'a basın...")
        except:
            time.sleep(86400)

if __name__ == "__main__":
    main()
