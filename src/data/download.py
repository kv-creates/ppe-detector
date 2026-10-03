"""Download 100% REAL PPE data sources. No synthetic data, ever.

Sources (all real, all documented in reports/dataset_card.md):
  A) SHWD demos — shallow git clone (11 demo frames, kept as background images)
  B) Ultralytics Construction-PPE — 1,416 real site photos, YOLO format, 11
     source classes (helmet/gloves/vest/boots/goggles/none/Person/no_helmet/
     no_goggle/no_gloves/no_boots), direct GitHub release download, no key.
     URL: https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip
  C) Roboflow PPE — public export (works with network; needs no key for the
     configured mirror, fails fast otherwise)
  D) Kaggle andrewmvd/hard-hat-detection — needs `kaggle` credentials
  E) HuggingFace keremberke/construction-site-safety — needs HF token
  F) BYOD — user-supplied: drop images into data/raw/byod/images/ and labels
     (YOLO TXT + classes.txt, or VOC XML) into data/raw/byod/labels/.

If a gated source is unavailable it is SKIPPED with a warning (never
fabricated). If the total real image count is below MIN_IMAGES the script
exits non-zero so the user knows legit data is missing.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("download")

RAW = "data/raw"
MIN_IMAGES = 50
SHWD_URL = "https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset.git"
CONSTRUCTION_PPE_URL = ("https://github.com/ultralytics/assets/releases/"
                        "download/v0.0.0/construction-ppe.zip")
ROBOFLOW_URLS = [
    "https://public.roboflow.com/ds/mZhPj6HnEG?key=roboflow_public",
]
KAGGLE_DATASET = "andrewmvd/hard-hat-detection"
HF_DATASET = "keremberke/construction-site-safety"


def _count_images(dest: str) -> int:
    return sum(1 for _, _, fs in os.walk(dest) for f in fs
               if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")))


# ---------------------------------------------------------------- A) SHWD ---
def download_shwd(dest: str = f"{RAW}/shwd") -> int:
    if os.path.isdir(dest) and _count_images(dest) > 0:
        log.info("SHWD already present at %s", dest)
    else:
        log.info("Cloning SHWD (shallow) ...")
        shutil.rmtree(dest, ignore_errors=True)
        try:
            subprocess.run(["git", "clone", "--depth", "1", SHWD_URL, dest],
                           check=True, timeout=300,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as exc:  # noqa: BLE001
            log.warning("SHWD clone failed: %s", exc)
            return 0
    out = os.path.join(dest, "images")
    os.makedirs(out, exist_ok=True)
    n = 0
    for root, _, files in os.walk(dest):
        if os.path.abspath(root).startswith(os.path.abspath(out)):
            continue
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png")) and "result" not in f.lower():
                src = os.path.join(root, f)
                dst = os.path.join(out, f"shwd_{n:04d}.jpg")
                if os.path.abspath(src) != os.path.abspath(dst):
                    shutil.copy(src, dst)
                n += 1
    log.info("SHWD: collected %d demo images (kept as background)", n)
    return n


# ------------------------------------------------- B) Construction-PPE ------
def download_construction_ppe(dest: str = f"{RAW}/construction_ppe") -> int:
    """Ultralytics Construction-PPE: 1,416 real images, YOLO labels included."""
    if _count_images(dest) > 1000:
        log.info("Construction-PPE already present at %s", dest)
        return _count_images(dest)
    log.info("Downloading Ultralytics Construction-PPE (178 MB) ...")
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)
    zpath = os.path.join(RAW, "_construction_ppe.zip")
    try:
        req = urllib.request.Request(CONSTRUCTION_PPE_URL,
                                     headers={"User-Agent": "ppe-detector/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(zpath, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(dest)
        os.remove(zpath)
    except Exception as exc:  # noqa: BLE001
        log.error("Construction-PPE download failed: %s", exc)
        return 0
    n = _count_images(dest)
    log.info("Construction-PPE: extracted %d images", n)
    return n


# ------------------------------------------------------------- C) Roboflow ---
def download_roboflow(dest: str = f"{RAW}/roboflow_ppe") -> int:
    os.makedirs(dest, exist_ok=True)
    for url in ROBOFLOW_URLS:
        try:
            log.info("Trying Roboflow mirror ...")
            req = urllib.request.Request(url, headers={"User-Agent": "ppe-detector/1.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()
            if len(data) < 100_000:
                continue
            import io
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(dest)
            n = _count_images(dest)
            log.info("Roboflow: extracted %d images", n)
            return n
        except Exception as exc:  # noqa: BLE001
            log.warning("Roboflow mirror failed: %s", exc)
    log.warning("Roboflow skipped (endpoint needs API key or moved).")
    return 0


# --------------------------------------------------------------- D) Kaggle ---
def download_kaggle(dest: str = f"{RAW}/kaggle_hardhat") -> int:
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore
    except Exception:
        log.warning("kaggle package/credentials not available; skipping Kaggle source.")
        return 0
    try:
        log.info("Downloading Kaggle dataset %s ...", KAGGLE_DATASET)
        api = KaggleApi()
        api.authenticate()
        os.makedirs(dest, exist_ok=True)
        api.dataset_download_files(KAGGLE_DATASET, path=dest, unzip=True)
        n = _count_images(dest)
        log.info("Kaggle: downloaded %d images", n)
        return n
    except Exception as exc:  # noqa: BLE001
        log.warning("Kaggle download failed: %s", exc)
        return 0


# ------------------------------------------------------------------ E) HF ---
def download_huggingface(dest: str = f"{RAW}/hf_ppe") -> int:
    try:
        from huggingface_hub import snapshot_download  # type: ignore
    except Exception:
        log.warning("huggingface_hub not installed; skipping HuggingFace source.")
        return 0
    try:
        log.info("Downloading HuggingFace dataset %s ...", HF_DATASET)
        snapshot_download(repo_id=HF_DATASET, repo_type="dataset",
                          local_dir=dest, local_dir_use_symlinks=False)
        n = _count_images(dest)
        log.info("HuggingFace: downloaded %d images", n)
        return n
    except Exception as exc:  # noqa: BLE001
        log.warning("HuggingFace download failed (token required?): %s", exc)
        return 0


# ----------------------------------------------------------------- F) BYOD ---
def ingest_byod(dest: str = f"{RAW}/byod") -> int:
    """Bring-your-own-data: images in <dest>/images, YOLO TXT (+classes.txt or
    data.yaml) or VOC XML in <dest>/labels (or next to images)."""
    n = _count_images(os.path.join(dest, "images")) if os.path.isdir(dest) else 0
    if n == 0:
        n = _count_images(dest)
        if n:
            log.info("BYOD: found %d images directly under %s", n, dest)
    else:
        log.info("BYOD: found %d user-supplied images", n)
    return n


# ------------------------------------------------------------------ main ----
def main() -> None:
    os.makedirs(RAW, exist_ok=True)
    counts = {
        "shwd": download_shwd(),
        "construction_ppe": download_construction_ppe(),
        "roboflow": download_roboflow(),
        "kaggle": download_kaggle(),
        "huggingface": download_huggingface(),
        "byod": ingest_byod(),
    }
    total = sum(counts.values())
    log.info("Real images collected: %s (total %d)", counts, total)
    with open(f"{RAW}/download_summary.json", "w") as fh:
        json.dump(counts, fh, indent=2)
    if total < MIN_IMAGES:
        log.error("Only %d real images (< %d). Add credentials (Kaggle/HF) or drop "
                  "files into data/raw/byod/ and re-run. No synthetic fallback — "
                  "this pipeline uses legit data only.", total, MIN_IMAGES)
        return 1
    log.info("DONE. All data is real (no synthetic images).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
