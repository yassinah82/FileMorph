@echo off
setlocal
cd /d "%~dp0"
echo =========================================================================
echo Enabling FileMorph on Windows 11 Main Right-Click Menu...
echo (Bypasses "Show more options" so FileMorph shows directly on right-click)
echo =========================================================================

python main.py --enable-win11-main

echo.
echo Windows Explorer has been refreshed. FileMorph is now on the main menu!
pause
