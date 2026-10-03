"""Precompute analytics cache (val-set inference) for the Analytics page.

Run: python src/ui/analytics_cache.py
Writes reports/analytics_cache.json:
  {class_counts, zone_counts, latencies_ms, n_images, model, conf}
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from src.inference.predictor import PPEPredictor

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def _images(split: str) -> list[str]:
    d = os.path.join("data/processed/images", split)
    return sorted(os.path.join(d, f) for f in os.listdir(d)
                  if f.lower().endswith(IMG_EXTS))


def main() -> None:
    pred = PPEPredictor(conf=0.30)
    class_counts: dict[str, int] = {}
    zone_counts = {"red": 0, "yellow": 0, "green": 0}
    lat = []
    files = _images("val")
    for f in files:
        r = pred.predict(f, camera_id="analytics")
        lat.append(r["latency_ms"])
        for d in r["detections"]:
            class_counts[d["class_name"]] = class_counts.get(d["class_name"], 0) + 1
            zone_counts[d["zone"]] = zone_counts.get(d["zone"], 0) + 1
    out = {"class_counts": class_counts, "zone_counts": zone_counts,
           "latencies_ms": lat, "n_images": len(files),
           "model": pred.weights_path, "conf": pred.conf}
    os.makedirs("reports", exist_ok=True)
    with open("reports/analytics_cache.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"cache: {len(files)} images, {sum(class_counts.values())} detections")


if __name__ == "__main__":
    sys.exit(main())
