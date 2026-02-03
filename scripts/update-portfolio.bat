@echo off
echo ============================================
echo PORTFOLIO UPDATE SCRIPT
echo ============================================
echo.
echo This script will:
echo   1. Sync data from Google Sheet
echo   2. Download missing videos and thumbnails
echo   3. Create preview clips
echo.

cd /d "%~dp0.."

python scripts/sync_from_sheet.py --populate --download

echo.
echo ============================================
echo UPDATE COMPLETE!
echo ============================================
echo.
pause
