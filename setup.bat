@echo off
rem ScrapeLite — one-time setup. Creates the virtual environment, installs
rem packages, and makes sure Ollama + the model are present.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
echo.
pause
