"""Local model setup + evaluation.

Priority:
  1. Colab weights present (models/checkpoints/*/weights/best.pt + optional
     reports/colab_metrics.json) -> evaluate best on the test split.
  2. Else train a SMALL local CPU smoke baseline (yolov8n, 8 epochs, imgsz 320)
     to validate the pipeline end-to-end. This is explicitly a smoke test, NOT
     the official training (60 epochs, T4 GPU, on Colab). Its curves/metrics are
     saved under reports/figures/local_baseline/ and labelled as such.
  3. If even that fails -> COCO-pretrained placeholder + COLAB_PENDING notice.

Outputs:
  reports/figures/local_predictions_grid.png — 8 test images w/ predictions
  reports/figures/local_metrics_table.png    — per-class metrics table
  reports/local_metrics.json                 — {mAP50, mAP50_95, precision,
                                               recall, precision_no_helmet, ...}
  models/checkpoints/yolov8_final/weights/best.pt — promoted best model

Run: python -m src.training.local_eval
"""
from __future__ import annotations

import glob
import json
import logging
import os
import shutil
import sys

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("local_eval")

CLASSES = ["person", "helmet", "vest", "no-helmet", "no-vest", "boots"]
COL_C = {"person": (255, 200, 60), "helmet": (60, 200, 60), "vest": (60, 200, 60),
         "boots": (60, 200, 60),
         "no-helmet": (60, 60, 230), "no-vest": (60, 60, 230)}
FINAL = "models/checkpoints/yolov8_final/weights/best.pt"


def find_colab_weights() -> list[str]:
    out = []
    for p in glob.glob("models/checkpoints/*/weights/best.pt"):
        parts = p.replace("\\", "/").split("/")
        if any("final" in part for part in parts):
            continue
        out.append(p)
    return sorted(out)


def train_smoke() -> str:
    """Tiny CPU training run to validate the pipeline. Returns best.pt path."""
    from ultralytics import YOLO
    log.info("No Colab weights: training local CPU smoke baseline "
             "(yolov8n, 8 epochs, imgsz 320). Full training runs on Colab.")
    proj = os.path.abspath("models/smoke")  # absolute: ultralytics 8.4.x
    # mis-resolves relative project dirs on some Windows setups
    model = YOLO("yolov8n.pt")
    model.train(data=os.path.abspath("data/processed/dataset.yaml"), epochs=8,
                imgsz=320, batch=32, device="cpu", workers=0, project=proj,
                name="yolov8n_smoke", plots=True, save=True, exist_ok=True, verbose=False)
    best = os.path.join(proj, "yolov8n_smoke", "weights", "best.pt")
    if not os.path.exists(best):  # last-resort search
        cands = glob.glob(os.path.join(proj, "**", "best.pt"), recursive=True)
        if not cands:
            raise FileNotFoundError(f"best.pt not produced under {proj}")
        best = cands[0]
    # archive the real smoke-training curves for the report
    os.makedirs("reports/figures/local_baseline", exist_ok=True)
    for f in glob.glob("models/smoke/yolov8n_smoke/*.png") + \
             glob.glob("models/smoke/yolov8n_smoke/*.jpg"):
        shutil.copy(f, os.path.join("reports/figures/local_baseline",
                                    "lb_" + os.path.basename(f)))
        log.info("archived %s", f)
    with open("reports/COLAB_PENDING.txt", "w") as fh:
        fh.write("Full 60-epoch GPU training has NOT run yet.\n"
                 "A local CPU smoke baseline (yolov8n, 8 epochs, imgsz 320) is in use.\n"
                 "Run colab/train_ppe_colab.ipynb on a T4 GPU, copy weights/metrics back,\n"
                 "then re-run: python -m src.training.local_eval\n")
    return best


def archive_smoke_plots() -> None:
    """Copy Ultralytics plots from any smoke run into reports/figures/local_baseline/."""
    import glob as _glob
    os.makedirs("reports/figures/local_baseline", exist_ok=True)
    for f in _glob.glob("models/smoke/*/*.png") + _glob.glob("models/smoke/*/*.jpg"):
        if os.path.isfile(f):
            dst = os.path.join("reports/figures/local_baseline",
                               "lb_" + os.path.basename(f))
            if not os.path.exists(dst):
                shutil.copy(f, dst)
                log.info("archived %s", f)


def per_class_pr(box) -> tuple[list[float], list[float]]:
    """Per-class precision/recall straight from the val metrics object."""
    import numpy as np

    def _arr(v):
        a = np.array(v, dtype=float).ravel()
        return a.tolist()

    p, r = _arr(box.p), _arr(box.r)
    # pad in case a class has no predictions
    p += [0.0] * (len(CLASSES) - len(p))
    r += [0.0] * (len(CLASSES) - len(r))
    return p[:len(CLASSES)], r[:len(CLASSES)]


def draw_predictions_grid(model, out_path: str, title: str = "final model") -> None:
    exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    files = sorted(f for f in glob.glob("data/processed/images/test/*")
                   if f.lower().endswith(exts))[:8]
    fig, axes = plt.subplots(2, 4, figsize=(14, 8))
    for ax, img_f in zip(axes.ravel(), files):
        img = cv2.imread(img_f)
        r = model.predict(img_f, conf=0.35, imgsz=640, verbose=False)[0]
        for b in r.boxes:
            cid = int(b.cls.item())
            name = CLASSES[cid] if 0 <= cid < len(CLASSES) else f"cls{cid}"
            x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
            cv2.rectangle(img, (x1, y1), (x2, y2), COL_C.get(name, (255, 255, 255)), 2)
            cv2.putText(img, f"{name} {float(b.conf.item()):.2f}", (x1, max(12, y1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, COL_C.get(name, (255, 255, 255)), 1)
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        ax.set_title(os.path.basename(img_f)[:26], fontsize=8)
        ax.axis("off")
    fig.suptitle(f"Test predictions — {title}")
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("saved %s", out_path)


def draw_metrics_table(metrics: dict, out_path: str) -> None:
    rows = [[k, f"{v:.4f}" if isinstance(v, float) else str(v)]
            for k, v in metrics.items() if k != "source"]
    fig, ax = plt.subplots(figsize=(7, 2 + 0.4 * len(rows)))
    ax.axis("off")
    ax.set_title(f"Per-split metrics ({metrics.get('source', '')})")
    tbl = ax.table(cellText=rows, colLabels=["metric", "value"], loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("saved %s", out_path)


def main() -> None:
    from ultralytics import YOLO
    colab = find_colab_weights()
    metrics_path = "reports/colab_metrics.json"
    if colab and os.path.exists(metrics_path):
        with open(metrics_path) as fh:
            cm = json.load(fh)
        # pick best Colab model by mAP50
        def _m(k):
            v = cm.get(k, {})
            return float(v.get("mAP50", 0)) if isinstance(v, dict) else 0.0
        best_name = max(cm.keys(), key=_m)
        best = f"models/checkpoints/{best_name}/weights/best.pt"
        source = f"colab:{best_name}"
        log.info("Evaluating Colab weights %s", best)
        model = YOLO(best)
        r = model.val(data=os.path.abspath("data/processed/dataset.yaml"), split="test",
                      verbose=False, save=False, plots=False)
        metrics = {"source": source, "mAP50": float(r.box.map50),
                   "mAP50_95": float(r.box.map),
                   "precision": float(r.box.mp), "recall": float(r.box.mr)}
    elif colab:
        best = colab[0]
        source = f"colab-weights:{os.path.basename(os.path.dirname(os.path.dirname(best)))}"
        log.info("Evaluating Colab weights %s (no metrics.json; running val)", best)
        model = YOLO(best)
        r = model.val(data=os.path.abspath("data/processed/dataset.yaml"), split="test",
                      verbose=False, save=False, plots=False)
        metrics = {"source": source, "mAP50": float(r.box.map50),
                   "mAP50_95": float(r.box.map),
                   "precision": float(r.box.mp), "recall": float(r.box.mr)}
    else:
        # Reuse an existing local baseline (smoke run or promoted final) when
        # present so re-runs don't retrain from scratch.
        reuse = (glob.glob("models/smoke/*/weights/best.pt") +
                 glob.glob("models/checkpoints/yolov8_final/weights/best.pt"))
        if reuse:
            best = sorted(reuse)[0]
            source = "local-smoke:yolov8n (8ep, imgsz320, CPU)"
            log.info("Reusing existing local baseline %s (no retrain)", best)
            model = YOLO(best)
            r = model.val(data=os.path.abspath("data/processed/dataset.yaml"), split="test",
                          verbose=False, save=False, plots=False)
            metrics = {"source": source, "mAP50": float(r.box.map50),
                       "mAP50_95": float(r.box.map),
                       "precision": float(r.box.mp), "recall": float(r.box.mr)}
        else:
            try:
                best = train_smoke()
                source = "local-smoke:yolov8n (8ep, imgsz320, CPU)"
                model = YOLO(best)
                r = model.val(data=os.path.abspath("data/processed/dataset.yaml"), split="test",
                              verbose=False, save=False, plots=False)
                metrics = {"source": source, "mAP50": float(r.box.map50),
                           "mAP50_95": float(r.box.map),
                           "precision": float(r.box.mp), "recall": float(r.box.mr)}
            except Exception as exc:  # noqa: BLE001
                log.warning("Smoke training failed (%s); COCO placeholder path", exc)
                with open("reports/COLAB_PENDING.txt", "w") as fh:
                    fh.write(f"Colab training pending. Local smoke training failed: {exc}\n"
                             "Using COCO-pretrained yolov8s.pt placeholder.\n")
                model = YOLO("yolov8s.pt")
                best, source = "yolov8s.pt", "coco-placeholder"
                metrics = {"source": source, "mAP50": 0.0, "mAP50_95": 0.0,
                           "precision": 0.0, "recall": 0.0}

    if metrics["mAP50"] > 0:
        import numpy as _np
        p_cls, r_cls = per_class_pr(r.box)
        maps = _np.array(r.box.maps, dtype=float).ravel().tolist()
        metrics["precision_no_helmet"] = round(p_cls[3], 4)
        metrics["recall_no_helmet"] = round(r_cls[3], 4)
        metrics["per_class"] = {
            CLASSES[i]: {"precision": round(p_cls[i], 4),
                         "recall": round(r_cls[i], 4),
                         "mAP50": round(maps[i], 4) if i < len(maps) else 0.0}
            for i in range(len(CLASSES))}
        log.info("no-helmet P=%.3f R=%.3f mAP50=%.3f",
                 p_cls[3], r_cls[3], maps[3] if len(maps) > 3 else 0.0)
    else:
        metrics["precision_no_helmet"] = 0.0

    with open("reports/local_metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2)
    if os.path.isdir("models/smoke"):
        archive_smoke_plots()
    draw_predictions_grid(model, "reports/figures/local_predictions_grid.png",
                            title=metrics["source"])
    draw_metrics_table(metrics, "reports/figures/local_metrics_table.png")

    if best != "yolov8s.pt":
        os.makedirs(os.path.dirname(FINAL), exist_ok=True)
        if not (os.path.exists(FINAL) and os.path.samefile(best, FINAL)):
            shutil.copy(best, FINAL)
            log.info("Promoted %s -> %s", best, FINAL)
        else:
            log.info("Best model already at %s", FINAL)
    log.info("METRICS: %s", json.dumps(metrics))


if __name__ == "__main__":
    sys.exit(main())
