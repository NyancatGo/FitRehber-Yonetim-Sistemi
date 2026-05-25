@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "DB_NAME=fitrehber_yonetim_demo"
set "MYSQL_ROOT_PASSWORD=123"

where docker >nul 2>nul
if errorlevel 1 (
    echo [HATA] Docker bulunamadi. Docker Desktop kurulu ve calisir durumda olmali.
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

docker compose run --rm web python manage.py createcachetable rate_limit_cache_table

docker compose exec -T db mysql -uroot -p%MYSQL_ROOT_PASSWORD% --default-character-set=utf8mb4 %DB_NAME% < "sql\fitrehber_db.sql"
if errorlevel 1 exit /b 1

docker compose exec -T db mysql -uroot -p%MYSQL_ROOT_PASSWORD% --default-character-set=utf8mb4 %DB_NAME% < "sql\demo_data.sql"
if errorlevel 1 exit /b 1

docker compose up -d web
if errorlevel 1 exit /b 1

echo.
echo Docker kurulum tamamlandi.
echo Uygulama: http://127.0.0.1:8001/
echo Panel:    http://127.0.0.1:8001/yonetim-sistemi/
echo Giris:    Nyancat / demo1234
echo Workbench Docker DB: 127.0.0.1 port 3307, root / 123
pause
