@echo off
REM Geriye donuk uyumluluk icin: BASLA.bat artik dogrudan baslat.bat'i cagirir.
REM Tek tikla calistirilmasi gereken dosya: baslat.bat
call "%~dp0baslat.bat" %*
exit /b %ERRORLEVEL%
