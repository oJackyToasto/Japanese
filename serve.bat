@echo off
cd /d "%~dp0"
echo Serving at http://localhost:8000
echo.
python -m http.server 8000
pause