@echo off
echo Sugarcane Germination Analyzer
echo ================================
echo.

cd /d "%~dp0"

:: Create venv if it doesn't exist
if not exist "venv\" (
    echo Setting up virtual environment for the first time...
    py -3.12 -m venv venv
    call venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
    echo Setup complete.
    echo.
) else (
    call venv\Scripts\activate
)

echo Starting app...
echo When ready, your browser will open automatically.
echo To stop the app, press Ctrl+C or close this window.
echo.

streamlit run app.py

pause
