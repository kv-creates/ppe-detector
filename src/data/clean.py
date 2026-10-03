"""Clean raw images: drop corrupt, drop <min_size, perceptual-hash dedup.

Reads configs/dataset.yaml (clean.min_size, clean.phash_threshold).
Writes data/processed/clean_manifest.csv with one row per kept image:
image_filename,width,height,source_dataset,num_objects_hint,keep_reason
"""
from __future__ import annotations

import csv
import logging
import os
import sys

import cv2
import yaml
from PIL import Image

try:
    import imagehash
    HAVE_PHASH = True
except Exception:  # pragma: no cover
    HAVE_PHASH = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("clean")

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def load_cfg() -> dict:
    with open("configs/dataset.yaml") as fh:
        return yaml.safe_load(fh) or {}


def iter_raw_images(raw_dir: str):
    for root, _, files in os.walk(raw_dir):
        for f in sorted(files):
            if f.lower().endswith(IMG_EXTS):
                # source = first path component under data/raw
                rel = os.path.relpath(os.path.join(root, f), raw_dir)
                source = rel.split(os.sep)[0]
                yield os.path.join(root, f), source, f


def main() -> None:
    cfg = load_cfg()
    raw_dir = cfg.get("raw_dir", "data/raw")
    min_size = int((cfg.get("clean") or {}).get("min_size", 320))
    ph_thresh = int((cfg.get("clean") or {}).get("phash_threshold", 5))
    if not HAVE_PHASH:
        log.warning("imagehash not installed; dedup disabled")

    seen: list = []  # perceptual hashes of kept images
    kept, dropped_corrupt, dropped_small, dropped_dup = 0, 0, 0, 0
    rows = []
    for path, source, fname in iter_raw_images(raw_dir):
        try:
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("cv2 could not decode")
            h, w = img.shape[:2]
        except Exception:  # noqa: BLE001
            dropped_corrupt += 1
            continue
        if min(w, h) < min_size:
            dropped_small += 1
            continue
        if HAVE_PHASH:
            try:
                ph = imagehash.phash(Image.open(path))
                if any((ph - s) <= ph_thresh for s in seen):
                    dropped_dup += 1
                    continue
                seen.append(ph)
            except Exception:  # noqa: BLE001
                pass
        kept += 1
        rows.append({"image_filename": fname, "abs_path": path, "width": w,
                     "height": h, "source_dataset": source, "split": "",
                     "num_objects": "", "classes_present": ""})

    os.makedirs("data/processed", exist_ok=True)
    with open("data/processed/clean_manifest.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["image_filename", "abs_path", "width",
                                            "height", "source_dataset", "split",
                                            "num_objects", "classes_present"])
        wr.writeheader()
        wr.writerows(rows)
    log.info("kept=%d corrupt=%d small=<%dpx=%d near-dup=%d",
             kept, dropped_corrupt, min_size, dropped_small, dropped_dup)
    log.info("Wrote data/processed/clean_manifest.csv")


if __name__ == "__main__":
    sys.exit(main())
