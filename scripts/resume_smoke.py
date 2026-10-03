"""Resume the interrupted smoke training run (epoch 8/8 + final plots)."""
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from ultralytics import YOLO

last = os.path.abspath("models/smoke/yolov8n_smoke/weights/last.pt")
model = YOLO(last)
model.train(resume=True)
print("RESUME DONE")
