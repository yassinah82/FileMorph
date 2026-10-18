@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo Installing FileMorph Context Menu into Windows Explorer...
echo ========================================================

python main.py --install-menu

echo.
pause
