"""Locate round-2 7.6 pieces and LoF entries."""
from docx import Document

d = Document("reports/final_report.docx")
ts = [p.text for p in d.paragraphs]
for i, t in enumerate(ts):
    if "Upload any site video" in t or t.startswith("Figure 7.5") \
            or "Behind the button" in t or t == "7.6 VIDEO MONITOR PAGE":
        kind = "IMG" if t == "" else "TXT"
        print(i, kind, t[:70].replace("\n", " "))
print("---- LoF Figure 7.x ----")
for i, t in enumerate(ts):
    if t.startswith("Figure 7."):
        print(i, t[:60])
