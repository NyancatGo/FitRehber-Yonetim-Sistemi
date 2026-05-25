@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "HOST=127.0.0.1"
if not defined APP_PORT set "APP_PORT=8001"

echo ============================================================
echo FitRehber Yonetim Sistemi - Sunucu Baslatma
echo ============================================================
echo.
echo Bu dosya kurulum tamamlandiktan sonra kullanilir.
echo Ilk kurulum yapilmadiysa once kurulum.bat calistirilmalidir.
echo.

if not exist "%PYTHON_EXE%" (
    where docker >nul 2>nul
    if not errorlevel 1 (
        echo [BILGI] Proje sanal ortami bulunamadi, ancak Docker mevcut.
        docker info >nul 2>nul
        if errorlevel 1 (
            echo [HATA] Docker bulundu fakat Docker Desktop calismiyor.
            echo Docker Desktop'i acin ve BASLA.bat dosyasini tekrar calistirin.
            pause
            exit /b 1
        )
        set "COMPOSE_CMD="
        docker compose version >nul 2>nul
        if not errorlevel 1 set "COMPOSE_CMD=docker compose"
        if not defined COMPOSE_CMD (
            docker-compose version >nul 2>nul
            if not errorlevel 1 set "COMPOSE_CMD=docker-compose"
        )
        if not defined COMPOSE_CMD (
            echo [HATA] Docker Compose bulunamadi.
            echo Docker Desktop'i guncelleyin veya BASLA.bat ile local MySQL yolunu deneyin.
            pause
            exit /b 1
        )
        if not exist ".env" (
            echo [HATA] .env dosyasi bulunamadi. Docker kurulumu daha once tamamlanmamis.
            echo Lutfen once BASLA.bat dosyasini calistirin.
            pause
            exit /b 1
        )
        echo Docker servisleri veritabani sifirlanmadan baslatiliyor...
        !COMPOSE_CMD! up -d db web
        if errorlevel 1 (
            echo [HATA] Docker servisleri baslatilamadi.
            echo Ilk kurulum tamamlanmadiysa BASLA.bat dosyasini calistirin.
            pause
            exit /b 1
        )
        for /f "tokens=2 delims=:" %%P in ('!COMPOSE_CMD! port web 8000 2^>nul') do set "PORT=%%P"
        if not defined PORT set "PORT=%APP_PORT%"
        echo Docker servisleri baslatildi.
        echo Panel: http://127.0.0.1:!PORT!/yonetim-sistemi/
        start "" "http://127.0.0.1:!PORT!/yonetim-sistemi/"
        pause
        exit /b 0
    )
    echo [HATA] Proje sanal ortami bulunamadi.
    echo Lutfen once BASLA.bat dosyasini calistirin.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [HATA] .env dosyasi bulunamadi.
    echo Once kurulum.bat dosyasini calistirin.
    echo Docker ile kurulum yapildiysa docker-kurulum.bat dosyasini kullanin.
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
echo Tarayicida yukarida yazan Panel adresini acin.
echo Sunucuyu kapatmak icin bu pencerede Ctrl+C yapabilirsiniz.
echo.

"%PYTHON_EXE%" manage.py runserver %HOST%:%PORT%

pause
exit /b 0

:port_free
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalAddress '%HOST%' -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>nul
exit /b %ERRORLEVEL%
