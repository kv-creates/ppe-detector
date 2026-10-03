"""Seed the violations DB by running /api/detect over sample images."""
import os
import sys

sys.path.insert(0, ".")
import requests

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
test_dir = "data/processed/images/test"
files = sorted(os.path.join(test_dir, f) for f in os.listdir(test_dir)
               if f.lower().endswith(IMG_EXTS))[:60]

n_vio = 0
for i, f in enumerate(files):
    cam = f"cam-0{(i % 3) + 1}"
    with open(f, "rb") as fh:
        r = requests.post("http://127.0.0.1:8000/api/detect",
                          params={"camera_id": cam},
                          files={"file": ("frame.jpg", fh, "image/jpeg")},
                          timeout=180)
    r.raise_for_status()
    d = r.json()
    n_vio += d["violation"]
    print(f"{os.path.basename(f)} {cam} violation={d['violation']} n={d['num_detections']}")
print(f"seeded; violations in batch: {n_vio}")
