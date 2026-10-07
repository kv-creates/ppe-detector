"""Round-2 additive edits: 5.5 Telegram, 5.6 video pipeline, 7.6 Video Monitor
page + Figure 7.5, LoF entry, 7.1 touch-up, diagram renumber + page count.

Only touches what the new features require; everything else is insertion.
Run: python scripts/enrich_docx2.py
"""
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor
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


def before(doc, idx):
    el = OxmlElement("w:p")
    doc.paragraphs[idx]._p.addprevious(el)
    p = _P(el, doc)
    p.style = "Normal"
    return p


def body(doc, idx, text):
    p = before(doc, idx)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    set_run(r, 12)


def head(doc, idx, text):
    p = before(doc, idx)
    r = p.add_run(text.upper())
    set_run(r, 12, bold=True)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)


def code(doc, idx, lines):
    for ln in reversed(lines):
        p = before(doc, idx)
        r = p.add_run(ln if ln else " ")
        set_run(r, 10)


def caption(doc, idx, text):
    p = before(doc, idx)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    set_run(r, 12, italic=True)


TG_CODE = [
    "def send_violation_alert(camera_id, class_name, conf, zone, ...):",
    "    if now - last[(camera_id, class_name)] < cooldown_s:  # 2 min",
    "        return False            # one alert per incident burst",
    '    text = f"PPE VIOLATION - {class_name} ({conf:.0%}) ..."',
    "    return send_photo(snapshot, caption=text)  # Bot API",
]
TG_TXT = ("In plain words: every violation wants to shout, but a ten-minute "
          "incident would send hundreds of messages. The cooler keeps one "
          "timestamp per camera and violation type and ignores repeats for "
          "two minutes. The message itself is plain text plus the snapshot "
          "photo, sent through Telegram's own web address — no extra software "
          "library needed. The bot token and chat number come from environment "
          "variables, so no secret ever sits in the code.")
VID_CODE = [
    "for n, frame in read_video(path):",
    "    if (n - 1) % sample_every: continue  # score every Nth frame",
    "    out = predictor.predict(frame)      # local, no network trip",
    "    log_violations_to_db(out)           # snapshot + zone + confidence",
    "    maybe_send_telegram(out)            # cooler-guarded (see 5.5)",
    "    stamp_banner_and_write(frame, out)  # H264 annotated MP4",
]
VID_TXT = ("Read it line by line: open the video, skip frames to stay fast, "
           "score only the kept frames with the model living in the same "
           "program (no waiting on network), save every violation with its "
           "photo evidence, ping Telegram unless the cooler says quiet, and "
           "paint boxes plus a red violation banner onto an output video that "
           "plays right in the page. scripts/make_demo_reel.py builds the "
           "sample reel from 60 real test photos so the page works with zero "
           "uploads.")
VM_A = ("Upload any site video (MP4, AVI, MOV) or run the bundled 60-frame "
        "demo reel made of real test photos. Set the camera name, the "
        "confidence level, and how many frames to skip between checks, then "
        "press Process Video: a glossy green progress bar tracks the run, "
        "four counters summarise it (frames scored, violations, Telegram "
        "alerts sent, Telegram on/off), and the finished annotated video "
        "plays back with a download button.")
VM_B = ("Behind the button runs the Section 5.6 pipeline: violations land in "
        "the same incident database as Live View, so they appear in the "
        "Incident Log instantly, and each one can also arrive on your phone "
        "as a Telegram photo message with the camera name, the missing gear, "
        "and the site zone. The setup guide on the page connects a new bot in "
        "about two minutes.")

CAP75 = ("Figure 7.5: Video upload page — sample site reel or MP4 upload, "
         "camera and confidence controls, frame-sampling slider, Telegram "
         "toggle with connection status, glossy progress bar, and a 2-minute "
         "BotFather setup guide.")


def before_el(doc, ref_el):
    el = OxmlElement("w:p")
    ref_el.addprevious(el)
    p = _P(el, doc)
    p.style = "Normal"
    return p


def main():
    doc = Document(PATH)
    ts = [p.text for p in doc.paragraphs]
    # locate fresh anchors by content (robust to shifts)
    i_6 = next(i for i, t in enumerate(ts) if t.strip() == "6. EXPERIMENTAL RESULTS & MODEL COMPARISON")
    i_76 = next(i for i, t in enumerate(ts) if t.strip() == "7.6 ARCHITECTURE DIAGRAM")
    i_lof74 = next(i for i, t in enumerate(ts) if t.startswith("Figure 7.4:"))
    i_purple = next(i for i, t in enumerate(ts) if "No purple gradients" in t)
    i_4pages = next(i for i, t in enumerate(ts) if "app.py + 4 pages" in t)

    # 1) 5.5 + 5.6 before section 6 (bottom-to-top: video block first)
    for ln in reversed(VID_CODE):
        p = before(doc, i_6)
        r = p.add_run(ln if ln else " ")
        set_run(r, 10)
    body(doc, i_6, VID_TXT)
    head(doc, i_6, "5.6 VIDEO PIPELINE")
    for ln in reversed(TG_CODE):
        p = before(doc, i_6)
        r = p.add_run(ln if ln else " ")
        set_run(r, 10)
    body(doc, i_6, TG_TXT)
    head(doc, i_6, "5.5 TELEGRAM ALERTS")

    # re-locate (indices shifted)
    ts = [p.text for p in doc.paragraphs]
    i_76 = next(i for i, t in enumerate(ts) if t.strip() == "7.6 ARCHITECTURE DIAGRAM")
    # 2) 7.6 video page block before architecture diagram (pinned element,
    #    inserted last-to-first so final order is head, text, text, image, caption)
    ref76 = doc.paragraphs[i_76]._p

    def h76(text):
        p = _P(OxmlElement("w:p"), doc)
        ref76.addprevious(p._p)
        p.style = "Normal"
        return p

    pc = h76("")
    pc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = pc.add_run(CAP75)
    set_run(r, 12, italic=True)
    pi = h76("")
    pi.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pi.add_run().add_picture("reports/figures/ui_video_monitor.png",
                             width=Inches(6.0))
    pb = h76("")
    pb.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = pb.add_run(VM_B)
    set_run(r, 12)
    pa = h76("")
    pa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = pa.add_run(VM_A)
    set_run(r, 12)
    ph = h76("7.6 VIDEO MONITOR PAGE")
    r = ph.add_run("7.6 VIDEO MONITOR PAGE")
    set_run(r, 12, bold=True)
    ph.paragraph_format.space_before = Pt(12)
    ph.paragraph_format.space_after = Pt(6)
    # 3) renumber diagram head + page count (minimal required edits)
    ts = [p.text for p in doc.paragraphs]
    i_76b = next(i for i, t in enumerate(ts) if t.strip() == "7.6 ARCHITECTURE DIAGRAM")
    p = doc.paragraphs[i_76b]
    p.text = ""
    r = p.add_run("7.7 ARCHITECTURE DIAGRAM")
    set_run(r, 12, bold=True)
    i_4 = next(i for i, t in enumerate([p.text for p in doc.paragraphs])
               if "app.py + 4 pages" in t)
    doc.paragraphs[i_4].text = doc.paragraphs[i_4].text.replace(
        "app.py + 4 pages", "app.py + 5 pages")
    # 4) LoF entry after Figure 7.4 (LAST body caption would duplicate;
    # LoF lives before ABSTRACT, so take the FIRST match here)
    ts = [p.text for p in doc.paragraphs]
    i_lof = next(i for i, t in enumerate(ts) if t.startswith("Figure 7.4:"))
    # insert after: anchor = next para
    nxt = doc.paragraphs[i_lof + 1]._p
    el = OxmlElement("w:p")
    nxt.addprevious(el)
    lp = _P(el, doc)
    lp.style = "List Bullet"
    lp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = lp.add_run(CAP75)
    set_run(r, 12)
    # 5) 7.1 philosophy touch-up (append Aero v2 sentence)
    ts = [p.text for p in doc.paragraphs]
    i_pu = next(i for i, t in enumerate(ts) if "No purple gradients" in t)
    p = doc.paragraphs[i_pu]
    r = p.add_run(" The second-generation skin deepens the Aero glass, "
                  "etches the group boxes, and replaces the flat status strip "
                  "with a dark glass taskbar carrying a glowing Start orb.")
    set_run(r, 12)

    doc.save(PATH)
    print("round-2 done")


if __name__ == "__main__":
    main()
