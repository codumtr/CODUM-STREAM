@echo off
chcp 65001 > nul
title CODUM.TR STREAM PRO STUDIO - Baslatici ve Yonetim Paneli
cd /d "%~dp0"

echo ==============================================================================
echo    CODUM.TR STREAM PRO STUDIO - CANLI DUBLAJ VE CEVIRI SISTEMI v1.0.0
echo    Tescilli Freeware - Tum Haklari CODUM.TR STREAM'e Aittir.
echo ==============================================================================
echo.
echo   [1] Masaustu Programini Baslat (Onerilen: OBS / Discord gibi bagimsiz pencere)
echo   [2] Tarayici Uzerinden Paneli Ac (Chrome / Edge / Opera vb.)
echo   [3] OBS Studio Icin Altyazi / Overlay Baglantisini Kopyala
echo   [4] Hizli Baslangic Kilavuzunu Oku (Kurulum ve OBS Ayarlari)
echo   [5] Cikis
echo.
echo ==============================================================================
set /p choice="Lutfen bir secim yapin [1-5] (Varsayilan: 1): "

if "%choice%"=="" set choice=1
if "%choice%"=="1" goto start_desktop
if "%choice%"=="2" goto start_browser
if "%choice%"=="3" goto copy_obs
if "%choice%"=="4" goto open_guide
if "%choice%"=="5" goto exit_app

:start_desktop
cls
echo ==============================================================================
echo  Masaustu Program Penceresi Baslatiliyor...
echo ==============================================================================
if exist "CODUM_StreamDub.exe" (
    start "" "CODUM_StreamDub.exe"
) else (
    echo [HATA] CODUM_StreamDub.exe bulunamadi! Lutfen zip dosyasini bir klasore cikarin.
    pause
)
exit

:start_browser
cls
echo ==============================================================================
echo  Tarayici Modunda Baslatiliyor...
echo ==============================================================================
if exist "CODUM_StreamDub.exe" (
    start "" "CODUM_StreamDub.exe" --browser
) else (
    echo [HATA] CODUM_StreamDub.exe bulunamadi!
    pause
)
exit

:copy_obs
cls
echo ==============================================================================
echo  OBS STUDIO OVERLAY BAGLANTISI:
echo ==============================================================================
echo.
echo  Tarayici Kaynagi (Browser Source) URL Adresi:
echo  http://127.0.0.1:8765/overlay
echo.
echo  OBS Ayarlari:
echo  - Genislik (Width) : 1920
echo  - Yukseklik (Height): 1080
echo  - Ozel CSS          : body { background-color: rgba(0, 0, 0, 0); margin: 0px auto; overflow: hidden; }
echo.
echo ==============================================================================
echo Adres panoya kopyalaniyor...
echo http://127.0.0.1:8765/overlay | clip
echo [BASARILI] OBS Overlay URL panoya kopyalandi!
echo.
pause
goto start_desktop

:open_guide
cls
if exist "KULLANIM_KILAVUZU.txt" (
    start "" notepad.exe "KULLANIM_KILAVUZU.txt"
) else (
    echo Kilavuz bulunamadi.
    pause
)
exit

:exit_app
exit
