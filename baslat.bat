@echo off
chcp 65001 > nul
title CODUM.TR STREAM Studio
cd /d "%~dp0"
echo ========================================================
echo  CODUM.TR STREAM AI Studio Baslatiliyor...
echo  Yonetim Paneli : http://127.0.0.1:8765/dashboard
echo  OBS Overlay    : http://127.0.0.1:8765/overlay?channel=streamer
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
            echo [HATA] Python bulunamadi! Lutfen Python 3.10+ yukleyin veya PATH'e ekleyin.
            pause
            exit /b 1
        )
    )
)

"%PY_CMD%" -m uvicorn server.app:app --host 127.0.0.1 --port 8765
pause
