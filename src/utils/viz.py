"""EDA visualisation: 5 raw PNG figures for reports/figures/.

Run: python -m src.utils.viz
"""
from __future__ import annotations

import csv
import os
import random
import sys

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.utils.screenshot import save_fig

CLASSES = ["person", "helmet", "vest", "no-helmet", "no-vest", "boots"]
COLORS = ["#3B6EA5", "#6BA3D6", "#2E5C8A", "#C0392B", "#E67E22", "#27AE60"]

META = "data/processed/metadata.csv"
IMG = "data/processed/images"
LBL = "data/processed/labels"


def load_meta():
    with open(META) as fh:
        return list(csv.DictReader(fh))


def plot_class_distribution(rows) -> None:
    counts = {c: 0 for c in CLASSES}
    for r in rows:
        for c in (r["classes_present"] or "").split(";"):
            if c in counts:
                counts[c] += 1
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(CLASSES, [counts[c] for c in CLASSES], color=COLORS, edgecolor="#444")
    ax.set_title("Class frequency (images containing class)")
    ax.set_ylabel("images")
    plt.xticks(rotation=30, ha="right")
    for i, c in enumerate(CLASSES):
        ax.text(i, counts[c] + 2, str(counts[c]), ha="center", fontsize=8)
    fig.tight_layout()
    save_fig(fig, "class_dist")
    plt.close(fig)


def plot_bbox_histogram(rows) -> None:
    areas = []
    for r in rows:
        lp = os.path.join(LBL, r["split"],
                          os.path.splitext(r["image_filename"])[0] + ".txt")
        if not os.path.exists(lp):
            continue
        with open(lp) as fh:
            for line in fh:
                p = line.split()
                if len(p) == 5:
                    areas.append(float(p[3]) * float(p[4]))
    areas = np.array(areas)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(areas, bins=40, color="#3B6EA5", edgecolor="#222")
    ax.set_title(f"Bounding-box area distribution (n={len(areas)})")
    ax.set_xlabel("normalised area (w*h)")
    ax.set_ylabel("boxes")
    ax.axvline(float(np.median(areas)), color="#C0392B", ls="--",
               label=f"median={np.median(areas):.4f}")
    ax.legend()
    fig.tight_layout()
    save_fig(fig, "bbox_dist")
    plt.close(fig)


def plot_sample_grid(rows) -> None:
    rng = random.Random(42)
    picks = rng.sample(rows, min(16, len(rows)))
    fig, axes = plt.subplots(4, 4, figsize=(12, 9))
    for ax, r in zip(axes.ravel(), picks):
        img = cv2.imread(os.path.join(IMG, r["split"], r["image_filename"]))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        lp = os.path.join(LBL, r["split"], os.path.splitext(r["image_filename"])[0] + ".txt")
        if os.path.exists(lp):
            with open(lp) as fh:
                for line in fh:
                    p = line.split()
                    if len(p) != 5:
                        continue
                    ci, cx, cy, bw, bh = int(p[0]), *map(float, p[1:])
                    x1, y1 = int((cx - bw / 2) * w), int((cy - bh / 2) * h)
                    x2, y2 = int((cx + bw / 2) * w), int((cy + bh / 2) * h)
                    col = tuple(int(COLORS[ci % 10].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                    cv2.rectangle(img, (x1, y1), (x2, y2), col, 2)
                    cv2.putText(img, CLASSES[ci], (x1, max(0, y1 - 4)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)
        ax.imshow(img)
        ax.set_title(r["image_filename"][:22], fontsize=7)
        ax.axis("off")
    fig.suptitle("Sample images with ground-truth boxes")
    fig.tight_layout()
    save_fig(fig, "sample_grid")
    plt.close(fig)


def plot_resolution_hist(rows) -> None:
    mp = [(int(r["width"]) * int(r["height"])) / 1e6 for r in rows]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(mp, bins=25, color="#3B6EA5", edgecolor="#222")
    ax.set_title("Image resolution histogram")
    ax.set_xlabel("megapixels")
    ax.set_ylabel("images")
    fig.tight_layout()
    save_fig(fig, "resolution_hist")
    plt.close(fig)


def plot_source_breakdown(rows) -> None:
    from collections import Counter
    c = Counter(r["source_dataset"] for r in rows)
    labels = list(c.keys())
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(labels, [c[k] for k in labels], color=COLORS[:len(labels)], edgecolor="#444")
    ax.set_title("Images per source dataset")
    ax.set_ylabel("images")
    plt.xticks(rotation=20, ha="right")
    for i, k in enumerate(labels):
        ax.text(i, c[k] + 3, str(c[k]), ha="center", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "source_breakdown")
    plt.close(fig)


def main() -> None:
    rows = load_meta()
    print(f"EDA on {len(rows)} images")
    plot_class_distribution(rows)
    plot_bbox_histogram(rows)
    plot_sample_grid(rows)
    plot_resolution_hist(rows)
    plot_source_breakdown(rows)
    print("EDA DONE")


if __name__ == "__main__":
    sys.exit(main())
