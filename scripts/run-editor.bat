@echo off
REM Launch the local portfolio editor.
REM Usage: scripts\run-editor.bat
REM   Opens http://127.0.0.1:8765/ in the default browser. Ctrl+C to stop.

cd /d "%~dp0.."
python scripts\editor-server.py %*
