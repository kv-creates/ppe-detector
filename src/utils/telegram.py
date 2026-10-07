"""Telegram alert sender (direct Bot API, no extra dependency).

Configuration (first found wins):
  1. Streamlit secrets (cloud): st.secrets["telegram"]["bot_token" | "chat_id"]
  2. Environment: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
  3. configs/app.yaml -> telegram: {bot_token, chat_id, cooldown_s}

send_violation_alert() is cooldown-guarded per (camera_id, class_name) so a
long violation burst does not spam the chat. Returns True on HTTP 200.
"""
from __future__ import annotations

import logging
import os
import time

import requests
import yaml

log = logging.getLogger("telegram")
API = "https://api.telegram.org/bot{token}/{method}"
_last_sent: dict[tuple[str, str], float] = {}


def load_settings() -> dict:
    try:  # Streamlit Cloud secrets (import is cheap; fails outside runtime)
        import streamlit as st
        sec = st.secrets.get("telegram", {})
        if sec.get("bot_token") and sec.get("chat_id"):
            return {"bot_token": str(sec["bot_token"]),
                    "chat_id": str(sec["chat_id"]),
                    "cooldown_s": int(sec.get("cooldown_s", 120)),
                    "zones": [z.strip().lower() for z in
                              str(sec.get("zones", "red")).split(",")]}
    except Exception:  # noqa: BLE001
        pass
    cfg = {}
    try:
        with open("configs/app.yaml") as fh:
            cfg = (yaml.safe_load(fh) or {}).get("telegram", {}) or {}
    except Exception:  # noqa: BLE001
        pass
    zones = os.environ.get("TELEGRAM_ZONES", None)
    if zones is None:
        zones = cfg.get("zones", ["red"])
    if isinstance(zones, str):
        zones = [z.strip().lower() for z in zones.split(",")]
    return {
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", cfg.get("bot_token", "")),
        "chat_id": os.environ.get("TELEGRAM_CHAT_ID", cfg.get("chat_id", "")),
        "cooldown_s": int(os.environ.get("TELEGRAM_COOLDOWN_S",
                                         cfg.get("cooldown_s", 120))),
        "zones": [str(z).lower() for z in zones],
    }


def configured() -> bool:
    s = load_settings()
    return bool(s["bot_token"] and s["chat_id"])


def _call(method: str, payload: dict, files: dict | None = None) -> bool:
    s = load_settings()
    if not s["bot_token"] or not s["chat_id"]:
        log.info("Telegram not configured; alert skipped.")
        return False
    payload = {"chat_id": s["chat_id"], **payload}
    try:
        r = requests.post(API.format(token=s["bot_token"], method=method),
                          data=payload, files=files, timeout=20)
        ok = r.status_code == 200 and r.json().get("ok", False)
        if not ok:
            log.warning("Telegram API error: %s", r.text[:200])
        return ok
    except Exception as exc:  # noqa: BLE001
        log.warning("Telegram send failed: %s", exc)
        return False


def send_message(text: str) -> bool:
    return _call("sendMessage", {"text": text, "parse_mode": "HTML"})


def send_photo(image_bytes: bytes, caption: str = "") -> bool:
    return _call("sendPhoto", {"caption": caption[:1024]},
                 files={"photo": ("violation.jpg", image_bytes, "image/jpeg")})


def send_violation_alert(camera_id: str, class_name: str, conf: float,
                         zone: str, frame_no: int,
                         snapshot: bytes | None = None,
                         allowed_zones: list[str] | None = None) -> bool:
    """Cooldown-guarded violation alert (text + optional snapshot photo).

    Only fires when the detection zone is allowed (red-only by default:
    the overhead-hazard area where a missing helmet can be fatal).
    """
    s = load_settings()
    default_zones = s.get("zones") or ["red", "yellow", "green"]
    zones = [z.lower() for z in (allowed_zones if allowed_zones else default_zones)]
    if zone.lower() not in zones:
        log.info("Alert suppressed: %s zone not in %s.", zone, zones)
        return False
    now = time.time()
    key = (camera_id, class_name)
    if now - _last_sent.get(key, 0) < s["cooldown_s"]:
        return False
    _last_sent[key] = now
    import datetime as _dt
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    zone_word = {"red": "RED zone (overhead hazard area)",
                 "yellow": "YELLOW zone (active workface)",
                 "green": "GREEN zone (walkway)"}.get(zone, zone)
    text = (f"<b>PPE VIOLATION</b> {stamp}\nCamera: {camera_id}\n"
            f"Missing gear: <b>{class_name}</b> ({conf:.0%})\n"
            f"Area: {zone_word}\nFrame: {frame_no}")
    if snapshot:
        return send_photo(snapshot, caption=text)
    return send_message(text)
