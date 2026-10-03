"""Stratified 70/15/15 split into train/val/test.

Stratification key = (source_dataset, person-count bucket): this simulates
site-level grouping (each source folder ~= one construction site) so that all
splits contain every site but shuffled deterministically with seed 42.
Writes data/processed/dataset.yaml (Ultralytics format) + metadata.csv and
updates clean_manifest split column.
"""
from __future__ import annotations

import csv
import logging
import os
import shutil
import sys

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("split")


def bucket(n: int) -> str:
    if n == 0:
        return "b0"
    if n <= 3:
        return "b1-3"
    if n <= 8:
        return "b4-8"
    return "b9+"


def main() -> None:
    with open("configs/dataset.yaml") as fh:
        cfg = yaml.safe_load(fh) or {}
    ratios = cfg.get("split_ratios", {"train": 0.70, "val": 0.15, "test": 0.15})
    seed = int(cfg.get("seed", 42))
    classes: list[str] = cfg.get("classes", [])

    import random
    rng = random.Random(seed)
    with open("data/processed/clean_manifest.csv") as fh:
        rows = list(csv.DictReader(fh))

    groups: dict[tuple[str, str], list] = {}
    for r in rows:
        key = (r["source_dataset"], bucket(int(r.get("num_objects") or 0)))
        groups.setdefault(key, []).append(r)
    for g in groups.values():
        rng.shuffle(g)

    tr, va, te = ratios["train"], ratios["val"], ratios["test"]
    for g in groups.values():
        n = len(g)
        n_tr = max(1 if n >= 3 else 0, int(round(n * tr)))
        n_va = max(1 if n - n_tr >= 2 else 0, int(round(n * va)))
        for r in g[:n_tr]:
            r["split"] = "train"
        for r in g[n_tr:n_tr + n_va]:
            r["split"] = "val"
        for r in g[n_tr + n_va:]:
            r["split"] = "test"
    # any leftovers (tiny groups) -> train
    for r in rows:
        if not r.get("split"):
            r["split"] = "train"

    for split in ("train", "val", "test"):
        for sub in ("images", "labels"):
            d = os.path.join("data/processed", sub, split)
            os.makedirs(d, exist_ok=True)
            for f in os.listdir(d):  # idempotent rebuilds: clear stale files
                fp = os.path.join(d, f)
                if os.path.isfile(fp):
                    os.remove(fp)
    counts = {"train": 0, "val": 0, "test": 0}
    for r in rows:
        s = r["split"]
        shutil.copy(r["staged_path"], os.path.join("data/processed/images", s, r["image_filename"]))
        stem = os.path.splitext(r["image_filename"])[0]
        shutil.copy(os.path.join("data/processed/labels/all", stem + ".txt"),
                    os.path.join("data/processed/labels", s, stem + ".txt"))
        counts[s] += 1

    ds_yaml = {
        "path": os.path.abspath("data/processed").replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {i: c for i, c in enumerate(classes)},
        "nc": len(classes),
    }
    with open("data/processed/dataset.yaml", "w") as fh:
        yaml.safe_dump(ds_yaml, fh, sort_keys=False)
    with open("data/processed/metadata.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["image_filename", "width", "height",
                                            "source_dataset", "split", "num_objects",
                                            "classes_present", "annotation_format"])
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in
                         ["image_filename", "width", "height", "source_dataset", "split",
                          "num_objects", "classes_present", "annotation_format"]})
    with open("data/processed/clean_manifest.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    log.info("split counts: %s (total %d)", counts, len(rows))
    log.info("Wrote data/processed/dataset.yaml + metadata.csv")


if __name__ == "__main__":
    sys.exit(main())
