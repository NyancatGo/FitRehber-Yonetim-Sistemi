@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "DB_NAME=fitrehber_yonetim_demo"
set "APP_DB_USER=fitrehber_demo"
set "APP_DB_PASS=FitRehberDemo2026!"
set "MYSQL_ROOT_PASSWORD=123"
set "HOST=127.0.0.1"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not defined APP_PORT set "APP_PORT=8001"

echo ============================================================
echo FitRehber Yonetim Sistemi - Tek Tik Akilli Baslatma
echo ============================================================
echo.
echo Bu dosya tek basina yeterlidir.
echo Kurulum yoksa kurar, kurulum varsa dogrudan sunucuyu baslatir.
echo.

REM ============================================================
REM 1) MEVCUT KURULUM TESPITI
REM ============================================================

if exist "%PYTHON_EXE%" if exist ".env" goto :start_local
if exist ".env" goto :env_without_venv
goto :auto_install

:env_without_venv
where docker >nul 2>nul
if not errorlevel 1 (
    docker info >nul 2>nul
    if not errorlevel 1 goto :start_docker
)
echo [BILGI] .env bulundu fakat Python sanal ortami yok.
echo Local kurulum otomatik olarak yenilenecek.
echo.
goto :install_local

REM ============================================================
REM 2) ILK KURULUM SECIMI
REM ============================================================

:auto_install
echo [BILGI] Bilgisayarinizda kurulum bulunamadi.
echo Otomatik kurulum baslatiliyor...
echo.

where docker >nul 2>nul
if errorlevel 1 goto :install_local

docker info >nul 2>nul
if errorlevel 1 (
    echo Docker bulundu fakat Docker Desktop calismiyor.
    echo Local MySQL kurulumu denenecek.
    echo.
    goto :install_local
)

echo Docker Desktop calisiyor. Docker kurulumu kullanilacak.
echo Bu yontemde bilgisayarinizdaki MySQL sifresine ihtiyac yoktur.
echo.
call :install_docker
if errorlevel 1 (
    echo.
    echo Docker kurulumu tamamlanamadi.
    choice /C EH /N /M "E=Local MySQL ile devam et, H=Cikis: "
    if errorlevel 2 exit /b 1
    goto :install_local
)
exit /b 0

REM ============================================================
REM 3) LOCAL MYSQL KURULUMU
REM ============================================================

:install_local
call :find_python
if errorlevel 1 exit /b 1

if not defined MYSQL_ROOT_USER set /p MYSQL_ROOT_USER=MySQL yonetici kullanici adi [root]:
if "%MYSQL_ROOT_USER%"=="" set "MYSQL_ROOT_USER=root"

echo.
echo Not: MySQL sifresini bilmiyorsaniz Enter'a basmak yerine Docker Desktop'i acip
echo baslat.bat dosyasini tekrar calistirabilirsiniz.
if not defined MYSQL_ROOT_PASS set /p MYSQL_ROOT_PASS=MySQL yonetici sifresi [123]:
if "%MYSQL_ROOT_PASS%"=="" set "MYSQL_ROOT_PASS=123"

call :find_mysql
if errorlevel 1 exit /b 1

echo.
echo [1/9] Python sanal ortami hazirlaniyor...
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [HATA] Python sanal ortami olusturulamadi.
        pause
        exit /b 1
    )
)
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

echo.
echo [2/9] Python paketleri kuruluyor...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [HATA] pip guncellenemedi.
    pause
    exit /b 1
)
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [HATA] requirements.txt paketleri kurulamadi.
    pause
    exit /b 1
)

echo.
echo [3/9] Guvenli local .env hazirlaniyor...
if not exist ".env" (
    copy ".env.example" ".env" >nul
) else (
    echo .env zaten var, korunuyor.
)

echo.
echo [4/9] MySQL baglantisi kontrol ediliyor...
"%MYSQL_EXE%" -u"%MYSQL_ROOT_USER%" -p"%MYSQL_ROOT_PASS%" --default-character-set=utf8mb4 -e "SELECT VERSION();" >nul
if errorlevel 1 (
    echo [HATA] MySQL baglantisi basarisiz. Kullanici adi/sifreyi kontrol edin.
    echo Sifreyi bilmiyorsaniz Docker Desktop'i acip baslat.bat'i tekrar calistirin.
    pause
    exit /b 1
)

echo.
echo [5/9] Demo veritabani ve uygulama kullanicisi olusturuluyor...
"%MYSQL_EXE%" -u"%MYSQL_ROOT_USER%" -p"%MYSQL_ROOT_PASS%" --default-character-set=utf8mb4 -e "DROP DATABASE IF EXISTS `%DB_NAME%`; CREATE DATABASE `%DB_NAME%` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS '%APP_DB_USER%'@'%%' IDENTIFIED BY '%APP_DB_PASS%'; ALTER USER '%APP_DB_USER%'@'%%' IDENTIFIED BY '%APP_DB_PASS%'; GRANT ALL PRIVILEGES ON `%DB_NAME%`.* TO '%APP_DB_USER%'@'%%'; FLUSH PRIVILEGES;"
if errorlevel 1 (
    echo [HATA] Demo veritabani olusturulamadi.
    pause
    exit /b 1
)

echo.
echo [6/9] Django migration kuruluyor...
"%PYTHON_EXE%" manage.py migrate --noinput
if errorlevel 1 (
    echo [HATA] Django migration adimi basarisiz oldu.
    pause
    exit /b 1
)

echo.
echo [7/9] Stored Procedure / Function / Trigger omurgasi uygulaniyor...
"%MYSQL_EXE%" -u"%MYSQL_ROOT_USER%" -p"%MYSQL_ROOT_PASS%" --default-character-set=utf8mb4 "%DB_NAME%" < "sql\fitrehber_db.sql"
if errorlevel 1 (
    echo [HATA] sql\fitrehber_db.sql uygulanamadi.
    pause
    exit /b 1
)

echo.
echo [8/9] Sanitize demo verisi yukleniyor...
"%MYSQL_EXE%" -u"%MYSQL_ROOT_USER%" -p"%MYSQL_ROOT_PASS%" --default-character-set=utf8mb4 "%DB_NAME%" < "sql\demo_data.sql"
if errorlevel 1 (
    echo [HATA] sql\demo_data.sql yuklenemedi.
    pause
    exit /b 1
)

echo.
echo [9/9] Rate-limit cache tablosu garanti kuruluyor...
"%PYTHON_EXE%" manage.py createcachetable rate_limit_cache_table
if errorlevel 1 (
    echo [HATA] rate_limit_cache_table olusturulamadi.
    pause
    exit /b 1
)

echo.
echo Son kontrol yapiliyor...
"%PYTHON_EXE%" manage.py check
if errorlevel 1 (
    echo [HATA] Django sistem kontrolu basarisiz oldu.
    pause
    exit /b 1
)

echo.
echo Kurulum tamamlandi. Sunucu baslatiliyor...
echo.
goto :start_local

REM ============================================================
REM 4) DOCKER KURULUMU
REM ============================================================

:install_docker
call :find_compose
if errorlevel 1 exit /b 1
call :docker_pick_port
if errorlevel 1 exit /b 1

if not exist ".env" copy ".env.example" ".env" >nul

echo Docker DB sifirlaniyor ve servisler hazirlaniyor...
%COMPOSE_CMD% up -d db
if errorlevel 1 (
    echo [HATA] Docker DB servisi baslatilamadi.
    pause
    exit /b 1
)

echo MySQL container hazir olana kadar bekleniyor...
set "MYSQL_WAIT_TRIES=0"
:wait_mysql
%COMPOSE_CMD% exec -T db mysqladmin ping -uroot -p%MYSQL_ROOT_PASSWORD% --silent >nul 2>nul
if not errorlevel 1 goto :mysql_ready
set /a MYSQL_WAIT_TRIES+=1
if %MYSQL_WAIT_TRIES% GEQ 40 goto :mysql_wait_failed
timeout /t 3 /nobreak >nul
goto :wait_mysql

:mysql_wait_failed
echo [HATA] MySQL container 120 saniye icinde hazir olmadi.
%COMPOSE_CMD% logs db --tail=50
pause
exit /b 1

:mysql_ready
%COMPOSE_CMD% exec -T db mysql -uroot -p%MYSQL_ROOT_PASSWORD% --default-character-set=utf8mb4 -e "DROP DATABASE IF EXISTS %DB_NAME%; CREATE DATABASE %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if errorlevel 1 (
    echo [HATA] Docker MySQL demo veritabani sifirlanamadi.
    pause
    exit /b 1
)

%COMPOSE_CMD% build web
if errorlevel 1 (
    echo [HATA] Docker web imaji build edilemedi.
    pause
    exit /b 1
)

%COMPOSE_CMD% run --rm web python manage.py migrate --noinput
if errorlevel 1 (
    echo [HATA] Docker migration adimi basarisiz oldu.
    pause
    exit /b 1
)

%COMPOSE_CMD% exec -T db mysql -uroot -p%MYSQL_ROOT_PASSWORD% --default-character-set=utf8mb4 %DB_NAME% < "sql\fitrehber_db.sql"
if errorlevel 1 (
    echo [HATA] Docker SQL omurgasi uygulanamadi.
    pause
    exit /b 1
)

%COMPOSE_CMD% exec -T db mysql -uroot -p%MYSQL_ROOT_PASSWORD% --default-character-set=utf8mb4 %DB_NAME% < "sql\demo_data.sql"
if errorlevel 1 (
    echo [HATA] Docker demo verisi yuklenemedi.
    pause
    exit /b 1
)

%COMPOSE_CMD% run --rm web python manage.py createcachetable rate_limit_cache_table
if errorlevel 1 (
    echo [HATA] Docker rate_limit_cache_table olusturulamadi.
    pause
    exit /b 1
)

%COMPOSE_CMD% up -d web
if errorlevel 1 (
    echo [HATA] Docker web servisi baslatilamadi.
    pause
    exit /b 1
)

echo.
echo Docker kurulum tamamlandi.
echo Panel: http://127.0.0.1:%APP_PORT%/yonetim-sistemi/
echo Giris: Nyancat / demo1234
echo Workbench Docker DB: 127.0.0.1 port 3307, root / 123
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:%APP_PORT%/yonetim-sistemi/'"
pause
exit /b 0

REM ============================================================
REM 5) DOCKER MEVCUT KURULUMU BASLATMA
REM ============================================================

:start_docker
call :find_compose
if errorlevel 1 exit /b 1

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
REM 6) LOCAL SUNUCU BASLATMA
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
echo Sunucuyu kapatmak icin bu pencerede Ctrl+C yapabilirsiniz.
echo.

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://%HOST%:%PORT%/yonetim-sistemi/'"
"%PYTHON_EXE%" manage.py runserver %HOST%:%PORT%

pause
exit /b 0

REM ============================================================
REM 7) YARDIMCI FONKSIYONLAR
REM ============================================================

:find_python
set "PYTHON_CMD="
if defined PYTHON_BOOTSTRAP (
    set "PYTHON_CMD="%PYTHON_BOOTSTRAP%""
    goto :python_found
)
if exist "%~dp0..\WEB\venv\Scripts\python.exe" (
    set "PYTHON_CMD="%~dp0..\WEB\venv\Scripts\python.exe""
    goto :python_found
)
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto :python_found
)
python -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_found
)
echo [HATA] Python 3 bulunamadi.
echo Python yoksa https://www.python.org/downloads/ adresinden Python 3 kurun.
echo Kurulumda "Add python.exe to PATH" seceneginin isaretli olmasi onerilir.
pause
exit /b 1

:python_found
exit /b 0

:find_mysql
set "MYSQL_EXE="
for /f "delims=" %%I in ('where mysql 2^>nul') do if not defined MYSQL_EXE set "MYSQL_EXE=%%I"
for /d %%D in ("C:\Program Files\MySQL\MySQL Server *") do if not defined MYSQL_EXE if exist "%%~fD\bin\mysql.exe" set "MYSQL_EXE=%%~fD\bin\mysql.exe"
for /d %%D in ("C:\Program Files\MySQL\MySQL Workbench *") do if not defined MYSQL_EXE if exist "%%~fD\mysql.exe" set "MYSQL_EXE=%%~fD\mysql.exe"
if not defined MYSQL_EXE if exist "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" set "MYSQL_EXE=C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
if not defined MYSQL_EXE if exist "C:\Program Files\MySQL\MySQL Workbench 8.0\mysql.exe" set "MYSQL_EXE=C:\Program Files\MySQL\MySQL Workbench 8.0\mysql.exe"
if not defined MYSQL_EXE (
    echo [HATA] mysql.exe bulunamadi.
    echo MySQL Server/Workbench kurulu degilse Docker Desktop acik halde baslat.bat'i tekrar calistirin.
    pause
    exit /b 1
)
exit /b 0

:find_compose
where docker >nul 2>nul
if errorlevel 1 (
    echo [HATA] Docker bulunamadi.
    pause
    exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
    echo [HATA] Docker Desktop kapali gorunuyor.
    echo Docker Desktop'i acin ve "Docker Desktop is running" durumunu bekleyin.
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
    echo [HATA] Docker Compose bulunamadi. Docker Desktop'i guncelleyin.
    pause
    exit /b 1
)
exit /b 0

:docker_pick_port
call :port_free "%APP_PORT%"
if not errorlevel 1 exit /b 0
echo [UYARI] 127.0.0.1:%APP_PORT% portu dolu. Docker icin bos port araniyor...
for /L %%P in (8002,1,8010) do (
    call :port_free "%%P"
    if not errorlevel 1 (
        set "APP_PORT=%%P"
        exit /b 0
    )
)
echo [HATA] 8001-8010 arasinda bos port bulunamadi.
echo Baska bir port secmek icin:
echo   set APP_PORT=8020
echo   baslat.bat
pause
exit /b 1

:port_free
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalAddress '%HOST%' -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>nul
exit /b %ERRORLEVEL%
