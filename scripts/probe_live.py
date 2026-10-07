"""Detailed probe of Live View render state."""
from playwright.sync_api import sync_playwright
import re

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto("http://127.0.0.1:8501/Live_View", wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(45000)
    html = pg.content()
    for token in ["PPE VIOLATION DETECTED", "No violation", "Unsafe count",
                  "Telegram photo alert", "Telegram: not configured",
                  "Compliance %", "Raw detections"]:
        print(f"{token!r}: {token in html}")
    b.close()
