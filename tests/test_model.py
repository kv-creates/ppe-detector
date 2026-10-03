"""Model tests: weights load, inference returns sane boxes."""
import glob
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _p(*parts):
    return os.path.join(ROOT, *parts)


def test_weights_exist():
    assert os.path.exists(_p("models/checkpoints/yolov8_final/weights/best.pt"))


def test_predictor_loads_and_predicts():
    import sys
    sys.path.insert(0, ROOT)
    from src.inference.predictor import PPEPredictor
    pred = PPEPredictor()
    assert pred.is_placeholder is False, "expected trained PPE weights, got placeholder"
    exts = (".jpg", ".jpeg", ".png")
    img = sorted(f for f in glob.glob(_p("data/processed/images/test/*"))
                 if f.lower().endswith(exts))[0]
    out = pred.predict(img, camera_id="test")
    assert out["num_detections"] >= 0
    for d in out["detections"]:
        assert d["class_name"] in ("person", "helmet", "vest", "no-helmet",
                                   "no-vest", "boots")
        assert d["zone"] in ("red", "yellow", "green")
        x1, y1, x2, y2 = d["bbox_xyxy"]
        assert x2 > x1 and y2 > y1


def test_zones():
    import sys
    sys.path.insert(0, ROOT)
    from src.inference.zones import get_zone
    assert get_zone((0.5, 0.1)) == "red"
    assert get_zone((0.5, 0.5)) == "yellow"
    assert get_zone((0.5, 0.9)) == "green"
