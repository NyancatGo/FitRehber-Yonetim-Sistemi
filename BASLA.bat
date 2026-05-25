@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo FitRehber Yonetim Sistemi - Kolay Baslat
echo ============================================================
echo.
echo Bu dosya GitHub ZIP indirildikten sonra ilk calistirilmesi
echo onerilen dosyadir.
echo.
echo Tercih sirasi:
echo 1) Docker Desktop acik ve calisirsa otomatik Docker kurulumu
echo 2) Docker yoksa veya kullanilmayacaksa local MySQL kurulumu
echo.

where docker >nul 2>nul
if errorlevel 1 goto local_mysql

docker info >nul 2>nul
if errorlevel 1 goto docker_not_running

echo Docker Desktop calisiyor. Docker kurulum yolu kullanilacak.
echo.
call docker-kurulum.bat
if errorlevel 1 (
    echo.
    echo Docker kurulum yolu tamamlanamadi.
    choice /C ML /N /M "M=Local MySQL kurulumunu dene, L=Cikis: "
    if errorlevel 2 exit /b 1
    goto local_mysql
)
exit /b 0

:docker_not_running
echo Docker komutu bulundu ama Docker Desktop su an calismiyor.
echo.
echo En kolay yol:
echo - Docker Desktop uygulamasini acin.
echo - "Docker Desktop is running" durumunu bekleyin.
echo - Sonra BASLA.bat dosyasini tekrar calistirin.
echo.
choice /C ML /N /M "M=Local MySQL kurulumunu dene, L=Cikis: "
if errorlevel 2 exit /b 1
goto local_mysql

:local_mysql
echo Local MySQL kurulum yolu kullanilacak.
echo Bu yol icin MySQL yonetici kullanici adi ve sifresi gerekir.
echo MySQL sifresini bilmiyorsaniz Docker Desktop'i acip BASLA.bat'i tekrar calistirin.
echo.
call kurulum.bat
if errorlevel 1 exit /b %ERRORLEVEL%

call baslat.bat
exit /b %ERRORLEVEL%
