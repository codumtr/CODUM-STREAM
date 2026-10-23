@echo off
chcp 65001 > nul
title CODUM.TR STREAM - Standalone Windows Program Derleyici
cd /d "%~dp0"

echo ========================================================
echo   CODUM.TR STREAM: Standalone Masaustu Programi Derleniyor
echo   (Discord / OBS gibi bagimsiz masaustu penceresi)
echo ========================================================
echo.

if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    ) else (
        where python >nul 2>nul
        if %errorlevel% equ 0 (
            set "PY_CMD=python"
        ) else (
            echo [HATA] Python bulunamadi! Lutfen Python yukleyin veya PATH'e ekleyin.
            pause
            exit /b 1
        )
    )
)

echo [1/3] Gerekli paketler kontrol ediliyor...
"%PY_CMD%" -m pip install pyinstaller pywebview

echo.
echo [2/3] CODUM_StreamDub.exe derleniyor (Native Desktop App)...
"%PY_CMD%" -m PyInstaller --noconfirm --onedir --name "CODUM_StreamDub" ^
    --add-data "streamer_dashboard;streamer_dashboard" ^
    --add-data "overlay;overlay" ^
    --add-data "profiles;profiles" ^
    --add-data "assets;assets" ^
    --add-data ".env.example;.env.example" ^
    --add-data "LICENSE.md;LICENSE.md" ^
    --collect-all pywebview ^
    --hidden-import="uvicorn.logging" ^
    --hidden-import="uvicorn.loops" ^
    --hidden-import="uvicorn.loops.auto" ^
    --hidden-import="uvicorn.protocols" ^
    --hidden-import="uvicorn.protocols.http" ^
    --hidden-import="uvicorn.protocols.http.auto" ^
    --hidden-import="uvicorn.protocols.websockets" ^
    --hidden-import="uvicorn.protocols.websockets.auto" ^
    --hidden-import="uvicorn.lifespan" ^
    --hidden-import="uvicorn.lifespan.on" ^
    run_app.py

echo.
echo [3/3] Ek belgeler paket klasorune kopyalaniyor...
copy /Y "KULLANIM_KILAVUZU.txt" "dist\CODUM_StreamDub\" > nul
copy /Y "LICENSE.md" "dist\CODUM_StreamDub\" > nul

echo.
echo ========================================================
echo   [BASARILI] Masaustu Program Paketi Olusturuldu!
echo   Klasor: dist\CODUM_StreamDub\
echo   - CODUM_BASLAT.bat (Cift tikla yonetim paneli)
echo   - CODUM_StreamDub.exe (Masaustu pencere programi)
echo   - KULLANIM_KILAVUZU.txt (Detayli adim adim rehber)
echo ========================================================
