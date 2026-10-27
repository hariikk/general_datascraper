@echo off
rem ScrapeLite — double-click to launch the web app.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found - running setup first...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Setup did not complete. Please double-click setup.bat and read the messages.
    pause
    exit /b 1
)

.venv\Scripts\python.exe app.py
pause
