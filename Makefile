.PHONY: data eda eval api ui shots test kpi report all

PY=python

data:
	$(PY) -m src.data.download
	$(PY) -m src.data.clean
	$(PY) -m src.data.merge
	$(PY) -m src.data.split
	$(PY) -m src.data.metadata

eda:
	$(PY) -m src.utils.viz

eval:
	$(PY) -m src.training.local_eval

api:
	uvicorn src.api.main:app --host 127.0.0.1 --port 8000

ui:
	streamlit run src/ui/app.py --server.port 8501 --server.address 127.0.0.1

shots:
	$(PY) -c "from src.utils.screenshot import screenshot_pages; screenshot_pages()"

test:
	pytest tests/ -v

kpi:
	$(PY) -m src.utils.kpi

all: data eda eval test kpi
