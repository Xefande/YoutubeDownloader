@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1

if not exist ".venv-build\Scripts\python.exe" (
    py -3.12 -m venv ".venv-build"
    if errorlevel 1 goto failed
)
".venv-build\Scripts\python.exe" -c "import platform, struct, sys; sys.exit(0 if sys.version_info[:2] == (3, 12) and sys.platform == 'win32' and struct.calcsize('P') == 8 and platform.machine().lower() in ('amd64', 'x86_64') else 'Build requires Windows x64 and Python 3.12 x64.')"
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" -m pip install --disable-pip-version-check -r "requirements-build.txt"
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" -B "build.py"
exit /b %ERRORLEVEL%

:failed
echo Build failed. Check the error above; Python 3.12 x64 must be installed.
exit /b 1
