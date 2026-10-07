"""Realtime tests: telegram config/cooldown + video pipeline smoke."""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _p(*parts):
    return os.path.join(ROOT, *parts)


def test_telegram_unconfigured_by_default():
    import sys
    sys.path.insert(0, ROOT)
    from src.utils import telegram
    assert telegram.configured() is False
    assert telegram.send_message("hi") is False
    assert telegram.send_violation_alert("cam-01", "no-helmet", 0.9, "red", 1) is False


def test_telegram_cooldown_and_format():
    import sys
    sys.path.insert(0, ROOT)
    from src.utils import telegram
    # monkeypatch settings + transport
    telegram.load_settings = lambda: {"bot_token": "t", "chat_id": "c", "cooldown_s": 3600}
    calls = []
    telegram._call = lambda method, payload, files=None: calls.append(method) or True
    assert telegram.send_violation_alert("cam-01", "no-vest", 0.8, "red", 10,
                                         snapshot=b"fake") is True
    assert calls == ["sendPhoto"]
    # second alert within cooldown is suppressed
    assert telegram.send_violation_alert("cam-01", "no-vest", 0.8, "red", 11) is False


def test_video_pipeline_smoke():
    import sys
    sys.path.insert(0, ROOT)
    from src.inference.video import process_video
    reel = _p("data/violations/demo_site.mp4")
    assert os.path.exists(reel), "build the reel: python scripts/make_demo_reel.py"
    s = process_video(reel, camera_id="cam-test", conf=0.30,
                      sample_every=30, notify=False)
    assert s["frames_scored"] >= 2
    assert os.path.exists(s["annotated_path"])
    assert isinstance(s["violations"], int)
