@echo off
echo Starting Sugarcane Germination Analyzer...
echo.
echo When the app is ready, it will open automatically in your browser.
echo To stop the app, close this window or press Ctrl+C.
echo.

cd /d "%~dp0"
call ..\venv\Scripts\activate
streamlit run app.py

pause
