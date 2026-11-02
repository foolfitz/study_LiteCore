#!/usr/bin/env python3
"""SPEC-P-demo-batch-4 P4: the heading menu, the two list toggles and the caret, on the Writer page.

On a mirror of dist/ with real keys and a real pointer, on the levels fixture.  The saved ODT is the answer: each arm presses, saves and
reads the paragraph's tag, heading level, list membership and text.  Every check is recorded and the run goes on past a red one.

  T1  bullet and number reverse: three presses read on, off, on (finding 030's opposite).
  T2  each level: body -> Hn -> body; Hn -> Hm; 內文 from a heading.
  T3  what the document already holds comes off, and a bullet item takes numbering.
  T4  the caret stays (finding 180): place, press, type q, the q is where it was placed.  Paragraph start, middle, end, wrapped lines,
      an empty paragraph, the last empty paragraph, a list item, a heading.  Each place has a control with nothing pressed, so a wrong
      expectation reads red on the control and not on the product (P4 run-01).
  T5  a one-paragraph blank document: both lists and H2 on and off, no notice, the status line never says 失敗.
  T6  ranges: a selection inside a paragraph styles the paragraph and builds no frame; a range from inside a paragraph across two reaches both.
  T7  refusals: numbering on a heading, a selection across a table, more paragraphs than the read will walk: a sentence, the whole document
      unchanged (`body`, not a projection), the session ready.
  T8  one Ctrl+Z undoes each press.
  T9  what the toolbar shows, after the caret arrives: the menu's check mark and the two buttons' aria-pressed; a fresh document claims no level.
  T10 the menu: opens, closes on Escape and outside, keyboard reaches an item, an item press does not take the sink's focus.
  T11 reopened: a saved heading and list are still there.
  T12 a paragraph with an as-char frame: both toggles work, and the frame stays.

--mutate is the instrument's red case and touches only this run: swap-levels exchanges H2 and H3 at the Worker boundary, no-undo skips the
Ctrl+Z, no-second-press skips T1's second press.

  check_writer_toggle.py --out DIR [--browsers chrome,firefox] [--profile NAME] [--mutate swap-levels|no-undo|no-second-press] [--only T1,T2]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_writer_align as a  # noqa: E402
from check_writer_align import common, evaluate, pp, real, z  # noqa: E402
from check_writer_shift_lines import WATCH  # noqa: E402

EVIDENCE = z.PROJECT.parent / "findings/evidence/demo-batch-4/fixture"
LEVELS = EVIDENCE / "levels-fixture.odt"
BLANK = EVIDENCE / "blank-fixture.odt"
TABLE = EVIDENCE / "table-caret-fixture.odt"
CARET = EVIDENCE / "caret-fixture.odt"
TEXT = a.TEXT
STYLE = a.STYLE
BULLET, NUMBER = '[data-action="toggle-list-unordered"]', '[data-action="toggle-list-ordered"]'
# paragraph index on the levels fixture, as arrow-downs from the start
BODY, BODY2, H1, H2, H3, H4, ITEM, ITEM2, NUMBERED, JULIET, EMPTY_MID, KILO, EMPTY_LAST = range(13)
WATCH_ACTIONS = """<script>
(() => { const Native = window.Worker, other = {'toggle-heading-2': 'toggle-heading-3', 'toggle-heading-3': 'toggle-heading-2'};
  window.Worker = class extends Native {
    postMessage(m, ...rest) {
      if (m?.kind === 'request' && m.operation === 'editorActionV2' && other[m.payload.action]) m.payload.action = other[m.payload.action];
      return super.postMessage(m, ...rest); } };
})();
</script>"""
TOOLBAR = """(() => { const q = s => document.querySelector(s), b = q('#heading-menu-button'), m = q('#heading-menu');
  const items = [...m.querySelectorAll('button')].map(i => ({action: i.dataset.action, checked: i.getAttribute('aria-checked'), label: i.textContent.trim()}));
  const r = m.getBoundingClientRect();
  return {open: !m.hidden, expanded: b.getAttribute('aria-expanded'), pressed: b.getAttribute('aria-pressed'), items,
    box: {left: r.left, top: r.top, right: r.right, bottom: r.bottom, innerWidth, innerHeight},
    bullet: q('[data-action="toggle-list-unordered"]').getAttribute('aria-pressed'), number: q('[data-action="toggle-list-ordered"]').getAttribute('aria-pressed'),
    legacyHidden: [...document.querySelectorAll('[data-setter-group]')].every(n => n.hidden), toggleHidden: [...document.querySelectorAll('[data-toggle-group]')].some(n => n.hidden),
    focus: document.activeElement?.id || document.activeElement?.dataset?.action || document.activeElement?.tagName,
    latency: q('#s-latency')?.textContent ?? null, notice: q('#notice')?.dataset.show ?? null, toast: q('#toast')?.textContent ?? ''}; })()"""


def shape(raw):
    """Every paragraph as the saved file holds it, in order."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    parents = {child: parent for parent in root.iter() for child in parent}
    # The list's kind is the style's first level: the arms put the paragraph at level 1.
    kinds = {}
    for style in root.iter(TEXT + "list-style"):
        first = next(iter(style), None)
        kinds[style.get(STYLE + "name")] = "ul" if first is not None and first.tag.endswith("bullet") else "ol"
    rows = []
    for p in root.iter():
        if p.tag not in (TEXT + "p", TEXT + "h"):
            continue
        walk, in_list, named = p, False, None
        while walk in parents:
            walk = parents[walk]
            if walk.tag == TEXT + "list":
                in_list = True
                named = walk.get(TEXT + "style-name") or named
        rows.append({"text": "".join(p.itertext()), "level": int(p.get(TEXT + "outline-level") or 0) if p.tag == TEXT + "h" else 0, "list": in_list,
                     "kind": kinds.get(named) if in_list else None, "style": p.get(TEXT + "style-name")})
    return rows


def body(raw):
    """The document as a canonical string, with the attributes a save rewrites taken out: two reads are equal only if nothing else moved."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    for node in root.iter():
        for name in [a for a in node.attrib if a.endswith("rsid") or a.endswith("paragraph-rsid")]:
            del node.attrib[name]
    return ET.tostring(root, encoding="unicode")


def frames(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return archive.read("content.xml").count(b"<draw:frame")


class Page(a.Page):
    def toolbar(self):
        return evaluate(self.session, TOOLBAR)

    def level(self, action):
        """Pick a menu item with the real pointer."""
        self.press("#heading-menu-button")
        time.sleep(.2)
        self.press(f'#heading-menu [data-action="{action}"]')
        self.quiet()


def fresh(page, raw):
    a.fresh(page, raw)


def rows_of(page):
    return shape(page.save())


def t1(page, raw, mutate):
    for name, button, kind in (("bullet", BULLET, "ul"), ("number", NUMBER, "ol")):
        fresh(page, raw)
        page.place(BODY2)
        seen = []
        for press in range(3):
            if not (mutate == "no-second-press" and press == 1):
                page.press(button)
                page.quiet()
            seen.append(rows_of(page)[BODY2]["kind"])
        page.check(f"T1/{name}/on-off-on", seen == [kind, None, kind], seen)
        page.check(f"T1/{name}/no-red-toast", page.toasts() == 0, evaluate(page.session, "window.__s.toasts.at(-1) ?? null"))


def t2(page, raw):
    for level in (1, 2, 3, 4):
        fresh(page, raw)
        page.place(BODY2)
        page.level(f"toggle-heading-{level}")
        on = rows_of(page)[BODY2]
        page.level(f"toggle-heading-{level}")
        off = rows_of(page)[BODY2]
        page.check(f"T2/h{level}/on", on["level"] == level, on)
        page.check(f"T2/h{level}/same-level-goes-back-to-body", off["level"] == 0, off)
    fresh(page, raw)
    page.place(BODY2)
    page.level("toggle-heading-1")
    page.level("toggle-heading-4")
    got = rows_of(page)[BODY2]
    page.check("T2/level-to-level", got["level"] == 4, got)
    page.level("set-paragraph-body")
    got = rows_of(page)[BODY2]
    page.check("T2/body-item", got["level"] == 0, got)
    page.check("T2/no-red-toast", page.toasts() == 0, evaluate(page.session, "window.__s.toasts.at(-1) ?? null"))


def t3(page, raw):
    for name, paragraph, press, want in (("heading-comes-off", H3, lambda: page.level("toggle-heading-3"), lambda r: r["level"] == 0),
                                         ("bullet-comes-off", ITEM, lambda: page.press(BULLET), lambda r: not r["list"]),
                                         ("number-comes-off", NUMBERED, lambda: page.press(NUMBER), lambda r: not r["list"])):
        fresh(page, raw)
        page.place(paragraph)
        press()
        page.quiet()
        got = rows_of(page)[paragraph]
        page.check(f"T3/{name}", want(got), got)
    fresh(page, raw)
    page.place(ITEM)
    page.press(NUMBER)
    page.quiet()
    got = rows_of(page)[ITEM]
    page.check("T3/bullet-item-takes-numbering", got["kind"] == "ol", got)


def t4(page, raw, caret_raw):
    presses = {"bullet": lambda p: p.press(BULLET), "number": lambda p: p.press(NUMBER), "h2": lambda p: p.level("toggle-heading-2"),
               "body": lambda p: p.level("set-paragraph-body"), "center": lambda p: p.press('[data-action="set-align-center"]')}
    def on(paragraph, right):
        def place(p):
            p.place(paragraph)
            p.key("Home")
            for _ in range(right):
                p.key("ArrowRight")
        return place
    places = {"body-start": (BODY2, on(BODY2, 0), "qBRAVO plain paragraph two"), "body-middle": (BODY2, on(BODY2, 2), "BRqAVO plain paragraph two"),
              "bullet-middle": (ITEM, on(ITEM, 2), "GqOLF bullet item"), "heading-middle": (H1, on(H1, 3), "CHAqRLIE heading one"),
              "number-start": (NUMBERED, on(NUMBERED, 0), "qINDIA numbered item")}
    for place_name, (paragraph, place, want) in places.items():
        # bullet-middle is offset 1: Home on a list item stops in front of the label and the first ArrowRight only clears that (crsrsh.cxx:342).
        fresh(page, raw)
        place(page)
        page.quiet()
        page.key("q")
        page.quiet()
        got = rows_of(page)[paragraph]["text"]
        page.check(f"T4/{place_name}/control", got == want, got)
        for name, press in presses.items():
            if name == "number" and place_name == "heading-middle":
                continue  # T7: refused
            fresh(page, raw)
            place(page)
            press(page)
            page.quiet()
            page.key("q")
            page.quiet()
            got = rows_of(page)[paragraph]["text"]
            page.check(f"T4/{place_name}/{name}", got == want, got)
    for name, press in presses.items():
        for place_name, paragraph in (("empty-middle", EMPTY_MID), ("empty-last", EMPTY_LAST)):
            fresh(page, raw)
            page.place(paragraph)
            press(page)
            page.quiet()
            page.key("q")
            page.quiet()
            got = rows_of(page)[paragraph]["text"]
            page.check(f"T4/{place_name}/{name}", got == "q", got)
    def on_wrapped(p, press):
        """End stops at the visual line's end, so the place is inside the paragraph; where exactly is what the control measures."""
        fresh(p, caret_raw)
        p.key("Home", ("ctrl",))
        for _ in range(4):
            p.key("ArrowDown")
        p.key("End")
        p.key("ArrowLeft")
        before = evaluate(p.session, "window.__z.caret")
        press(p)
        p.quiet()
        p.key("q")
        p.quiet()
        return before, next(r for r in rows_of(p) if r["text"].startswith("HOTEL"))["text"]
    before, control = on_wrapped(page, lambda p: None)
    page.check("T4/wrapped-line/control", control.count("q") == 1 and 0 < control.index("q") < len(control) - 1,
               {"caret": before, "at": control.find("q"), "length": len(control)})
    for name, press in presses.items():
        before, wrapped = on_wrapped(page, press)
        page.check(f"T4/wrapped-line/{name}", wrapped == control, {"caret": before, "at": wrapped.find("q"), "want": control.find("q")})


def t5(page, blank):
    def clean(name):  # before the save: a save writes over both
        s = page.toolbar()
        page.check(f"T5/{name}/no-notice", "失敗" not in (s["latency"] or "") and "待確認" not in (s["latency"] or "")
                   and "動作已送出" not in s["toast"] and page.toasts() == 0, {"latency": s["latency"], "toast": s["toast"]})
    for name, press, field, value in (("bullet", lambda: page.press(BULLET), "kind", "ul"), ("number", lambda: page.press(NUMBER), "kind", "ol"),
                                      ("h2", lambda: page.level("toggle-heading-2"), "level", 2)):
        fresh(page, blank)
        press()
        page.quiet()
        clean(name + "-on")
        on = rows_of(page)[0]
        press()
        page.quiet()
        clean(name + "-off")
        off = rows_of(page)[0]
        page.key("q")
        page.quiet()
        typed = rows_of(page)[0]
        page.check(f"T5/{name}/on-then-off", on[field] == value and not off[field], {"on": on, "off": off})
        page.check(f"T5/{name}/typing-lands", typed["text"] == "q", typed)


def t6(page, raw):
    fresh(page, raw)
    page.place(BODY2)
    page.key("Home")
    for _ in range(3):
        page.key("ArrowRight", ("shift",))
    page.level("toggle-heading-2")
    saved = page.save()
    got = shape(saved)[BODY2]
    page.check("T6/leading-selection/styles-the-paragraph", got["level"] == 2 and got["text"] == "BRAVO plain paragraph two", got)
    page.check("T6/leading-selection/no-frame", frames(saved) == 0, frames(saved))
    fresh(page, raw)
    page.place(BODY)
    page.key("Home")
    page.key("ArrowRight")
    page.key("ArrowRight")
    page.key("ArrowDown", ("shift",))
    page.level("toggle-heading-3")
    rows = rows_of(page)
    page.check("T6/range-from-inside/both-styled", rows[BODY]["level"] == 3 and rows[BODY2]["level"] == 3, rows[:2])
    page.level("toggle-heading-3")
    rows = rows_of(page)
    page.check("T6/range-from-inside/second-press-both-off", rows[BODY]["level"] == 0 and rows[BODY2]["level"] == 0, rows[:2])
    page.press(BULLET)
    page.quiet()
    rows = rows_of(page)
    page.check("T6/range/bullet-on-both", rows[BODY]["kind"] == "ul" and rows[BODY2]["kind"] == "ul", rows[:2])
    page.press(BULLET)
    page.quiet()
    rows = rows_of(page)
    page.check("T6/range/bullet-off-both", not rows[BODY]["list"] and not rows[BODY2]["list"], rows[:2])
    fresh(page, raw)
    page.place(BODY2)
    page.press(BULLET)
    page.quiet()
    page.key("ArrowUp")
    page.key("Home")
    page.key("ArrowDown", ("shift",))
    page.key("End", ("shift",))
    page.press(BULLET)
    page.quiet()
    rows = rows_of(page)
    page.check("T6/range/mixed-goes-on-not-off", rows[BODY]["kind"] == "ul" and rows[BODY2]["kind"] == "ul", rows[:2])
    page.check("T6/no-red-toast", page.toasts() == 0, evaluate(page.session, "window.__s.toasts.at(-1) ?? null"))


def t7(page, raw, table, long_raw):
    fresh(page, raw)
    before = body(page.save())
    page.place(H2)
    page.press(NUMBER)
    page.quiet()
    s = page.toolbar()
    page.check("T7/number-on-heading/sentence", "標題段落不能加編號" in s["toast"], s["toast"])
    page.check("T7/number-on-heading/unchanged", body(page.save()) == before, None)
    page.check("T7/number-on-heading/ready", evaluate(page.session, "document.querySelector('#state-pill').dataset.state") == "ready", None)
    fresh(page, table)
    before = body(page.save())
    page.key("Home", ("ctrl",))
    page.key("ArrowDown", ("shift",))
    page.key("ArrowDown", ("shift",))
    page.press(BULLET)
    page.quiet()
    s = page.toolbar()
    page.check("T7/selection-across-a-table/sentence", "表格或其他物件" in s["toast"], s["toast"])
    page.check("T7/selection-across-a-table/unchanged", body(page.save()) == before, None)
    fresh(page, long_raw)
    before = body(page.save())
    page.key("a", ("ctrl",))
    page.quiet()
    page.press(BULLET)
    page.quiet()
    s = page.toolbar()
    page.check("T7/too-many-paragraphs/sentence", "選取的段落太多" in s["toast"], s["toast"])
    page.check("T7/too-many-paragraphs/unchanged", body(page.save()) == before, None)
    page.check("T7/too-many-paragraphs/ready", evaluate(page.session, "document.querySelector('#state-pill').dataset.state") == "ready", None)


def t8(page, raw, mutate):
    for name, paragraph, press in (("bullet", BODY2, lambda: page.press(BULLET)), ("number", BODY2, lambda: page.press(NUMBER)),
                                   ("h2", BODY2, lambda: page.level("toggle-heading-2")), ("bullet-off", ITEM, lambda: page.press(BULLET)),
                                   ("h3-off", H3, lambda: page.level("toggle-heading-3"))):
        fresh(page, raw)
        base = rows_of(page)
        page.place(paragraph)
        press()
        page.quiet()
        changed = rows_of(page)
        if mutate != "no-undo":
            page.key("z", ("ctrl",))
            page.quiet()
        after = rows_of(page)
        page.check(f"T8/{name}", changed != base and [(r["text"], r["level"], r["kind"], r["list"]) for r in after] == [(r["text"], r["level"], r["kind"], r["list"]) for r in base],
                   {"changed": changed[paragraph], "after": after[paragraph]})


def t9(page, raw):
    fresh(page, raw)
    # A fresh document, caret placed: body, or nothing yet.  Never a level it does not have.
    first = page.toolbar()
    page.check("T9/fresh-document-claims-no-level", [i["action"] for i in first["items"] if i["checked"] == "true"] in ([], ["set-paragraph-body"]) and first["pressed"] != "true", first["items"])
    want = {H1: (1, "false", None), H2: (2, "false", None), H3: (3, "false", None), H4: (4, "false", None), BODY2: (0, "false", "false"),
            ITEM: (0, "true", "false"), NUMBERED: (0, "false", "true"), JULIET: (0, "false", "false")}
    for paragraph, (level, bullet, number) in want.items():
        page.place(paragraph)
        for _ in range(20):  # the state follows the caret within 355 ms (cache-freshness/run-02)
            s = page.toolbar()
            checked = [i["action"] for i in s["items"] if i["checked"] == "true"]
            if len(checked) == 1 and s["bullet"] == bullet and s["number"] == number:
                break
            time.sleep(.1)
        item = "set-paragraph-body" if level == 0 else f"toggle-heading-{level}"
        page.check(f"T9/paragraph-{paragraph}", checked == [item] and s["bullet"] == bullet and s["number"] == number and s["pressed"] == ("true" if level else "false"),
                   {"checked": checked, "bullet": s["bullet"], "number": s["number"], "pressed": s["pressed"]})


def t10(page, raw):
    fresh(page, raw)
    s = page.toolbar()
    page.check("T10/setters-hidden-toggles-shown", s["legacyHidden"] and not s["toggleHidden"], s)
    page.press("#heading-menu-button")
    s = page.toolbar()
    page.check("T10/opens", s["open"] and s["expanded"] == "true", s["expanded"])
    page.check("T10/inside-the-window", 0 <= s["box"]["left"] and s["box"]["right"] <= s["box"]["innerWidth"] and s["box"]["bottom"] <= s["box"]["innerHeight"], s["box"])
    page.check("T10/five-items", [i["label"] for i in s["items"]] == ["內文", "標題 1", "標題 2", "標題 3", "標題 4"], [i["label"] for i in s["items"]])
    page.check("T10/mouse-open-leaves-the-sink-focused", s["focus"] == "sink", s["focus"])
    real.key(page.session, page.browser, "Escape", ())
    s = page.toolbar()
    page.check("T10/escape-closes-a-mouse-open", not s["open"] and s["focus"] == "sink", {"open": s["open"], "focus": s["focus"]})
    page.press("#heading-menu-button")
    page.check("T10/opens-again", page.toolbar()["open"], None)
    page.click_paper(1500, 1500)
    s = page.toolbar()
    page.check("T10/closes-outside", not s["open"], s["open"])
    evaluate(page.session, "document.querySelector('#heading-menu-button').focus()")
    real.key(page.session, page.browser, "ArrowDown", ())
    s = page.toolbar()
    page.check("T10/keyboard-opens-on-an-item", s["open"] and s["focus"] in ("set-paragraph-body", "toggle-heading-1", "toggle-heading-2", "toggle-heading-3", "toggle-heading-4"), s["focus"])
    real.key(page.session, page.browser, "ArrowDown", ())
    moved = page.toolbar()["focus"]
    page.check("T10/arrow-moves", moved != s["focus"], moved)
    real.key(page.session, page.browser, "Escape", ())
    s = page.toolbar()
    page.check("T10/escape-closes-and-returns", not s["open"] and s["focus"] == "heading-menu-button", {"open": s["open"], "focus": s["focus"]})
    real.key(page.session, page.browser, "ArrowDown", ())
    page.check("T10/keyboard-reopens", page.toolbar()["open"], None)
    real.key(page.session, page.browser, "Enter", ())
    page.quiet()
    s = page.toolbar()
    page.check("T10/keyboard-press-gives-the-sink-back", not s["open"] and s["focus"] == "sink", {"open": s["open"], "focus": s["focus"]})
    page.key("q")
    page.quiet()
    page.check("T10/typing-after-a-keyboard-press-lands", any("q" in r["text"] for r in rows_of(page)), None)


def t11(page, raw):
    fresh(page, raw)
    page.place(BODY2)
    page.level("toggle-heading-4")
    page.place(JULIET)
    page.press(BULLET)
    page.quiet()
    saved = page.save()
    fresh(page, saved)
    rows = rows_of(page)
    page.check("T11/reopened", rows[BODY2]["level"] == 4 and rows[JULIET]["list"], [rows[BODY2], rows[JULIET]])


def t12(page, image):
    """A paragraph holding an as-char frame: refused before v32 (finding 037's guard), and the read never asks for the selection's text."""
    fresh(page, image)
    page.place(1)
    page.press(BULLET)
    page.quiet()
    saved = page.save()
    page.check("T12/caret-in-a-paragraph-with-a-frame", shape(saved)[1]["kind"] == "ul" and frames(saved) == 1, shape(saved)[1])
    page.press(BULLET)
    page.quiet()
    page.check("T12/second-press", shape(page.save())[1]["kind"] is None, None)
    page.place(0)
    page.key("ArrowDown", ("shift",))
    page.key("End", ("shift",))
    page.level("toggle-heading-2")
    saved = page.save()
    rows = shape(saved)
    page.check("T12/range-over-a-frame", rows[0]["level"] == 2 and rows[1]["level"] == 2 and frames(saved) == 1, rows[:2])
    page.check("T12/responsive", evaluate(page.session, "document.querySelector('#state-pill').dataset.state") == "ready", None)


GROUPS = ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12")


def run_one(record, raws, out, mutate, only):
    session = None
    try:
        session = common.open_browser(record["browser"], (1400, 1000))
        record["version"] = getattr(session, "version", None)
        page = Page(session, record["browser"], record)
        raw = raws["levels"]
        page.open(raw)
        page.click_paper(1500, 1500)
        page.quiet()
        base = rows_of(page)
        page.check("setup/fixture-reads-as-written", [r["level"] for r in base][:6] == [0, 0, 1, 2, 3, 4] and base[ITEM]["list"], base[:7])
        steps = {"T1": lambda: t1(page, raw, mutate), "T2": lambda: t2(page, raw), "T3": lambda: t3(page, raw), "T4": lambda: t4(page, raw, raws["caret"]),
                 "T5": lambda: t5(page, raws["blank"]), "T6": lambda: t6(page, raw), "T7": lambda: t7(page, raw, raws["table"], raws["long"]), "T8": lambda: t8(page, raw, mutate),
                 "T9": lambda: t9(page, raw), "T10": lambda: t10(page, raw), "T11": lambda: t11(page, raw), "T12": lambda: t12(page, raws["image"])}
        for group in GROUPS:
            if only and group not in only:
                continue
            try:
                steps[group]()
            except Exception:
                record["checks"].append({"id": f"{group}/fatal", "pass": False, "actual": traceback.format_exc()[-800:]})
        (out / f"{record['browser']}-after.png").write_bytes(session.screenshot())
    except Exception:
        record["fatal"] = traceback.format_exc()
    finally:
        if session is not None:
            record["cleanup"] = common.close_browser(session)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--profile")
    parser.add_argument("--mutate", choices=("swap-levels", "no-undo", "no-second-press"))
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raws = {"levels": LEVELS.read_bytes(), "blank": BLANK.read_bytes(), "table": TABLE.read_bytes(), "caret": CARET.read_bytes(),
            "long": (EVIDENCE / "long-fixture.odt").read_bytes(), "image": (EVIDENCE / "image-valid-fixture.odt").read_bytes()}
    only = set(filter(None, args.only.split(",")))
    page = z.APP.read_text(encoding="utf-8")
    if args.profile:
        page = pp.repointed_page(page, args.profile, z.PROJECT / "dist/profiles" / args.profile / "sdk-manifest.json")[0]
    html = z.HTML.read_text(encoding="utf-8")
    report = {"argv": sys.argv, "mutate": args.mutate, "tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "profile": args.profile,
              "page": hashlib.sha256(page.encode()).hexdigest(), "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="writer-toggle-", dir=z.PROJECT / "build"))
    try:
        with common.browser_lock("check_writer_toggle"):
            pre = common.pre_run_checks()
            report["preRun"] = {k: pre[k] for k in ("refuse", "loadavg")}
            if pre["refuse"]:
                raise SystemExit(f"pre-run refused: {pre['refuse']}")
            pp.build_mirror(common.DIST, scratch / "m", {
                "e2-editor.html": common.inject(html, [z.OBSERVER, WATCH] + ([WATCH_ACTIONS] if args.mutate == "swap-levels" else [])).encode(),
                "e2-editor-app.js": page.encode()})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    record = {"browser": browser, "base": base, "checks": []}
                    report["runs"].append(record)
                    run_one(record, raws, out, args.mutate, only)
                    print(browser, sum(c["pass"] for c in record["checks"]), "/", len(record["checks"]),
                          sorted({c["id"] for c in record["checks"] if not c["pass"]})[:30],
                          (record.get("fatal") or "").strip().splitlines()[-1:] or "", file=sys.stderr, flush=True)
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    checks = [c for r in report["runs"] for c in r["checks"]]
    held = bool(checks) and all(c["pass"] for c in checks) and not any(r.get("fatal") for r in report["runs"])
    report["verdict"] = "P4_HOLDS" if held else "P4_RED"
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], file=sys.stderr)
    return 0 if held else 1


if __name__ == "__main__":
    raise SystemExit(main())
