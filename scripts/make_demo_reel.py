"""Build a demo site reel (data/violations/demo_site.mp4) from real test frames.

The reel stitches consecutive test images into a 10 fps MP4 so the Video
Monitor page has a real-frames sample without shipping video files.
Run: python scripts/make_demo_reel.py
"""
import glob
import os
import sys

sys.path.insert(0, os.path.abspath("."))
import cv2

N = 60
FPS = 10


def main() -> None:
    exts = (".jpg", ".jpeg", ".png")
    files = sorted(f for f in glob.glob("data/processed/images/test/*")
                   if f.lower().endswith(exts))[:N]
    if not files:
        raise SystemExit("no test images found")
    frame = cv2.imread(files[0])
    h, w = frame.shape[:2]
    os.makedirs("data/violations", exist_ok=True)
    out = "data/violations/demo_site.mp4"
    import imageio.v2 as imageio
    writer = imageio.get_writer(out, fps=FPS, codec="libx264", quality=8,
                                macro_block_size=None)
    for f in files:
        img = cv2.imread(f)
        if (img.shape[1], img.shape[0]) != (w, h):
            img = cv2.resize(img, (w, h))
        writer.append_data(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    writer.close()
    print(f"reel: {len(files)} frames -> {out}")


if __name__ == "__main__":
    main()
