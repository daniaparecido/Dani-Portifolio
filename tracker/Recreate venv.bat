@echo off
cd /d "%~dp0"
echo Removing old venv...
rmdir /s /q venv
echo.
echo Creating new virtual environment...
python -m venv venv
echo.
echo Installing dependencies...
venv\Scripts\pip.exe install -r requirements.txt
echo.
echo Done!
pause
