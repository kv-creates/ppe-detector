"""PPE Sentinel — Control Panel (home page, Windows 7 Aero style)."""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.ui.components import (api_health, inject_css, win7_groupbox,
                               win7_panel_close, win7_panel_open,
                               win7_status_bar, win7_tab_strip, win7_window)

st.set_page_config(page_title="PPE Sentinel", layout="wide")
inject_css()

with st.sidebar:
    st.markdown("### PPE Sentinel")
    st.markdown("Navigation")
    st.page_link("pages/1_Live_View.py", label="Live View", icon="📹")
    st.page_link("pages/2_Incident_Log.py", label="Incident Log", icon="📋")
    st.page_link("pages/3_Analytics.py", label="Analytics", icon="📊")
    st.page_link("pages/4_KPI_Report.py", label="KPI Report", icon="📈")
    st.markdown("---")
    ok = api_health()
    st.markdown(f"API status: **{':green[connected]' if ok else ':red[offline]'}**")

win7_window("PPE Sentinel — Control Panel", "◉")
win7_tab_strip("Home", ["Home", "Live View", "Incident Log", "Analytics", "KPI Report"])
win7_panel_open()

st.markdown("### Construction Site PPE Non-Compliance Detector")
st.markdown(
    "Real-time YOLOv8 monitoring of helmets, vests and boots. "
    "Open **Live View** to run detection, **Incident Log** for the violation "
    "history, **Analytics** for site statistics, and **KPI Report** for the "
    "formal evaluation."
)

c1, c2, c3 = st.columns(3)
with c1:
    win7_groupbox("Model", "YOLOv8m Colab (60 ep, T4)<br>mAP@0.5 = 0.695 (test)")
with c2:
    win7_groupbox("API", "FastAPI on 127.0.0.1:8000<br><a href='http://127.0.0.1:8000/docs'>/docs</a>")
with c3:
    win7_groupbox("Dataset", "1,400+ real images · 6 classes<br>see Analytics page")

st.markdown("---")
col_a, col_b = st.columns(2)
with col_a:
    if st.button("Open Live View"):
        st.switch_page("pages/1_Live_View.py")
with col_b:
    if st.button("Open KPI Report"):
        st.switch_page("pages/4_KPI_Report.py")

win7_panel_close()
win7_status_bar("Ready", "Model: YOLOv8m-Colab &nbsp;|&nbsp; API: "
                + ("connected" if ok else "offline — start uvicorn on :8000"))
