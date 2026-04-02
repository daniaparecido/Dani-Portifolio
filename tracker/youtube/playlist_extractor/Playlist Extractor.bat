@echo off
cd /d "%~dp0.."
start "" /B ..\venv\Scripts\pythonw.exe playlist_extractor\gui.py
