@echo off
setlocal enabledelayedexpansion
title AI-Chatbot Streamlit Launcher

:: 1. Automatically switch to the directory where run.bat is located
cd /d "%~dp0"

echo ===================================================
echo           AI Multimodal Chatbot Launcher          
echo ===================================================
echo.

:: 2. Check whether the virtual environment exists
set "VENV_ACTIVATE="

if exist "venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=venv\Scripts\activate.bat"
) else if exist "..\venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=..\venv\Scripts\activate.bat"
)

if "%VENV_ACTIVATE%"=="" (
    echo [ERROR] Virtual environment not found.
    echo Please create the venv first by running:
    echo     python -m venv venv
    echo.
    pause
    exit /b 1
)

:: 3. Activate virtual environment
echo Activating virtual environment (%VENV_ACTIVATE%)...
call "%VENV_ACTIVATE%"
echo.

:: 4. Check whether Streamlit is installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Streamlit is not installed in the virtual environment.
    echo Please install the required dependencies by running:
    echo     pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: 5. Run Streamlit application
echo Launching Streamlit AI Chatbot...
echo.
python -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Streamlit application encountered an issue.
    pause
)
