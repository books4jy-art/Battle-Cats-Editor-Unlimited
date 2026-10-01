@echo off
cd /d "%~dp0"
echo Installing requirements (first run takes a minute)...
py -m pip install -q -r requirements.txt || python -m pip install -q -r requirements.txt
echo.
echo Starting the save editor at http://localhost:8000
start "" http://localhost:8000
py app.py || python app.py
pause
