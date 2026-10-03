"""Generate colab/train_ppe_colab.ipynb (valid nbformat JSON). Run: python colab/make_notebook.py"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata["kernelspec"] = {"display_name": "Python 3 (GPU)", "language": "python", "name": "python3"}

nb.cells = [
    nbf.v4.new_markdown_cell(
        "# PPE Detector \u2014 YOLOv8 Training on Colab GPU\n"
        "This notebook trains YOLOv8n, YOLOv8s, YOLOv8m on the PPE dataset.\n"
        "**Step 1:** Runtime \u2192 Change runtime type \u2192 T4 GPU\n"
        "**Step 2:** Mount Drive to persist weights\n"
        "**Step 3:** Run all cells"),
    nbf.v4.new_code_cell("!nvidia-smi\n!pip install ultralytics==8.3.0 -q"),
    nbf.v4.new_code_cell(
        "from google.colab import drive\ndrive.mount('/content/drive')\n"
        "import os\nos.makedirs('/content/drive/MyDrive/ppe_detector/weights', exist_ok=True)"),
    nbf.v4.new_code_cell(
        "# Expects /content/drive/MyDrive/ppe_detector/dataset.zip\n"
        "# (zip of data/processed/ with images/train,val,test + labels/train,val,test)\n"
        "!unzip -q /content/drive/MyDrive/ppe_detector/dataset.zip -d /content/dataset\n"
        "!ls /content/dataset"),
    nbf.v4.new_code_cell(
        "yaml_content = '''\npath: /content/dataset\ntrain: images/train\n"
        "val: images/val\ntest: images/test\nnames:\n  0: person\n  1: helmet\n"
        "  2: vest\n  3: no-helmet\n  4: no-vest\n  5: boots\n'''\n"
        "open('/content/dataset.yaml','w').write(yaml_content)\nprint(open('/content/dataset.yaml').read())"),
    nbf.v4.new_code_cell(
        "from ultralytics import YOLO\nmodel = YOLO('yolov8n.pt')\n"
        "model.train(data='/content/dataset.yaml', epochs=60, imgsz=640, batch=32,\n"
        "            device=0, project='/content/runs', name='yolov8n_ppe',\n"
        "            plots=True, save=True, exist_ok=True)\n"
        "import shutil\nshutil.copytree('/content/runs/yolov8n_ppe',\n"
        "                '/content/drive/MyDrive/ppe_detector/weights/yolov8n_ppe',\n"
        "                dirs_exist_ok=True)"),
    nbf.v4.new_code_cell(
        "model = YOLO('yolov8s.pt')\n"
        "model.train(data='/content/dataset.yaml', epochs=60, imgsz=640, batch=32,\n"
        "            device=0, project='/content/runs', name='yolov8s_ppe',\n"
        "            plots=True, save=True, exist_ok=True)\n"
        "shutil.copytree('/content/runs/yolov8s_ppe',\n"
        "                '/content/drive/MyDrive/ppe_detector/weights/yolov8s_ppe',\n"
        "                dirs_exist_ok=True)"),
    nbf.v4.new_code_cell(
        "model = YOLO('yolov8m.pt')\n"
        "model.train(data='/content/dataset.yaml', epochs=60, imgsz=640, batch=16,\n"
        "            device=0, project='/content/runs', name='yolov8m_ppe',\n"
        "            plots=True, save=True, exist_ok=True)\n"
        "shutil.copytree('/content/runs/yolov8m_ppe',\n"
        "                '/content/drive/MyDrive/ppe_detector/weights/yolov8m_ppe',\n"
        "                dirs_exist_ok=True)"),
    nbf.v4.new_code_cell(
        "import json\nresults = {}\n"
        "for name in ['yolov8n_ppe','yolov8s_ppe','yolov8m_ppe']:\n"
        "    m = YOLO(f'/content/runs/{name}/weights/best.pt')\n"
        "    r = m.val(data='/content/dataset.yaml', split='test')\n"
        "    results[name] = {\n"
        "        'mAP50': float(r.box.map50),\n"
        "        'mAP50_95': float(r.box.map),\n"
        "        'precision': float(r.box.mp),\n"
        "        'recall': float(r.box.mr),\n"
        "    }\n"
        "json.dump(results, open('/content/drive/MyDrive/ppe_detector/metrics.json','w'), indent=2)\n"
        "print(json.dumps(results, indent=2))"),
    nbf.v4.new_code_cell(
        "!mkdir -p /content/drive/MyDrive/ppe_detector/plots\n"
        "!cp /content/runs/yolov8n_ppe/*.png /content/drive/MyDrive/ppe_detector/plots/n_*.png\n"
        "!cp /content/runs/yolov8s_ppe/*.png /content/drive/MyDrive/ppe_detector/plots/s_*.png\n"
        "!cp /content/runs/yolov8m_ppe/*.png /content/drive/MyDrive/ppe_detector/plots/m_*.png\n"
        "# These PNGs are results.png, confusion_matrix.png, PR_curve.png, F1_curve.png, val_batch*_pred.jpg"),
    nbf.v4.new_markdown_cell(
        "After running all cells, download the entire `/content/drive/MyDrive/ppe_detector/` "
        "folder and place:\n- `weights/*` \u2192 `models/checkpoints/`\n"
        "- `plots/*` \u2192 `reports/figures/colab_plots/`\n"
        "- `metrics.json` \u2192 `reports/colab_metrics.json`"),
]

with open("colab/train_ppe_colab.ipynb", "w", encoding="utf-8") as fh:
    nbf.write(nb, fh)
print("wrote colab/train_ppe_colab.ipynb with", len(nb.cells), "cells")
