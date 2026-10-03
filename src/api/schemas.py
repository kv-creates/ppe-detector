"""Pydantic schemas for the PPE Sentinel API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Detection(BaseModel):
    class_id: int
    class_name: str
    conf: float
    bbox_xyxy: list[float]
    zone: str = Field(description="red|yellow|green hazard zone")


class PredictionResponse(BaseModel):
    camera_id: str
    detections: list[Detection]
    violation: bool
    num_detections: int
    latency_ms: float
    model: str
    placeholder: bool = False


class ViolationRecord(BaseModel):
    id: int
    timestamp: str
    camera_id: str
    class_name: str
    conf: float
    zone: str
    snapshot_path: str | None = None

    model_config = {"from_attributes": True}


class KPIResponse(BaseModel):
    kpis: dict
