@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [HATA] Proje sanal ortami bulunamadi.
    echo Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [HATA] .env dosyasi bulunamadi.
    echo Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)

echo FitRehber Yonetim Sistemi baslatiliyor...
echo.
echo Ana site : http://127.0.0.1:8001/
echo Panel    : http://127.0.0.1:8001/yonetim-sistemi/
echo Giris    : Nyancat / demo1234
echo.

"%PYTHON_EXE%" manage.py runserver 127.0.0.1:8001

pause
