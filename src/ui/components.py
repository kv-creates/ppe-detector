"""Reusable Windows 7 chrome: window frame, groupbox, tab strip, status bar."""
from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    with open("src/ui/win7.css") as fh:
        st.markdown(f"<style>{fh.read()}</style>", unsafe_allow_html=True)


def win7_window(title: str, icon: str = "◉") -> None:
    st.markdown(
        f"<div class='win7-titlebar'>{icon}&nbsp;&nbsp;{title}"
        "<span class='winbtns'><span>&#95;</span><span>&#9744;</span>"
        "<span>&#10005;</span></span></div>",
        unsafe_allow_html=True,
    )


def win7_panel_open() -> None:
    st.markdown("<div class='win7-panel'>", unsafe_allow_html=True)


def win7_panel_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def win7_groupbox(label: str, body_html: str) -> None:
    st.markdown(
        f"<div class='win7-groupbox'><div class='gb-label'>{label}</div>"
        f"{body_html}</div>",
        unsafe_allow_html=True,
    )


def win7_tab_strip(active_tab: str, tabs: list[str]) -> None:
    cells = "".join(
        f"<div class='win7-tab{' active' if t == active_tab else ''}'>{t}</div>"
        for t in tabs
    )
    st.markdown(f"<div class='win7-tabs'>{cells}</div>", unsafe_allow_html=True)


def win7_status_bar(text_left: str, text_right: str) -> None:
    st.markdown(
        f"<div class='win7-statusbar'><span>{text_left}</span>"
        f"<span>{text_right}</span></div>",
        unsafe_allow_html=True,
    )


def api_health() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=3) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


BOX_COLORS = {
    "person": (255, 200, 60), "helmet": (60, 200, 60), "vest": (60, 200, 60),
    "boots": (60, 200, 60),
    "no-helmet": (60, 60, 230), "no-vest": (60, 60, 230),
}
COMPLIANT = {"helmet", "vest", "boots"}
VIOLATION = {"no-helmet", "no-vest"}


def call_detect(image_bytes: bytes, camera_id: str = "cam-01",
                filename: str = "frame.jpg") -> dict:
    """POST image bytes to the FastAPI /api/detect endpoint."""
    import requests
    r = requests.post("http://127.0.0.1:8000/api/detect",
                      params={"camera_id": camera_id},
                      files={"file": (filename, image_bytes, "image/jpeg")},
                      timeout=120)
    r.raise_for_status()
    return r.json()


def draw_boxes(img_bgr, detections: list[dict]):
    """Overlay detection boxes + labels (BGR input -> RGB output array)."""
    import cv2
    img = img_bgr.copy()
    for d in detections:
        x1, y1, x2, y2 = map(int, d["bbox_xyxy"])
        col = BOX_COLORS.get(d["class_name"], (255, 255, 255))
        cv2.rectangle(img, (x1, y1), (x2, y2), col, 2)
        cv2.putText(img, f"{d['class_name']} {d['conf']:.2f}", (x1, max(12, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def compliance_stats(detections: list[dict]) -> tuple[int, int, float]:
    safe = sum(1 for d in detections if d["class_name"] in COMPLIANT)
    unsafe = sum(1 for d in detections if d["class_name"] in VIOLATION)
    pct = 100.0 * safe / (safe + unsafe) if (safe + unsafe) else 100.0
    return safe, unsafe, round(pct, 1)
