"""Data pipeline tests: manifest, split counts, label format."""
import csv
import os

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _p(*parts):
    return os.path.join(ROOT, *parts)


def test_dataset_yaml_exists_and_valid():
    yp = _p("data/processed/dataset.yaml")
    assert os.path.exists(yp), "dataset.yaml missing"
    with open(yp) as fh:
        d = yaml.safe_load(fh)
    assert d["nc"] == 6
    assert len(d["names"]) == 6
    for s in ("train", "val", "test"):
        assert os.path.isdir(_p("data/processed/images", s))
        assert os.path.isdir(_p("data/processed/labels", s))


def test_split_counts_match_manifest():
    with open(_p("data/processed/metadata.csv")) as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) > 100, "dataset suspiciously small"
    for split in ("train", "val", "test"):
        n_meta = sum(1 for r in rows if r["split"] == split)
        n_img = len([f for f in os.listdir(_p("data/processed/images", split))
                     if f.lower().endswith((".jpg", ".jpeg", ".png"))])
        assert n_meta == n_img > 0, f"split {split}: meta={n_meta} files={n_img}"


def test_label_format_normalised():
    checked = 0
    for split in ("train", "val", "test"):
        ld = _p("data/processed/labels", split)
        for f in os.listdir(ld)[:50]:
            with open(os.path.join(ld, f)) as fh:
                for line in fh:
                    p = line.split()
                    assert len(p) == 5, f"bad label line in {f}"
                    assert 0 <= int(p[0]) <= 5
                    assert all(0.0 <= float(v) <= 1.0 for v in p[1:])
                    checked += 1
    assert checked > 500


def test_every_split_has_all_sources():
    with open(_p("data/processed/metadata.csv")) as fh:
        rows = list(csv.DictReader(fh))
    for split in ("train", "val", "test"):
        srcs = {r["source_dataset"] for r in rows if r["split"] == split}
        assert "construction_ppe" in srcs
