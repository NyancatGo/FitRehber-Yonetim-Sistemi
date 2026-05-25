@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "HOST=127.0.0.1"
if not defined APP_PORT set "APP_PORT=8001"

echo ============================================================
echo FitRehber Yonetim Sistemi - Akilli Baslatma
echo ============================================================
echo.
echo Bu dosya tek tikla calistirilir. Kurulum gerekli ise once
echo kurulumu otomatik tamamlar, ardindan sunucuyu baslatir.
echo.

REM ============================================================
REM 1) MEVCUT KURULUM TESPITI
REM ============================================================

REM Local MySQL kurulumu yapilmis (.venv ve .env mevcut)
if exist "%PYTHON_EXE%" if exist ".env" goto :start_local

REM .env var ama .venv yok -> Docker olabilir; degilse local kurulum yenilenir
if exist ".env" goto :env_without_venv

REM Hicbir iz yok -> ilk kurulum gerekli
goto :auto_install

:env_without_venv
where docker >nul 2>nul
if not errorlevel 1 (
    docker info >nul 2>nul
    if not errorlevel 1 goto :ensure_docker_running
)
echo [BILGI] .env bulundu fakat Python sanal ortami yok.
echo Local kurulum otomatik olarak yenilenecek.
echo.
goto :auto_install_local


REM ============================================================
REM 2) ILK KURULUM (otomatik secim)
REM ============================================================
:auto_install
echo [BILGI] Bilgisayarinizda kurulum bulunamadi.
echo Otomatik kurulum baslatiliyor...
echo.

REM Once Docker yolu denenir (MySQL sifresine ihtiyac yoktur)
where docker >nul 2>nul
if errorlevel 1 goto :auto_install_local

docker info >nul 2>nul
if errorlevel 1 (
    echo Docker bulundu fakat Docker Desktop calismiyor.
    echo Local MySQL kurulumu denenecek.
    echo.
    goto :auto_install_local
)

echo Docker Desktop calisiyor. Docker kurulumu kullanilacak.
echo Bu yontemde bilgisayarinizdaki MySQL sifresine ihtiyac yoktur.
echo.
set "BASLAT_AUTORUN=1"
call docker-kurulum.bat
set "DOCKER_RC=%ERRORLEVEL%"
set "BASLAT_AUTORUN="
if not "%DOCKER_RC%"=="0" (
    echo.
    echo Docker kurulumu tamamlanamadi.
    choice /C EH /N /M "E=Local MySQL ile devam et, H=Cikis: "
    if errorlevel 2 exit /b 1
    goto :auto_install_local
)
REM docker-kurulum.bat servisleri baslatti ve tarayiciyi acti
exit /b 0

:auto_install_local
REM Python kontrolu (en azindan birinin bulunmasi yeterli)
set "PY_FOUND="
where py >nul 2>nul && set "PY_FOUND=1"
if not defined PY_FOUND where python >nul 2>nul && set "PY_FOUND=1"
if not defined PY_FOUND if defined PYTHON_BOOTSTRAP set "PY_FOUND=1"

if not defined PY_FOUND (
    echo.
    echo [HATA] Ne Docker Desktop ne de Python 3 bulundu.
    echo.
    echo Lutfen asagidakilerden birini kurun ve baslat.bat'i tekrar calistirin:
    echo  - Docker Desktop  ^(https://www.docker.com/products/docker-desktop^)
    echo  - Python 3        ^(https://www.python.org/downloads/^) + MySQL Server 8.x
    echo.
    pause
    exit /b 1
)

echo Local MySQL kurulumu yapilacak.
echo MySQL yonetici sifresi sorulacak ^(varsayilan: root / 123^).
echo.
set "BASLAT_AUTORUN=1"
call kurulum.bat
set "INSTALL_RC=%ERRORLEVEL%"
set "BASLAT_AUTORUN="
if not "%INSTALL_RC%"=="0" exit /b %INSTALL_RC%

echo.
echo Kurulum tamamlandi. Sunucu baslatiliyor...
echo.
goto :start_local


REM ============================================================
REM 3) DOCKER KURULUMUNDA BASLATMA
REM ============================================================
:ensure_docker_running
where docker >nul 2>nul
if errorlevel 1 (
    echo [HATA] Onceden bir kurulum izi bulundu ^(.env^) fakat Docker yok.
    echo Eger MySQL kurulumunu sifirdan denemek istiyorsaniz .env dosyasini silip
    echo baslat.bat'i tekrar calistirin.
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo [HATA] Docker Desktop kapali gorunuyor.
    echo Docker Desktop'i acin, "Docker Desktop is running" durumunu bekleyin
    echo ve baslat.bat'i tekrar calistirin.
    pause
    exit /b 1
)

:start_docker
set "COMPOSE_CMD="
docker compose version >nul 2>nul
if not errorlevel 1 set "COMPOSE_CMD=docker compose"
if not defined COMPOSE_CMD (
    docker-compose version >nul 2>nul
    if not errorlevel 1 set "COMPOSE_CMD=docker-compose"
)
if not defined COMPOSE_CMD (
    echo [HATA] Docker Compose bulunamadi. Docker Desktop'i guncelleyin.
    pause
    exit /b 1
)

echo Docker servisleri baslatiliyor...
%COMPOSE_CMD% up -d db web
if errorlevel 1 (
    echo [HATA] Docker servisleri baslatilamadi.
    pause
    exit /b 1
)

set "PORT="
for /f "tokens=2 delims=:" %%P in ('%COMPOSE_CMD% port web 8000 2^>nul') do set "PORT=%%P"
if not defined PORT set "PORT=%APP_PORT%"

echo.
echo Panel: http://127.0.0.1:%PORT%/yonetim-sistemi/
echo Giris: Nyancat / demo1234
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:%PORT%/yonetim-sistemi/'"
pause
exit /b 0


REM ============================================================
REM 4) LOCAL MYSQL KURULUMUNDA BASLATMA
REM ============================================================
:start_local
set "PORT=%APP_PORT%"
call :port_free "%PORT%"
if errorlevel 1 (
    echo [UYARI] %HOST%:%PORT% portu dolu. Bos port araniyor...
    for /L %%P in (8002,1,8010) do (
        call :port_free "%%P"
        if not errorlevel 1 (
            set "PORT=%%P"
            goto :local_port_selected
        )
    )
    echo [HATA] 8001-8010 arasinda bos port bulunamadi.
    echo Baska bir port secmek icin:
    echo   set APP_PORT=8020
    echo   baslat.bat
    pause
    exit /b 1
)

:local_port_selected
echo FitRehber Yonetim Sistemi baslatiliyor...
echo.
echo Ana site : http://%HOST%:%PORT%/
echo Panel    : http://%HOST%:%PORT%/yonetim-sistemi/
echo Giris    : Nyancat / demo1234
echo.
echo Tarayicida yukarida yazan Panel adresini acin.
echo Sunucuyu kapatmak icin bu pencerede Ctrl+C yapabilirsiniz.
echo.

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://%HOST%:%PORT%/yonetim-sistemi/'"
"%PYTHON_EXE%" manage.py runserver %HOST%:%PORT%

pause
exit /b 0


:port_free
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalAddress '%HOST%' -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>nul
exit /b %ERRORLEVEL%
