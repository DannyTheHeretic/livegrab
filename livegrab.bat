@echo off
cd /d "%~dp0" || (
  echo Could not open the Livegrab folder.
  pause
  exit /b 1
)

py -3 livegrab.py
if not errorlevel 1 exit /b 0

python livegrab.py
if not errorlevel 1 exit /b 0

echo.
echo Livegrab failed to start.
pause
exit /b 1
