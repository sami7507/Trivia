#!/usr/bin/env bash
# One-click launcher for macOS/Linux (run after: pip install -r requirements.txt)
set -e
[ -f model/artifacts/triage_model.pkl ] || python model/train.py
export OTP_DEV_ECHO=true   # local demo: show the SMS code on screen
uvicorn backend.main:app --port 8000 &
API_PID=$!
trap "kill $API_PID" EXIT
sleep 4
BACKEND_URL=http://localhost:8000 streamlit run frontend/app.py
