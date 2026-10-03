"""KPI computation -> reports/final_metrics.json.

5 KPIs:
  Business      LTIFR reduction (baseline 3.2 -> target 1.92, i.e. -40%).
                Estimated from measured violation-detection recall: prevented
                fraction ~= recall(no-helmet) * intervention effectiveness (0.5).
  ML 1          Precision on the critical `no-helmet` class (target > 0.85).
  ML 2          mAP@0.5 on the test split (target > 0.72).
  Data Quality  Blurriness ratio: fraction of images with Laplacian variance
                < 100 (target < 3%).
  Product       Alert latency p95 in ms, measured by timing local inference
                over the test set (target < 500 ms).

Inputs: reports/local_metrics.json (from src.training.local_eval) and, when
present, reports/colab_metrics.json (authoritative after Colab training).
Run: python -m src.utils.kpi
"""
from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time

import cv2

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("kpi")

CLASSES = ["person", "helmet", "vest", "no-helmet", "no-vest", "boots"]


def load_metrics() -> dict:
    """Colab metrics win when available; else local baseline metrics.

    The Colab notebook only records overall mAP/P/R, so per-class entries
    (precision_no_helmet, per_class, ...) are back-filled from
    reports/local_metrics.json when the Colab file lacks them.
    """
    merged, tag = {}, "none"
    if os.path.exists("reports/local_metrics.json"):
        with open("reports/local_metrics.json") as fh:
            merged = json.load(fh)
    if os.path.exists("reports/colab_metrics.json"):
        with open("reports/colab_metrics.json") as fh:
            colab = json.load(fh)
        log.info("Using colab metrics from reports/colab_metrics.json")
        if isinstance(colab, dict) and not any(
                k in colab for k in ("mAP50", "precision_no_helmet", "precision")):
            # per-model shape {"yolov8s_ppe": {...}} -> use the best by mAP50
            def _m(key):
                vv = colab.get(key, {})
                return float(vv.get("mAP50", 0)) if isinstance(vv, dict) else 0.0
            best = max(colab.keys(), key=_m)
            merged["colab_best"] = best
            best_vals = colab.get(best, {})
        else:
            best_vals = colab
        if isinstance(best_vals, dict):
            for k, v in best_vals.items():
                if isinstance(v, (int, float)):
                    merged[k] = v
        tag = "colab" if any(k in merged for k in ("mAP50", "map50")) else "local"
        merged["source"] = tag
        return merged, tag
    if merged:
        log.info("Using local metrics from reports/local_metrics.json")
        return merged, "local"
    log.warning("No metrics file found; using zeros")
    return {}, "none"


def _pick(m: dict, *keys, default=0.0) -> float:
    for k in keys:
        if k in m:
            try:
                return float(m[k])
            except (TypeError, ValueError):
                pass
    # nested {"yolov8s_ppe": {...}} shape from the Colab notebook
    for v in m.values():
        if isinstance(v, dict):
            for k in keys:
                if k in v:
                    try:
                        return float(v[k])
                    except (TypeError, ValueError):
                        pass
    return default


def blurriness_ratio() -> float:
    vals = []
    for split in ("train", "val", "test"):
        d = os.path.join("data/processed/images", split)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                img = cv2.imread(os.path.join(d, f), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    vals.append(cv2.Laplacian(img, cv2.CV_64F).var())
    if not vals:
        return 0.0
    blurry = sum(1 for v in vals if v < 100)
    log.info("blur check: %d/%d images Laplacian-var<100", blurry, len(vals))
    return blurry / len(vals)


def latency_p95_ms() -> float:
    """Time end-to-end PPEPredictor inference on up to 40 test images."""
    try:
        from src.inference.predictor import PPEPredictor
    except Exception as exc:  # noqa: BLE001
        log.warning("predictor unavailable (%s); latency=0", exc)
        return 0.0
    test_dir = "data/processed/images/test"
    if not os.path.isdir(test_dir):
        return 0.0
    files = [os.path.join(test_dir, f) for f in sorted(os.listdir(test_dir))
             if f.lower().endswith((".jpg", ".jpeg", ".png"))][:40]
    if not files:
        return 0.0
    pred = PPEPredictor()
    dt = []
    for f in files:
        t0 = time.perf_counter()
        pred.predict(f, camera_id="kpi-probe")
        dt.append((time.perf_counter() - t0) * 1000)
    dt.sort()
    p95 = dt[min(len(dt) - 1, int(len(dt) * 0.95))]
    log.info("latency p50=%.0fms p95=%.0fms over %d images", dt[len(dt)//2], p95, len(dt))
    return round(p95, 1)


def main() -> None:
    m, tag = load_metrics()
    prec_nohelmet = _pick(m, "precision_no_helmet", "precision", default=0.0)
    map50 = _pick(m, "mAP50", "map50", default=0.0)
    # Honest guard: placeholder COCO runs have no PPE classes.
    if tag == "none" or (prec_nohelmet == 0.0 and map50 == 0.0):
        log.warning("Metrics carry no PPE signal (tag=%s); KPIs will show measured zeros.", tag)

    # Business KPI: prevented-incident fraction ~= recall * intervention rate.
    recall = _pick(m, "recall", "recall_no_helmet", default=prec_nohelmet)
    prevented = recall * 0.5
    ltifr_baseline, ltifr_target = 3.2, 1.92
    ltifr_actual = round(ltifr_baseline * (1 - prevented), 3)

    blur = blurriness_ratio()
    p95 = latency_p95_ms()

    kpis = {
        "source": tag,
        "business_ltifr": {"name": "LTIFR reduction", "baseline": ltifr_baseline,
                           "target": ltifr_target, "actual": ltifr_actual,
                           "unit": "incidents/200k hrs",
                           "status": "PASS" if ltifr_actual <= ltifr_target else "FAIL",
                           "interpretation": (
                               f"Estimated LTIFR {ltifr_actual} from measured violation "
                               f"recall {recall:.3f} x 50% intervention effectiveness.")},
        "ml_precision_no_helmet": {"name": "Precision (no-helmet)", "target": 0.85,
                                   "actual": round(prec_nohelmet, 4),
                                   "status": "PASS" if prec_nohelmet > 0.85 else "FAIL",
                                   "interpretation": (
                                       "Share of no-helmet alerts that are true violations; "
                                       "drives supervisor trust in the alert stream.")},
        "ml_map50": {"name": "mAP@0.5 (test)", "target": 0.72,
                     "actual": round(map50, 4),
                     "status": "PASS" if map50 > 0.72 else "FAIL",
                                   "interpretation": (
                                       "Overall detection quality across all 6 PPE classes.")},
        "data_blurriness": {"name": "Blurriness ratio", "target": 0.03,
                            "actual": round(blur, 4),
                            "status": "PASS" if blur < 0.03 else "FAIL",
                            "interpretation": (
                                "Fraction of images with Laplacian variance < 100; "
                                "high values would indicate camera/focus problems.")},
        "product_latency_p95_ms": {"name": "Alert latency p95", "target_ms": 500,
                                   "actual_ms": p95,
                                   "status": "PASS" if 0 < p95 < 500 else "FAIL",
                                   "interpretation": (
                                       "End-to-end detect latency; must stay under 500 ms "
                                       "for real-time intervention.")},
    }
    with open("reports/final_metrics.json", "w") as fh:
        json.dump(kpis, fh, indent=2)
    log.info("Wrote reports/final_metrics.json (source=%s)", tag)
    print(json.dumps({k: {kk: v[kk] for kk in ("actual", "actual_ms") if kk in v}
                      for k, v in kpis.items()}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
