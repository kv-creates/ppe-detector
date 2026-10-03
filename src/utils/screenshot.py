"""Figure helpers: raw matplotlib PNG export + Playwright UI screenshots."""
from __future__ import annotations

import os


def save_fig(fig, name: str, dpi: int = 150) -> str:
    """Save a matplotlib figure as a raw PNG under reports/figures/."""
    os.makedirs("reports/figures", exist_ok=True)
    path = os.path.join("reports/figures", f"{name}.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    print(f"saved {path}")
    return path


def screenshot_pages(base: str = "http://127.0.0.1:8501") -> list[str]:
    """Capture every Streamlit page as a raw full-page PNG (Playwright)."""
    from playwright.sync_api import sync_playwright

    pages = [
        ("ui_live_view", f"{base}/Live_View"),
        ("ui_incident_log", f"{base}/Incident_Log"),
        ("ui_analytics", f"{base}/Analytics"),
        ("ui_kpi_report", f"{base}/KPI_Report"),
    ]
    os.makedirs("reports/figures", exist_ok=True)
    saved = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, url in pages:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(10000)  # let detection + charts render
            out = f"reports/figures/{name}.png"
            page.screenshot(path=out, full_page=True)
            saved.append(out)
            print(f"saved {out}")
        browser.close()
    return saved
