@echo off
setlocal EnableExtensions

set "APPNAME=YTDownloader"
set "TARGET=%LOCALAPPDATA%\%APPNAME%"

echo ========================================
echo %APPNAME% eltavolito
echo Torles: "%TARGET%"
echo ========================================

echo Parancsikonok torlese...
del "%USERPROFILE%\Desktop\%APPNAME%.lnk" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$sm=[Environment]::GetFolderPath('StartMenu');" ^
  "$prog=Join-Path $sm 'Programs\%APPNAME%';" ^
  "if(Test-Path $prog){Remove-Item -Recurse -Force $prog}"

echo Program mappa torlese...
if exist "%TARGET%" rmdir /S /Q "%TARGET%"

echo.
echo KESZ.
pause
exit /b 0
