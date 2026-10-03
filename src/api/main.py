"""FastAPI application entrypoint. Run:
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api import db
from src.api.routes import router

db.init_db()

app = FastAPI(title="PPE Sentinel API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8501", "http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

os.makedirs("data/violations", exist_ok=True)
app.mount("/static", StaticFiles(directory="data/violations"), name="static")


@app.get("/")
def root():
    return {"service": "ppe-sentinel", "docs": "/docs", "health": "/api/health"}
