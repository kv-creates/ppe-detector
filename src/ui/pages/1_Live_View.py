"""Live View — detection on sample / upload / webcam snapshot."""
import glob
import os
import sys

import cv2
import numpy as np
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.ui.components import (api_health, call_detect, compliance_stats,
                               draw_boxes, inject_css, win7_panel_close,
                               win7_panel_open, win7_status_bar,
                               win7_tab_strip, win7_window)

st.set_page_config(page_title="PPE Sentinel — Live View", layout="wide")
inject_css()

win7_window("PPE Sentinel — Live View", "📹")
win7_tab_strip("Live View", ["Home", "Live View", "Incident Log", "Analytics", "KPI Report"])
win7_panel_open()

ok = api_health()
if not ok:
    st.markdown("<div class='win7-alert red'>⚠ API offline — start: "
                "<code>uvicorn src.api.main:app --host 127.0.0.1 --port 8000</code></div>",
                unsafe_allow_html=True)

source = st.selectbox("Source", ["Sample image", "Upload image", "Webcam snapshot"])
camera_id = st.selectbox("Camera", ["cam-01", "cam-02", "cam-03"])
conf = st.slider("Confidence threshold", 0.05, 0.80, 0.30, 0.05)

img_bgr, fname = None, "frame.jpg"
if source == "Sample image":
    exts = (".jpg", ".jpeg", ".png")
    samples = sorted(f for f in glob.glob("data/processed/images/test/*")
                     if f.lower().endswith(exts))[:12]
    choice = st.selectbox("Sample", samples, format_func=os.path.basename)
    if choice:
        img_bgr = cv2.imread(choice)
        fname = os.path.basename(choice)
elif source == "Upload image":
    up = st.file_uploader("Choose a JPG/PNG", type=["jpg", "jpeg", "png"])
    if up:
        img_bgr = cv2.imdecode(np.frombuffer(up.read(), np.uint8), cv2.IMREAD_COLOR)
        fname = up.name
else:
    shot = st.camera_input("Webcam snapshot")
    if shot:
        img_bgr = cv2.imdecode(np.frombuffer(shot.read(), np.uint8), cv2.IMREAD_COLOR)

if st.button("Run Detection", disabled=(img_bgr is None) or not ok) or (
        img_bgr is not None and ok and st.session_state.get("auto_ran") is None):
    st.session_state["auto_ran"] = True
    _, buf = cv2.imencode(".jpg", img_bgr)
    with st.spinner("Detecting..."):
        try:
            resp = call_detect(buf.tobytes(), camera_id=camera_id, filename=fname)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Detection failed: {exc}")
            resp = None
    if resp:
        overlay = draw_boxes(img_bgr, resp["detections"])
        st.image(overlay, caption=f"{fname} — {resp['model']} ({resp['latency_ms']} ms)",
                 use_container_width=True)
        safe, unsafe, pct = compliance_stats(resp["detections"])
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"<div class='win7-kpi'><div class='k-name'>Safe count</div>"
                        f"<div class='k-val'>{safe}</div></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='win7-kpi'><div class='k-name'>Unsafe count</div>"
                        f"<div class='k-val'>{unsafe}</div></div>", unsafe_allow_html=True)
        with m3:
            st.markdown(f"<div class='win7-kpi'><div class='k-name'>Compliance %</div>"
                        f"<div class='k-val'>{pct}%</div></div>", unsafe_allow_html=True)
        if resp["violation"]:
            st.markdown("<div class='win7-alert red'>⚠ <b>PPE VIOLATION DETECTED</b> — "
                        "supervisor notified, incident logged.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='win7-alert'>✔ No violation — site compliant.</div>",
                        unsafe_allow_html=True)
        with st.expander("Raw detections"):
            st.json(resp["detections"])

win7_panel_close()
win7_status_bar("Ready", f"Camera: {camera_id} &nbsp;|&nbsp; Conf: {conf:.2f}")
