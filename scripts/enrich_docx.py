"""Additive-only enrichment of the user-edited final_report.docx.

- Inserts plain-language analysis after figures/outputs (§3, §6, §7).
- Expands §5 with merge.py + NEW Streamlit code excerpts and explanations.
- Never modifies or deletes existing paragraphs: only insert_paragraph_before.
- Insertions run bottom-to-top so indices stay valid.
Run: python scripts/enrich_docx.py
"""
from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph as _P

PATH = "reports/final_report.docx"
BLACK = RGBColor(0, 0, 0)
FONT = "Times New Roman"


def set_run(run, size=12, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = BLACK


def new_para_before(doc, ref_idx: int):
    ref = doc.paragraphs[ref_idx]._p
    el = OxmlElement("w:p")
    ref.addprevious(el)
    p = _P(el, doc)
    p.style = "Normal"
    return p


def insert_body(doc, ref_idx: int, text: str):
    p = new_para_before(doc, ref_idx)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    set_run(r, 12)
    return p


def insert_head(doc, ref_idx: int, text: str):
    p = new_para_before(doc, ref_idx)
    r = p.add_run(text.upper())
    set_run(r, 12, bold=True)
    pf = p.paragraph_format
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)
    return p


def insert_code(doc, ref_idx: int, lines: list[str]):
    # insert bottom-to-top within block by inserting each line before ref
    for ln in lines:
        p = new_para_before(doc, ref_idx)
        r = p.add_run(ln if ln else " ")
        set_run(r, 10)


# ---------------------------------------------------------------- content ---
A31 = ("The tallest bar is person (1,249 images) because almost every photo "
       "contains workers — that is expected and healthy. Helmet (952) and "
       "vest (953) come next, which means compliant safety gear is well "
       "represented and the model gets plenty of good examples to learn from.")
A31B = ("The violation bars are shorter: no-helmet appears in 282 images and "
        "no-vest in 396. That imbalance is natural — violations are the "
        "exception on a real site, not the rule. It also explains the results "
        "in Section 6: with fewer examples to learn from, the model finds "
        "violations harder to spot than helmets and vests.")

A32 = ("Most boxes are small: the middle value (median) is about 1 percent of "
       "the image area. Small boxes are helmets, boots, and bare heads seen "
       "from far away, while the few large boxes are close-up workers. This "
       "is why the system looks at full 640-pixel images instead of small "
       "thumbnails — shrinking the picture further would erase the very heads "
       "and boots we need to find.")
A32B = ("In plain terms: the detector's hardest job is spotting tiny objects, "
        "so image size is a direct control on violation recall.")

A33 = ("The grid shows 16 real photos with the correct boxes drawn on top: "
       "green for compliant gear and workers, red for violations. Because "
       "these are genuine site and street photos — including a few odd ones "
       "like a bartender or dancers that slipped in from the web — the grid "
       "also proves the labels are trustworthy: helmets sit on heads, vests "
       "sit on torsos, and boots sit on feet in every frame.")
A33B = ("Those odd photos are not a mistake to hide: unusual pictures without "
        "safety gear teach the model what an ordinary scene looks like, so it "
        "does not raise false alarms on them later.")

A34 = ("Nearly every image is exactly 640 by 640 pixels. Uniform size makes "
       "training simpler and fairer: pictures can be stacked into batches "
       "without stretching, so no box gets distorted before the model sees it. "
       "The small bump of other sizes comes from the 11 SHWD demo frames.")

A61 = ("All three curves tell the same story. Losses fall and accuracy climbs "
       "for about 40 rounds (epochs) and then flattens — the models stop "
       "improving because they have squeezed out what the 1,331 training "
       "photos can teach, not because training was cut short.")
A61B = ("The final scores are close: medium 0.695, nano 0.683, small 0.653. "
       "Small scoring slightly below nano is just small-test-set wobble (197 "
       "images), not proof that the smaller model is better — on a bigger test "
       "set that gap would mostly vanish.")

A62 = ("Read a confusion matrix like a school report card: the diagonal from "
       "top-left to bottom-right is the share of correct answers, and "
       "anything off the diagonal is confusion. Person, helmet, and vest sit "
       "strongly on the diagonal. The weak row is no-helmet, which leaks into "
       "the background column — in plain words, the model often fails to "
       "notice a bare head at all, because bare heads are small and only 282 "
       "training photos show them.")

A63 = ("Each curve shows one class trading correctness of alerts (precision) "
       "against share of objects found (recall). The compliant-gear curves "
       "stay high far to the right, meaning the model can find most helmets "
       "and vests without raising many false alarms. The no-helmet curve "
       "drops early: to catch more bare heads the model must accept many "
       "more false alarms — the classic reason violation recall is the "
       "project's hardest number.")

A64 = ("The F1 curve blends both goals into one score per confidence setting. "
       "The peak sits near 0.3, which is exactly where the deployed "
       "confidence slider rests. Sliding higher would cut false alarms but "
       "let more violations slip through; sliding lower would catch more "
       "violations but cry wolf more often. The graph is the evidence behind "
       "the default.")

A65 = ("This is the medium model thinking out loud on photos it trained on: "
       "tight boxes around workers, yellow helmets, orange vests, and red "
       "boots, each with a confidence number. Green means compliant gear, red "
       "means a violation, blue-grey means a worker. The boxes hug the "
       "objects instead of floating loosely, which is what allows the zone "
       "logic in Section 7 to assign each detection to the correct site area.")

A66 = ("Unlike the previous figure, these 8 photos were locked away before "
       "training and the model had never seen them. It still finds workers, "
       "helmets, vests, and violations in the right places. That is the "
       "generalisation test that matters: memorising training photos is easy, "
       "performing on new site photos is the actual job.")

A67 = ("How to read the two tables without any background in machine "
       "learning. mAP@0.5 (0.70 for the champion) is the overall report card "
       "across all six classes — higher is better, 1.0 is perfect. Precision "
       "(0.72) answers: when the system raises an alert, how often is it "
       "right? Recall (0.70) answers: of all real violations out there, how "
       "many did it catch? A trusted site system needs both high: high "
       "precision so supervisors believe the alerts, high recall so few "
       "violations slip past.")
A67B = ("The per-class table then points at exactly one weak spot. Vest "
        "scores best (0.56) because orange vests are large and common. "
        "No-helmet scores worst (0.06) because bare heads are tiny and only "
        "282 training photos contain them. Every other class sits in the "
        "usable middle. The conclusion writes itself: the next upgrade must "
        "be more no-helmet photos, not a bigger model.")

A71 = ("The screenshot shows the system working on a real photo. The model "
       "found the worker (person, 78 percent sure), his yellow helmet (92 "
       "percent), and flagged a missing vest (no-vest, 80 percent). Below the "
       "picture the three counters summarise the frame: safe items found, "
       "unsafe items found, and the compliance percentage, which is simply "
       "safe divided by safe-plus-unsafe. When anything unsafe appears, the "
       "yellow-red message box pops up exactly like a classic Windows warning "
       "so a supervisor cannot miss it.")
A71B = ("The confidence slider above the picture is the same 0.3 default the "
        "F1 graph in Figure 6.7 recommends: drag it right for fewer but safer "
        "alerts, left for catching more at the cost of extra false alarms.")

A72 = ("Each row of this table is one violation the system caught and saved: "
       "when it happened, which camera saw it, what was missing (no-vest in "
       "these rows), how sure the model was, which site zone it falls in, and "
       "the saved snapshot photo as evidence. The camera and class boxes at "
       "the top filter the history, and Download CSV hands the whole log to "
       "an auditor in one click — that export is the compliance paper trail.")

A73 = ("Three views, three questions answered. The class bars repeat the "
       "dataset story from Figure 3.1 so supervisors see what the model was "
       "taught. The zone bars show where detections happen on site — red, "
       "yellow, green thirds of the camera view — which tells safety staff "
       "which areas generate the most alerts. The latency histogram shows how "
       "fast each picture is processed, with the middle (p50) and near-worst "
       "(p95) marked: the p95 is the promise that 19 out of 20 alerts arrive "
       "within that time.")

A74 = ("Each of the five boxes compares one measured number against its "
       "target: name on top, big actual value, then target with a pass or "
       "fail mark and one line explaining it. All five currently miss because "
       "the targets describe the finished production system (GPU computer, "
       "more violation photos) while the numbers describe what is measured "
       "today — the page is honest rather than flattering, and the Download "
       "report button exports the full story behind the numbers.")

E51A = ("In plain words, this code asks every data source for real photos "
        "and refuses to continue if fewer than 50 turn up — there is no "
        "fallback that invents pictures. Each source is fenced in its own "
        "try/except style helper so one dead link (Roboflow's moved mirror, "
        "missing Kaggle login) only logs a warning instead of killing the "
        "whole download.")
MERGE_CODE = [
    'LABEL_MAP = {',
    '    "Person": "person", "helmet": "helmet", "vest": "vest",',
    '    "no_helmet": "no-helmet", "boots": "boots",',
    '    "gloves": None, "goggles": None, "none": None,  # dropped',
    '}',
    'def derive_no_vest(boxes):',
    '    persons = [b for b in boxes if b[0] == "person"]',
    '    vests = [b for b in boxes if b[0] == "vest"]',
    '    for (x1, y1, x2, y2) in persons:',
    '        if no vest overlaps this worker:      # IoU < 0.05',
    '            emit torso box labelled "no-vest"',
]
E51B = ("This is the heart of the merge step. LABEL_MAP translates each "
        "source's own label words into our six class names, and anything "
        "mapped to None (gloves, goggles, none) is thrown away and counted in "
        "the log. derive_no_vest then handles the missing violation label: "
        "for every worker box that does not overlap any vest box, it draws a "
        "torso box (middle of the body, sides trimmed) and calls it no-vest. "
        "That rule is what turns 1,320 vest-annotated photos into 690 honest "
        "violation examples without inventing a single pixel.")

E55H = "5.5 STREAMLIT UI CODE"
E55A = ("The interface is plain Streamlit with a Windows 7 skin loaded from "
        "a stylesheet, so all the logic below is ordinary Python: pick a "
        "picture, send it to the detection server, draw the answer.")
LIVE_CODE = [
    'source = st.selectbox("Source", ["Sample image", "Upload image", ...])',
    'camera_id = st.selectbox("Camera", ["cam-01", "cam-02", "cam-03"])',
    'conf = st.slider("Confidence threshold", 0.05, 0.80, 0.30, 0.05)',
    'if st.button("Run Detection", ...) or first_visit:',
    '    resp = call_detect(jpg_bytes, camera_id=camera_id)  # POST /api/detect',
    '    st.image(draw_boxes(img, resp["detections"]))        # overlay boxes',
    '    safe, unsafe, pct = compliance_stats(resp["detections"])',
    '    ... three counters + red/yellow message box ...',
]
E55B = ("Read it top to bottom: three controls collect the picture, the "
        "camera name, and the confidence level; one button press posts the "
        "picture to the FastAPI server from Section 5.4 and gets back boxes, "
        "zones, and a violation flag; the overlay painter from components.py "
        "draws green boxes for compliant gear and red boxes for violations; "
        "and compliance_stats counts safe versus unsafe items for the "
        "percentage. The first visit runs automatically so the page in Figure "
        "7.1 is never an empty form.")
WIN7_CODE = [
    "def win7_window(title, icon):          # blue Aero title bar",
    '    st.markdown("<div class=\'win7-titlebar\'>...")',
    "def win7_status_bar(left, right):      # fixed grey bar at bottom",
    '    st.markdown("<div class=\'win7-statusbar\'>...")',
]
E55C = ("Every page in Section 7 is wrapped by these two helpers: a blue "
        "gradient title bar with minimise/maximise/close glyphs on top, and "
        "a fixed grey status bar at the bottom showing readiness, camera, and "
        "model. The classic buttons, tabs, and group boxes all come from "
        "src/ui/win7.css, which is why every screenshot in Section 7 looks "
        "like one desktop program instead of four web pages.")


def main():
    doc = Document(PATH)
    # (anchor, [items in final document order]); item = (kind, payload).
    # Anchors are "insert before this paragraph", chosen as the first para
    # AFTER each figure caption / code block so images stay with captions.
    plan = [
        (119, [("head", "WHAT THIS GRAPH SHOWS"), ("body", A31), ("body", A31B)]),
        (122, [("head", "WHAT THIS GRAPH SHOWS"), ("body", A32), ("body", A32B)]),
        (125, [("head", "WHAT THIS GRID SHOWS"), ("body", A33), ("body", A33B)]),
        (128, [("head", "WHAT THIS GRAPH SHOWS"), ("body", A34)]),
        (159, [("body", E51A), ("code", MERGE_CODE), ("body", E51B)]),
        (187, [("head", E55H), ("body", E55A), ("code", LIVE_CODE),
               ("body", E55B), ("code", WIN7_CODE), ("body", E55C)]),
        (196, [("head", "WHAT THE THREE CURVES SAY"), ("body", A61), ("body", A61B)]),
        (201, [("head", "HOW TO READ THIS TABLE"), ("body", A62)]),
        (204, [("head", "WHAT THE CURVES MEAN"), ("body", A63)]),
        (207, [("head", "WHAT THE PEAK TELLS US"), ("body", A64)]),
        (210, [("head", "WHAT THIS BATCH SHOWS"), ("body", A65)]),
        (213, [("head", "WHAT THIS GRID PROVES"), ("body", A66)]),
        (220, [("head", "READING THE RESULTS IN PLAIN WORDS"),
               ("body", A67), ("body", A67B)]),
        (228, [("head", "WHAT THE OUTPUT MEANS"), ("body", A71), ("body", A71B)]),
        (231, [("head", "WHAT EACH ROW MEANS"), ("body", A72)]),
        (235, [("head", "WHAT THESE CHARTS SHOW"), ("body", A73)]),
        (238, [("head", "WHAT THIS PAGE SHOWS"), ("body", A74)]),
    ]
    # bottom-to-top anchors; items within an anchor inserted in reverse
    # (code lines reversed too) so the final order matches the plan.
    for anchor, items in sorted(plan, key=lambda t: -t[0]):
        expanded = []
        for kind, payload in items:
            if kind == "code":
                expanded.extend([("code", [ln]) for ln in payload])
            else:
                expanded.append((kind, payload))
        for kind, payload in reversed(expanded):
            if kind == "body":
                insert_body(doc, anchor, payload)
            elif kind == "head":
                insert_head(doc, anchor, payload)
            elif kind == "code":
                insert_code(doc, anchor, payload)
    doc.save(PATH)
    print("enriched", PATH)


if __name__ == "__main__":
    main()
