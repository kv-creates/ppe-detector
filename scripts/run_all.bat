@echo off
REM Full pipeline (Windows equivalent of run_all.sh)
python -m src.data.download || exit /b 1
python -m src.data.clean || exit /b 1
python -m src.data.merge || exit /b 1
python -m src.data.split || exit /b 1
python -m src.data.metadata || exit /b 1
python -m src.utils.viz || exit /b 1
python -m src.training.local_eval || exit /b 1
start /min python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
timeout /t 5 >nul
start /min python -m streamlit run src/ui/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
timeout /t 10 >nul
python -c "from src.utils.screenshot import screenshot_pages; screenshot_pages()" || exit /b 1
python -m pytest tests/ -v || exit /b 1
python -m src.utils.kpi || exit /b 1
echo DONE. Report: reports/final_report.md
