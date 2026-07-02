@echo off
echo Starting Sugarcane Germination Analyzer (Interactive)...
echo.
echo When ready, open your browser and go to:
echo   http://localhost:5000
echo.
echo To stop the app, close this window or press Ctrl+C.
echo.

cd /d "%~dp0"
call ..\venv\Scripts\activate
python server.py

pause
