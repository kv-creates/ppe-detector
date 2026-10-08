"""One-off: replace cloud notify_telegram block (lines 116-127) + add helpers."""
PATH = "D:/yolo/ppe-sentinel-live/app.py"

NEW_BLOCK = '''def notify_telegram(text: str, photo_bytes: bytes | None = None) -> bool:
    """Send text, or a photo alert with caption when bytes are given."""
    try:
        sec = st.secrets.get("telegram", {})
        token, chat = sec.get("bot_token"), sec.get("chat_id")
        if not (token and chat):
            return False
        import requests
        if photo_bytes:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": str(chat), "caption": text[:1024]},
                files={"photo": ("violation.jpg", photo_bytes, "image/jpeg")},
                timeout=20)
        else:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              data={"chat_id": str(chat), "text": text}, timeout=20)
        return r.status_code == 200 and r.json().get("ok", False)
    except Exception:  # noqa: BLE001
        return False


def jpeg_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def stamp() -> str:
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
'''

lines = open(PATH).read().splitlines(keepends=True)
assert lines[115].startswith("def notify_telegram"), lines[115]
assert lines[126].strip() == "return False", lines[126]
lines[115:127] = [NEW_BLOCK]
open(PATH, "w").write("".join(lines))
print("replaced ok")
