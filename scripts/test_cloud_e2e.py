"""End-to-end test of the cloud app: image detect + video upload + screenshots."""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8502"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE + "/", wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(8000)
    # 1) image detect flow: click Run Detection (sample preselected)
    pg.get_by_role("button", name="Run Detection").click()
    pg.wait_for_timeout(60000)  # cold model load + inference on CPU
    pg.screenshot(path="cloud_detect.png")
    print("detect traceback on page:", "Traceback" in pg.content())
    print("violation shown:", "VIOLATION" in pg.content())
    # 2) video flow: open Source selectbox (first combobox) and pick video
    pg.locator("div[data-testid='stSelectbox']").first.click()
    pg.wait_for_timeout(1000)
    pg.get_by_text("Upload video (MP4)", exact=True).click()
    pg.wait_for_timeout(2000)
    pg.set_input_files("input[type=file]", "D:/yolo/ppe-detector/data/violations/demo_site.mp4")
    pg.wait_for_timeout(3000)
    pg.get_by_role("button", name="Process Video").click()
    pg.wait_for_timeout(180000)
    pg.screenshot(path="cloud_video.png", full_page=True)
    print("video traceback on page:", "Traceback" in pg.content())
    b.close()
print("done")
