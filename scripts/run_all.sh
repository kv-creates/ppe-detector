#!/bin/bash
set -e
python -m src.data.download
python -m src.data.clean
python -m src.data.merge
python -m src.data.split
python -m src.data.metadata
python -m src.utils.viz
python -m src.training.local_eval
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &
sleep 5
streamlit run src/ui/app.py --server.port 8501 --server.address 127.0.0.1 &
sleep 10
python -c "from src.utils.screenshot import screenshot_pages; screenshot_pages()"
pytest tests/ -v
python -m src.utils.kpi
echo "DONE. Report: reports/final_report.md"
