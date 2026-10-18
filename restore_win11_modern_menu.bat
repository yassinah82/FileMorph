@echo off
setlocal
cd /d "%~dp0"
echo =========================================================================
echo Restoring Default Windows 11 Modern Context Menu...
echo =========================================================================

python main.py --disable-win11-main

echo.
echo Windows Explorer has been refreshed. Default menu restored.
pause
