"""Check run formatting of body, caption, and code paragraphs."""
from docx import Document

d = Document("reports/final_report.docx")
for idx in (77, 118, 147, 223):
    p = d.paragraphs[idx]
    info = [(r.text[:25], r.font.name, str(r.font.size), r.font.bold, r.font.italic,
             str(r.font.color.rgb) if r.font.color.rgb else None) for r in p.runs if r.text.strip()]
    print(idx, "style=", p.style.name, "align=", p.alignment)
    for x in info[:3]:
        print("   ", x)
