"""KPI Report — 5 KPI groupboxes + report download."""
import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.ui.components import (inject_css, win7_panel_close, win7_panel_open,
                               win7_status_bar, win7_tab_strip, win7_window)

st.set_page_config(page_title="PPE Sentinel — KPI Report", layout="wide")
inject_css()

win7_window("PPE Sentinel — KPI Report", "📈")
win7_tab_strip("KPI Report", ["Home", "Live View", "Video Monitor", "Incident Log", "Analytics", "KPI Report"])
win7_panel_open()

kpis = {}
if os.path.exists("reports/final_metrics.json"):
    with open("reports/final_metrics.json") as fh:
        kpis = json.load(fh)
else:
    st.warning("KPIs not computed yet. Run: python -m src.utils.kpi")


def card(name: str, target: str, actual: str, status: str, interp: str) -> None:
    mark = "✅" if status == "PASS" else "❌"
    st.markdown(
        f"<div class='win7-kpi'><div class='k-name'>{name}</div>"
        f"<div class='k-val'>{actual}</div>"
        f"<div>Target: {target} &nbsp; {mark} {status}</div>"
        f"<div style='font-size:11px;color:#555'>{interp}</div></div>",
        unsafe_allow_html=True,
    )


if kpis:
    cols = st.columns(5)
    b = kpis.get("business_ltifr", {})
    with cols[0]:
        card("LTIFR (business)", f"≤ {b.get('target')}", str(b.get("actual")),
             b.get("status", "?"), b.get("interpretation", ""))
    m1 = kpis.get("ml_precision_no_helmet", {})
    with cols[1]:
        card("Precision no-helmet", f"> {m1.get('target')}", str(m1.get("actual")),
             m1.get("status", "?"), m1.get("interpretation", ""))
    m2 = kpis.get("ml_map50", {})
    with cols[2]:
        card("mAP@0.5", f"> {m2.get('target')}", str(m2.get("actual")),
             m2.get("status", "?"), m2.get("interpretation", ""))
    dq = kpis.get("data_blurriness", {})
    with cols[3]:
        card("Blurriness ratio", f"< {dq.get('target')}", str(dq.get("actual")),
             dq.get("status", "?"), dq.get("interpretation", ""))
    pr = kpis.get("product_latency_p95_ms", {})
    with cols[4]:
        card("Latency p95", f"< {pr.get('target_ms')} ms",
             f"{pr.get('actual_ms')} ms", pr.get("status", "?"),
             pr.get("interpretation", ""))
    st.markdown(f"*Metrics source: `{kpis.get('source', '?')}`*")

st.markdown("---")
if os.path.exists("reports/final_report.md"):
    with open("reports/final_report.md", encoding="utf-8") as fh:
        st.download_button("Download full report (Markdown)", data=fh.read(),
                           file_name="final_report.md", mime="text/markdown")
else:
    st.info("Formal report is generated at the end of the pipeline "
            "(reports/final_report.md).")

win7_panel_close()
win7_status_bar("Ready", "KPI Report")
