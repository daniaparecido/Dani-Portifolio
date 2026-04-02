@echo off
cd /d "%~dp0"
echo Installing yt-dlp...
venv\Scripts\pip.exe install yt-dlp
echo.
echo Done!
pause
