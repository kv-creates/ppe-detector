#!/bin/bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &
sleep 3
streamlit run src/ui/app.py --server.port 8501 --server.address 127.0.0.1
