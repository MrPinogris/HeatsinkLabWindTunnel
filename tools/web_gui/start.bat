@echo off
echo Installing dependencies (offline)...
python -m pip install --no-index --find-links wheels -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Dependency install failed.
    echo Make sure Python 3.12, 3.13 or 3.14 (64-bit) is installed.
    pause
    exit /b 1
)
echo Starting server...
python server.py
pause
