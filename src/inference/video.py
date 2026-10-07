"""Video-file monitoring: sampled YOLO inference + alerts + annotated export.

process_video(path, ...) reads a site video, scores every Nth frame with the
local PPEPredictor (no HTTP round-trip), writes each violation to SQLite with
a snapshot, fires cooldown-guarded Telegram alerts, and renders an annotated
MP4 (H264 if available, else mp4v) with boxes + a running violation banner.

Returns a summary dict consumed by the Streamlit Video Monitor page.
"""
from __future__ import annotations

import datetime
import logging
import os

import cv2

log = logging.getLogger("video")


def process_video(path: str, camera_id: str = "cam-01", conf: float = 0.30,
                  sample_every: int = 5, out_path: str | None = None,
                  progress_cb=None, notify: bool = True,
                  alert_zones: list[str] | None = None) -> dict:
    from src.api import db
    from src.inference.predictor import VIOLATIONS, PPEPredictor
    from src.inference.zones import get_zone
    from src.utils import telegram

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError(f"could not open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    pred = PPEPredictor(conf=conf)
    if out_path is None:
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.abspath(f"data/violations/{base}_annotated.mp4")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    writer = None
    use_imageio = False
    try:  # imageio-ffmpeg bundles a real H264 encoder (portable, browser-safe)
        import imageio.v2 as imageio
        out_fps = max(1.0, fps / max(1, sample_every))
        writer = imageio.get_writer(out_path, fps=out_fps, codec="libx264",
                                    quality=8, macro_block_size=None)
        use_imageio = True
    except Exception as exc:  # noqa: BLE001
        log.warning("imageio writer unavailable (%s); trying cv2", exc)
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        writer = cv2.VideoWriter(out_path, fourcc, fps / max(1, sample_every), (w, h))
        if not writer.isOpened():
            writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"),
                                     fps / max(1, sample_every), (w, h))

    db.init_db()
    session = db.get_session()
    frames_seen = frames_scored = 0
    violations = 0
    alerts_sent = 0
    counts: dict[str, int] = {}
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frames_seen += 1
            if (frames_seen - 1) % sample_every:
                if progress_cb and total:
                    progress_cb(min(1.0, frames_seen / total))
                continue
            frames_scored += 1
            out = pred.predict(frame, camera_id=camera_id)
            for d in out["detections"]:
                counts[d["class_name"]] = counts.get(d["class_name"], 0) + 1
                if d["class_name"] not in VIOLATIONS:
                    continue
                violations += 1
                ts = datetime.datetime.now().isoformat(timespec="seconds")
                snap = os.path.abspath(
                    f"data/violations/{camera_id}_vid{frames_seen}_{d['class_name']}.jpg")
                cv2.imwrite(snap, frame)
                session.add(db.Violation(timestamp=ts, camera_id=camera_id,
                                         class_name=d["class_name"], conf=d["conf"],
                                         zone=d["zone"], snapshot_path=snap))
                if notify and telegram.configured():
                    _, buf = cv2.imencode(".jpg", frame)
                    if telegram.send_violation_alert(
                            camera_id, d["class_name"], d["conf"], d["zone"],
                            frames_seen, snapshot=buf.tobytes(),
                            allowed_zones=alert_zones):
                        alerts_sent += 1
            # overlay + banner
            for d in out["detections"]:
                x1, y1, x2, y2 = map(int, d["bbox_xyxy"])
                col = (60, 60, 230) if d["class_name"] in VIOLATIONS else (60, 200, 60)
                cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
                cv2.putText(frame, f"{d['class_name']} {d['conf']:.2f}", (x1, max(12, y1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
            if out["violation"]:
                cv2.rectangle(frame, (0, 0), (w, 36), (0, 0, 200), -1)
                cv2.putText(frame, "PPE VIOLATION - ALERT SENT", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            writer.write(frame) if not use_imageio else writer.append_data(
                cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if progress_cb and total:
                progress_cb(min(1.0, frames_seen / total))
        session.commit()
    finally:
        session.close()
        cap.release()
        try:
            writer.close() if use_imageio else writer.release()
        except Exception:  # noqa: BLE001
            pass
    log.info("video done: %d scored, %d violations, %d alerts",
             frames_scored, violations, alerts_sent)
    return {"frames_seen": frames_seen, "frames_scored": frames_scored,
            "violations": violations, "alerts_sent": alerts_sent,
            "class_counts": counts, "annotated_path": out_path,
            "telegram": telegram.configured()}
