@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo Compiling FileMorph Standalone Windows Application...
echo ========================================================

python build_exe.py

echo.
pause
