@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "DB_NAME=fitrehber_yonetim_demo"
set "APP_DB_USER=fitrehber_demo"
set "APP_DB_PASS=FitRehberDemo2026!"

echo ============================================================
echo FitRehber Yonetim Sistemi - Tek Komut Local Kurulum
echo ============================================================
echo.
echo Bu kurulum yerel MySQL Server/Workbench icindir.
echo MySQL root bilgisi sadece demo DB ve demo kullanici olusturmak icin kullanilir.
echo.

if not defined MYSQL_ROOT_USER set /p MYSQL_ROOT_USER=MySQL yonetici kullanici adi [root]:
if "%MYSQL_ROOT_USER%"=="" set "MYSQL_ROOT_USER=root"

if not defined MYSQL_ROOT_PASS set /p MYSQL_ROOT_PASS=MySQL yonetici sifresi [123]:
if "%MYSQL_ROOT_PASS%"=="" set "MYSQL_ROOT_PASS=123"

set "MYSQL_EXE="
for /f "delims=" %%I in ('where mysql 2^>nul') do if not defined MYSQL_EXE set "MYSQL_EXE=%%I"
if not defined MYSQL_EXE if exist "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" set "MYSQL_EXE=C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
if not defined MYSQL_EXE if exist "C:\Program Files\MySQL\MySQL Workbench 8.0\mysql.exe" set "MYSQL_EXE=C:\Program Files\MySQL\MySQL Workbench 8.0\mysql.exe"

if not defined MYSQL_EXE (
    echo [HATA] mysql.exe bulunamadi.
    echo MySQL Server 8.0 veya MySQL Workbench kurulu oldugundan emin olun.
    pause
    exit /b 1
)

echo.
echo [1/8] Python sanal ortami hazirlaniyor...
if not exist ".venv\Scripts\python.exe" (
    if defined PYTHON_BOOTSTRAP (
        "%PYTHON_BOOTSTRAP%" -m venv .venv
    ) else if exist "%~dp0..\WEB\venv\Scripts\python.exe" (
        "%~dp0..\WEB\venv\Scripts\python.exe" -m venv .venv
    ) else (
        where py >nul 2>nul
        if "%ERRORLEVEL%"=="0" (
        py -3 -m venv .venv
        ) else (
            python -m venv .venv
        )
    )
    if errorlevel 1 (
        echo [HATA] Python sanal ortami olusturulamadi. Python 3 kurulu mu?
        echo Python kuruluysa ama PATH icinde degilse su sekilde calistirabilirsiniz:
        echo set PYTHON_BOOTSTRAP=C:\Python311\python.exe
        echo kurulum.bat
        pause
        exit /b 1
    )
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

echo.
echo [2/8] Python paketleri kuruluyor...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo [3/8] Guvenli local .env hazirlaniyor...
if not exist ".env" (
    copy ".env.example" ".env" >nul
) else (
    echo .env zaten var, korunuyor.
)

echo.
echo [4/8] MySQL baglantisi kontrol ediliyor...
"%MYSQL_EXE%" -u"%MYSQL_ROOT_USER%" -p"%MYSQL_ROOT_PASS%" --default-character-set=utf8mb4 -e "SELECT VERSION();" >nul
if errorlevel 1 (
    echo [HATA] MySQL baglantisi basarisiz. Kullanici adi/sifreyi kontrol edin.
    pause
    exit /b 1
)

echo.
echo [5/8] Demo veritabani ve uygulama kullanicisi olusturuluyor...
"%MYSQL_EXE%" -u"%MYSQL_ROOT_USER%" -p"%MYSQL_ROOT_PASS%" --default-character-set=utf8mb4 -e "DROP DATABASE IF EXISTS `%DB_NAME%`; CREATE DATABASE `%DB_NAME%` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS '%APP_DB_USER%'@'%%' IDENTIFIED BY '%APP_DB_PASS%'; ALTER USER '%APP_DB_USER%'@'%%' IDENTIFIED BY '%APP_DB_PASS%'; GRANT ALL PRIVILEGES ON `%DB_NAME%`.* TO '%APP_DB_USER%'@'%%'; FLUSH PRIVILEGES;"
if errorlevel 1 (
    echo [HATA] Demo veritabani olusturulamadi.
    pause
    exit /b 1
)

echo.
echo [6/8] Django migration ve cache tablosu kuruluyor...
"%PYTHON_EXE%" manage.py migrate --noinput
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" manage.py createcachetable rate_limit_cache_table
if errorlevel 1 (
    echo Cache tablosu zaten varsa bu uyari yok sayilabilir.
)

echo.
echo [7/8] Stored Procedure / Function / Trigger omurgasi uygulaniyor...
"%MYSQL_EXE%" -u"%MYSQL_ROOT_USER%" -p"%MYSQL_ROOT_PASS%" --default-character-set=utf8mb4 "%DB_NAME%" < "sql\fitrehber_db.sql"
if errorlevel 1 (
    echo [HATA] sql\fitrehber_db.sql uygulanamadi.
    pause
    exit /b 1
)

echo.
echo [8/8] Sanitize demo verisi yukleniyor...
"%MYSQL_EXE%" -u"%MYSQL_ROOT_USER%" -p"%MYSQL_ROOT_PASS%" --default-character-set=utf8mb4 "%DB_NAME%" < "sql\demo_data.sql"
if errorlevel 1 (
    echo [HATA] sql\demo_data.sql yuklenemedi.
    pause
    exit /b 1
)

echo.
echo Son kontrol yapiliyor...
"%PYTHON_EXE%" manage.py check
if errorlevel 1 exit /b 1

echo.
echo ============================================================
echo Kurulum tamamlandi.
echo ============================================================
echo Panel: http://127.0.0.1:8001/yonetim-sistemi/
echo Giris: Nyancat / demo1234
echo Workbench DB: %DB_NAME%
echo Workbench uygulama kullanicisi: %APP_DB_USER% / %APP_DB_PASS%
echo.
echo Not: 8001 portu doluysa baslat.bat otomatik olarak 8002-8010 arasinda bos port secer.
echo.
echo Sunucuyu acmak icin baslat.bat calistirin.
pause
