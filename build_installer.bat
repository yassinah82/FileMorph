@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo Building FileMorph Standalone Installer Wizard...
echo ========================================================

python build_installer.py

echo.
pause
