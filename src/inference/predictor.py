"""PPEPredictor: loads a YOLO model once, predicts on images.

Weight resolution order (first existing file wins):
  1. models/checkpoints/yolov8_final/weights/best.pt  (promoted best)
  2. models/checkpoints/yolov8s_ppe/weights/best.pt    (Colab YOLOv8s)
  3. models/checkpoints/yolov8n_ppe/weights/best.pt    (Colab/smoke YOLOv8n)
  4. yolov8s.pt pretrained (COCO placeholder; person-only mapping)

.predict(image, camera_id) -> dict with detections + violation flag + zones.
Each detection: {class_id, class_name, conf, bbox_xyxy, zone}.
"""
from __future__ import annotations

import logging
import os
import time

import yaml

log = logging.getLogger("predictor")

CLASSES = ["person", "helmet", "vest", "no-helmet", "no-vest", "boots"]
VIOLATIONS = {"no-helmet", "no-vest"}

# COCO-pretrained fallback: only class 0 (person) is meaningful.
COCO_MAP = {0: "person"}


def load_app_cfg() -> dict:
    with open("configs/app.yaml") as fh:
        return yaml.safe_load(fh) or {}


class PPEPredictor:
    def __init__(self, weights: str | None = None, conf: float | None = None,
                 imgsz: int | None = None):
        from ultralytics import YOLO
        cfg = load_app_cfg()
        mcfg = cfg.get("model", {}) or {}
        cands = ([weights] if weights else []) + list(mcfg.get("candidates", []))
        self.weights_path, self.is_placeholder = None, True
        for c in cands:
            if c and os.path.exists(c):
                self.weights_path, self.is_placeholder = c, False
                break
        if self.weights_path is None:
            self.weights_path, self.is_placeholder = "yolov8s.pt", True
            log.warning("No PPE weights found; using COCO placeholder yolov8s.pt")
        self.conf = conf if conf is not None else float(mcfg.get("conf_threshold", 0.35))
        self.imgsz = imgsz or int(mcfg.get("imgsz", 640))
        log.info("Loading %s (placeholder=%s)", self.weights_path, self.is_placeholder)
        self.model = YOLO(self.weights_path)
        # Warm up once so latency measurements exclude init cost.
        import numpy as np
        self.model.predict(np.zeros((480, 640, 3), dtype=np.uint8),
                           conf=self.conf, imgsz=320, verbose=False)

    @property
    def names(self) -> dict:
        return getattr(self.model, "names", {})

    def _map(self, cid: int) -> str | None:
        if self.is_placeholder:
            return COCO_MAP.get(cid)  # person only
        if 0 <= cid < len(CLASSES):
            return CLASSES[cid]
        return None

    def predict(self, image, camera_id: str = "cam-01") -> dict:
        from src.inference.zones import get_zone
        t0 = time.perf_counter()
        res = self.model.predict(image, conf=self.conf, imgsz=self.imgsz, verbose=False)[0]
        dets = []
        img_h, img_w = res.orig_shape
        for b in res.boxes:
            cid = int(b.cls.item())
            name = self._map(cid)
            if name is None:
                continue
            x1, y1, x2, y2 = (float(v) for v in b.xyxy[0].tolist())
            cx, cy = ((x1 + x2) / 2 / img_w, (y1 + y2) / 2 / img_h)
            dets.append({"class_id": CLASSES.index(name), "class_name": name,
                         "conf": round(float(b.conf.item()), 3),
                         "bbox_xyxy": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                         "zone": get_zone((cx, cy))})
        violation = any(d["class_name"] in VIOLATIONS for d in dets)
        return {"camera_id": camera_id, "detections": dets,
                "violation": violation,
                "num_detections": len(dets),
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "model": os.path.basename(str(self.weights_path)),
                "placeholder": self.is_placeholder}
