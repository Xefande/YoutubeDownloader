@echo off
setlocal EnableExtensions

set "APPNAME=YTDownloader"
set "SRC=%~dp0app"
set "TARGET=%LOCALAPPDATA%\%APPNAME%"

echo ========================================
echo %APPNAME% installer
echo Target Folder: "%TARGET%"
echo ========================================

if not exist "%SRC%\%APPNAME%.exe" (
  echo Error: Cant find %APPNAME%.exe-t
  echo Check that: "%SRC%"
  pause
  exit /b 1
)

if not exist "%TARGET%" mkdir "%TARGET%"

echo Copy...
xcopy "%SRC%\*" "%TARGET%\" /E /I /Y >nul

echo Create shortcut (Desktop + Start Menu)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$app='%TARGET%\%APPNAME%.exe';" ^
  "$wd='%TARGET%';" ^
  "$ws=New-Object -ComObject WScript.Shell;" ^
  "$desktop=[Environment]::GetFolderPath('Desktop');" ^
  "$lnk=$ws.CreateShortcut($desktop+'\%APPNAME%.lnk');" ^
  "$lnk.TargetPath=$app; $lnk.WorkingDirectory=$wd; $lnk.IconLocation=$app; $lnk.Save();" ^
  "$sm=[Environment]::GetFolderPath('StartMenu');" ^
  "$prog=Join-Path $sm 'Programs\%APPNAME%'; if(!(Test-Path $prog)){New-Item -ItemType Directory -Path $prog | Out-Null};" ^
  "$lnk2=$ws.CreateShortcut((Join-Path $prog '%APPNAME%.lnk')); " ^
  "$lnk2.TargetPath=$app; $lnk2.WorkingDirectory=$wd; $lnk2.IconLocation=$app; $lnk2.Save();"

echo.
echo Done! Enjoy: "%APPNAME%"
echo (Folder: "%TARGET%")
echo ....... with love by Xefande
echo.
pause
exit /b 0
