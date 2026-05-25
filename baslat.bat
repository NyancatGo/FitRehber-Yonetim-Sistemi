@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "HOST=127.0.0.1"
if not defined APP_PORT set "APP_PORT=8001"

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

set "PORT=%APP_PORT%"
call :port_free "%PORT%"
if errorlevel 1 (
    echo [UYARI] %HOST%:%PORT% portu dolu. Bos port araniyor...
    for /L %%P in (8002,1,8010) do (
        call :port_free "%%P"
        if not errorlevel 1 (
            set "PORT=%%P"
            goto :port_selected
        )
    )
    echo [HATA] 8001-8010 arasinda bos port bulunamadi.
    echo Baska bir port secmek icin:
    echo set APP_PORT=8020
    echo baslat.bat
    pause
    exit /b 1
)

:port_selected
echo FitRehber Yonetim Sistemi baslatiliyor...
echo.
echo Ana site : http://%HOST%:%PORT%/
echo Panel    : http://%HOST%:%PORT%/yonetim-sistemi/
echo Giris    : Nyancat / demo1234
echo.

"%PYTHON_EXE%" manage.py runserver %HOST%:%PORT%

pause
exit /b 0

:port_free
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalAddress '%HOST%' -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>nul
exit /b %ERRORLEVEL%
