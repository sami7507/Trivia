@echo off
REM One-click launcher for Windows (run after: pip install -r requirements.txt)
if not exist model\artifacts\triage_model.pkl python model\train.py
REM Local demo: show the SMS code on screen instead of sending a real SMS
set OTP_DEV_ECHO=true
start "Triavia API" cmd /k uvicorn backend.main:app --port 8000
timeout /t 4 >nul
set BACKEND_URL=http://localhost:8000
streamlit run frontend/app.py
