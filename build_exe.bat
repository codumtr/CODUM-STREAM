@echo off
chcp 65001 > nul
title CODUM.TR STREAM - Standalone Windows EXE Derleyici
cd /d "%~dp0"

echo ========================================================
echo   CODUM.TR STREAM: Standalone EXE Paketi Olusturuluyor
echo   (Yayinici bilgisayarinda Python YUKLEMEK GEREKMEZ)
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    ) else (
        if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
            set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
        ) else (
            echo [HATA] Python bulunamadi! Lutfen Python yukleyin veya PATH'e ekleyin.
            pause
            exit /b 1
        )
    )
)

echo [1/3] PyInstaller kontrol ediliyor...
"%PY_CMD%" -m pip install pyinstaller

echo.
echo [2/3] CODUM_StreamDub.exe derleniyor (Stand-alone portable paket)...
"%PY_CMD%" -m PyInstaller --noconfirm --onedir --name "CODUM_StreamDub" ^
    --add-data "streamer_dashboard;streamer_dashboard" ^
    --add-data "overlay;overlay" ^
    --add-data "profiles;profiles" ^
    --add-data ".env.example;.env.example" ^
    --add-data "LICENSE.md;LICENSE.md" ^
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
    --hidden-import="engineio.async_drivers.asgi" ^
    run_app.py

echo.
echo ========================================================
echo   [BASARILI] EXE Paketi Olusturuldu!
echo   Klasor: dist\CODUM_StreamDub\
echo   Yayiniciya sadece 'dist\CODUM_StreamDub' klasorunu veya ZIP'ini verin.
echo   Yayinici cift tikladiginda otomatik calisir, Python gerekmez!
echo ========================================================
pause
