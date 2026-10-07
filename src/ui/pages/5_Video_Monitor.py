"""Video Monitor — upload a site video, get violations + Telegram alerts."""
import glob
import os
import sys
import tempfile

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.inference.video import process_video
from src.ui.components import (inject_css, win7_panel_close, win7_panel_open,
                               win7_status_bar, win7_tab_strip, win7_window)
from src.utils import telegram

st.set_page_config(page_title="PPE Sentinel — Video Monitor", layout="wide")
inject_css()

win7_window("PPE Sentinel — Video Monitor", "🎬")
win7_tab_strip("Video Monitor", ["Home", "Live View", "Video Monitor",
                                 "Incident Log", "Analytics", "KPI Report"])
win7_panel_open()

tg_ok = telegram.configured()
st.markdown(
    "<div class='win7-alert'>Telegram alerts: <b>{}</b> {}</div>".format(
        "CONNECTED" if tg_ok else "NOT CONFIGURED",
        "— violations will message your bot." if tg_ok
        else "— set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID to enable."),
    unsafe_allow_html=True)

src = st.selectbox("Source", ["Sample site reel", "Upload video file"])
camera_id = st.selectbox("Camera", ["cam-01", "cam-02", "cam-03"])
c1, c2 = st.columns(2)
with c1:
    conf = st.slider("Confidence threshold", 0.05, 0.80, 0.30, 0.05)
with c2:
    sample_every = st.slider("Analyse every Nth frame", 1, 15, 5)
notify = st.checkbox("Send Telegram alerts on violation", value=True,
                     disabled=not tg_ok)
alert_zones = st.multiselect("Alert on zones", ["red", "yellow", "green"],
                             default=["red"],
                             help="Red = overhead-hazard area (recommended). "
                                  "Alerts fire only for violations in these zones.")

video_path, cleanup = None, None
if src == "Sample site reel":
    reels = sorted(glob.glob("data/violations/demo_site*.mp4") +
                   glob.glob("samples/*.mp4"))
    if reels:
        video_path = st.selectbox("Reel", reels, format_func=os.path.basename)
    else:
        st.warning("No demo reel yet. Run: python scripts/make_demo_reel.py")
else:
    up = st.file_uploader("Upload MP4 / AVI / MOV", type=["mp4", "avi", "mov", "mkv"])
    if up:
        fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(up.name)[1])
        with os.fdopen(fd, "wb") as fh:
            fh.write(up.read())
        video_path, cleanup = tmp, True

if st.button("Process Video", disabled=video_path is None):
    bar = st.progress(0, text="Opening video...")
    with st.spinner("Scoring frames (CPU ~1-2 s/frame, GPU much faster)..."):
        try:
            summary = process_video(
                video_path, camera_id=camera_id, conf=conf,
                sample_every=sample_every, notify=notify and tg_ok,
                alert_zones=alert_zones,
                progress_cb=lambda f: bar.progress(min(1.0, f), text=f"Scoring... {f:.0%}"))
        except Exception as exc:  # noqa: BLE001
            st.error(f"Processing failed: {exc}")
            summary = None
    if cleanup:
        os.remove(video_path)
    if summary:
        bar.progress(1.0, text="Done.")
        m1, m2, m3, m4 = st.columns(4)
        for col, name, val in ((m1, "Frames scored", summary["frames_scored"]),
                               (m2, "Violations", summary["violations"]),
                               (m3, "Telegram alerts", summary["alerts_sent"]),
                               (m4, "Telegram", "on" if summary["telegram"] else "off")):
            with col:
                st.markdown(f"<div class='win7-kpi'><div class='k-name'>{name}</div>"
                            f"<div class='k-val'>{val}</div></div>",
                            unsafe_allow_html=True)
        st.markdown("**Annotated output video** (boxes + violation banner):")
        st.video(summary["annotated_path"])
        with open(summary["annotated_path"], "rb") as fh:
            st.download_button("Download annotated MP4", data=fh.read(),
                               file_name=os.path.basename(summary["annotated_path"]),
                               mime="video/mp4")
        with st.expander("Per-class counts"):
            st.json(summary["class_counts"])

with st.expander("How to connect your Telegram bot (2 minutes)"):
    st.markdown("1. Open Telegram, chat with **@BotFather**: send `/newbot`, "
                "pick a name — it replies with a token like `123:ABC`.\n"
                "2. Open `https://t.me/<your_bot_name>`, press Start, send any message.\n"
                "3. Open `https://api.telegram.org/bot<token>/getUpdates` in a browser "
                "and copy the number after `\"id\"` inside `chat` — that is your chat ID.\n"
                "4. Set environment variables and restart the API/UI:\n"
                "`TELEGRAM_BOT_TOKEN=<token>` and `TELEGRAM_CHAT_ID=<id>`.\n"
                "Alerts are capped at one per camera+violation every 2 minutes "
                "(`telegram.cooldown_s` in `configs/app.yaml`) so a long incident "
                "does not spam the chat.")

win7_panel_close()
win7_status_bar("Ready", f"Camera: {camera_id} &nbsp;|&nbsp; Telegram: "
                + ("connected" if tg_ok else "offline"))
