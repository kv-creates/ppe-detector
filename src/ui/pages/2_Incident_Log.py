"""Incident Log — violation history with filters + CSV export."""
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.ui.components import (inject_css, win7_panel_close, win7_panel_open,
                               win7_status_bar, win7_tab_strip, win7_window)

st.set_page_config(page_title="PPE Sentinel — Incident Log", layout="wide")
inject_css()

win7_window("PPE Sentinel — Incident Log", "📋")
win7_tab_strip("Incident Log", ["Home", "Live View", "Incident Log", "Analytics", "KPI Report"])
win7_panel_open()


def fetch_violations(camera: str, cls: str) -> pd.DataFrame:
    import requests
    params = {}
    if camera != "All":
        params["camera_id"] = camera
    if cls != "All":
        params["class_name"] = cls
    r = requests.get("http://127.0.0.1:8000/api/violations",
                     params=params, timeout=30)
    r.raise_for_status()
    return pd.DataFrame(r.json())


f1, f2, f3 = st.columns(3)
with f1:
    f_camera = st.selectbox("Camera", ["All", "cam-01", "cam-02", "cam-03"])
with f2:
    f_class = st.selectbox("Class", ["All", "no-helmet", "no-vest"])
with f3:
    st.markdown("<br>", unsafe_allow_html=True)
    refresh = st.button("Refresh")

try:
    df = fetch_violations(f_camera, f_class)
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not reach API: {exc}")
    df = pd.DataFrame()

if not df.empty:
    st.markdown(f"**{len(df)} incident(s)**")
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode()
    st.download_button("Download CSV", data=csv, file_name="incidents.csv",
                       mime="text/csv")
else:
    st.markdown("<div class='win7-alert'>No incidents recorded yet. Run Live View "
                "detections with violations to populate this log.</div>",
                unsafe_allow_html=True)

win7_panel_close()
win7_status_bar("Ready", "Incident Log")
