@echo off
REM -------------------------------
REM Cocoon Preview Installer & Launcher
REM -------------------------------

REM Check Python installation
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python is not installed. Please install Python 3.10+ and ensure python is in PATH.
    pause
    exit /b 1
)

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install dependencies
python -m pip install --upgrade Pillow av

REM Run the program
python "app.py"

pause