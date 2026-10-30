#!/usr/bin/env python3
"""S4 (SPEC-M3-v28-last-line-fallback 7.3, procedure pinned by its append 1): finding 083's path on a multi-paragraph
document's LAST line, on the user's path -- v28's fallback (`.uno:CharLeftSel`, judged by the readback's last block)
verifies the five paragraph actions there, refuses a table with its own sentence, and leaves the blank document as
it was.

Derived from tools/check_v81_blank_line_bullet.py (S3) and tools/check_v81_blank_bullet.py (S2′), both IMPORTED and
not edited (their evidence binds them).  Every input is real (tools/v21_input.py: Chrome CDP Input.*, Firefox
WebDriver actions).  S3's observer, page read and save Blob read are used as they are; `one()` is S3's procedure
with the cell's parameters (fixture, Enters, action, whether a marker is typed, how undo is pressed).

Cells (spec 7.3 S4, append 1):
  a          two-plain, click below the text, Enter, bullet, type, save; Ctrl+Z twice, save
  e          two-plain, Enter twice, bullet, type, save
  b-number   two-plain, Enter, 1. 編號, save; Ctrl+Z once, save
  b-heading  two-plain, Enter, 標題, save; Ctrl+Z once, save
  b-none     bulleted-last (an empty bullet item last), no Enter, 移除清單, save; Ctrl+Z once, save
  b-body     realheading-last (an empty real Heading 1 last), no Enter, 內文, save; Ctrl+Z once, save
  d          table-then-empty-last, no Enter, bullet, type, save; the toolbar 「↶ 復原」 twice, save
  c          the blank document: B1's procedure (arms noclick, click) through S2′'s judge, plus the worker reply row

Products (tools/v82_f_products.py, identity checked file by file): before = generation 81 (v27), after = the
generation-82 candidate as dist/ serves it (v28).

Mutations (spec 7.3), each its own report, each must make every run FAIL:
  --mutation press-list-none     cell a on after, pressing 移除清單 instead of the bullet
  --mutation cosmetic-review     cell a on generation 81 with a page that hides the review (no toast, no
                                 [review] line, `N ms` in the strip): only the worker reply row can be red
  --mutation wrong-button-b-number|b-none|b-heading|b-body
                                 the cell on after with the wrong button (append 1 item 5)

  check_v82_last_line_bullet.py --out DIR [--cells a,e,...] [--browsers chrome,firefox] [--repetitions 3]
                                [--mutation NAME]
  check_v82_last_line_bullet.py --self-test REPORT    (every clause's mutation on a holding report: red)

Verdicts: S4_HOLDS (all eight cells, both identities, every after run PASS, every judged before run red for 083,
cell c's user-visible results one value across both products, full count); S4_SUBSET_HOLDS (the same over a
--cells subset; not S4); S4_MUTATION_CAUGHT.  --out must not exist.  Nothing under dist/ is written.  Not a timing
measurement.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
sys.path.insert(0, str(PROJECT / "tools"))
import check_v81_blank_line_bullet as s3  # noqa: E402
import check_v81_blank_bullet as s2p  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v82_f_products as products  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

b1 = s2p.b1
S4_FIXTURES = REPO / "findings/evidence/v28-083/fixtures-s4/build-01"
FIXTURES = {
    "two-plain": (s3.FIXTURE, s3.FIXTURE_SHA256),
    "bulleted-last": (S4_FIXTURES / "bulleted-last.odt",
                      "de281bc50308fc1d0623f4ef112071730d288838c118e3bb0b4dcdac74aaf234"),
    "realheading-last": (S4_FIXTURES / "realheading-last.odt",
                         "00be627b33ffc4c2f0a00a1954a54736f8a5dc27b242e1b97a896030b75393eb"),
    "table-then-empty-last": (S4_FIXTURES / "table-then-empty-last.odt",
                              "42bd8b5b0f22f03414fef0508d2efa86f18ea8b6d1d3a8222ff7cc8fa3fb2c84"),
}
CLICK = (0.80, 0.15)  # PL-1-v28's point, below the text (append 1 item 2)
MARKER = "mks4q"
FIRST, NEXT, CELL_TEXT = "Plain first", "E1-EMPTY-AFTER", "Cell text"
LABELS = {"set-list-unordered": "• 項目符號", "set-list-ordered": "1. 編號", "set-list-none": "移除清單",
          "set-paragraph-heading": "標題", "set-paragraph-body": "內文"}
BULLET, NUMBER = "list-level-style-bullet", "list-level-style-number"
EMPTY_SENTENCE = "這一段是空的"
FALLBACK_SENTENCE = "往前多選一格"
UNDO_WORDS = "不是你要的就按「復原」"
CHECKPOINT = "回到檢查點"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
BARRIER_KEYS = ("route", "readbackBlockCount", "itemCount", "failureShape", "dispatched", "selectionResultSeen",
                "undo", "fallback")
UNDO_BOX = pp.BUTTON_BOX.replace("ARG_SELECTOR", '#toolbar button[data-action="undo"]')

# name: fixture, Enters, action, marker typed, undo (kind, count)
CELLS = {
    "a": ("two-plain", 1, "set-list-unordered", True, ("ctrl-z", 2)),
    "e": ("two-plain", 2, "set-list-unordered", True, None),
    "b-number": ("two-plain", 1, "set-list-ordered", False, ("ctrl-z", 1)),
    "b-heading": ("two-plain", 1, "set-paragraph-heading", False, ("ctrl-z", 1)),
    "b-none": ("bulleted-last", 0, "set-list-none", False, ("ctrl-z", 1)),
    "b-body": ("realheading-last", 0, "set-paragraph-body", False, ("ctrl-z", 1)),
    "d": ("table-then-empty-last", 0, "set-list-unordered", True, ("button", 2)),
    "c": ("blank", None, "set-list-unordered", True, None),
}
WRONG = {"b-number": "set-list-unordered", "b-none": "set-list-ordered", "b-heading": "set-paragraph-body",
         "b-body": "set-paragraph-heading"}
# mutation: (cell, product, the button pressed)
MUTATIONS = {"press-list-none": ("a", "after", "set-list-none"), "cosmetic-review": ("a", "cosmetic-review", None),
             **{f"wrong-button-{cell}": (cell, "after", action) for cell, action in WRONG.items()}}
# The clause each mutation must be red ON, in every run: a run that is red only because the strip shows another
# button's label would be a catch by the wrong clause.  cosmetic-review must ALSO hold the page's three clauses:
# that the worker reply row is the only thing that sees it is the point (v27 S3).
MUTATION_RED_ON = {"press-list-none": "saved-target-state", "cosmetic-review": "reply-ok",
                   **{f"wrong-button-{cell}": "saved-target-state" for cell in WRONG}}
COSMETIC_HOLDS = ("no-toast", "no-review-line", "strip")


def odt_reading(raw: bytes) -> dict:
    """S3's reading of the body paragraphs, plus each paragraph's style and whether it is in a table cell."""
    package = zipfile.ZipFile(io.BytesIO(raw))
    root = ET.fromstring(package.read("content.xml"))
    base = s3.odt_reading(raw)
    parent = {child: node for node in root.iter() for child in node}
    body = next(root.iter("{urn:oasis:names:tc:opendocument:xmlns:office:1.0}text"))
    extra = []
    for node in body.iter():
        if node.tag not in (f"{{{TEXT_NS}}}p", f"{{{TEXT_NS}}}h"):
            continue
        up, in_table = parent.get(node), False
        while up is not None and up is not body:
            in_table = in_table or up.tag == f"{{{TABLE_NS}}}table-cell"
            up = parent.get(up)
        extra.append({"style": node.get(f"{{{TEXT_NS}}}style-name"), "inTable": in_table})
    for p, more in zip(base["paragraphs"], extra, strict=True):
        p.update(more)
    return base


def rows(session, start):
    record = evaluate(session, "window.__s3")
    replies = {r.get("requestId"): r for r in record["responses"]}
    out = []
    for q in record["requests"][start:]:
        payload = q.get("payload") or {}
        reply = replies.get(q.get("requestId")) or {}
        error, result = reply.get("error") or {}, reply.get("result") or {}
        barrier = result.get("formatBarrier") or error.get("formatBarrier") or (error.get("details") or {}).get("formatBarrier")
        out.append({"operation": q.get("operation"), "action": payload.get("action"), "replied": bool(reply),
                    "ok": reply.get("ok"), "code": error.get("code"), "message": error.get("message"),
                    "recovery": error.get("recovery"), "completion": result.get("completion"),
                    "formatBarrier": {k: barrier.get(k) for k in BARRIER_KEYS} if barrier else None,
                    "revision": [result.get("beforeRevision"), result.get("revision")]})
    return out


def save(session, out, key):
    blobs = evaluate(session, s3.PAGE)["blobs"]
    evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    _, out[key + "Settled"] = s3.wait(session, lambda s: s["blobs"] > blobs, 60)
    if out[key + "Settled"]:
        out[key] = odt_reading(base64.b64decode(evaluate(session, s3.BLOB)))


def settled_edit(session, mark, limit=30):
    return s3.wait(session, lambda s: s["requests"] > mark["requests"] and s["responses"] >= s["requests"]
                   and s["revision"] != mark["revision"], limit)[1]


def one(session, browser, base, cell, raw_doc, action):
    fixture, enters, _, typed, undo = CELLS[cell]
    navigate(session, base)
    _, ok = s3.wait(session, lambda s: s["pill"] == "ready", 240)
    if not ok:
        return {"fatal": "page not ready"}
    workers = evaluate(session, s3.PAGE)["workers"]
    opened = evaluate(session, pp.OPEN_BYTES.replace("ARG_B64", base64.b64encode(raw_doc).decode())
                      .replace("ARG_NAME", FIXTURES[fixture][0].name))
    state, ok = s3.wait(session, lambda s: s["workers"] > workers and s["pill"] == "ready", 120)
    if not ok:
        return {"fatal": f"document not opened ({opened})", "page": state}
    time.sleep(1.5)
    out = {"action": action, "opened": evaluate(session, s3.PAGE)}
    evaluate(session, real.SCROLL_TO_FRACTION.replace("ARG_F", repr(CLICK[1])))
    time.sleep(0.25)
    rect = evaluate(session, real.PAPER_RECT)
    point = (rect["left"] + rect["width"] * CLICK[0], rect["top"] + rect["height"] * CLICK[1])
    out["clickAt"] = {"fraction": CLICK, "viewport": point}
    real.click(session, browser, *point)
    _, out["caretPlaced"] = s3.wait(session, lambda s: "定位游標" in (s["latency"] or ""), 30)
    time.sleep(0.8)
    out["enters"] = []
    for _ in range(enters):
        mark = evaluate(session, s3.PAGE)
        real.key(session, browser, "Enter")
        out["enters"].append(settled_edit(session, mark))
        time.sleep(0.8)
    evaluate(session, pp.CLEAR_TOAST)
    start = evaluate(session, s3.PAGE)
    label = evaluate(session, pp.BUTTON_LABEL.replace("ARG_ACTION", action))
    box = evaluate(session, pp.BUTTON_BOX.replace("ARG_SELECTOR", f'#toolbar button[data-action="{action}"]'))
    if not box or not label:
        out["fatal"] = f"no {action} button"
        return out
    out["label"] = label
    real.click(session, browser, box["x"], box["y"])
    _, out["pressSettled"] = s3.wait(session, lambda s: s["pill"] in ("recoverable-error", "restart-required")
                                     or label in (s["latency"] or ""), 60)
    time.sleep(1.5)
    out["press"] = evaluate(session, s3.PAGE)
    out["pressRows"] = rows(session, start["requests"])
    out["pressWarns"] = evaluate(session, "window.__s3.warns")[start["warns"]:]
    if typed:
        mark = evaluate(session, s3.PAGE)
        for ch in MARKER:
            real.key(session, browser, ch)
            time.sleep(0.12)
        out["typedSettled"] = s3.wait(session, lambda s: s["requests"] > mark["requests"]
                                      and s["responses"] >= s["requests"] and s["pill"] == "ready"
                                      and s["revision"] != mark["revision"], 30)[1]
        time.sleep(1.5)
        out["typed"] = evaluate(session, s3.PAGE)
        out["typedRows"] = rows(session, mark["requests"])
    save(session, out, "saved")
    if undo:
        kind, count = undo
        out["undo"] = []
        for _ in range(count):
            evaluate(session, s3.CLEAR_LATENCY)
            mark = evaluate(session, s3.PAGE)
            if kind == "ctrl-z":
                real.key(session, browser, "z", ("ctrl",))
            else:
                ubox = evaluate(session, UNDO_BOX)
                real.click(session, browser, ubox["x"], ubox["y"])
            settled = s3.wait(session, lambda s: s["requests"] > mark["requests"] and s["responses"] >= s["requests"]
                              and "復原" in (s["latency"] or ""), 30)[1]
            time.sleep(1.0)
            out["undo"].append({"kind": kind, "settled": settled, "page": evaluate(session, s3.PAGE),
                                "rows": rows(session, mark["requests"])})
        save(session, out, "savedAfterUndo")
    return out


def one_blank(session, browser, base, arm, raw_blank):
    """Cell c: B1's procedure unchanged, then the bullet's reply row with `fallback`, read from B1's observer."""
    out = b1.one(session, browser, base, arm, raw_blank, "after")
    record = evaluate(session, "window.__b1")
    replies = {r.get("requestId"): r for r in record["responses"]}
    bullet = [q for q in record["requests"] if (q.get("payload") or {}).get("action") == "set-list-unordered"]
    out["bulletRequests"] = len(bullet)
    if bullet:
        error = (replies.get(bullet[-1].get("requestId")) or {}).get("error") or {}
        barrier = error.get("formatBarrier") or (error.get("details") or {}).get("formatBarrier") or {}
        out["bulletFallback"] = barrier.get("fallback", "ABSENT")
    return out


# ------------------------------------------------------------------ judging

def press_row(run):
    return next((r for r in run.get("pressRows") or [] if r.get("action") == run.get("action")), None)


def barrier(run):
    return (press_row(run) or {}).get("formatBarrier") or {}


def fallback(run):
    return barrier(run).get("fallback") or {}


def ps(run, key):
    return (run.get(key) or {}).get("paragraphs") or []


def plain(p, text):
    return bool(p) and p["text"] == text and p["tag"] == "p" and not p["inList"] and not p.get("inTable")


def _press(run):
    return run.get("press") or {}


def strip_verified(cell):
    return re.compile(re.escape(LABELS[CELLS[cell][2]]) + r" \d+ ms")


def last_state_ok(cell, p):
    """The target state of the cell's action, read on the saved last paragraph."""
    action = CELLS[cell][2]
    if not p:
        return False
    if action == "set-list-unordered":
        return p["inList"] and p["listLevel1"] == BULLET
    if action == "set-list-ordered":
        return p["inList"] and p["listLevel1"] == NUMBER
    if action == "set-list-none":
        return not p["inList"]
    if action == "set-paragraph-heading":
        return p["tag"] == "h"
    return p["tag"] == "p"


def fixture_last_ok(cell, p):
    """The saved last paragraph back in the fixture's state (after undo)."""
    fixture = CELLS[cell][0]
    if not p or p["text"] != "":
        return False
    if fixture == "bulleted-last":
        return p["inList"] and p["listLevel1"] == BULLET
    if fixture == "realheading-last":
        return p["tag"] == "h" and not p["inList"]
    return p["tag"] == "p" and not p["inList"]


def neighbours_ok(cell, paragraphs):
    """Every paragraph before the last unchanged in text and kind; the count the procedure implies."""
    fixture, enters = CELLS[cell][0], CELLS[cell][1]
    if fixture == "two-plain":
        want = [FIRST, NEXT] + [""] * (enters - 1)
        return len(paragraphs) == len(want) + 1 and all(plain(p, t) for p, t in zip(paragraphs, want))
    if fixture == "table-then-empty-last":
        return (len(paragraphs) == 3 and plain(paragraphs[0], FIRST) and paragraphs[1]["text"] == CELL_TEXT
                and paragraphs[1]["inTable"] and not paragraphs[1]["inList"])
    return len(paragraphs) == 2 and plain(paragraphs[0], FIRST)


def last(run, key):
    paragraphs = ps(run, key)
    return paragraphs[-1] if paragraphs else None


def marker_last(run):
    paragraphs = ps(run, "saved")
    found = [i for i, p in enumerate(paragraphs) if MARKER in p["text"]]
    return len(found) == 1 and found[0] == len(paragraphs) - 1 and paragraphs[-1]["text"] == MARKER


def undo_ok(run):
    kind, count = CELLS[run["cell"]][4]
    undo = run.get("undo") or []
    return len(undo) == count and all(u["settled"] and any(r["operation"] == "undo" and r["ok"] is True
                                                           for r in u["rows"]) for u in undo)


def typed_ok(run):
    inserts = [r for r in run.get("typedRows") or [] if r.get("operation") == "insertText"]
    return bool(run.get("typedSettled")) and bool(inserts) and all(r.get("ok") is True for r in inserts)


def _set(path_fn, key, value):
    def mutate(run):
        path_fn(run)[key] = value
    return mutate


def _row_set(key, value):
    return lambda r: press_row(r).__setitem__(key, value)


def _barrier_set(key, value):
    return lambda r: barrier(r).__setitem__(key, value)


def _fallback_set(key, value):
    return lambda r: fallback(r).__setitem__(key, value)


def _last_set(key, value, which="saved"):
    return lambda r: ps(r, which)[-1].__setitem__(key, value)


def _first_text(which):
    return lambda r: ps(r, which)[0].__setitem__("text", "Plain first changed")


def _undo_refused(run):
    for r in run["undo"][-1]["rows"]:
        if r["operation"] == "undo":
            r["ok"] = False


def _state_mutation(cell):
    action = CELLS[cell][2]
    if action == "set-list-unordered":
        return _last_set("listLevel1", NUMBER)
    if action == "set-list-ordered":
        return _last_set("listLevel1", BULLET)
    if action == "set-list-none":
        return _last_set("inList", True)
    if action == "set-paragraph-heading":
        return _last_set("tag", "p")
    return _last_set("tag", "h")


def _undo_state_mutation(cell):
    fixture = CELLS[cell][0]
    if fixture == "bulleted-last":
        return _last_set("inList", False, "savedAfterUndo")
    if fixture == "realheading-last":
        return _last_set("tag", "p", "savedAfterUndo")
    return _last_set("inList", True, "savedAfterUndo")


def after_clauses(cell):
    """(id, predicate over one after run of `cell`, mutation of a run that holds it)."""
    if cell == "d":
        return D_CLAUSES
    clauses = [
        ("ready", lambda r: _press(r).get("pill") == "ready", _set(_press, "pill", "recoverable-error")),
        ("no-toast", lambda r: (_press(r).get("toast") or "").strip() == "",
         _set(_press, "toast", "• 項目符號：動作已送出，但這一段是空的")),
        ("no-review-line", lambda r: not any(w.startswith("[review]") for w in r.get("pressWarns") or []),
         lambda r: r["pressWarns"].append("[review] x: MUTATION_OUTCOME_UNKNOWN")),
        ("strip", lambda r: strip_verified(r["cell"]).fullmatch(_press(r).get("latency") or "") is not None,
         _set(_press, "latency", "x：待確認")),
        ("reply-ok", lambda r: (press_row(r) or {}).get("ok") is True, _row_set("ok", False)),
        ("completion", lambda r: (press_row(r) or {}).get("completion") == "verified-format-readback",
         _row_set("completion", None)),
        ("route", lambda r: barrier(r).get("route") == "collapsed", _barrier_set("route", "range-single")),
        ("fallback-ran", lambda r: fallback(r).get("ran") is True, _fallback_set("ran", False)),
        ("fallback-two-blocks", lambda r: fallback(r).get("blockCount") == 2, _fallback_set("blockCount", 3)),
        ("restore-confirmed", lambda r: fallback(r).get("restoreConfirmed") is True,
         _fallback_set("restoreConfirmed", False)),
        ("saved-target-state", lambda r: last_state_ok(r["cell"], last(r, "saved")), _state_mutation(cell)),
        ("saved-neighbours", lambda r: neighbours_ok(r["cell"], ps(r, "saved")), _first_text("saved")),
    ]
    if cell in ("a", "e"):
        clauses.append(("fallback-last-ul", lambda r: fallback(r).get("lastListTag") == "ul",
                        _fallback_set("lastListTag", "")))
    if CELLS[cell][3]:
        clauses += [("typed", typed_ok, lambda r: r["typedRows"].clear()),
                    ("saved-marker-last", marker_last, _last_set("text", ""))]
    if CELLS[cell][4]:
        clauses += [("undo-replies-ok", undo_ok, _undo_refused),
                    ("undo-neighbours", lambda r: neighbours_ok(r["cell"], ps(r, "savedAfterUndo")),
                     _first_text("savedAfterUndo")),
                    ("undo-fixture-state", lambda r: fixture_last_ok(r["cell"], last(r, "savedAfterUndo")),
                     _undo_state_mutation(cell))]
    return clauses


D_CLAUSES = [
    ("ready", lambda r: _press(r).get("pill") == "ready", _set(_press, "pill", "recoverable-error")),
    ("new-sentence", lambda r: FALLBACK_SENTENCE in (_press(r).get("toast") or "")
     and UNDO_WORDS in (_press(r).get("toast") or ""), _set(_press, "toast", "• 項目符號：動作已送出，但這一段是空的")),
    ("no-checkpoint", lambda r: CHECKPOINT not in (_press(r).get("toast") or "")
     and (_press(r).get("notice") or {}).get("show") != "1",
     lambda r: _press(r)["notice"].__setitem__("show", "1")),
    ("strip-review", lambda r: _press(r).get("latency") == "• 項目符號：待確認", _set(_press, "latency", "• 項目符號 失敗")),
    ("review-line", lambda r: any(w.startswith("[review]") for w in r.get("pressWarns") or []),
     lambda r: r["pressWarns"].clear()),
    ("refused-shape", lambda r: (press_row(r) or {}).get("ok") is False
     and barrier(r).get("failureShape") == "fallback-readback-refused" and barrier(r).get("route") == "collapsed"
     and barrier(r).get("dispatched") is True, _barrier_set("failureShape", "select-text-returned-none")),
    ("refusal-table", lambda r: fallback(r).get("refusal") == "unknown-structural-tag",
     _fallback_set("refusal", "unexpected-block-count")),
    ("restore-confirmed", lambda r: fallback(r).get("restoreConfirmed") is True,
     _fallback_set("restoreConfirmed", False)),
    ("typed", typed_ok, lambda r: r["typedRows"].clear()),
    ("saved-marker-last", marker_last, _last_set("text", "")),
    ("saved-neighbours", lambda r: neighbours_ok("d", ps(r, "saved")),
     lambda r: ps(r, "saved")[1].__setitem__("text", "Cell textmks4q")),
    ("undo-replies-ok", undo_ok, _undo_refused),
    ("undo-neighbours", lambda r: neighbours_ok("d", ps(r, "savedAfterUndo")), _first_text("savedAfterUndo")),
    ("undo-fixture-state", lambda r: fixture_last_ok("d", last(r, "savedAfterUndo")),
     _last_set("inList", True, "savedAfterUndo")),
]
BEFORE_083 = [
    ("B.083-shape", lambda r: (press_row(r) or {}).get("ok") is False
     and barrier(r).get("failureShape") == "select-text-returned-none",
     _barrier_set("failureShape", "postcondition-not-met")),
    ("B.083-sentence", lambda r: EMPTY_SENTENCE in (_press(r).get("toast") or ""), _set(_press, "toast", "")),
    ("B.no-fallback", lambda r: bool(barrier(r)) and barrier(r).get("fallback") is None,
     _barrier_set("fallback", {"ran": True})),
]


def blank_after(run):
    outcome, why = s2p.judge_after(run)
    fb = run.get("bulletFallback")
    if not (isinstance(fb, dict) and fb.get("ran") is True and fb.get("selectionType") == 0):
        why = list(why) + [f"fallback {fb!r}"]
    if outcome == "NE":
        return outcome, why
    return ("PASS" if not why else "FAIL"), why


def blank_before(run):
    outcome, why = s2p.judge_after(run)
    if outcome == "NE":
        return outcome, why
    if run.get("bulletFallback") not in ("ABSENT", None):
        why = list(why) + [f"fallback present on v27: {run.get('bulletFallback')!r}"]
    return ("PASS" if not why else "FAIL"), why


def visible(run):
    press, typed = run.get("press") or {}, run.get("typed") or {}
    return [press.get("pill"), press.get("toast"), press.get("latency"), typed.get("latency"),
            (press.get("notice") or {}).get("show") == "1"]


def judge(run, clauses):
    if run.get("fatal"):
        return "NE", {"fatal": run["fatal"].strip().splitlines()[-1]}
    results = {}
    for cid, holds, _ in clauses:
        try:
            results[cid] = bool(holds(run))
        except Exception as error:  # noqa: BLE001 -- unreadable is not holding
            results[cid] = False
            results[cid + ":error"] = f"{type(error).__name__}: {error}"
    return ("PASS" if all(v for k, v in results.items() if ":" not in k) else "FAIL"), results


def judge_run(run, mutation):
    cell = run["cell"]
    if cell == "c":
        outcome, why = (blank_before if run["product"] == "before" else blank_after)(run)
        return outcome, {"why": why}
    if run["product"] == "before" and not mutation:
        if cell in ("d", "e"):
            return "RECORDED", {}
        return judge(run, BEFORE_083)
    return judge(run, after_clauses(cell))


def verdict(report):
    config = report["config"]
    mutation = config.get("mutation")
    per = len(config["browsers"]) * config["repetitions"]
    problems = [f"{name}: identity failed" for name in config["products"] if not report["products"].get(name, {}).get("ok")]
    for r in report["runs"]:
        r["outcome"], r["clauses"] = judge_run(r, mutation)
        r["failedClauses"] = sorted(k for k, v in r["clauses"].items() if v is False)
    runs = report["runs"]
    if mutation:
        if not (len(runs) == per and all(r["outcome"] == "FAIL" for r in runs)):
            problems.append(f"mutation {mutation}: {sum(r['outcome'] == 'FAIL' for r in runs)}/{per} runs FAIL "
                            f"(outcomes {[r['outcome'] for r in runs]})")
        for r in runs:
            if MUTATION_RED_ON[mutation] not in r["failedClauses"]:
                problems.append(f"{r['browser']} {r['repetition']}: not red on {MUTATION_RED_ON[mutation]} "
                                f"(red on {r['failedClauses']})")
            if mutation == "cosmetic-review" and any(c in r["failedClauses"] for c in COSMETIC_HOLDS):
                problems.append(f"{r['browser']} {r['repetition']}: the page itself was red "
                                f"({r['failedClauses']}), so this is not the reply-row-only case")
        return ("S4_MUTATION_CAUGHT" if not problems else "S4_MUTATION_MISSED"), problems
    for cell in config["cells"]:
        want = per * (len(config["arms"]) if cell == "c" else 1)
        for product in ("before", "after"):
            got = [r for r in runs if r["cell"] == cell and r["product"] == product]
            if product == "before" and cell in ("d", "e"):
                if len(got) != want:
                    problems.append(f"{cell} before: {len(got)}/{want} runs recorded")
                continue
            passed = sum(r["outcome"] == "PASS" for r in got)
            if not (len(got) == want and passed == want):
                problems.append(f"{cell} {product}: {passed}/{want} PASS")
    blank = [r for r in runs if r["cell"] == "c"]
    if blank:
        values = {json.dumps(visible(r), ensure_ascii=False) for r in blank}
        if len(values) != 1:
            problems.append(f"c: the user-visible results differ across runs: {sorted(values)}")
    complete = sorted(config["cells"]) == sorted(CELLS)
    if problems:
        return "S4_RED", problems
    return ("S4_HOLDS" if complete else "S4_SUBSET_HOLDS"), problems


def self_test(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    base, _ = verdict(copy.deepcopy(report))
    if base not in ("S4_HOLDS", "S4_SUBSET_HOLDS"):
        print(f"self-test needs a holding report; this one is {base}", file=sys.stderr)
        return 2
    results = {}

    def index(cell, product):
        return next(i for i, r in enumerate(report["runs"]) if r["cell"] == cell and r["product"] == product)
    for cell in report["config"]["cells"]:
        if cell == "c":
            continue
        for cid, _, mutate in after_clauses(cell):
            mutated = copy.deepcopy(report)
            mutate(mutated["runs"][index(cell, "after")])
            results[f"{cell}/{cid}"] = verdict(mutated)[0]
        if cell not in ("d", "e"):
            for cid, _, mutate in BEFORE_083:
                mutated = copy.deepcopy(report)
                mutate(mutated["runs"][index(cell, "before")])
                results[f"{cell}/{cid}"] = verdict(mutated)[0]
    if "c" in report["config"]["cells"]:
        blank_mutations = {
            "c/after-fallback-absent": lambda r: r["runs"][index("c", "after")].__setitem__("bulletFallback", "ABSENT"),
            "c/after-fallback-read": lambda r: r["runs"][index("c", "after")]["bulletFallback"].__setitem__("selectionType", 1),
            "c/before-fallback-present": lambda r: r["runs"][index("c", "before")].__setitem__("bulletFallback", {"ran": True}),
            "c/after-strip-failed": lambda r: r["runs"][index("c", "after")]["press"].__setitem__("latency", "• 項目符號 失敗"),
            "c/before-visible-differs": lambda r: r["runs"][index("c", "before")]["press"].__setitem__(
                "toast", r["runs"][index("c", "before")]["press"]["toast"] + "。"),
        }
        for name, mutate in blank_mutations.items():
            mutated = copy.deepcopy(report)
            mutate(mutated)
            results[name] = verdict(mutated)[0]
    for name, mutate in {"one-run-missing": lambda r: r["runs"].pop(0),
                         "identity-failed": lambda r: r["products"]["after"].__setitem__("ok", False),
                         "one-run-fatal": lambda r: r["runs"][-1].__setitem__("fatal", "Traceback\nRuntimeError: x")}.items():
        mutated = copy.deepcopy(report)
        mutate(mutated)
        results[name] = verdict(mutated)[0]
    red = all(v not in ("S4_HOLDS", "S4_SUBSET_HOLDS") for v in results.values())
    print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": len(results),
                      "held": sorted(k for k, v in results.items() if v in ("S4_HOLDS", "S4_SUBSET_HOLDS")),
                      "results": results}, indent=1, ensure_ascii=False))
    return 0 if red else 1


def summary(run):
    if run["cell"] == "c":
        press = run.get("press") or {}
        return [press.get("pill"), repr(press.get("latency")), (press.get("toast") or "")[:30], run.get("bulletFallback")]
    row, press = press_row(run) or {}, run.get("press") or {}
    fb = (row.get("formatBarrier") or {}).get("fallback") or {}
    return [press.get("pill"), press.get("latency"), row.get("ok"), row.get("completion"),
            (row.get("formatBarrier") or {}).get("failureShape"),
            {k: fb.get(k) for k in ("ran", "blockCount", "lastListTag", "lastBlockTag", "refusal", "restoreConfirmed")},
            (press.get("toast") or "")[:30]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", type=Path, metavar="REPORT")
    parser.add_argument("--cells", default=",".join(CELLS))
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--arms", default="noclick,click")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--mutation", choices=sorted(MUTATIONS))
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test)
    if not args.out:
        parser.error("--out is required")
    cells = [c for c in args.cells.split(",") if c]
    unknown = sorted(set(cells) - set(CELLS))
    if unknown:
        parser.error(f"unknown cells {unknown}")
    raw = {}
    for name, (path, digest) in FIXTURES.items():
        raw[name] = path.read_bytes()
        if hashlib.sha256(raw[name]).hexdigest() != digest:
            raise SystemExit(f"fixture {name} changed")
    raw["blank"] = b1.BLANK.read_bytes()
    if hashlib.sha256(raw["blank"]).hexdigest() != b1.BLANK_SHA256:
        raise SystemExit("blank template changed")
    if args.mutation:
        cell, product, pressed = MUTATIONS[args.mutation]
        plan = [(product, [(cell, pressed or CELLS[cell][2])])]
    else:
        plan = [(product, [(c, CELLS[c][2]) for c in cells]) for product in ("before", "after")]
    config = {"products": [p for p, _ in plan], "cells": [c for c, _ in plan[0][1]],
              "browsers": [x for x in args.browsers.split(",") if x], "arms": [x for x in args.arms.split(",") if x],
              "repetitions": args.repetitions, "mutation": args.mutation}
    args.out.mkdir(parents=True, exist_ok=False)
    report = {"argv": sys.argv, "tool": "check_v82_last_line_bullet", "config": config, "marker": MARKER,
              "click": CLICK, "fixtures": {n: {"path": str(p.relative_to(REPO)), "sha256": d}
                                           for n, (p, d) in FIXTURES.items()},
              "blank": {"path": str(b1.BLANK), "sha256": b1.BLANK_SHA256}, "products": {}, "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="s4-last-line-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_v82_last_line_bullet"):
            report["preRun"] = common.pre_run_checks()
            if report["preRun"]["refuse"]:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            for name, work in plan:
                for family, observer in (("s3", s3.OBSERVER), ("b1", b1.OBSERVER)):
                    todo = [(c, a) for c, a in work if (c == "c") == (family == "b1")]
                    if not todo:
                        continue
                    mirror = scratch / f"{name}-{family}"
                    pp.build_mirror(common.DIST, mirror, products.overrides(name, [observer]))
                    ident = products.identity(name, mirror)
                    report["products"].setdefault(name, ident)
                    if not ident["ok"]:
                        report["products"][name] = ident
                        print(name, family, "identity FAILED, not run:", ident["checks"], file=sys.stderr, flush=True)
                        continue
                    with common.served(mirror) as base:
                        for cell, action in todo:
                            for browser in config["browsers"]:
                                for arm in (config["arms"] if cell == "c" else [None]):
                                    for n in range(1, args.repetitions + 1):
                                        run = {"cell": cell, "product": name, "browser": browser, "arm": arm,
                                               "repetition": n}
                                        session = None
                                        try:
                                            session = common.open_browser(browser)
                                            run["browserVersion"] = getattr(session, "version", None)
                                            if cell == "c":
                                                run.update(one_blank(session, browser, base, arm, raw["blank"]))
                                            else:
                                                run.update(one(session, browser, base, cell, raw[CELLS[cell][0]], action))
                                        except Exception:  # noqa: BLE001 -- recorded
                                            run["fatal"] = traceback.format_exc()
                                        finally:
                                            if session is not None:
                                                run["cleanup"] = common.close_browser(session)
                                        report["runs"].append(run)
                                        print(cell, name, browser, arm or "", n, *summary(run),
                                              (run.get("fatal") or "").strip().splitlines()[-1:] or "",
                                              file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["verdict"], report["problems"] = verdict(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report["problems"], file=sys.stderr)
    return 0 if report["verdict"] in ("S4_HOLDS", "S4_SUBSET_HOLDS", "S4_MUTATION_CAUGHT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
