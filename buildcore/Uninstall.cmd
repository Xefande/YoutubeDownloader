@echo off
setlocal EnableExtensions

set "APPNAME=YTDownloader"
set "TARGET=%LOCALAPPDATA%\%APPNAME%"

echo ========================================
echo %APPNAME% removal
echo Delete: "%TARGET%"
echo ========================================

echo Delete Shortcut...
del "%USERPROFILE%\Desktop\%APPNAME%.lnk" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$sm=[Environment]::GetFolderPath('StartMenu');" ^
  "$prog=Join-Path $sm 'Programs\%APPNAME%';" ^
  "if(Test-Path $prog){Remove-Item -Recurse -Force $prog}"

echo Delete folder...
if exist "%TARGET%" rmdir /S /Q "%TARGET%"

echo.
echo Done.
echo Thank you for using my tools.
echo .
echo Send me feedback https://www.linkedin.com/in/orovec
pause
exit /b 0
