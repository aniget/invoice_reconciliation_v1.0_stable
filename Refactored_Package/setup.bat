@echo off
REM Quick Start Script for Invoice Reconciliation System (Windows)

echo ==========================================
echo Invoice Reconciliation System - Setup
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Python not found. Please install Python 3.7+
    pause
    exit /b 1
)

echo [OK] Python found
python --version

REM Install dependencies
echo.
echo Installing dependencies...
pip install -q -r requirements.txt

if %errorlevel% neq 0 (
    echo X Failed to install dependencies
    pause
    exit /b 1
)

echo [OK] Dependencies installed

REM Create directories
echo.
echo Creating directory structure...
if not exist "input_evd" mkdir input_evd
if not exist "input_pdf" mkdir input_pdf
if not exist "output" mkdir output

echo [OK] Directories created

echo.
echo ==========================================
echo [OK] Setup Complete!
echo ==========================================
echo.
echo To start the application:
echo   python app.py
echo.
echo Then open your browser to:
echo   http://localhost:7860
echo.
echo For help, see:
echo   README.md     - Quick start
echo   USER_GUIDE.md - Detailed usage
echo.
echo ==========================================
pause
