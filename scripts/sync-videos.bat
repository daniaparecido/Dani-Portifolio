@echo off
cd /d "%~dp0.."
python scripts/sync_from_sheet.py %*
pause
