#!/bin/sh
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
echo "Starting the save editor at http://localhost:8000"
( sleep 2; open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null ) &
python3 app.py
