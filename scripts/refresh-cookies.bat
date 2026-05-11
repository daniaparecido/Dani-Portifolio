@echo off
REM One-click wrapper for refresh-cookies.ps1
REM Usage: refresh-cookies.bat [browser]
REM   refresh-cookies.bat          (defaults to chrome)
REM   refresh-cookies.bat edge
REM   refresh-cookies.bat firefox

setlocal
set BROWSER=%~1
if "%BROWSER%"=="" set BROWSER=chrome

powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0refresh-cookies.ps1" -Browser %BROWSER%
if errorlevel 1 (
    echo.
    echo Cookie refresh failed. Common causes:
    echo   - Browser is still open (close it and retry)
    echo   - Not logged into Instagram in that browser
    echo   - gh CLI not authenticated (run: gh auth login)
    pause
    exit /b 1
)

echo.
pause
