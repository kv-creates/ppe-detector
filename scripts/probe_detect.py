"""Smoke-test POST /api/detect with a real test image."""
import json
import os
import urllib.request
import uuid

test_dir = "data/processed/images/test"
img_path = os.path.join(test_dir, sorted(os.listdir(test_dir))[0])
img = open(img_path, "rb").read()
b = uuid.uuid4().hex
CRLF = "\r\n"
head = ("--" + b + CRLF + "Content-Disposition: form-data; name=\"file\"; "
        "filename=\"t.jpg\"" + CRLF + "Content-Type: image/jpeg" + CRLF + CRLF).encode()
body = head + img + (CRLF + "--" + b + "--" + CRLF).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/detect?camera_id=cam-01", data=body,
    headers={"Content-Type": "multipart/form-data; boundary=" + b})
r = json.load(urllib.request.urlopen(req, timeout=120))
print("violation:", r["violation"], "| dets:", r["num_detections"],
      "| latency_ms:", r["latency_ms"], "| model:", r["model"])
print([(d["class_name"], d["conf"], d["zone"]) for d in r["detections"]][:8])
