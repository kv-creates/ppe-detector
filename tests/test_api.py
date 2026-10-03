"""API tests (live server on 127.0.0.1:8000): health, detect, kpis."""
import glob
import os

import httpx

BASE = "http://127.0.0.1:8000"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_health():
    r = httpx.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_detect():
    exts = (".jpg", ".jpeg", ".png")
    img = sorted(f for f in glob.glob(os.path.join(ROOT, "data/processed/images/test/*"))
                 if f.lower().endswith(exts))[0]
    with open(img, "rb") as fh:
        r = httpx.post(f"{BASE}/api/detect", params={"camera_id": "cam-01"},
                       files={"file": ("t.jpg", fh, "image/jpeg")}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert "detections" in d and "violation" in d and "latency_ms" in d


def test_kpis_and_violations():
    r = httpx.get(f"{BASE}/api/kpis", timeout=10)
    assert r.status_code == 200
    r = httpx.get(f"{BASE}/api/violations?limit=5", timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
