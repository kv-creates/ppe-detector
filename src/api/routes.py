"""API routes: /api/detect, /api/violations, /api/kpis, /api/health."""
from __future__ import annotations

import datetime
import io
import json
import logging
import os

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from src.api import db
from src.api.schemas import Detection, PredictionResponse, ViolationRecord
from src.inference.predictor import VIOLATIONS, PPEPredictor

log = logging.getLogger("routes")
router = APIRouter(prefix="/api")

_predictor: PPEPredictor | None = None


def get_predictor() -> PPEPredictor:
    global _predictor
    if _predictor is None:
        _predictor = PPEPredictor()
    return _predictor


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/detect", response_model=PredictionResponse)
async def detect(camera_id: str = "cam-01", file: UploadFile = File(...)):
    try:
        raw = await file.read()
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("could not decode image")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"invalid image: {exc}") from exc
    out = get_predictor().predict(img, camera_id=camera_id)
    # persist violations + snapshot
    if out["violation"]:
        snap_dir = os.path.abspath("data/violations")
        os.makedirs(snap_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        snap = os.path.join(snap_dir, f"{camera_id}_{ts}.jpg")
        cv2.imwrite(snap, img)
        session = db.get_session()
        try:
            for d in out["detections"]:
                if d["class_name"] in VIOLATIONS:
                    session.add(db.Violation(
                        timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
                        camera_id=camera_id, class_name=d["class_name"],
                        conf=d["conf"], zone=d["zone"], snapshot_path=snap))
            session.commit()
        finally:
            session.close()
    out["detections"] = [Detection(**d) for d in out["detections"]]
    return PredictionResponse(**out)


@router.get("/violations", response_model=list[ViolationRecord])
def list_violations(camera_id: str | None = Query(None),
                    class_name: str | None = Query(None),
                    limit: int = Query(200, le=2000)):
    session = db.get_session()
    try:
        q = session.query(db.Violation).order_by(db.Violation.id.desc())
        if camera_id:
            q = q.filter(db.Violation.camera_id == camera_id)
        if class_name:
            q = q.filter(db.Violation.class_name == class_name)
        return [ViolationRecord.model_validate(v) for v in q.limit(limit).all()]
    finally:
        session.close()


@router.get("/violations/{vid}/snapshot")
def violation_snapshot(vid: int):
    session = db.get_session()
    try:
        v = session.query(db.Violation).filter(db.Violation.id == vid).first()
    finally:
        session.close()
    if not v or not v.snapshot_path or not os.path.exists(v.snapshot_path):
        raise HTTPException(404, "snapshot not found")
    return FileResponse(v.snapshot_path, media_type="image/jpeg")


@router.get("/kpis")
def kpis():
    for p in ("reports/final_metrics.json", "reports/local_metrics.json",
              "reports/colab_metrics.json"):
        if os.path.exists(p):
            with open(p) as fh:
                return {"source_file": p, "kpis": json.load(fh)}
    raise HTTPException(503, "metrics not computed yet; run src.utils.kpi")
