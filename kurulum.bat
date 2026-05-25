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
echo Bu dosya ilk kurulum icindir. Kurulum bittikten sonra siteyi
echo acmak icin gunluk olarak baslat.bat calistirilir.
echo.
echo Bu kurulum yerel MySQL Server/Workbench icindir.
echo Sadece "%DB_NAME%" demo veritabani sifirlanir; baska semalara dokunulmaz.
echo MySQL root bilgisi sadece demo DB ve demo kullanici olusturmak icin kullanilir.
echo.
echo MySQL yonetici sifresini bilmiyorsaniz bu pencereyi kapatin
echo ve Docker Desktop kuruluysa docker-kurulum.bat dosyasini kullanin.
echo.

if not defined MYSQL_ROOT_USER set /p MYSQL_ROOT_USER=MySQL yonetici kullanici adi [root]:
if "%MYSQL_ROOT_USER%"=="" set "MYSQL_ROOT_USER=root"

echo.
echo Not: Sifre bilinmiyorsa Enter'a basmak yerine Docker yolunu kullanin.
if not defined MYSQL_ROOT_PASS set /p MYSQL_ROOT_PASS=MySQL yonetici sifresi [123]:
if "%MYSQL_ROOT_PASS%"=="" set "MYSQL_ROOT_PASS=123"

set "MYSQL_EXE="
for /f "delims=" %%I in ('where mysql 2^>nul') do if not defined MYSQL_EXE set "MYSQL_EXE=%%I"
for /d %%D in ("C:\Program Files\MySQL\MySQL Server *") do if not defined MYSQL_EXE if exist "%%~fD\bin\mysql.exe" set "MYSQL_EXE=%%~fD\bin\mysql.exe"
for /d %%D in ("C:\Program Files\MySQL\MySQL Workbench *") do if not defined MYSQL_EXE if exist "%%~fD\mysql.exe" set "MYSQL_EXE=%%~fD\mysql.exe"
if not defined MYSQL_EXE if exist "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" set "MYSQL_EXE=C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
if not defined MYSQL_EXE if exist "C:\Program Files\MySQL\MySQL Workbench 8.0\mysql.exe" set "MYSQL_EXE=C:\Program Files\MySQL\MySQL Workbench 8.0\mysql.exe"

if not defined MYSQL_EXE (
    echo [HATA] mysql.exe bulunamadi.
    echo MySQL Server 8.0 veya MySQL Workbench kurulu oldugundan emin olun.
    echo MySQL kurulu degilse Docker Desktop ile docker-kurulum.bat kullanilabilir.
    pause
    exit /b 1
)

echo.
echo [1/9] Python sanal ortami hazirlaniyor...
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
        echo Python yoksa https://www.python.org/downloads/ adresinden Python 3 kurun.
        echo Kurulumda "Add python.exe to PATH" seceneginin isaretli olmasi onerilir.
        echo Python kuruluysa ama PATH icinde degilse su sekilde calistirabilirsiniz:
        echo set PYTHON_BOOTSTRAP=C:\Python311\python.exe
        echo kurulum.bat
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
    echo Sifreyi bilmiyorsaniz bu kurulumu kapatip docker-kurulum.bat kullanin.
    echo Docker yolu kendi MySQL container'ini acar ve lokal root sifresi istemez.
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
echo ============================================================
echo Kurulum tamamlandi.
echo ============================================================
echo Panel: http://127.0.0.1:8001/yonetim-sistemi/
echo Giris: Nyancat / demo1234
echo Workbench DB: %DB_NAME%
echo Workbench uygulama kullanicisi: %APP_DB_USER% / %APP_DB_PASS%
echo.
echo Not: 8001 portu doluysa baslat.bat otomatik olarak 8002-8010 arasinda bos port secer.
echo Tarayicida mutlaka baslat.bat ekraninda yazan URL acilmalidir.
echo.
echo Sunucuyu acmak icin baslat.bat calistirin.
pause
