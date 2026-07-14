@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m local.main
if errorlevel 1 pause
