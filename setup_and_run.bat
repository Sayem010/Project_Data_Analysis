@echo off
REM setup_and_run.bat
REM Run this from the project root on Windows

echo ============================================
echo  QDArchive Seeding Pipeline - Setup + Run
echo  Student ID: 23455702
echo ============================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Create venv if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Run pipeline
echo.
echo Starting pipeline...
python main.py

echo.
echo ============================================
echo  Done! Check 23455702-seeding.db
echo ============================================
pause
