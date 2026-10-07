"""Verify round-2: originals intact, new blocks ordered correctly."""
from docx import Document

d = Document("reports/final_report.docx")
ts = [p.text for p in d.paragraphs]
print("paras:", len(ts))

# 1) 5.5/5.6 order check
i = ts.index("5.5 TELEGRAM ALERTS")
print("5.5 @", i, "| next:", ts[i + 1][:50], "| then:", ts[i + 2][:50])
i6 = ts.index("5.6 VIDEO PIPELINE")
print("5.6 @", i6, "| next:", ts[i6 + 1][:60])

# 2) 7.6 block order
i7 = ts.index("7.6 VIDEO MONITOR PAGE")
print("7.6 @", i7)
for t in ts[i7:i7 + 6]:
    kind = "IMG" if t == "" else ("CAP" if t.startswith("Figure 7.5") else "TXT")
    print("   ", kind, ":", t[:70].replace("\n", " "))
i77 = ts.index("7.7 ARCHITECTURE DIAGRAM")
print("diagram renumbered @", i77)

# 3) LoF entry
lof = [t for t in ts if t.startswith("Figure 7.")]
print("LoF 7.x entries:", len(lof))

# 4) formatting of new runs
bad = 0
for p in d.paragraphs:
    for r in p.runs:
        if r.text.strip() and (r.font.name != "Times New Roman"
                               or (r.font.color.rgb is not None
                                   and str(r.font.color.rgb) != "000000")):
            bad += 1
            print("BAD:", r.text[:40], r.font.name, r.font.color.rgb)
print("format violations:", bad)

# 5) user content intact: title page + TOC + all-caps heads
print("title ok:", ts[2] if len(ts) > 2 else "?")
import zipfile
z = zipfile.ZipFile("reports/final_report.docx")
print("media files:", len([n for n in z.namelist() if "word/media/" in n]))
