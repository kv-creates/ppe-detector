"""Analytics — Win7-themed Plotly charts (class distribution, zones, latency)."""
import csv
import json
import os
import sys

import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.ui.components import (inject_css, win7_panel_close, win7_panel_open,
                               win7_status_bar, win7_tab_strip, win7_window)

st.set_page_config(page_title="PPE Sentinel — Analytics", layout="wide")
inject_css()

win7_window("PPE Sentinel — Analytics", "📊")
win7_tab_strip("Analytics", ["Home", "Live View", "Video Monitor", "Incident Log", "Analytics", "KPI Report"])
win7_panel_open()

WIN7 = {"paper_bgcolor": "white", "plot_bgcolor": "white",
        "font": {"family": "Segoe UI", "size": 12, "color": "#1A1A1A"},
        "xaxis": {"linecolor": "#A0A0A0", "gridcolor": "#E5E5E5"},
        "yaxis": {"linecolor": "#A0A0A0", "gridcolor": "#E5E5E5"}}

tab = st.radio("View", ["Class Distribution", "Zone Heatmap", "Latency Histogram"],
               horizontal=True)

if tab == "Class Distribution":
    # ground-truth distribution from metadata (full dataset)
    counts: dict[str, int] = {}
    with open("data/processed/metadata.csv") as fh:
        for r in csv.DictReader(fh):
            for c in (r["classes_present"] or "").split(";"):
                if c:
                    counts[c] = counts.get(c, 0) + 1
    fig = px.bar(x=list(counts.keys()), y=list(counts.values()),
                 labels={"x": "class", "y": "images containing class"},
                 title="Class distribution (ground truth, all splits)",
                 color_discrete_sequence=["#3B6EA5"])
    fig.update_layout(**WIN7)
    st.plotly_chart(fig, use_container_width=True)

elif tab == "Zone Heatmap":
    zones = {"red": 0, "yellow": 0, "green": 0}
    src = "live"
    if os.path.exists("reports/analytics_cache.json"):
        with open("reports/analytics_cache.json") as fh:
            cache = json.load(fh)
        zones.update(cache.get("zone_counts", {}))
        src = f"val-set cache ({cache.get('n_images', 0)} images, {cache.get('model', '')})"
    fig = px.bar(x=list(zones.keys()), y=list(zones.values()),
                 labels={"x": "hazard zone", "y": "detections"},
                 title=f"Detections per hazard zone — {src}",
                 color_discrete_sequence=["#C0392B", "#E67E22", "#27AE60"])
    fig.update_layout(**WIN7)
    st.plotly_chart(fig, use_container_width=True)

else:
    lat = []
    if os.path.exists("reports/analytics_cache.json"):
        with open("reports/analytics_cache.json") as fh:
            lat = json.load(fh).get("latencies_ms", [])
    if lat:
        fig = px.histogram(x=lat, nbins=20, title="Inference latency histogram (val set)",
                           labels={"x": "latency (ms)"},
                           color_discrete_sequence=["#3B6EA5"])
        fig.update_layout(**WIN7)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"p50 = {sorted(lat)[len(lat)//2]:.0f} ms · "
                    f"p95 = {sorted(lat)[int(len(lat)*0.95)]:.0f} ms · n = {len(lat)}")
    else:
        st.warning("No latency cache. Run: python src/ui/analytics_cache.py")

win7_panel_close()
win7_status_bar("Ready", "Analytics")
