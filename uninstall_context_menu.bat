@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo Removing FileMorph Context Menu from Windows Explorer...
echo ========================================================

python main.py --uninstall-menu

echo.
pause
