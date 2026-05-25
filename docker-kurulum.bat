@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "DB_NAME=fitrehber_yonetim_demo"
set "MYSQL_ROOT_PASSWORD=123"
if not defined APP_PORT set "APP_PORT=8001"

echo ============================================================
echo FitRehber Yonetim Sistemi - Docker Kurulum
echo ============================================================
echo.
echo Bu yol MySQL root sifresi bilinmiyorsa veya lokal MySQL
echo ayarlariyla ugrasmak istenmiyorsa kullanilir.
echo Docker kendi MySQL container'ini acar; bilgisayardaki MySQL
echo kullanici adi veya sifresi gerekmez.
echo.
echo Gereken on kosul: Docker Desktop kurulu ve calisir durumda olmali.
echo.

call :port_free "%APP_PORT%"
if errorlevel 1 (
    echo [UYARI] 127.0.0.1:%APP_PORT% portu dolu. Docker icin bos port araniyor...
    for /L %%P in (8002,1,8010) do (
        call :port_free "%%P"
        if not errorlevel 1 (
            set "APP_PORT=%%P"
            goto :docker_port_selected
        )
    )
    echo [HATA] 8001-8010 arasinda bos port bulunamadi.
    echo Baska bir port secmek icin:
    echo set APP_PORT=8020
    echo docker-kurulum.bat
    pause
    exit /b 1
)

:docker_port_selected

where docker >nul 2>nul
if errorlevel 1 (
    echo [HATA] Docker bulunamadi. Docker Desktop kurulu ve calisir durumda olmali.
    echo Docker kullanmak istemiyorsaniz ve MySQL root sifresini biliyorsaniz kurulum.bat kullanin.
    pause
    exit /b 1
)

if not exist ".env" copy ".env.example" ".env" >nul

echo Docker DB sifirlaniyor ve servisler hazirlaniyor...
docker compose up -d db
if errorlevel 1 exit /b 1

echo MySQL container hazir olana kadar bekleniyor...
timeout /t 12 /nobreak >nul

docker compose exec -T db mysql -uroot -p%MYSQL_ROOT_PASSWORD% --default-character-set=utf8mb4 -e "DROP DATABASE IF EXISTS %DB_NAME%; CREATE DATABASE %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if errorlevel 1 exit /b 1

docker compose build web
if errorlevel 1 exit /b 1

docker compose run --rm web python manage.py migrate --noinput
if errorlevel 1 exit /b 1

docker compose exec -T db mysql -uroot -p%MYSQL_ROOT_PASSWORD% --default-character-set=utf8mb4 %DB_NAME% < "sql\fitrehber_db.sql"
if errorlevel 1 exit /b 1

docker compose exec -T db mysql -uroot -p%MYSQL_ROOT_PASSWORD% --default-character-set=utf8mb4 %DB_NAME% < "sql\demo_data.sql"
if errorlevel 1 exit /b 1

docker compose run --rm web python manage.py createcachetable rate_limit_cache_table
if errorlevel 1 exit /b 1

docker compose up -d web
if errorlevel 1 exit /b 1

echo.
echo Docker kurulum tamamlandi.
echo Uygulama: http://127.0.0.1:%APP_PORT%/
echo Panel:    http://127.0.0.1:%APP_PORT%/yonetim-sistemi/
echo Giris:    Nyancat / demo1234
echo Workbench Docker DB: 127.0.0.1 port 3307, root / 123
echo.
echo Tarayicida yukarida yazan Panel adresini acin.
echo Docker servislerini kapatmak icin: docker compose down
pause
exit /b 0

:port_free
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>nul
exit /b %ERRORLEVEL%
