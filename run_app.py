"""
CODUM.TR STREAM - Standalone Masaüstü Uygulaması (Native Desktop GUI & Studio Hub)
Bu uygulama çift tıklandığında modern, bağımsız bir masaüstü program penceresi açar
(Discord / OBS / Streamlabs tarzında).
Tüm hakları CODUM.TR STREAM'e aittir.
"""

import sys
import os
import time
import socket
import threading
import urllib.request
import webbrowser
import traceback
import ctypes

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

LOG_FILE = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else application_path, "codum_studio.log")

def log(msg: str):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {msg}\n"
    print(msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def show_error_box(title: str, message: str):
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass

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
        err = f"Sunucu baslatma hatasi: {e}\n{traceback.format_exc()}"
        log(err)
        show_error_box("CODUM.TR STREAM Sunucu Hatası", f"Sunucu başlatılamadı:\n{e}\n\nAyrıntılar için codum_studio.log dosyasını inceleyin.")

def wait_for_server(port: int, max_wait_sec: float = 6.0) -> bool:
    start = time.time()
    url = f"http://127.0.0.1:{port}/"
    while time.time() - start < max_wait_sec:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CODUM-Checker"})
            with urllib.request.urlopen(req, timeout=0.5) as res:
                if res.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def main():
    try:
        log("CODUM.TR STREAM PRO STUDIO baslatiliyor...")
        target_port = 8765
        server_needed = True

        force_browser = "--browser" in sys.argv

        if is_port_in_use(target_port):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{target_port}/", headers={"User-Agent": "CODUM-Checker"})
                with urllib.request.urlopen(req, timeout=0.8) as res:
                    content = res.read().decode('utf-8', errors='ignore')
                    if "CODUM.TR" in content:
                        log(f"Mevcut CODUM sunucusu port {target_port} üzerinde zaten çalışıyor.")
                        server_needed = False
                    else:
                        target_port = find_available_port(8766)
                        log(f"Port 8765 baska servis tarafindan mesgul. Yeni port: {target_port}")
            except Exception:
                target_port = find_available_port(8766)
                log(f"Port 8765 yanit vermedi. Yeni port: {target_port}")

        if server_needed:
            log(f"FastAPI + WebSocket AI Hub port {target_port} uzerinde baslatiliyor...")
            server_thread = threading.Thread(target=start_server_daemon, args=(target_port,), daemon=True)
            server_thread.start()
            
            # Sunucunun ayağa kalkmasını garantile
            if not wait_for_server(target_port, max_wait_sec=8.0):
                log("UYARI: Sunucu HTTP kontrolune zamaninda yanit vermedi, arayuz yinede acilacak.")
            else:
                log(f"Sunucu basariyla aktif: http://127.0.0.1:{target_port}")

        app_url = f"http://127.0.0.1:{target_port}/dashboard"
        overlay_url = f"http://127.0.0.1:{target_port}/overlay"

        print("=" * 64)
        print("  CODUM.TR STREAM PRO STUDIO - YONETIM MERKEZI AKTIF")
        print("=" * 64)
        print(f"  Yayıncı Paneli : {app_url}")
        print(f"  OBS Overlay URL: {overlay_url}")
        print("=" * 64)

        if force_browser:
            log("Kullanici tercihi: Tarayici modunda aciliyor.")
            webbrowser.open(app_url)
            print("\nProgram calisiyor. Kapatmak icin bu pencereyi kapatin veya Ctrl+C yapin...")
            while True:
                time.sleep(1)

        # Standalone Native Desktop Penceresini Baslat
        try:
            import webview
            log("Native WebView2 Masaustu Penceresi olusturuluyor...")
            window = webview.create_window(
                title="CODUM.TR STREAM PRO STUDIO - Canlı Çeviri & Dublaj Masası",
                url=app_url,
                width=1280,
                height=840,
                min_size=(960, 620),
                background_color='#0b0f19',
                text_select=True
            )
            webview.start(gui="edgechromium")
            log("Masaustu penceresi kullanici tarafindan kapatildi. Cikis yapiliyor.")
        except Exception as e:
            log(f"Masaustu penceresi acilamadi, tarayici fallback devreye giriyor: {e}")
            webbrowser.open(app_url)
            print("\n[BILGI] Masaustu penceresi tarayicinizda acildi.")
            print("Program arka planda calisiyor. Kapatmak icin bu pencereyi kapatin...")
            while True:
                time.sleep(1)

    except Exception as e:
        err_msg = f"Kritik Baslatma Hatasi:\n{e}\n\n{traceback.format_exc()}"
        log(err_msg)
        show_error_box("CODUM.TR STREAM Başlatma Hatası", f"Program başlatılırken bir sorun oluştu:\n\n{e}\n\nAyrıntılar için program klasöründeki codum_studio.log dosyasına bakın.")

if __name__ == "__main__":
    main()
