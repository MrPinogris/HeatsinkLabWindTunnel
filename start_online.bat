@echo off
cd /d "%~dp0tools\web_gui"
echo Installing dependencies (online)...
python -m pip install -r requirements.txt
if errorlevel 1 goto install_error
echo Starting server...
python server.py
pause
exit /b 0

:install_error
echo.
echo ERROR: Dependency install failed.
echo Make sure Python 3.12, 3.13 or 3.14 (64-bit) is installed and that this PC has internet access.
pause
exit /b 1
