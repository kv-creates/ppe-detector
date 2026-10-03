@echo off
REM Launch API + UI (Windows equivalent of start.sh)
start /min python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
timeout /t 3 >nul
python -m streamlit run src/ui/app.py --server.port 8501 --server.address 127.0.0.1
