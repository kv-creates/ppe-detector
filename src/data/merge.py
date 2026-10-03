"""Merge annotations (YOLO TXT + Pascal VOC XML + COCO JSON) into unified labels.

Unified 6-class taxonomy (all boxes trace to REAL annotations):
  person, helmet, vest, no-helmet, no-vest, boots

Source-label mapping drops out-of-scope classes (gloves, goggles, no_gloves,
no_goggle, no_boots, none) — documented in reports/dataset_card.md.

no-vest derivation (documented heuristic, same convention as SHWD's own
head-vs-helmet labelling): for sources whose taxonomy includes `vest` but NOT
a native `no-vest` label, any `person` box with IoU < 0.05 against every vest
box gets a `no-vest` torso box (x inset 12%, y spanning 20%..62% of the person
box). Rationale: the source annotates every visible vest, so a worker with no
overlapping vest box is genuinely not wearing one.

Images without any kept annotation become background images (capped at 5%).
Output staging: data/processed/images/all + data/processed/labels/all.
"""
from __future__ import annotations

import csv
import glob
import json
import logging
import os
import shutil
import sys
import xml.etree.ElementTree as ET

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("merge")

CLASSES = ["person", "helmet", "vest", "no-helmet", "no-vest", "boots"]
CLS2ID = {c: i for i, c in enumerate(CLASSES)}

# source label -> unified class (lower-cased). Out-of-scope labels map to None.
LABEL_MAP = {
    "person": "person", "people": "person", "worker": "person", "man": "person",
    "helmet": "helmet", "hardhat": "helmet", "hard_hat": "helmet", "hat": "helmet",
    "helmet_on": "helmet", "with_helmet": "helmet", "safety_helmet": "helmet",
    "head": "no-helmet", "no_helmet": "no-helmet", "no-helmet": "no-helmet",
    "without_helmet": "no-helmet", "nohelmet": "no-helmet", "hat_off": "no-helmet",
    "vest": "vest", "safety_vest": "vest", "safety-vest": "vest", "highvis": "vest",
    "reflective_vest": "vest", "hi_vis": "vest",
    "no_vest": "no-vest", "no-vest": "no-vest", "without_vest": "no-vest",
    "novest": "no-vest",
    "boots": "boots", "safety_boots": "boots", "boot": "boots", "safety_shoe": "boots",
    # explicitly out of scope (dropped, counted in the log):
    "gloves": None, "no_gloves": None, "goggles": None, "no_goggle": None,
    "no_boots": None, "none": None, "background": None,
}


def norm_label(name: str):
    return LABEL_MAP.get(name.strip().lower().replace(" ", "_"), "UNKNOWN")


def box_iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


# ------------------------------------------------------------- format readers
def voc_to_boxes(xml_path: str):
    out, unknown = [], set()
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:  # noqa: BLE001
        return out, unknown
    for obj in root.findall("object"):
        cls = norm_label(obj.findtext("name") or "")
        if cls is None:
            continue
        if cls == "UNKNOWN":
            unknown.add((obj.findtext("name") or "").strip())
            continue
        bb = obj.find("bndbox")
        try:
            out.append((cls, int(float(bb.findtext("xmin"))), int(float(bb.findtext("ymin"))),
                        int(float(bb.findtext("xmax"))), int(float(bb.findtext("ymax")))))
        except Exception:  # noqa: BLE001
            continue
    return out, unknown


def find_source_names(label_file: str) -> list[str] | None:
    """Locate a data.yaml/dataset.yaml/classes.txt near a YOLO label file."""
    base = os.path.dirname(os.path.abspath(label_file))
    for _ in range(5):
        for nm in ("data.yaml", "dataset.yaml", "data.yml"):
            p = os.path.join(base, nm)
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        d = yaml.safe_load(fh) or {}
                    names = d.get("names")
                    if isinstance(names, dict):
                        return [names[k] for k in sorted(names)]
                    if isinstance(names, list):
                        return names
                except Exception:  # noqa: BLE001
                    pass
        for nm in ("classes.txt", "names.txt", "obj.names"):
            p = os.path.join(base, nm)
            if os.path.exists(p):
                with open(p) as fh:
                    return [ln.strip() for ln in fh if ln.strip()]
        base = os.path.dirname(base)
    return None


def yolo_txt_to_boxes(label_file: str, names: list[str], w: int, h: int):
    out, unknown = [], set()
    with open(label_file) as fh:
        for line in fh:
            p = line.split()
            if len(p) != 5:
                continue
            try:
                ci = int(float(p[0]))
                src = names[ci] if 0 <= ci < len(names) else f"idx{ci}"
            except Exception:  # noqa: BLE001
                continue
            cls = norm_label(src)
            if cls is None:
                continue
            if cls == "UNKNOWN":
                unknown.add(src)
                continue
            _, cx, cy, bw, bh = map(float, p)
            out.append((cls, int((cx - bw / 2) * w), int((cy - bh / 2) * h),
                        int((cx + bw / 2) * w), int((cy + bh / 2) * h)))
    return out, unknown


# ------------------------------------------------------- no-vest derivation --
def derive_no_vest(boxes):
    """Append torso no-vest boxes for persons without vest overlap."""
    persons = [b for b in boxes if b[0] == "person"]
    vests = [b[1:] for b in boxes if b[0] == "vest"]
    if not persons or any(b[0] == "no-vest" for b in boxes):
        return boxes, 0
    extra, n = [], 0
    for _, x1, y1, x2, y2 in persons:
        if vests and max(box_iou((x1, y1, x2, y2), v) for v in vests) >= 0.05:
            continue
        bw, bh = x2 - x1, y2 - y1
        tx1, tx2 = int(x1 + 0.12 * bw), int(x2 - 0.12 * bw)
        ty1, ty2 = int(y1 + 0.20 * bh), int(y1 + 0.62 * bh)
        if tx2 - tx1 >= 8 and ty2 - ty1 >= 8:
            extra.append(("no-vest", tx1, ty1, tx2, ty2))
            n += 1
    return boxes + extra, n


def write_yolo(label_path: str, boxes, w: int, h: int) -> None:
    with open(label_path, "w") as fh:
        for cls, x1, y1, x2, y2 in boxes:
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            fh.write(f"{CLS2ID[cls]} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} "
                     f"{(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}\n")


def main() -> None:
    with open("configs/dataset.yaml") as fh:
        cfg = yaml.safe_load(fh) or {}
    raw_dir = cfg.get("raw_dir", "data/raw")
    img_all = "data/processed/images/all"
    lbl_all = "data/processed/labels/all"
    os.makedirs(img_all, exist_ok=True)
    os.makedirs(lbl_all, exist_ok=True)

    # COCO index (unchanged behaviour)
    coco_index: dict[str, list] = {}
    for root, _, files in os.walk(raw_dir):
        for f in files:
            if not f.lower().endswith(".json"):
                continue
            try:
                with open(os.path.join(root, f)) as fh:
                    d = json.load(fh)
                if not (isinstance(d, dict) and "images" in d and "annotations" in d):
                    continue
                cats = {c["id"]: c.get("name", "") for c in d.get("categories", [])}
                imgs = {im["id"]: im.get("file_name", "") for im in d.get("images", [])}
                for an in d.get("annotations", []):
                    fn = imgs.get(an.get("image_id"), "")
                    cls = norm_label(str(cats.get(an.get("category_id"), "")))
                    if not fn or cls is None or cls == "UNKNOWN":
                        continue
                    x, y, bw, bh = an.get("bbox", [0, 0, 0, 0])
                    coco_index.setdefault(os.path.basename(fn), []).append(
                        (cls, int(x), int(y), int(x + bw), int(y + bh)))
            except Exception:  # noqa: BLE001
                continue

    with open("data/processed/clean_manifest.csv") as fh:
        rows = list(csv.DictReader(fh))

    # source -> does its taxonomy declare vest without no-vest?
    source_declares_vest: dict[str, bool] = {}
    n_yolo = n_voc = n_coco = n_empty = n_derived = 0
    dropped: dict[str, int] = {}
    staged = []
    for r in rows:
        src_img, fname, source = r["abs_path"], r["image_filename"], r["source_dataset"]
        w, h = int(r["width"]), int(r["height"])
        boxes, fmt, unknown = [], "none", set()
        stem = os.path.splitext(fname)[0]
        img_dir = os.path.dirname(src_img)
        yolo_cands = [os.path.join(img_dir, stem + ".txt"),
                      os.path.join(img_dir, "labels", stem + ".txt")]
        # sibling labels dir: <root>/images/<split>/foo.jpg <-> <root>/labels/<split>/foo.txt
        parent, leaf = os.path.split(img_dir)
        grandparent, parent_leaf = os.path.split(parent)
        if parent_leaf == "images":
            yolo_cands.append(os.path.join(grandparent, "labels", leaf, stem + ".txt"))
        yolo_cands.append(os.path.join(parent, "labels", stem + ".txt"))
        yolo_file = next((c for c in yolo_cands if os.path.exists(c)), None)
        if yolo_file:
            names = find_source_names(yolo_file) or []
            boxes, unknown = yolo_txt_to_boxes(yolo_file, names, w, h)
            fmt = "YOLO"
            n_yolo += 1
            if source not in source_declares_vest:
                uni = {norm_label(n) for n in names}
                source_declares_vest[source] = ("vest" in uni and "no-vest" not in uni)
        else:
            voc = None
            for c in (os.path.join(os.path.dirname(src_img), stem + ".xml"),
                      os.path.join(os.path.dirname(src_img), "annotations", stem + ".xml")):
                if os.path.exists(c):
                    voc = c
                    break
            if voc:
                boxes, unknown = voc_to_boxes(voc)
                fmt = "VOC"
                n_voc += 1
            elif fname in coco_index:
                boxes = coco_index[fname]
                fmt = "COCO"
                n_coco += 1
        for u in unknown:
            dropped[u] = dropped.get(u, 0) + 1
        if fmt != "none" and source_declares_vest.get(source, False):
            boxes, nd = derive_no_vest(boxes)
            n_derived += nd
        dst_img = os.path.join(img_all, f"{source}_{fname}")
        shutil.copy(src_img, dst_img)
        write_yolo(os.path.join(lbl_all, os.path.splitext(os.path.basename(dst_img))[0] + ".txt"),
                   boxes, w, h)
        if not boxes:
            n_empty += 1
        r["image_filename"] = os.path.basename(dst_img)
        r["num_objects"] = str(len(boxes))
        r["classes_present"] = ";".join(sorted({b[0] for b in boxes}))
        r["annotation_format"] = fmt
        r["staged_path"] = dst_img
        staged.append(r)

    with_boxes = [r for r in staged if int(r["num_objects"]) > 0]
    empties = [r for r in staged if int(r["num_objects"]) == 0]
    keep_empty = min(len(empties), max(1, int(0.05 * len(with_boxes))))
    final = with_boxes + empties[:keep_empty]
    for r in empties[keep_empty:]:
        os.remove(os.path.join(img_all, r["image_filename"]))
        os.remove(os.path.join(lbl_all, os.path.splitext(r["image_filename"])[0] + ".txt"))
    log.info("YOLO=%d VOC=%d COCO=%d derived_no_vest=%d empty-kept=%d final=%d",
             n_yolo, n_voc, n_coco, n_derived, keep_empty, len(final))
    log.info("dropped out-of-scope labels: %s", dropped)

    with open("data/processed/clean_manifest.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["image_filename", "abs_path", "width", "height",
                                            "source_dataset", "split", "num_objects",
                                            "classes_present", "annotation_format", "staged_path"])
        wr.writeheader()
        wr.writerows(final)
    log.info("Staged %d images -> data/processed/images/all", len(final))


if __name__ == "__main__":
    sys.exit(main())
