"""Write reports/dataset_card.md — the formal dataset documentation.

Covers domain, source URLs, before/after cleaning counts, annotation formats,
the 6-class taxonomy, the metadata "column" schema (image data => one row per
image), 3 sample metadata rows, and per-source rationale.
"""
from __future__ import annotations

import csv
import datetime
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("metadata")

CLASS_TABLE = [
    ("0", "person", "Neutral", "Anchor for compliance logic: violations are assessed per detected worker."),
    ("1", "helmet", "Compliant PPE", "OSHA 1926.100 head protection; primary compliance signal."),
    ("2", "vest", "Compliant PPE", "OSHA high-visibility requirement for road/high-traffic zones."),
    ("3", "no-helmet", "Violation", "Critical safety risk; triggers immediate alert (native labels)."),
    ("4", "no-vest", "Violation", "Visibility risk; derived torso boxes for vest-less workers (documented heuristic)."),
    ("5", "boots", "Compliant PPE", "Foot protection against crush/puncture hazards."),
]

COLUMN_TABLE = [
    ("image_filename", "str", "Unique image ID", "construction_ppe_train00042.jpg"),
    ("width", "int", "Image width (px)", "640"),
    ("height", "int", "Image height (px)", "480"),
    ("source_dataset", "str", "Origin dataset", "construction_ppe"),
    ("split", "str", "train / val / test", "train"),
    ("num_objects", "int", "Total bounding boxes", "4"),
    ("classes_present", "list[str]", "Unique classes in image", "[person, helmet, no-vest]"),
    ("annotation_format", "str", "Original annotation format", "YOLO"),
]

SOURCES = [
    ("Construction-PPE (Ultralytics)",
     "https://docs.ultralytics.com/datasets/detect/construction-ppe "
     "(zip: github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip)",
     "YOLO TXT", "AGPL-3.0",
     "Primary source: 1,416 real construction-site photos with helmet/vest/boots/person/no_helmet labels (compliant AND violation cases). Out-of-scope labels (gloves, goggles, no_gloves, no_goggle, no_boots, none) are dropped by src/data/merge.py."),
    ("SHWD",
     "https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset",
     "unlabelled JPG", "Public",
     "The GitHub repo hosts only 11 demo frames (full 7,581-image set is on Baidu Pan); kept as background images."),
    ("Roboflow PPE (Hard Hat Workers)",
     "https://universe.roboflow.com/roboflow-universe-projects/hard-hat-workers",
     "YOLO TXT", "CC BY 4.0",
     "Attempted automatically; skipped without a reachable public mirror. Adds vest/no-vest diversity when available."),
    ("Kaggle Hard Hat Detection",
     "https://www.kaggle.com/datasets/andrewmvd/hard-hat-detection",
     "Pascal VOC XML", "CC0",
     "Attempted automatically; needs `kaggle` credentials. 5,000+ crowd-sourced site photos when available."),
    ("HuggingFace construction-site-safety",
     "https://huggingface.co/datasets/keremberke/construction-site-safety",
     "YOLO TXT", "varies",
     "Attempted automatically; needs a HuggingFace token."),
    ("Bring-your-own-data",
     "local folder data/raw/byod/",
     "YOLO TXT or VOC XML", "user-provided",
     "Drop images into data/raw/byod/images/ with YOLO TXT (+classes.txt) or VOC XML labels; ingested with zero code changes."),
]


def main() -> None:
    with open("data/processed/metadata.csv") as fh:
        rows = list(csv.DictReader(fh))
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["source_dataset"]] = counts.get(r["source_dataset"], 0) + 1
    total = len(rows)
    try:
        with open("data/raw/download_summary.json") as fh:
            summary = json.load(fh)
    except Exception:  # noqa: BLE001
        summary = {}

    src_rows = "\n".join(
        f"| {n} | {u} | {counts.get(k, 0)} | {f} | {lic} |"
        for k, (n, u, f, lic, _) in
        zip(["construction_ppe", "shwd", "roboflow_ppe", "kaggle_hardhat",
             "hf_ppe", "byod"], SOURCES))
    rationale = "\n".join(f"- **{n}** — {why}" for n, _, _, _, why in SOURCES)
    col_rows = "\n".join(f"| {c} | {t} | {d} | `{e}` |" for c, t, d, e in COLUMN_TABLE)
    cls_rows = "\n".join(f"| {i} | {c} | {t} | {r} |" for i, c, t, r in CLASS_TABLE)
    sample = rows[:3]
    sample_rows = "\n".join(
        f"| {r['image_filename']} | {r['width']} | {r['height']} | {r['source_dataset']} "
        f"| {r['split']} | {r['num_objects']} | {r['classes_present']} | {r['annotation_format']} |"
        for r in sample)

    card = f"""# Dataset Card — Construction Site PPE Non-Compliance Detection

**Generated:** {datetime.date.today().isoformat()}
**Domain:** Workplace Safety / Construction / Industrial EHS
**Task:** Multi-class object detection (6 classes) for PPE compliance monitoring

## 1. Sources

| Dataset | Source URL | Images (after cleaning) | Annotation format | License |
|---------|-----------|------------------------|-------------------|---------|
{src_rows}

Raw download attempts: `{json.dumps(summary)}`.
The GitHub SHWD repo hosts only demo images + code (full 7,581-image set is
distributed via Baidu Pan); Roboflow/Kaggle/HuggingFace are attempted
automatically and skipped with a warning when credentials or endpoints are
unavailable. Every image in this dataset is real — this pipeline contains no
synthetic data.

## 2. Totals before / after cleaning

- Images collected (raw): see `data/raw/download_summary.json`
- Images after cleaning (dedup + resolution + corrupt filter): **{total}**
- Cleaning steps: perceptual-hash dedup (Hamming <= 5), drop min(w,h) < 320px,
  drop undecodable files. Manifest: `data/processed/clean_manifest.csv`.

## 3. Annotation formats

Source annotations arrive as YOLO TXT, Pascal VOC XML, or COCO JSON and are
unified to YOLO TXT (`class cx cy w h`, normalised) by `src/data/merge.py`.
Source labels are normalised through a synonym map (e.g. `hardhat` -> `helmet`,
`head`/`no_helmet` -> `no-helmet`) while out-of-scope labels (gloves, goggles,
`none`, ...) are dropped and counted in the merge log. `no-vest` boxes are
derived for vest-less workers of vest-annotated sources (torso geometry,
documented in `src/data/merge.py`).

## 4. Class taxonomy (6 classes)

| ID | Class | Type | Rationale |
|----|-------|------|-----------|
{cls_rows}

## 5. Metadata schema ("columns")

Each image is one record:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
{col_rows}

Full table: `data/processed/metadata.csv`.

### Sample rows

| image_filename | width | height | source_dataset | split | num_objects | classes_present | annotation_format |
|----------------|-------|--------|----------------|-------|-------------|-----------------|-------------------|
{sample_rows}

## 6. Rationale per source

{rationale}

## 7. Split & leakage prevention

70/15/15 stratified by (source folder ~= site, object-count bucket), seed 42
(`src/data/split.py`, Ultralytics manifest `data/processed/dataset.yaml`).
Augmentation is applied only at training time (post-split); near-duplicates are
removed pre-split via pHash, preventing same-scene leakage across splits.
"""
    os.makedirs("reports", exist_ok=True)
    with open("reports/dataset_card.md", "w") as fh:
        fh.write(card)
    log.info("Wrote reports/dataset_card.md (%d images)", total)


if __name__ == "__main__":
    sys.exit(main())
