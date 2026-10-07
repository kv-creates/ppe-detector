"""UI smoke tests: components import, CSS non-empty, pages compile."""
import os
import py_compile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_css_nonempty_and_win7():
    css = os.path.join(ROOT, "src/ui/win7.css")
    assert os.path.getsize(css) > 1000
    text = open(css, encoding="utf-8").read()
    for token in ("Segoe UI", "#3B6EA5", "win7-titlebar", "win7-statusbar", "stButton"):
        assert token in text, f"CSS missing {token}"
    import re
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)  # ignore comments
    assert "glassmorphism" not in code.lower()
    assert "Poppins" not in text and "Inter" not in text


def test_components_import():
    import sys
    sys.path.insert(0, ROOT)
    import src.ui.components as c
    for fn in ("win7_window", "win7_status_bar", "win7_groupbox",
               "win7_tab_strip", "call_detect", "draw_boxes", "compliance_stats"):
        assert callable(getattr(c, fn)), fn


def test_pages_compile():
    pages = ["src/ui/app.py", "src/ui/pages/1_Live_View.py",
             "src/ui/pages/2_Incident_Log.py", "src/ui/pages/3_Analytics.py",
             "src/ui/pages/4_KPI_Report.py", "src/ui/pages/5_Video_Monitor.py"]
    for p in pages:
        assert os.path.exists(os.path.join(ROOT, p)), p
        py_compile.compile(os.path.join(ROOT, p), doraise=True)
