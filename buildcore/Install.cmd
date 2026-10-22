@echo off
setlocal EnableExtensions
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Mode Install
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Installation failed. Close YouTube Downloader and check the error above.
pause
exit /b %RESULT%
