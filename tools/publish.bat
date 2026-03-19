@echo off
setlocal

:: ============================================================
::  publish.bat  –  Push public-facing files to the public repo
::  Run from anywhere inside the private repo
:: ============================================================

set PUBLIC_REPO=https://github.com/MrPinogris/HeatsinkLabWindTunnel-public.git
set TEMP_DIR=%TEMP%\heatlab_publish_%RANDOM%
set PRIVATE_ROOT=%~dp0..

:: Get current git hash for the commit message
for /f %%i in ('git -C "%PRIVATE_ROOT%" rev-parse --short HEAD') do set GIT_HASH=%%i

echo.
echo [publish] Private repo commit: %GIT_HASH%
echo [publish] Cloning public repo into temp folder...
echo.

git clone %PUBLIC_REPO% "%TEMP_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to clone public repo. Check the URL and your credentials.
    pause
    exit /b 1
)

:: ---- Copy files ----
echo [publish] Copying files...

xcopy /Y /I "%PRIVATE_ROOT%\src\main.cpp"              "%TEMP_DIR%\src\"
xcopy /Y /I "%PRIVATE_ROOT%\src\PIDController.cpp"     "%TEMP_DIR%\src\"
xcopy /Y /I "%PRIVATE_ROOT%\src\PIDController.h"       "%TEMP_DIR%\src\"
xcopy /Y /I "%PRIVATE_ROOT%\include\README"             "%TEMP_DIR%\include\"
xcopy /Y /I "%PRIVATE_ROOT%\lib\README"                 "%TEMP_DIR%\lib\"
xcopy /Y /I "%PRIVATE_ROOT%\platformio.ini"             "%TEMP_DIR%\"
xcopy /Y /I "%PRIVATE_ROOT%\README.md"                  "%TEMP_DIR%\"
xcopy /Y /I "%PRIVATE_ROOT%\tools\web_gui\server.py"          "%TEMP_DIR%\tools\web_gui\"
xcopy /Y /I "%PRIVATE_ROOT%\tools\web_gui\requirements.txt"   "%TEMP_DIR%\tools\web_gui\"
xcopy /Y /I "%PRIVATE_ROOT%\tools\web_gui\static\index.html"  "%TEMP_DIR%\tools\web_gui\static\"
xcopy /Y /I "%PRIVATE_ROOT%\tools\web_gui\MANUAL.md"          "%TEMP_DIR%\tools\web_gui\"

:: Write a trimmed .gitignore for the public repo
(
echo .pio/
echo .vscode/
echo logs/
echo pid_gui_state.json
echo __pycache__/
echo *.pyc
) > "%TEMP_DIR%\.gitignore"

:: ---- Commit and push ----
echo [publish] Committing and pushing...
cd /d "%TEMP_DIR%"
git add -A
git commit -m "chore: sync from private repo @ %GIT_HASH%"
git push origin main

if errorlevel 1 (
    echo [ERROR] Push failed.
    cd /d "%PRIVATE_ROOT%"
    rmdir /s /q "%TEMP_DIR%"
    pause
    exit /b 1
)

:: ---- Cleanup ----
cd /d "%PRIVATE_ROOT%"
rmdir /s /q "%TEMP_DIR%"

echo.
echo [publish] Done! Public repo updated.
echo    https://github.com/MrPinogris/HeatsinkLabWindTunnel-public
echo.
pause
