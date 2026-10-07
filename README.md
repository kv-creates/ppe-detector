# PPE Sentinel — Construction Site PPE Non-Compliance Detector

Real-time YOLOv8 system that watches construction-site camera feeds and flags
missing safety gear (helmets, high-visibility vests) the moment it appears.
Every detection carries a confidence score, a hazard zone, and a logged
incident with a snapshot for auditors. The interface is styled as a classic
Windows 7 desktop application.

A live demo build of the detector (no backend required) lives in a separate
repository: **ppe-sentinel-live**, deployable to Streamlit Community Cloud in
one click.

## Contents

- [How it works](#how-it-works)
- [Repository structure](#repository-structure)
- [Installation](#installation)
- [Quickstart (Windows)](#quickstart-windows)
- [Dataset](#dataset)
- [Training](#training)
- [Models](#models)
- [REST API](#rest-api)
- [Streamlit UI](#streamlit-ui)
- [KPIs](#kpis)
- [Tests](#tests)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [References](#references)
- [License](#license)

## How it works

```text
Camera / Upload ──> Streamlit UI (:8501) ──> FastAPI (:8000)
                                                 ├── YOLOv8 (.pt weights)
                                                 └── SQLite (violations.db)
Training (offline): Google Colab T4 GPU ──> models/checkpoints/
```

1. The operator opens **Live View** and picks a sample image, an upload, or a
   webcam snapshot.
2. The Streamlit app POSTs the frame to `POST /api/detect`.
3. The API runs the YOLOv8 model once, maps each box to a hazard zone
   (red/yellow/green frame thirds), flags violations (`no-helmet`,
   `no-vest`), saves a snapshot, and writes one database row per violation.
4. The UI overlays boxes on the frame, updates Safe/Unsafe/Compliance
   counters, and pops a Windows-style alert on violation.
5. **Incident Log** lists history with camera/class filters and CSV export.
   **Analytics** shows class, zone, and latency charts. **KPI Report** shows
   the five formal KPIs.

## Repository structure

```text
ppe-detector/
├── colab/                  # train_ppe_colab.ipynb (Colab T4 training)
├── configs/                # dataset.yaml (taxonomy, splits), app.yaml
├── data/                   # raw/ processed/ violations/ (blobs git-ignored)
├── models/checkpoints/     # Colab best.pt per model (tracked)
├── scripts/                # run_all / start (.sh + .bat), helpers
├── src/
│   ├── data/               # download, clean, merge, split, metadata
│   ├── inference/          # PPEPredictor, hazard zones
│   ├── api/                # FastAPI: main, routes, schemas, db
│   ├── ui/                 # Streamlit app (Win7 theme) + 4 pages
│   ├── utils/              # viz, screenshot, kpi
│   └── training/           # local_eval (Colab-weight eval / CPU smoke run)
└── tests/                  # pytest suite (13 tests)
```

Large artefacts (`data/*` blobs, `reports/`, `*.zip`, checkpoints'
`last.pt`) are git-ignored by design; see `.gitignore`. Regenerate data with
Section [Dataset](#dataset); weights download with Section
[Models](#models).

## Installation

Requirements: Python 3.10–3.12 (pinned stack), 3.13 works with newer
equivalents, Windows/macOS/Linux, 8 GB RAM. GPU optional locally (training
runs on Colab).

```bat
git clone https://github.com/kv-creates/ppe-detector.git
cd ppe-detector
pip install -r requirements.txt
python -m playwright install chromium
```

## Quickstart (Windows)

```bat
REM 1. Build the dataset (real sources only, no synthetic data)
python -m src.data.download
python -m src.data.clean
python -m src.data.merge
python -m src.data.split
python -m src.data.metadata
python -m src.utils.viz

REM 2. Evaluate / promote the model weights
python -m src.training.local_eval

REM 3. Launch backend + UI (two windows or start /min)
scripts\start.bat
REM UI  -> http://127.0.0.1:8501
REM Docs-> http://127.0.0.1:8000/docs

REM 4. Optional: screenshots, tests, KPIs
python -c "from src.utils.screenshot import screenshot_pages; screenshot_pages()"
python -m pytest tests/ -v
python -m src.utils.kpi
```

On Unix, `bash scripts/run_all.sh` runs the whole pipeline and
`bash scripts/start.sh` launches the servers.

## Dataset

100 percent real photographs — the pipeline contains zero synthetic data and
fails loudly instead of inventing any.

| Source | Images | Annotation | Access |
|---|---|---|---|
| Ultralytics Construction-PPE | 1,416 | YOLO TXT (11 classes) | Public download, no key |
| SHWD (GitHub demo frames) | 11 | Unlabelled (background) | Public git clone |
| Roboflow Hard Hat Workers | 0 | YOLO TXT | Skipped: needs reachable mirror |
| Kaggle andrewmvd/hard-hat-detection | 0 | Pascal VOC XML | Skipped: needs `kaggle` credentials |
| HuggingFace keremberke/construction-site-safety | 0 | YOLO TXT | Skipped: needs HF token |
| BYOD (`data/raw/byod/`) | user-supplied | YOLO TXT or VOC XML | Drop-in, zero code changes |

After cleaning (pHash dedup, 320 px minimum, corrupt filter): **1,331
images, 7,933 boxes**, split 933/201/197 (70/15/15, stratified, seed 42).

Unified 6-class taxonomy — every box traces to a real annotation:

| ID | Class | Origin |
|---|---|---|
| 0 | person | Native `Person` labels |
| 1 | helmet | Native `helmet` labels |
| 2 | vest | Native `vest` labels |
| 3 | no-helmet | Native `no_helmet` labels |
| 4 | no-vest | Derived torso boxes for vest-less workers (documented geometric rule) |
| 5 | boots | Native `boots` labels |

Out-of-scope source labels (`gloves`, `goggles`, `no_gloves`,
`no_goggle`, `no_boots`, `none`) are dropped and counted in the merge log.
Full documentation is generated at `reports/dataset_card.md` (git-ignored).

## Training

### Official training — Google Colab (T4 GPU)

1. Zip `data/processed/images` + `data/processed/labels` to `dataset.zip`
   (top level must be exactly `images/` and `labels/`) and upload to
   `MyDrive/ppe_detector/dataset.zip`.
2. Open `colab/train_ppe_colab.ipynb` in Colab, select the T4 GPU runtime,
   run all cells: trains YOLOv8n, YOLOv8s, YOLOv8m (60 epochs, imgsz 640),
   evaluates on the test split to `metrics.json`, archives all plots.
3. Copy back: `weights/*` to `models/checkpoints/`, `plots/*` to
   `reports/figures/colab_plots/`, `metrics.json` to
   `reports/colab_metrics.json`.
4. Refresh local artefacts:
   `python -m src.training.local_eval && python -m src.utils.kpi`.

### Local validation — CPU smoke run

`python -m src.training.local_eval` without Colab weights trains a tiny
YOLOv8n baseline (8 epochs, imgsz 320, CPU) so the pipeline is verifiable
without a GPU. With Colab weights present it instead evaluates the best
model, redraws the prediction grid, and promotes it to
`models/checkpoints/yolov8_final/`.

## Models

| Model | Params | Size | mAP@0.5 (test) | Precision | Recall |
|---|---|---|---|---|---|
| YOLOv8n (60 ep, T4) | 3.0 M | 6.2 MB | 0.6825 | 0.6757 | 0.6791 |
| YOLOv8s (60 ep, T4) | 11.2 M | 22.5 MB | 0.6528 | 0.6810 | 0.6492 |
| YOLOv8m (60 ep, T4, deployed) | 25.9 M | 52.0 MB | 0.6951 | 0.7163 | 0.6976 |

Per-class detail (deployed YOLOv8m): person 0.48, helmet 0.45, vest 0.56,
no-helmet 0.06, no-vest 0.23, boots 0.38 (mAP@0.5). The weak no-helmet score
(282 native samples, tiny bare heads) is the documented data ceiling — the
prescribed fix is more violation photos (Kaggle/BYOD), not more parameters.

## REST API

Base URL `http://127.0.0.1:8000`. Interactive docs at `/docs`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | `{"status": "ok"}` |
| POST | `/api/detect?camera_id=cam-01` | Multipart image; returns detections, zones, violation flag, latency; persists violations + snapshot |
| GET | `/api/violations?camera_id=&class_name=&limit=` | Filtered incident history |
| GET | `/api/violations/{id}/snapshot` | Snapshot JPEG for an incident |
| GET | `/api/kpis` | Computed KPI JSON |

Detection schema (per box): `class_id, class_name, conf, bbox_xyxy, zone`
where zone is `red`, `yellow`, or `green` by frame third.

## Streamlit UI

Windows 7 Aero styling (Segoe UI, blue title bars, classic tabs/buttons,
status bar). Pages:

- **Control Panel** (`app.py`) — overview, model/dataset status, navigation.
- **Live View** — sample/upload/webcam input, camera picker, confidence
  slider, overlay frame, Safe/Unsafe/Compliance counters, violation alert.
- **Video Monitor** — upload a site MP4 (or run the demo reel), sampled
  scoring with progress bar, annotated MP4 playback/download, cooldown-guarded
  Telegram photo alerts (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`).

Alert policy is red-zone-only by default (overhead-hazard area): yellow/green
violations log silently. Override per call or with
`TELEGRAM_ZONES="red,yellow"`. One alert per camera and violation class every
2 minutes (`telegram.cooldown_s`) so incident bursts do not spam the chat.
- **Incident Log** — SQLite-backed table, camera/class filters, CSV export.
- **Analytics** — class distribution, zone heatmap, latency histogram
  (Plotly, Win7 theme).
- **KPI Report** — five KPI cards with target/actual/status, report download.

## KPIs

Targets describe the finished production system (GPU inference, larger
violation sample); actuals are measured on the reference machine and
reported honestly.

| Type | Name | Target | Actual | Status |
|---|---|---|---|---|
| Business | LTIFR reduction | ≤ 1.92 | 2.084 | FAIL |
| ML | Precision (no-helmet) | > 0.85 | 0.308 | FAIL |
| ML | mAP@0.5 | > 0.72 | 0.695 | FAIL |
| Data | Blurriness ratio | < 3% | 6.0% | FAIL |
| Product | Alert latency p95 | < 500 ms | 1,672 ms (i3 CPU) | FAIL |

## Tests

```bat
python -m pytest tests/ -v
```

13 tests cover the dataset manifest/split/label format, model loading and
inference output, live API endpoints, and UI module/CSS checks.

## Configuration

- `configs/dataset.yaml` — paths, 6-class list, 70/15/15 split, seed,
  cleaning thresholds.
- `configs/app.yaml` — API/UI hosts and ports, weight resolution order,
  confidence threshold (0.30), violation classes, database URL.
- Gated sources: set `KAGGLE_USERNAME`/`KAGGLE_KEY` for Kaggle,
  `hf auth login` for HuggingFace, then re-run `python -m src.data.download`.
- Bring your own data: put images in `data/raw/byod/images/` with YOLO TXT
  (+ `classes.txt`) or VOC XML labels — the pipeline ingests them untouched.

## Troubleshooting

- `dataset.zip` not found in Colab: confirm the exact Drive path
  `MyDrive/ppe_detector/dataset.zip` (case-sensitive) and that the upload
  finished; `!ls` the folder before unzipping.
- Colab out of memory on YOLOv8m: lower `batch=16` to `batch=8`.
- API offline in the UI: start
  `python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000`.
- Ultralytics writes runs to a strange `path/` folder on some Windows
  setups: `src/training/local_eval.py` already uses absolute project paths
  to avoid this.
- Python 3.13: several pins in `requirements.txt` have no 3.13 wheels;
  use Python 3.10–3.12 for the pinned stack or accept newer equivalents.

## References

- Redmon et al., "You Only Look Once" (CVPR 2016).
- Jocher et al., Ultralytics YOLOv8 (2023–2024).
- Dalvi et al., Construction-PPE dataset, Ultralytics (2025).
- SHWD, Roboflow Hard Hat Workers, Kaggle andrewmvd/hard-hat-detection.
- OSHA 29 CFR 1926 Subpart E; ANSI/ISEA 107.

## License

MIT — see `LICENSE`. Dataset licensing (AGPL-3.0 for Construction-PPE)
applies to the data, not to this code.
