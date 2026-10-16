#!/usr/bin/env python3
"""The judge of the v21 shakedown, item 1 (ARMS-item1.md, rulings §8; ARMS.md §2; spec §11.1, §12.2, §12.3).

Reads every `report-*.json` in a directory (what `run_v21_shakedown_item1.py` wrote) and the saved
documents beside them, and prints one verdict per criterion per browser: PASS, FAIL or NOT_ESTABLISHED,
with every failing line named.  Exit 0 only when every judged criterion PASSes on both browsers and none
is missing.  Records (D6, R-xlc, R-table) are printed, never judged; D6 is printed 「未量」 when no round of
it was measured (spec §12.3 (e): item 2 is not shipped, so the dialog D6 needs has no entry).  D2 (host),
D5's unit half, D12's unit half and D13 are not judged here (they are other tools' or other runs').

Spec §12.3 (2026-10-17, before any evidence run):
  * D11b dirty, (b): 22/23 take no checkpoint -- no `save` before Ctrl+End or Ctrl+Home, `dirty` stays
    true, `#s-checkpoint` reads 「無」.  Replaces ARMS-item1.md D11b's "exactly one checkpoint save".
  * D14, (c): dirty plain3 and long60, Ctrl+End, Q typed <= 30 ms after its keydown lands at the
    document end (the S-7 adapter's last body paragraph's end); N/N per fixture.
  * E0, (e): the item-2 entry is hidden at every arm's start state in every report (the 0.2.24 page of
    D8's red case is not the final shell and is not read).

Rules the judge enforces before reading a cell:
  * `--expect-page` is required; a report whose served v21 page differs is refused (the declared
    exceptions: the v20 page of D5-w and the 0.2.24 page of D8's red case, checked by profile instead);
  * a report flagged `smoke` is a development run: refused unless `--smoke-preview`, and then every
    verdict is printed as "SMOKE (not evidence)" and the exit code is 3;
  * one report per (browser, arm); a second one FAILS the cell (move superseded runs under witness/);
  * N rounds per arm per browser (`--rounds`, default 3): fewer done rounds is NOT_ESTABLISHED;
  * zero instances is NOT_ESTABLISHED, never PASS.

  judge_v21_shakedown_item1.py --dir DIR --expect-page SHA256 [--rounds 3]
  judge_v21_shakedown_item1.py --self-test
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fodt_to_odt  # noqa: E402
import v21_item1_marker as marker  # noqa: E402
import v21_item1_population as population  # noqa: E402

PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"
BROWSERS = ("chrome", "firefox")
PAGE_V21 = "3d5112161b23b060b2057a25bbbeb7cbc96628cde67e3e5c3c0dab92b435b5c5"
CRITERIA = ("D1", "D2p", "D4", "D5w", "D7", "D8", "D9", "D10", "D11a", "D11b", "D11c", "D12", "D14", "E0")
RECORDS = ("D6", "R-xlc", "R-table")
ARM_OF = {"D1": "d1", "D4": "d1", "D7": "d1", "D2p": "d2p", "D5w": "d5w", "D8": "d8", "D9": "d9", "D10": "d10",
          "D11a": "d11a", "D11b": "d11b", "D11c": "d11c", "D12": "d12", "D14": "d14"}   # E0 reads every arm
D14_FIXTURES = ("plain3", "long60")
D14_DIRTY, D14_MARKER = "Z", "Q"     # diag-dirty-move V1/V4's characters; neither occurs in either fixture
D14_WINDOW_MS = 30.0                 # spec §12.3 (c) 「30 ms 內」, read on the page's own keydown times
E0_NOT_FINAL_SHELL = ("dist0224",)   # D8's 0.2.24 red-case page
D6_NOT_RUNNABLE = "not runnable: item 2 not shipped (spec §12.3 (e))"
ASK7_WINDOW = (450.0, 550.0)
SILENT_LIMIT_MS = 500.0
D9_READY_MS = 500.0


def worst(verdicts: list[str]) -> str:
    if not verdicts:
        return NE
    if FAIL in verdicts:
        return FAIL
    if NE in verdicts:
        return NE
    return PASS


class Docs:
    """Saved documents: files beside the reports, or (self-test) bytes in memory."""

    def __init__(self, root: Path | None, memory: dict | None = None):
        self.root, self.memory = root, memory or {}

    def read(self, save: dict | None) -> bytes | None:
        if not save or not save.get("saved"):
            return None
        name = save.get("file")
        if name in self.memory:
            return self.memory[name]
        if self.root is None:
            return None
        path = self.root / name
        return path.read_bytes() if path.is_file() else None


# ------------------------------------------------------------------ D1, D4, D7

def judge_d1(result: dict, docs: Docs, rounds: int, native=marker.native_landing) -> tuple[str, list[str]]:
    lines = []
    pops = population.populations()
    names = [a["name"] for a in pops["d1"]]
    controls = {c["name"]: c["pairedWith"] for c in pops["controls"]}
    if result.get("population", {}).get("in") != names:
        return NE, ["the report's population is not d1_population's (refused)"]
    by_arm: dict[str, list] = {}
    for rec in result.get("rounds", []):
        by_arm.setdefault(rec.get("arm"), []).append(rec)
    verdicts = []
    landed: dict[str, list] = {}
    for name in names + list(controls):
        recs = by_arm.get(name, [])
        cell = []
        for rec in recs:
            if rec.get("outcome") != "done":
                cell.append(NE)
                lines.append(f"{name} r{rec.get('round')}: {rec.get('outcome')}: {str(rec.get('error'))[:120]}")
                continue
            raw = docs.read(rec.get("save"))
            if raw is None:
                cell.append(NE)
                lines.append(f"{name} r{rec.get('round')}: no saved document")
                continue
            try:
                got = marker.landing(raw)
            except marker.LandingError as error:
                cell.append(FAIL)
                lines.append(f"{name} r{rec.get('round')}: {error}")
                continue
            landed.setdefault(name, []).append(got)
            if name in controls:
                cell.append(PASS)
                continue
            want = native(name)
            if got != want:
                cell.append(FAIL)
                lines.append(f"{name} r{rec.get('round')}: landing {got} != native {want}")
            else:
                cell.append(PASS)
        if len([v for v in cell if v != NE]) < rounds and FAIL not in cell:
            cell.append(NE)
            if len(recs) < rounds:
                lines.append(f"{name}: {len(recs)} of {rounds} rounds")
        verdicts.append(worst(cell))
    for control, paired in controls.items():
        mine = {(p, i, o) for p, i, _, o in landed.get(control, [])}
        theirs = {(p, i, o) for p, i, _, o in landed.get(paired, [])}
        if not mine or not theirs:
            verdicts.append(NE)
            lines.append(f"control {control}: no landing to compare")
        elif mine & theirs:
            verdicts.append(NE)
            lines.append(f"control {control} lands where {paired} lands: the reader cannot tell them apart")
    return worst(verdicts), lines


def _presses_by_arm(result: dict) -> dict:
    out = {}
    for rec in result.get("rounds", []):
        if rec.get("role") == "D1":
            out.setdefault(rec["arm"], []).append(rec)
    return out


def judge_d4(result: dict, docs: Docs, rounds: int, native=marker.native_landing) -> tuple[str, list[str]]:
    lines = []
    pops = population.populations()
    if not pops["d4"]:
        return NE, ["zero range arms"]
    verdicts = []
    by_arm = _presses_by_arm(result)
    for name in pops["d4"]:
        cell = []
        for rec in by_arm.get(name, []):
            if rec.get("outcome") != "done" or not rec.get("presses"):
                cell.append(NE)
                lines.append(f"{name} r{rec.get('round')}: {rec.get('outcome')}")
                continue
            if not rec.get("rangeSelectionText"):
                cell.append(NE)
                lines.append(f"{name} r{rec.get('round')}: the selection before the key was not a range")
                continue
            press = rec["presses"][-1]
            response = press.get("response") or {}
            if not response.get("ok"):
                cell.append(FAIL)
                lines.append(f"{name} r{rec.get('round')}: the move was refused: {response.get('code')}")
                continue
            if not press.get("placeCaretBefore"):
                cell.append(FAIL)
                lines.append(f"{name} r{rec.get('round')}: no place-caret request before the move (moveFromPoint not taken)")
                continue
            raw = docs.read(rec.get("save"))
            try:
                got = marker.landing(raw) if raw else None
            except marker.LandingError as error:
                cell.append(FAIL)
                lines.append(f"{name} r{rec.get('round')}: {error}")
                continue
            if got is None:
                cell.append(NE)
            elif got != native(name):
                cell.append(FAIL)
                lines.append(f"{name} r{rec.get('round')}: landing {got} != native")
            else:
                cell.append(PASS)
                ops = sorted({p.get("op") for p in press["placeCaretBefore"]})
                if ops != ["editorPlaceCaretV2"]:
                    lines.append(f"{name} r{rec.get('round')}: DEVIATION-D4-op: the place-caret request was {ops}, "
                                 "the arm text names editorPlaceCaretV2 (on an open range the session's placeCaret "
                                 "takes v67's `click`, narrow-editor-v2-session.js:734-737); counted, for the main session")
        if len([v for v in cell if v != NE]) < rounds and FAIL not in cell:
            cell.append(NE)
        verdicts.append(worst(cell))
    return worst(verdicts), lines


def caret_equal(a, b) -> bool:
    return isinstance(a, dict) and isinstance(b, dict) and all(a.get(k) == b.get(k) for k in ("x", "y", "width", "height"))


def judge_press(cls: str, press: dict) -> tuple[str, str]:
    response = press.get("response") or {}
    ask = press.get("ask7") or {}
    if not response:
        return NE, "no response"
    if not response.get("ok"):
        return FAIL, f"refused: {response.get('code')}"
    completion = str(response.get("completion") or "")
    if cls == "cursor" and not completion.startswith("documented-callback-"):
        return FAIL, f"a native cursor press completed {completion}"
    if cls == "silent":
        if completion != "verified-move-readback":
            return FAIL, f"a native silent press completed {completion}"
        elapsed = (response.get("t") or 0) - (response.get("tRq") or 0)
        if not (0 < elapsed < SILENT_LIMIT_MS):
            return FAIL, f"a silent press answered after {elapsed:.1f} ms"
    if not ask or ask.get("tPosted") is None:
        return NE, "no +500 ms read"
    delta = ask["tPosted"] - response.get("t", 0)
    if not (ASK7_WINDOW[0] <= delta <= ASK7_WINDOW[1]):
        return NE, f"the read was posted {delta:.1f} ms after the reply (outside 500±50)"
    if not ask.get("ok"):
        return NE, f"the read was not answered: {ask.get('code')}"
    if not caret_equal(response.get("caret"), ask.get("caret")):
        return FAIL, f"reply caret {response.get('caret')} != read caret {ask.get('caret')}"
    return PASS, ""


def judge_d7(result: dict, rounds: int) -> tuple[str, list[str]]:
    lines = []
    pops = population.populations()
    if not pops["d7"]:
        return NE, ["zero presses"]
    by_arm = _presses_by_arm(result)
    verdicts = []
    for press in pops["d7"]:
        cell = []
        for rec in by_arm.get(press["arm"], []):
            if rec.get("outcome") != "done":
                cell.append(NE)
                continue
            if rec.get("foreign") and rec["foreign"].get("ok") is False:
                cell.append(NE)
                lines.append(f"{press['arm']} r{rec.get('round')}: foreign CPU over the limit: {rec['foreign'].get('overLimit')}")
                continue
            got = rec.get("presses") or []
            if len(got) <= press["press"]:
                cell.append(NE)
                lines.append(f"{press['arm']} r{rec.get('round')} press {press['press']}: missing")
                continue
            verdict, why = judge_press(press["class"], got[press["press"]])
            cell.append(verdict)
            if why:
                lines.append(f"{press['arm']} r{rec.get('round')} {press['label']} ({press['class']}): {why}")
        if len([v for v in cell if v != NE]) < rounds and FAIL not in cell:
            cell.append(NE)
        verdicts.append(worst(cell))
    return worst(verdicts), lines


# ------------------------------------------------------------------ D2', D8, D9, D10, D11, D12, D5-w

FIXTURE_SHAPES = {}


def fixture_read(name: str):
    if name not in FIXTURE_SHAPES:
        raw = (marker.FIXTURES / f"{name}.fodt").read_bytes()
        FIXTURE_SHAPES[name] = (marker.read_results.para_shapes(raw), [t for _, _, t in marker.read_marker.paragraphs(raw)])
    return FIXTURE_SHAPES[name]


def judge_d2p(result: dict, docs: Docs, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    shapes, texts = fixture_read("numbered-second")
    by_round: dict[int, dict] = {}
    for rec in result.get("rounds", []):
        by_round.setdefault(rec.get("round"), {})[rec.get("kind")] = rec
    for round_no, kinds in sorted(by_round.items()):
        b2b, witness, control = kinds.get("back-to-back"), kinds.get("witness"), kinds.get("control")
        if not all(r and r.get("outcome") == "done" for r in (b2b, witness, control)):
            verdicts.append(NE)
            lines.append(f"r{round_no}: a part did not run")
            continue
        try:
            if marker.landing(docs.read(witness.get("save")) or b"")[:2] != ("body", 1) or \
                    marker.landing(docs.read(witness.get("save")))[3] != 0:
                verdicts.append(NE)
                lines.append(f"r{round_no}: the placement witness is not at P2's start")
                continue
        except (marker.LandingError, TypeError) as error:
            verdicts.append(NE)
            lines.append(f"r{round_no}: placement witness unreadable: {error}")
            continue
        control_raw = docs.read(control.get("save"))
        if control_raw is None or marker.shapes_of(control_raw) == shapes:
            verdicts.append(NE)
            lines.append(f"r{round_no}: the Backspace-alone control did not change P2: the reading cannot tell")
            continue
        keys = [e for e in b2b.get("log", []) if e.get("k") == "kd"]
        move = (b2b.get("move") or {})
        backspace = next((e for e in keys if e.get("key") == "Backspace"), None)
        if not move or backspace is None or backspace.get("t", 1e18) >= move.get("t", 0):
            verdicts.append(NE)
            lines.append(f"r{round_no}: the Backspace keydown did not come before the move's reply")
            continue
        raw = docs.read(b2b.get("save"))
        if raw is None:
            verdicts.append(NE)
            continue
        got_shapes, got_texts = marker.shapes_of(raw), [t for _, _, t in marker.paragraphs_of(raw)]
        if got_shapes != shapes or got_texts != texts:
            verdicts.append(FAIL)
            lines.append(f"r{round_no}: P2 changed: {got_shapes} {got_texts}")
        else:
            verdicts.append(PASS)
        lines.append(f"r{round_no}: recorded: move {move.get('completion')}, Backspace {(b2b.get('delete') or {}).get('completion')}")
    if len([v for v in verdicts if v == PASS]) < rounds and FAIL not in verdicts:
        verdicts.append(NE)
    return worst(verdicts), lines


PLAIN3 = ["Alpha first paragraph", "Bravo second paragraph", "Charlie third paragraph"]
D8_EXPECT = {
    "a": (["Alpha first paragraph", "Bravo second paragraph", "Charlie third paragrap"],
          ["delete-backward", "move-document-end", "delete-backward"]),
    "b": (PLAIN3, None),
    "c": (["Alpha first paragraph", "Bravo second paragraph", "Charlie third paragra"], None),
    "d": (["Alpha first paragraph", "Brav second paragraph", "Charlie third paragraph"], None),
    "e": (["Alpha first paragraph", "Bra second paragraph", "Charlie third paragraph"],
          ["delete-backward", "delete-backward", "move-document-end", "delete-forward"]),
}


def _editor_requests(log: list[dict]) -> list[str]:
    return [e.get("action") for e in log if e.get("k") == "rq" and e.get("op") == "editorActionV2"]


def judge_d8_round(rec: dict, docs: Docs) -> tuple[str, str]:
    name = rec.get("sequence")
    if rec.get("outcome") != "done":
        return NE, f"{rec.get('outcome')}: {str(rec.get('error'))[:100]}"
    log = rec.get("log", [])
    responses = [e for e in log if e.get("k") == "rs" and e.get("op") == "editorActionV2"]
    first = responses[0] if responses else None
    if name in "abcd":
        if not first or first.get("completion") != "verified-boundary-noop":
            return NE, f"the first Backspace was not a boundary no-op: {first and first.get('completion')}"
        later = [e for e in log if e.get("k") == "kd"][1:]
        if any(e.get("t", 0) >= first.get("t", 0) for e in later):
            return NE, "a later key came after the first answer: the hold was not exercised"
    if name == "b" and len([e for e in log if e.get("k") == "bi"]) < 19:
        return NE, "fewer than 19 beforeinputs: the presses did not reach the page"
    if name == "d":
        click = next((e for e in log if e.get("k") == "rs" and e.get("op") in ("editorPlaceCaretV2", "click")), None)
        if not click or not caret_equal(click.get("caret"), rec.get("clickTarget")):
            return NE, f"placement-mismatch: the click landed at {click and click.get('caret')}, target {rec.get('clickTarget')}"
    raw = docs.read(rec.get("save"))
    if raw is None:
        return NE, "no saved document"
    texts = [t for _, _, t in marker.paragraphs_of(raw)]
    want_texts, want_requests = D8_EXPECT[name]
    if texts != want_texts:
        return FAIL, f"text {texts} != {want_texts}"
    requests = _editor_requests(log)
    if name == "b":
        deletes = [a for a in requests if str(a).startswith("delete")]
        if len(deletes) > 2:
            return FAIL, f"{len(deletes)} deletes reached the engine"
    if want_requests and requests != want_requests:
        return FAIL, f"requests {requests} != {want_requests}"
    return PASS, ""


def judge_d8(result: dict, red: dict | None, docs: Docs, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for name in "abcde":
        cell = []
        for rec in [r for r in result.get("rounds", []) if r.get("sequence") == name]:
            verdict, why = judge_d8_round(rec, docs)
            cell.append(verdict)
            if why:
                lines.append(f"({name}) r{rec.get('round')}: {why}")
        if len([v for v in cell if v != NE]) < rounds and FAIL not in cell:
            cell.append(NE)
        verdicts.append(worst(cell))
    # The 0.2.24 red case (ruling D-9 B): (d) must be RED on dist/'s page, or D8 lacks its red.
    red_rounds = [r for r in (red or {}).get("rounds", []) if r.get("sequence") == "d"]
    red_seen = [judge_d8_round(r, docs) for r in red_rounds]
    if not any(v == FAIL for v, _ in red_seen):
        verdicts.append(NE)
        lines.append(f"the 0.2.24 red case is missing or not red: {[v for v, _ in red_seen]}")
    else:
        lines.append(f"0.2.24 red case: {[(v, w[:60]) for v, w in red_seen]}")
    return worst(verdicts), lines


def judge_d9(result: dict, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for key in ("Ctrl+Home", "Ctrl+End"):
        for flagged in (True, False):
            cell = []
            for rec in [r for r in result.get("rounds", []) if r.get("key") == key and r.get("flagged") == flagged]:
                tag = f"{key} {'flagged' if flagged else 'unflagged'} r{rec.get('round')}"
                if rec.get("outcome") != "done":
                    cell.append(NE)
                    continue
                if rec.get("foreign") and rec["foreign"].get("ok") is False:
                    cell.append(NE)
                    lines.append(f"{tag}: foreign CPU over the limit")
                    continue
                log = rec.get("log", [])
                action = "move-document-start" if key.endswith("Home") else "move-document-end"
                downs = [e for e in log if e.get("k") == "kd" and e.get("ctrl")]
                if flagged and not any(e.get("repeat") for e in downs):
                    cell.append(NE)
                    lines.append(f"{tag}: no flagged repeat reached the page")
                    continue
                if not flagged and any(e.get("repeat") for e in downs):
                    cell.append(NE)
                    lines.append(f"{tag}: a repeat was flagged in the unflagged burst")
                    continue
                sent = [e for e in log if e.get("k") == "rq" and e.get("action") == action]
                answered = [e for e in log if e.get("k") == "rs" and e.get("action") == action]
                if not sent or not answered:
                    cell.append(NE)
                    lines.append(f"{tag}: no move was sent and answered")
                    continue
                overlap = False
                for request in sent:
                    open_before = [e for e in sent if e["s"] < request["s"]
                                   and not any(a["rq"] == e["rq"] and a["s"] < request["s"] for a in answered)]
                    if open_before:
                        overlap = True
                if overlap:
                    cell.append(FAIL)
                    lines.append(f"{tag}: a same-key move was sent while another was unanswered")
                    continue
                last_up = max((e["t"] for e in log if e.get("k") == "ku" and e.get("ctrl") is not None
                               and e.get("key") in ("Home", "End")), default=None)
                if last_up is None:
                    cell.append(NE)
                    continue
                last_answer = max(e["t"] for e in answered)
                states = [e for e in log if e.get("k") == "st"]
                ready_at = None
                for e in states:
                    if e["t"] >= max(last_up, last_answer) and e.get("state") == "ready" and str(e.get("pending")) == "0":
                        ready_at = e["t"]
                        break
                if ready_at is None:
                    tail = [e for e in states if e["t"] <= max(last_up, last_answer)]
                    if tail and tail[-1].get("state") == "ready" and str(tail[-1].get("pending")) == "0":
                        ready_at = max(last_up, last_answer)
                if ready_at is None:
                    cell.append(NE)
                    lines.append(f"{tag}: no ready state seen after the release")
                    continue
                after = max(0.0, ready_at - last_up)
                if after > D9_READY_MS:
                    cell.append(FAIL)
                    lines.append(f"{tag}: ready {after:.0f} ms after the release")
                else:
                    cell.append(PASS)
                    lines.append(f"{tag}: {len(sent)} move(s), ready {after:.0f} ms after the release")
            if len([v for v in cell if v != NE]) < rounds and FAIL not in cell:
                cell.append(NE)
            verdicts.append(worst(cell))
    return worst(verdicts), lines


def _region(geo: dict, doc_w: int, doc_h: int) -> dict | None:
    if not geo or not geo.get("paperHeight"):
        return None
    top = max(geo["deskTop"], geo["paperTop"]) - geo["paperTop"]
    bottom = min(geo["deskBottom"], geo["paperBottom"]) - geo["paperTop"]
    if bottom <= top:
        return None
    scale = doc_h / geo["paperHeight"]
    return {"y": top * scale, "height": (bottom - top) * scale}


def _last_page(text: str | None) -> tuple[int | None, int | None]:
    import re
    m = re.match(r"^第 (\d+)(?:–(\d+))? 頁，共 (\d+) 頁$", text or "")
    if not m:
        return None, None
    return int(m.group(2) or m.group(1)), int(m.group(3))


def judge_d10(result: dict, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for rec in result.get("rounds", []):
        tag = f"r{rec.get('round')}"
        if rec.get("outcome") != "done":
            verdicts.append(NE)
            continue
        if rec.get("foreign") and rec["foreign"].get("ok") is False:
            verdicts.append(NE)
            lines.append(f"{tag}: foreign CPU over the limit")
            continue
        rects = rec.get("rects") or {}
        raw = rects.get("raw") or ""
        pages = [list(map(int, p.replace(" ", "").split(","))) for p in raw.split(";") if p.strip()]
        if not pages or rects.get("parts") != len(pages):
            verdicts.append(NE)
            lines.append(f"{tag}: no rectangles or parts != rectangles")
            continue
        m_pages, doc_h, doc_w = len(pages), rects.get("docH"), rects.get("docW")
        press = rec.get("press") or {}
        verdict, why = judge_press("cursor", press)
        if verdict != PASS:
            verdicts.append(verdict)
            lines.append(f"{tag}: freshness/completion: {why}")
            continue
        last = pages[-1]
        reads = [("read 1", (press.get("response") or {}).get("caret"), (rec.get("read1") or {}).get("geo"),
                  (rec.get("read1") or {}).get("ps"), (rec.get("read1") or {}).get("psHidden")),
                 ("read 2", ((rec.get("read2") or {}).get("ask") or {}).get("caret"), (rec.get("read2") or {}).get("geometry"),
                  ((rec.get("read2") or {}).get("geometry") or {}).get("text"), ((rec.get("read2") or {}).get("geometry") or {}).get("hidden"))]
        ok = True
        for label, caret, geo, text, hidden in reads:
            region = _region(geo, doc_w, doc_h) if geo and doc_h else None
            if not caret or region is None:
                ok = False
                verdicts.append(NE)
                lines.append(f"{tag} {label}: no caret or geometry")
                break
            inside = region["y"] <= caret["y"] and caret["y"] + caret["height"] <= region["y"] + region["height"]
            page_last, total = _last_page(text)
            on_last = last[1] <= caret["y"] < last[1] + last[3]
            if hidden or not inside or page_last != m_pages or total != m_pages or not on_last:
                ok = False
                verdicts.append(FAIL)
                lines.append(f"{tag} {label}: caret {caret} region {region} status {text!r} hidden {hidden} on last page {on_last}")
                break
            lines.append(f"{tag} {label}: status {text!r}")
        if ok:
            verdicts.append(PASS)
    if len([v for v in verdicts if v != NE]) < rounds and FAIL not in verdicts:
        verdicts.append(NE)
    return worst(verdicts), lines


def judge_d11a(result: dict, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for rec in result.get("rounds", []):
        tag = f"r{rec.get('round')}"
        if rec.get("outcome") != "done":
            verdicts.append(NE)
            continue
        if "唯讀" not in (rec.get("doc") or "") or "insertText" in (rec.get("typedRequests") or []):
            verdicts.append(NE)
            lines.append(f"{tag}: the page is not view-only ({rec.get('doc')!r}, typed {rec.get('typedRequests')})")
            continue
        press = rec.get("press") or {}
        response = press.get("response") or {}
        host = rec.get("hostAfter") or {}
        unsaved = [u.get("value") for u in host.get("unsaved", [])]
        moved = response.get("ok") and not caret_equal((rec.get("start") or {}).get("caret"), (press.get("ask7") or {}).get("caret"))
        if "save" in (rec.get("requests") or []) or host.get("saves") or any(v is not False for v in unsaved) or not unsaved:
            verdicts.append(FAIL)
            lines.append(f"{tag}: save requests {rec.get('requests')}, host saves {host.get('saves')}, unsaved {unsaved}")
        elif not moved:
            verdicts.append(FAIL)
            lines.append(f"{tag}: the caret did not move: {response.get('completion')} {press.get('ask7')}")
        else:
            verdicts.append(PASS)
    if len([v for v in verdicts if v != NE]) < rounds and FAIL not in verdicts:
        verdicts.append(NE)
    return worst(verdicts), lines


def judge_d11b(result: dict, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for rec in result.get("rounds", []):
        tag = f"{rec.get('kind')} r{rec.get('round')}"
        if rec.get("outcome") != "done":
            verdicts.append(NE)
            continue
        ops = [r.get("op") for r in rec.get("requests", [])]
        presses = rec.get("presses", [])
        if len(presses) != 2 or not all((p.get("response") or {}).get("ok") for p in presses):
            verdicts.append(NE)
            lines.append(f"{tag}: the two moves did not both complete")
            continue
        if rec.get("kind") == "clean":
            if "save" in ops or any(p.get("unsavedAfter") != "false" for p in presses) or \
                    any(p.get("checkpoint") != "無" for p in presses):
                verdicts.append(FAIL)
                lines.append(f"{tag}: requests {ops}, unsaved {[p.get('unsavedAfter') for p in presses]}, checkpoint {[p.get('checkpoint') for p in presses]}")
            else:
                verdicts.append(PASS)
        else:
            # Spec §12.3 (b), replacing ARMS-item1.md D11b's "exactly one save before the first move":
            # 22/23 take no checkpoint, so no `save` before Ctrl+End or Ctrl+Home, `dirty` stays true and
            # `#s-checkpoint` stays 「無」.
            if rec.get("unsavedAfterTyping") != "true":
                verdicts.append(NE)
                lines.append(f"{tag}: dirty read false after typing: the read is blind")
                continue
            moves = [i for i, op in enumerate(ops) if op == "editorActionV2"]
            if len(moves) < 2:
                verdicts.append(NE)
                lines.append(f"{tag}: {len(moves)} move request(s) in the log: 'no save before a move' would be vacuous")
                continue
            saves = [i for i, op in enumerate(ops) if op == "save" and i < moves[1]]
            if saves:
                verdicts.append(FAIL)
                which = "Ctrl+End" if saves[0] < moves[0] else "Ctrl+Home"
                lines.append(f"{tag}: a checkpoint save before {which} (spec §12.3 (b)): requests {ops}")
            elif any(p.get("checkpoint") != "無" for p in presses):
                verdicts.append(FAIL)
                lines.append(f"{tag}: #s-checkpoint {[p.get('checkpoint') for p in presses]}, not 「無」")
            elif any(p.get("unsavedAfter") != "true" for p in presses):
                verdicts.append(FAIL)
                lines.append(f"{tag}: dirty lost after a move")
            else:
                verdicts.append(PASS)
    if len([v for v in verdicts if v != NE]) < 2 * rounds and FAIL not in verdicts:
        verdicts.append(NE)
    return worst(verdicts), lines


def judge_d11c(result: dict, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for rec in result.get("rounds", []):
        tag = f"r{rec.get('round')}"
        if rec.get("outcome") != "done":
            verdicts.append(NE)
            lines.append(f"{tag}: {rec.get('outcome')}")
            continue
        calls = {c["action"]: c for c in rec.get("calls", [])}
        doc_end, line_home, mutate = (calls.get(a) for a in ("move-document-end", "move-line-home", "insert-paragraph-break"))
        if not (doc_end and line_home and mutate):
            verdicts.append(NE)
            continue
        if ((mutate.get("sdk") or {}).get("error") or {}).get("code") != "STALE_REVISION":
            verdicts.append(NE)
            lines.append(f"{tag}: the mutating control was not STALE_REVISION: {mutate.get('sdk')}")
            continue
        engine = [(c.get("engine") or [None])[0] for c in (doc_end, line_home)]
        if any(e is None for e in engine):
            verdicts.append(NE)
            continue
        if any((e.get("code") == "STALE_REVISION") for e in engine):
            verdicts.append(FAIL)
            lines.append(f"{tag}: a move was refused as stale: {engine}")
            continue
        move_class = lambda c: str(c or "").startswith("documented-callback-") or c == "verified-move-readback"  # noqa: E731
        same_engine = [(e.get("ok"), move_class(e.get("completion")), e.get("rev")) for e in engine]
        sdk_codes = [((c.get("sdk") or {}).get("error") or {}).get("code") if not (c.get("sdk") or {}).get("ok") else "ok"
                     for c in (doc_end, line_home)]
        moved = not caret_equal((doc_end.get("before") or {}).get("caret"), (doc_end.get("after") or {}).get("caret"))
        if same_engine[0] != same_engine[1] or sdk_codes[0] != sdk_codes[1] or not engine[0].get("ok") or not moved:
            verdicts.append(FAIL)
            lines.append(f"{tag}: engine {same_engine}, SDK {sdk_codes}, moved {moved}")
        else:
            verdicts.append(PASS)
            lines.append(f"{tag}: observation (spec §12.2 (f)): the SDK reports {sdk_codes[0]} for both moves")
    if len([v for v in verdicts if v != NE]) < rounds and FAIL not in verdicts:
        verdicts.append(NE)
    return worst(verdicts), lines


def judge_d12(result: dict, docs: Docs, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for rec in result.get("rounds", []):
        tag = f"r{rec.get('round')}"
        if rec.get("outcome") != "done":
            verdicts.append(NE)
            lines.append(f"{tag}: {rec.get('outcome')}")
            continue
        control = rec.get("control") or {}
        if not (control.get("sdk") or {}).get("ok"):
            verdicts.append(NE)
            lines.append(f"{tag}: the collapsed control did not complete: {control.get('sdk')}")
            continue
        bad = False
        for block in rec.get("ranges", []):
            before = block.get("before") or {}
            if before.get("selectionType") != "text" or not before.get("selectionText"):
                verdicts.append(NE)
                lines.append(f"{tag} {block.get('range')}: no range before the call")
                bad = True
                break
            for call in block.get("calls", []):
                if call["action"] == "move-line-end":
                    continue
                sdk = call.get("sdk") or {}
                after = call.get("after") or {}
                if sdk.get("ok") or (sdk.get("error") or {}).get("code") != "EDITOR_FORMAT_GESTURE_UNSUPPORTED":
                    verdicts.append(FAIL)
                    lines.append(f"{tag} {block.get('range')} {call['action']}: {sdk}")
                    bad = True
                elif after.get("selectionText") != before.get("selectionText") or after.get("rev") != before.get("rev"):
                    verdicts.append(FAIL)
                    lines.append(f"{tag} {block.get('range')} {call['action']}: the selection or revision changed")
                    bad = True
        raw = docs.read(rec.get("save"))
        if not bad:
            if raw is None:
                verdicts.append(NE)
            elif [t for _, _, t in marker.paragraphs_of(raw)] != PLAIN3:
                verdicts.append(FAIL)
                lines.append(f"{tag}: the document changed")
            else:
                verdicts.append(PASS)
    if len([v for v in verdicts if v != NE]) < rounds and FAIL not in verdicts:
        verdicts.append(NE)
    return worst(verdicts), lines


def judge_d5w(result: dict, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for rec in result.get("rounds", []):
        tag = f"{rec.get('page')} r{rec.get('round')}"
        if rec.get("outcome") != "done":
            verdicts.append(NE)
            continue
        for chord in rec.get("chords", []):
            log = chord.get("log", [])
            kd = next((e for e in log if e.get("k") == "kd"), None)
            kdp = next((e for e in log if e.get("k") == "kdp" and kd and e.get("of") == kd.get("s")), None)
            moves = [e for e in log if e.get("k") == "rq" and str(e.get("action") or "").startswith("move-document-")]
            if kd is None or kdp is None or kd.get("focus") != "sink":
                verdicts.append(NE)
                lines.append(f"{tag} {chord['chord']}: the key did not reach the sink")
                continue
            shift = "shift" in chord["chord"]
            if rec.get("page") == "v20" or shift:
                if kdp.get("prevented") or moves:
                    verdicts.append(FAIL)
                    lines.append(f"{tag} {chord['chord']}: taken (prevented {kdp.get('prevented')}, moves {len(moves)})")
                else:
                    verdicts.append(PASS)
            else:
                if not kdp.get("prevented") or len(moves) != 1:
                    verdicts.append(NE)
                    lines.append(f"{tag} {chord['chord']}: the v21 positive control was not taken")
                else:
                    verdicts.append(PASS)
    if len([r for r in result.get("rounds", []) if r.get("outcome") == "done"]) < 2 * rounds and FAIL not in verdicts:
        verdicts.append(NE)
    return worst(verdicts), lines


# ------------------------------------------------------------------ records (printed, never judged)

def d14_class(raw: bytes) -> str:
    """Where D14's marker landed, read through the S-7 adapter (`marker.paragraphs_of`): the document end
    (the last body paragraph's end), the pre-move caret (right after the dirtying character at the
    start), or elsewhere.  The class words are the ones diag-dirty-move's `q_class` printed for V1/V4."""
    try:
        paras = marker.paragraphs_of(raw)
    except Exception as error:  # noqa: BLE001 -- the parser's own message is the payload
        return f"unreadable: {type(error).__name__}: {error}"
    body = [t for p, _, t in paras if p == "body"]
    hits = [(p, i, off) for p, i, t in paras for off, c in enumerate(t) if c == D14_MARKER]
    if len(hits) != 1:
        return f"{len(hits)} markers in the saved document"
    part, _, _ = hits[0]
    if part != "body":
        return f"elsewhere: in the {part} part"
    index, offset = next((i, off) for i, t in enumerate(body) for off, c in enumerate(t) if c == D14_MARKER)
    if index == len(body) - 1 and offset == len(body[-1]) - 1:
        return "document end"
    if index == 0 and body[0][:offset] == D14_DIRTY:
        return "pre-move caret"
    return f"elsewhere: body {index} offset {offset} {body[index][:40]!r}"


def _d14_recorded(log: list[dict], end_kd: dict | None) -> str:
    """Recorded, not judged (spec §12.3 (c) judges only the landing): the move's completion and time,
    and the request order."""
    move = next((e for e in log if e.get("k") == "rs" and e.get("action") == "move-document-end"), None)
    order = [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")]
    if move is None:
        return f"move: no reply; order {order}"
    round_trip = round(move["t"] - move["tRq"], 1) if "t" in move and "tRq" in move else None
    after_key = round(move["t"] - end_kd["t"], 1) if end_kd and "t" in move else None
    return (f"move {move.get('completion') or move.get('code')} round trip {round_trip} ms, reply {after_key} ms "
            f"after Ctrl+End's keydown; order {' > '.join(map(str, order))}")


def judge_d14_round(rec: dict, docs: Docs) -> tuple[str, str]:
    if rec.get("outcome") != "done":
        return NE, f"{rec.get('outcome')}: {str(rec.get('error'))[:100]}"
    typed = ((rec.get("typed") or {}).get("response") or {})
    if not typed.get("ok") or rec.get("unsavedAfterTyping") != "true":
        return NE, (f"the document was not dirty before the move (typed {typed.get('ok')}, "
                    f"unsaved {rec.get('unsavedAfterTyping')!r})")
    log = rec.get("log", [])
    end_kd = next((e for e in log if e.get("k") == "kd" and e.get("key") == "End" and e.get("ctrl")), None)
    mark_kd = next((e for e in log if e.get("k") == "kd" and e.get("key") == D14_MARKER), None)
    recorded = _d14_recorded(log, end_kd)
    if end_kd is None or mark_kd is None:
        return NE, f"no keydown for {'Ctrl+End' if end_kd is None else D14_MARKER} on the page; {recorded}"
    gap = round(mark_kd["t"] - end_kd["t"], 1)
    if not 0 < gap <= D14_WINDOW_MS:
        return NE, (f"{D14_MARKER} {gap} ms after Ctrl+End's keydown: the arm did not test the "
                    f"<= {D14_WINDOW_MS:g} ms window; {recorded}")
    raw = docs.read(rec.get("save"))
    if raw is None:
        return NE, f"no saved document; {recorded}"
    where = d14_class(raw)
    if where.startswith("unreadable"):
        return FAIL, f"{where}; {recorded}"
    texts = [t for _, _, t in marker.paragraphs_of(raw)]
    body0 = next((t for p, _, t in marker.paragraphs_of(raw) if p == "body"), "")
    if sum(t.count(D14_DIRTY) for t in texts) != 1 or not body0.startswith(D14_DIRTY):
        return NE, f"the dirtying {D14_DIRTY} is not (only) at the document start: {body0[:40]!r}; {recorded}"
    if where != "document end":
        return FAIL, f"{D14_MARKER} at the {where} ({gap} ms after Ctrl+End); {recorded}"
    return PASS, f"{D14_MARKER} at the document end, {gap} ms after Ctrl+End; {recorded}"


def judge_d14(result: dict, docs: Docs, rounds: int) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for fixture in D14_FIXTURES:
        cell = []
        for rec in [r for r in result.get("rounds", []) if r.get("fixture") == fixture]:
            verdict, why = judge_d14_round(rec, docs)
            cell.append(verdict)
            lines.append(f"{fixture} r{rec.get('round')}: {verdict}: {why}")
        established = len([v for v in cell if v != NE])
        if established < rounds and FAIL not in cell:
            cell.append(NE)
            lines.append(f"{fixture}: {established} of {rounds} round(s) established")
        verdicts.append(worst(cell))
    return worst(verdicts), lines


def judge_e0(reports: list[dict]) -> tuple[str, list[str]]:
    """Spec §12.3 (e): the item-2 entry is hidden at every arm's start state, in every report."""
    if not reports:
        return NE, ["no report"]
    lines, verdicts = [], []
    for report in reports:
        name = ",".join(report.get("arms") or sorted((report.get("results") or {}).keys()))
        reads, missing = [], 0
        for arm, result in (report.get("results") or {}).items():
            for rec in (result or {}).get("rounds", []) or []:
                start = rec.get("start") if isinstance(rec, dict) else None
                if not isinstance(start, dict):
                    continue
                entry = start.get("entry")
                if entry is None:
                    missing += rec.get("outcome") == "done"
                    continue
                if entry.get("variant") not in E0_NOT_FINAL_SHELL:
                    reads.append((f"{arm} r{rec.get('round')}", entry))
        if not reads:
            verdicts.append(NE)
            lines.append(f"[{name}]: no entry read on the final shell")
            continue
        shown = [(w, e) for w, e in reads if (e.get("exists") and e.get("hidden") is not True) or e.get("visibleOpeners")]
        blind = [w for w, e in reads if e.get("controlVisible") is not True]
        if shown:
            verdicts.append(FAIL)
            lines += [f"[{name}] {w}: entry exists {e.get('exists')} hidden {e.get('hidden')}, visible openers "
                      f"{e.get('visibleOpeners')}" for w, e in shown[:6]]
        elif blind or missing:
            verdicts.append(NE)
            lines.append(f"[{name}]: {len(blind)} read(s) where the control button reads not visible (the read is "
                         f"blind), {missing} done round(s) without the read")
        else:
            verdicts.append(PASS)
            variants = sorted({e.get("variant") for _, e in reads})
            exists = sorted({bool(e.get("exists")) for _, e in reads})
            lines.append(f"[{name}]: hidden in {len(reads)} read(s) on {variants}; the button exists {exists}")
    return worst(verdicts), lines


def d6_class(raw: bytes) -> str:
    """Where D6's marker landed: the document end (plain3's last paragraph end), the paste end (the
    start of the original first paragraph, after the pasted blocks), or elsewhere."""
    try:
        part, index, text, offset = marker.landing(raw)
    except marker.LandingError as error:
        return f"unreadable: {error}"
    paras = marker.paragraphs_of(raw)
    body = [t for p, _, t in paras if p == "body"]
    if text == "Charlie third paragraphZ" and index == len(body) - 1:
        return "document end"
    if text == "ZAlpha first paragraph":
        return "paste end"
    return f"elsewhere: body {index} offset {offset} {text[:40]!r}"


def _mm(shape: str) -> str:
    """A para_shapes row with its text-indent in millimetres (Writer re-exports 1cm as 0.3937in)."""
    import re
    m = re.search(r"text-indent (-?[\d.]+)(cm|mm|in|pt)$", shape)
    if not m:
        return shape
    factor = {"cm": 10.0, "mm": 1.0, "in": 25.4, "pt": 25.4 / 72}[m.group(2)]
    return shape[:m.start(1)] + f"{round(float(m.group(1)) * factor, 1)}mm"


def records(results: dict, docs: Docs) -> list[str]:
    lines = []
    for rec in (results.get("d6") or {}).get("rounds", []):
        raw = docs.read(rec.get("save"))
        log = rec.get("log", [])
        paste = next((e for e in log if e.get("k") == "rs" and e.get("op") == "pasteMarkdown"), None)
        move = next((e for e in log if e.get("k") == "rs" and e.get("action") == "move-document-end"), None)
        saves = [e for e in log if e.get("k") == "rq" and e.get("op") == "save"]
        lines.append(f"D6 r{rec.get('round')}: {rec.get('outcome')} paste {paste and (paste.get('ok'), paste.get('rev'))} "
                     f"checkpoint saves {len(saves)} move {move and move.get('completion')} "
                     f"marker {d6_class(raw) if raw else 'no document'} dialog closed after {rec.get('dialogClosedAfterMs')} ms")
    for name in ("xlc", "table"):
        for rec in (results.get(name) or {}).get("rounds", []):
            raw = docs.read(rec.get("save"))
            shapes = marker.shapes_of(raw) if raw else None
            delete = rec.get("delete") or {}
            fixture = rec.get("fixture")
            same = None
            if raw and fixture:
                base = fixture_read(fixture)
                same = ([_mm(x) for x in shapes] == [_mm(x) for x in base[0]]
                        and [t for _, _, t in marker.paragraphs_of(raw)] == base[1])
            lines.append(f"R-{name} {rec.get('arm')} r{rec.get('round')}: {rec.get('outcome')} Ctrl+Home "
                         f"{((rec.get('press') or {}).get('response') or {}).get('completion')} Backspace "
                         f"{delete.get('completion') or delete.get('code')} waited {delete.get('waitedMs')} "
                         f"gen {rec.get('generationAfter')} document as fixture: {same}")
    return lines


# ------------------------------------------------------------------ reports

def load(directory: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(directory.glob("report-*.json"))]


def judge_reports(reports: list[dict], docs: Docs, expect_page: str | None, rounds: int,
                  smoke_preview: bool = False) -> tuple[int, list[str]]:
    out = []
    if not expect_page:
        return 1, ["VERDICT NOT GIVEN: --expect-page is required"]
    smoke = [r for r in reports if r.get("smoke")]
    if smoke and not smoke_preview:
        return 2, [f"refused: {len(smoke)} report(s) are smokes (development runs), never judged as evidence"]
    cells: dict[tuple[str, str], list] = {}
    accepted = []
    for report in reports:
        browser = report.get("browser")
        pages = report.get("pages") or {}
        v21 = (pages.get("v21") or {}).get("pageServedSha256")
        if v21 is not None and v21 != expect_page:
            out.append(f"refused report ({browser}, {report.get('arms')}): served page {v21[:16]} is not {expect_page[:16]}")
            continue
        accepted.append(report)
        for variant, identity in pages.items():
            if variant == "v20" and identity.get("profile") != "e2-editor-v20":
                out.append(f"refused report ({browser}): the v20 page is not on e2-editor-v20")
        for arm, result in (report.get("results") or {}).items():
            cells.setdefault((browser, arm), []).append(result)
    verdicts: dict[tuple[str, str], tuple[str, list[str]]] = {}
    for browser in BROWSERS:
        def one(arm):
            got = cells.get((browser, arm), [])
            if len(got) > 1:
                return "DUPLICATE"
            return got[0] if got else None
        for criterion in CRITERIA:
            if criterion == "E0":
                verdicts[(criterion, browser)] = judge_e0([r for r in accepted if r.get("browser") == browser])
                continue
            result = one(ARM_OF[criterion])
            if result == "DUPLICATE":
                verdicts[(criterion, browser)] = (FAIL, ["two reports for one (browser, arm)"])
                continue
            if result is None or result.get("notRun") or result.get("runnerError"):
                why = (result or {}).get("notRun") or (result or {}).get("runnerError") or "missing"
                verdicts[(criterion, browser)] = (NE, [str(why)[:160]])
                continue
            if criterion == "D1":
                verdicts[(criterion, browser)] = judge_d1(result, docs, rounds)
            elif criterion == "D4":
                verdicts[(criterion, browser)] = judge_d4(result, docs, rounds)
            elif criterion == "D7":
                verdicts[(criterion, browser)] = judge_d7(result, rounds)
            elif criterion == "D2p":
                verdicts[(criterion, browser)] = judge_d2p(result, docs, rounds)
            elif criterion == "D8":
                red = one("d8red")
                verdicts[(criterion, browser)] = judge_d8(result, red if isinstance(red, dict) else None, docs, rounds)
            elif criterion == "D9":
                verdicts[(criterion, browser)] = judge_d9(result, rounds)
            elif criterion == "D10":
                verdicts[(criterion, browser)] = judge_d10(result, rounds)
            elif criterion == "D11a":
                verdicts[(criterion, browser)] = judge_d11a(result, rounds)
            elif criterion == "D11b":
                verdicts[(criterion, browser)] = judge_d11b(result, rounds)
            elif criterion == "D11c":
                verdicts[(criterion, browser)] = judge_d11c(result, rounds)
            elif criterion == "D12":
                verdicts[(criterion, browser)] = judge_d12(result, docs, rounds)
            elif criterion == "D5w":
                verdicts[(criterion, browser)] = judge_d5w(result, rounds)
            elif criterion == "D14":
                verdicts[(criterion, browser)] = judge_d14(result, docs, rounds)
    label = "SMOKE (not evidence) " if smoke else ""
    for report in reports:
        for line in records(report.get("results") or {}, docs):
            out.append(f"{label}record {report.get('browser')}: {line}")
    for browser in BROWSERS:
        # D6's pinned default for a record: 「未量，不做任何排序宣稱」.  Spec §12.3 (e): no entry, so no D6.
        d6 = cells.get((browser, "d6"), [])
        if not any(x.get("outcome") == "done" for r in d6 for x in r.get("rounds", [])):
            why = next((r.get("notRun") or r.get("runnerError") for r in d6 if r.get("notRun") or r.get("runnerError")),
                       None) or "no D6 report"
            out.append(f"{label}record {browser}: D6 未量 ({why}); default 「未量，不做任何排序宣稱」")
    failing = 0
    for criterion in CRITERIA:
        for browser in BROWSERS:
            verdict, lines = verdicts[(criterion, browser)]
            if verdict != PASS:
                failing += 1
            out.append(f"{label}{criterion:5s} {browser:8s} {verdict}")
            out += [f"    {line}" for line in lines[:40]]
    out.append(f"{label}VERDICT {'PASS' if failing == 0 else 'NOT PASS'} ({failing} criterion cell(s) not PASS)")
    return (3 if smoke else (0 if failing == 0 else 1)), out


# ------------------------------------------------------------------ self-test

def synthetic() -> tuple[list[dict], Docs]:
    """Reports that pass every judged clause, built from the native saved documents converted to ODT."""
    memory = {}

    def doc(name: str, raw: bytes) -> dict:
        memory[name] = raw
        return {"saved": True, "file": name}

    def odt_from_flat(raw: bytes) -> bytes:
        import gzip
        return fodt_to_odt.convert(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)

    pops = population.populations()
    caret = {"x": 1418, "y": 1418, "width": 0, "height": 276}
    reports = []
    for browser in BROWSERS:
        rounds = []
        for arm in pops["d1"]:
            presses = [p for p in pops["d7"] if p["arm"] == arm["name"]]
            press_recs = []
            for p in presses:
                completion = "documented-callback-visible-cursor" if p["class"] == "cursor" else "verified-move-readback"
                elapsed = 30.0 if p["class"] == "cursor" else 260.0
                press_recs.append({"response": {"ok": True, "completion": completion, "tRq": 1000.0, "t": 1000.0 + elapsed,
                                                "caret": caret, "rq": 7},
                                   "ask7": {"ok": True, "tPosted": 1000.0 + elapsed + 500.0, "caret": caret},
                                   "placeCaretBefore": [{"op": "editorPlaceCaretV2"}] if arm["name"] in pops["d4"] else []})
            raw = odt_from_flat(marker.native_saved(arm["name"], 1))
            rounds.append({"round": 1, "role": "D1", "arm": arm["name"], "outcome": "done", "presses": press_recs,
                           "rangeSelectionText": "second" if arm["name"] in pops["d4"] else None,
                           "foreign": {"ok": True},
                           "save": doc(f"{browser}-{arm['name']}.odt", raw)})
        for control in pops["controls"]:
            raw = odt_from_flat(marker.native_saved(control["name"], 1))
            rounds.append({"round": 1, "role": "control", "arm": control["name"], "outcome": "done",
                           "save": doc(f"{browser}-{control['name']}.odt", raw)})
        d1 = {"arm": "d1", "population": {"in": [a["name"] for a in pops["d1"]]}, "rounds": rounds}
        # D2'
        plain_num = (marker.FIXTURES / "numbered-second.fodt").read_bytes()
        witness = plain_num.replace(b"<text:p>Numbered second", b"<text:p>ZNumbered second", 1)
        control = plain_num.replace(b"<text:list-item><text:p>Numbered second</text:p></text:list-item>",
                                    b"<text:list-header><text:p>Numbered second</text:p></text:list-header>", 1)
        d2p = {"arm": "d2p", "rounds": [
            {"round": 1, "kind": "witness", "outcome": "done", "save": doc(f"{browser}-w.odt", odt_from_flat(witness))},
            {"round": 1, "kind": "control", "outcome": "done", "save": doc(f"{browser}-c.odt", odt_from_flat(control))},
            {"round": 1, "kind": "back-to-back", "outcome": "done", "move": {"t": 100.0, "completion": "documented-callback-visible-cursor"},
             "delete": {"completion": "verified-boundary-noop"},
             "log": [{"k": "kd", "key": "Home", "t": 10.0}, {"k": "kd", "key": "Backspace", "t": 12.0}],
             "save": doc(f"{browser}-b.odt", odt_from_flat(plain_num))}]}
        # D8
        plain3 = (marker.FIXTURES / "plain3.fodt").read_bytes()

        def edited(texts):
            raw = plain3
            for old, new in zip(PLAIN3, texts):
                raw = raw.replace(old.encode(), new.encode(), 1)
            return odt_from_flat(raw)

        def d8rec(name, variant_red=False):
            texts, requests = D8_EXPECT[name]
            log = [{"k": "kd", "key": "Backspace", "t": 1.0, "s": 1}, {"k": "kd", "key": "End", "t": 100.0, "s": 2}]
            log += [{"k": "rq", "op": "editorActionV2", "action": a, "s": 10 + i} for i, a in enumerate(requests or ["delete-backward"])]
            log.insert(0, {"k": "rs", "op": "editorActionV2", "action": "delete-backward", "completion": "verified-boundary-noop", "t": 2300.0, "s": 3})
            if name == "b":
                log += [{"k": "bi", "type": "deleteContentBackward"}] * 19
            rec = {"round": 1, "sequence": name, "outcome": "done", "log": log,
                   "save": doc(f"{browser}-d8{name}{'red' if variant_red else ''}.odt", edited(PLAIN3 if variant_red else texts))}
            if name == "d":
                rec["clickTarget"] = caret
                rec["log"].append({"k": "rs", "op": "editorPlaceCaretV2", "caret": caret, "s": 30})
            return rec
        d8 = {"arm": "d8", "rounds": [d8rec(n) for n in "abcde"]}
        d8red = {"arm": "d8red", "rounds": [d8rec("d", True)]}
        # D9
        d9_rounds = []
        for key in ("Ctrl+Home", "Ctrl+End"):
            action = "move-document-start" if key.endswith("Home") else "move-document-end"
            for flagged in (True, False):
                log = [{"k": "kd", "key": key[5:], "ctrl": True, "repeat": False, "t": 0.0, "s": 1},
                       {"k": "rq", "action": action, "rq": 1, "s": 2},
                       {"k": "rs", "action": action, "rq": 1, "t": 30.0, "s": 3},
                       {"k": "kd", "key": key[5:], "ctrl": True, "repeat": flagged, "t": 500.0, "s": 4},
                       {"k": "ku", "key": key[5:], "ctrl": True, "t": 1015.0, "s": 5},
                       {"k": "st", "state": "ready", "pending": "0", "t": 1020.0, "s": 6}]
                d9_rounds.append({"round": 1, "key": key, "flagged": flagged, "outcome": "done", "foreign": {"ok": True}, "log": log})
        d9 = {"arm": "d9", "rounds": d9_rounds}
        # D10
        pages = ";".join(f"284, {284 + i * 17122}, 11906, 16838" for i in range(60))
        last_caret = {"x": 2000, "y": 284 + 59 * 17122 + 6000, "width": 0, "height": 276}
        geo = {"deskTop": 100.0, "deskBottom": 800.0, "paperTop": 100.0 - 60000.0, "paperBottom": 100.0 - 60000.0 + 61000.0,
               "paperHeight": 61000.0}
        # map: doc_h 1027604 over 61000 px; region top = 60000 px * scale
        scale = 1027604 / 61000.0
        region_mid = (60000 + 350) * scale
        last_caret["y"] = int(region_mid)
        d10 = {"arm": "d10", "rounds": [{"round": 1, "outcome": "done", "foreign": {"ok": True},
                                         "rects": {"parts": 60, "raw": pages, "docH": 1027604, "docW": 12474},
                                         "press": {"response": {"ok": True, "completion": "documented-callback-visible-cursor",
                                                                "t": 10.0, "tRq": 0.0, "caret": last_caret},
                                                   "ask7": {"ok": True, "tPosted": 510.0, "caret": last_caret}},
                                         "read1": {"geo": geo, "ps": "第 60 頁，共 60 頁", "psHidden": False},
                                         "read2": {"ask": {"caret": last_caret},
                                                   "geometry": {**geo, "text": "第 60 頁，共 60 頁", "hidden": False}}}]}
        # D11
        d11a = {"arm": "d11a", "rounds": [{"round": 1, "outcome": "done", "doc": "plain3.odt（唯讀：只能檢視）", "typedRequests": [],
                                           "start": {"caret": caret},
                                           "press": {"response": {"ok": True}, "ask7": {"caret": last_caret}},
                                           "hostAfter": {"saves": 0, "unsaved": [{"value": False}, {"value": False}]},
                                           "requests": ["editorActionV2", "editorGetStateV2"]}]}
        d11b = {"arm": "d11b", "rounds": [
            {"round": 1, "kind": "clean", "outcome": "done", "requests": [{"op": "editorActionV2"}, {"op": "editorActionV2"}],
             "presses": [{"response": {"ok": True}, "unsavedAfter": "false", "checkpoint": "無"}] * 2},
            # Spec §12.3 (b): in a dirty document 22/23 take no checkpoint (no save, dirty stays, 「無」).
            {"round": 1, "kind": "dirty", "outcome": "done", "unsavedAfterTyping": "true",
             "requests": [{"op": "insertText"}, {"op": "editorActionV2"}, {"op": "editorActionV2"}],
             "presses": [{"response": {"ok": True}, "unsavedAfter": "true", "checkpoint": "無"}] * 2}]}
        engine_move = {"ok": True, "completion": "documented-callback-visible-cursor", "rev": 1}
        d11c = {"arm": "d11c", "rounds": [{"round": 1, "outcome": "done", "calls": [
            {"action": "move-document-end", "sdk": {"ok": False, "error": {"code": "EDITOR_RESULT_INVALID"}},
             "engine": [engine_move], "before": {"caret": caret}, "after": {"caret": last_caret}},
            {"action": "move-line-home", "sdk": {"ok": False, "error": {"code": "EDITOR_RESULT_INVALID"}},
             "engine": [engine_move], "before": {"caret": last_caret}, "after": {"caret": caret}},
            {"action": "insert-paragraph-break", "sdk": {"ok": False, "error": {"code": "STALE_REVISION"}}, "engine": []}]}]}
        refusal = {"ok": False, "error": {"code": "EDITOR_FORMAT_GESTURE_UNSUPPORTED"}}
        range_state = {"selectionType": "text", "selectionText": "second", "rev": 0}
        d12 = {"arm": "d12", "rounds": [{"round": 1, "outcome": "done", "control": {"sdk": {"ok": True}},
                                         "ranges": [{"range": "single", "before": range_state, "calls": [
                                             {"action": "move-document-start", "sdk": refusal, "after": range_state},
                                             {"action": "move-document-end", "sdk": refusal, "after": range_state},
                                             {"action": "move-line-end", "sdk": refusal, "after": range_state}]}],
                                         "save": doc(f"{browser}-d12.odt", odt_from_flat(plain3))}]}

        def chord_log(prevented, moves):
            log = [{"k": "kd", "s": 1, "focus": "sink"}, {"k": "kdp", "of": 1, "prevented": prevented}]
            return log + [{"k": "rq", "action": "move-document-start"}] * moves
        d5w = {"arm": "d5w", "rounds": [
            {"round": 1, "page": "v20", "outcome": "done",
             "chords": [{"chord": c, "log": chord_log(False, 0)} for c in ("ctrl+Home", "ctrl+End", "meta+Home", "meta+End", "ctrl+shift+Home")]},
            {"round": 1, "page": "v21", "outcome": "done",
             "chords": [{"chord": c, "log": chord_log(True, 1)} for c in ("ctrl+Home", "ctrl+End", "meta+Home", "meta+End")]
             + [{"chord": "ctrl+shift+Home", "log": chord_log(False, 0)}]}]}
        # D14 (spec §12.3 (c)): Z at the start, Ctrl+End, Q 21 ms after its keydown, Q at the document end.
        d14 = {"arm": "d14", "rounds": [
            {"round": 1, "fixture": fixture, "outcome": "done", "typed": {"response": {"op": "insertText", "ok": True}},
             "unsavedAfterTyping": "true", "log": d14_log(),
             "save": doc(f"{browser}-d14-{fixture}.odt",
                         _plain3_odt(D14_PLAIN3_END) if fixture == "plain3" else _long60_odt("Z", "Q"))}
            for fixture in D14_FIXTURES]}
        results = {"d1": d1, "d2p": d2p, "d8": d8, "d8red": d8red, "d9": d9, "d10": d10, "d11a": d11a,
                   "d11b": d11b, "d11c": d11c, "d12": d12, "d5w": d5w, "d14": d14}
        if browser == "chrome":   # D6 skipped by the runner in one browser, absent in the other: 未量 both ways
            results["d6"] = {"arm": "d6", "rounds": [], "notRun": D6_NOT_RUNNABLE}
        # E0 (spec §12.3 (e)): every arm's start state carries the entry read, as the runner's start_state does.
        for arm, result in results.items():
            for rec in result.get("rounds", []):
                variant = {"d8red": "dist0224", "d11a": "v21host", "d11c": "v21hook", "d12": "v21hook"}.get(arm, "v21")
                variant = rec.get("page", variant) if arm == "d5w" else variant
                rec.setdefault("start", {})["entry"] = dict(ENTRY_HIDDEN, variant=variant)
        reports.append({"browser": browser, "smoke": False,
                        "pages": {"v21": {"pageServedSha256": PAGE_V21, "profile": "e2-editor-v21"},
                                  "v20": {"profile": "e2-editor-v20"}},
                        "results": results})
    return reports, Docs(None, memory)


# The synthetic pieces D14 and E0 need (module level: the red cases rebuild documents with them).
D14_PLAIN3_END = ["ZAlpha first paragraph", "Bravo second paragraph", "Charlie third paragraphQ"]
D14_PLAIN3_PRE_MOVE = ["ZQAlpha first paragraph", "Bravo second paragraph", "Charlie third paragraph"]
ENTRY_HIDDEN = {"exists": True, "hidden": True, "hiddenAttr": True, "visibleOpeners": [], "candidates": 1,
                "controlVisible": True, "dialogExists": True, "dialogOpen": False}


def _plain3_odt(texts: list[str]) -> bytes:
    raw = (marker.FIXTURES / "plain3.fodt").read_bytes()
    for old, new in zip(PLAIN3, texts):
        raw = raw.replace(old.encode(), new.encode(), 1)
    return fodt_to_odt.convert(raw)


def _long60_odt(start: str, end: str) -> bytes:
    """The runner's long60 (create_long_document.build(60)) with `start` before its first paragraph's text
    and `end` after its last paragraph's text."""
    from create_long_document import build

    def change(members):
        content = members["content.xml"].replace(b">LD-PAGE-01<", b">" + start.encode() + b"LD-PAGE-01<", 1)
        head, sep, tail = content.rpartition(b"</text:p>")
        members["content.xml"] = head + end.encode() + sep + tail
    return marker._rezip(build(60), change)


def d14_log(gap_ms: float = 21.0) -> list[dict]:
    """A D14 round's observer log: Ctrl+End's keydown, the move, Q's keydown `gap_ms` later, the insert."""
    return [{"k": "kd", "key": "Control", "ctrl": True, "t": 1000.0, "s": 1},
            {"k": "kd", "key": "End", "ctrl": True, "t": 1000.4, "s": 2},
            {"k": "rq", "op": "editorActionV2", "action": "move-document-end", "rq": 9, "s": 3},
            {"k": "kd", "key": "Q", "ctrl": False, "t": 1000.4 + gap_ms, "s": 4},
            {"k": "rs", "op": "editorActionV2", "action": "move-document-end", "rq": 9, "ok": True,
             "completion": "documented-callback-visible-cursor", "tRq": 1001.0, "t": 1041.0, "s": 5},
            {"k": "rq", "op": "insertText", "rq": 10, "s": 6},
            {"k": "rs", "op": "insertText", "rq": 10, "ok": True, "t": 1060.0, "s": 7}]


def _rezip(odt: bytes, change) -> bytes:
    return marker._rezip(odt, change)


def mutations(docs: Docs) -> list[tuple[str, str, str, object]]:
    """(name, criterion, expected verdict, mutate(reports))"""
    def d1_rec(reports, arm):
        return next(r for r in reports[0]["results"]["d1"]["rounds"] if r["arm"] == arm)

    def set_doc(reports, arm, change):
        rec = d1_rec(reports, arm)
        docs.memory[rec["save"]["file"]] = _rezip(docs.memory[rec["save"]["file"]], change)

    def m_shift(r):
        set_doc(r, "a1-home-mid", lambda m: m.__setitem__("content.xml", m["content.xml"].replace(b"ZAlpha", b"AZlpha", 1)))

    def m_dup(r):
        set_doc(r, "a1-home-mid", lambda m: m.__setitem__("content.xml", m["content.xml"].replace(b"Bravo", b"BZravo", 1)))

    def m_noxml(r):
        set_doc(r, "a1-home-mid", lambda m: m.pop("content.xml"))

    def m_paragraph(r):
        set_doc(r, "a2-end-mid", lambda m: m.__setitem__("content.xml", m["content.xml"].replace(b"Charlie third paragraphZ", b"Charlie third paragraph", 1)
                                                         .replace(b"Bravo second paragraph", b"Bravo second paragraphZ", 1)))

    def m_missing_arm(r):
        r[0]["results"]["d1"]["rounds"] = [x for x in r[0]["results"]["d1"]["rounds"] if x["arm"] != "a1-home-mid"]

    def m_population(r):
        r[0]["results"]["d1"]["population"]["in"] = r[0]["results"]["d1"]["population"]["in"][:-1]

    def m_control_same(r):
        ctrl = d1_rec(r, "ctl-noctrl-a1-home-mid")
        ctrl["save"] = dict(d1_rec(r, "a1-home-mid")["save"])

    def m_zero(r):
        r[0]["results"]["d1"]["rounds"] = []

    def m_d4_noplace(r):
        d1_rec(r, "r-one-home")["presses"][-1]["placeCaretBefore"] = []

    def m_d4_refused(r):
        d1_rec(r, "r-cross-end")["presses"][-1]["response"] = {"ok": False, "code": "EDITOR_FORMAT_GESTURE_UNSUPPORTED"}

    def m_d4_norange(r):
        d1_rec(r, "r-bwd-home")["rangeSelectionText"] = ""

    def m_d7_cursor_readback(r):
        d1_rec(r, "a1-home-mid")["presses"][0]["response"]["completion"] = "verified-move-readback"

    def m_d7_silent_callback(r):
        d1_rec(r, "a3-home-at-start")["presses"][0]["response"]["completion"] = "documented-callback-visible-cursor"

    def m_d7_slow(r):
        p = d1_rec(r, "a3-home-at-start")["presses"][0]
        p["response"]["t"] = p["response"]["tRq"] + 520.0
        p["ask7"]["tPosted"] = p["response"]["t"] + 500.0

    def m_d7_caret(r):
        d1_rec(r, "a2-end-mid")["presses"][0]["ask7"]["caret"] = {"x": 1418, "y": 1419, "width": 0, "height": 276}

    def m_d7_late(r):
        p = d1_rec(r, "a2-end-mid")["presses"][0]
        p["ask7"]["tPosted"] = p["response"]["t"] + 600.0

    def m_d7_missing(r):
        d1_rec(r, "t-home-A1-n3")["presses"] = d1_rec(r, "t-home-A1-n3")["presses"][:2]

    def m_d7_foreign(r):
        d1_rec(r, "a2-end-mid")["foreign"] = {"ok": False, "overLimit": [{"pid": 1, "pct": 99}]}

    def b2b(r):
        return next(x for x in r[0]["results"]["d2p"]["rounds"] if x["kind"] == "back-to-back")

    def m_d2p_header(r):
        raw = (marker.FIXTURES / "numbered-second.fodt").read_bytes().replace(
            b"<text:list-item><text:p>Numbered second</text:p></text:list-item>",
            b"<text:list-header><text:p>Numbered second</text:p></text:list-header>", 1)
        docs.memory[b2b(r)["save"]["file"]] = fodt_to_odt.convert(raw)

    def m_d2p_merged(r):
        raw = (marker.FIXTURES / "numbered-second.fodt").read_bytes().replace(
            b"<text:p>Plain first</text:p>\n<text:list text:style-name=\"LN\"><text:list-item><text:p>Numbered second</text:p></text:list-item></text:list>",
            b"<text:p>Plain firstNumbered second</text:p>", 1)
        docs.memory[b2b(r)["save"]["file"]] = fodt_to_odt.convert(raw)

    def m_d2p_late(r):
        b2b(r)["log"][1]["t"] = 200.0

    def m_d2p_control(r):
        c = next(x for x in r[0]["results"]["d2p"]["rounds"] if x["kind"] == "control")
        docs.memory[c["save"]["file"]] = fodt_to_odt.convert((marker.FIXTURES / "numbered-second.fodt").read_bytes())

    def d8r(r, n):
        return next(x for x in r[0]["results"]["d8"]["rounds"] if x["sequence"] == n)

    def m_d8a_unchanged(r):
        docs.memory[d8r(r, "a")["save"]["file"]] = fodt_to_odt.convert((marker.FIXTURES / "plain3.fodt").read_bytes())

    def m_d8b_three(r):
        d8r(r, "b")["log"] += [{"k": "rq", "op": "editorActionV2", "action": "delete-backward"}] * 3

    def m_d8d_start(r):
        docs.memory[d8r(r, "d")["save"]["file"]] = fodt_to_odt.convert(
            (marker.FIXTURES / "plain3.fodt").read_bytes().replace(b"Alpha first", b"lpha first", 1))

    def m_d8e_realdelete(r):
        d8r(r, "e")["log"] = [e for e in d8r(r, "e")["log"] if e.get("action") != "delete-forward"] + \
            [{"k": "rq", "op": "editorActionV2", "action": "delete-backward"}]

    def m_d8_notnoop(r):
        d8r(r, "a")["log"][0]["completion"] = "verified-selection-delete"

    def m_d8_late(r):
        d8r(r, "a")["log"][2]["t"] = 3000.0

    def m_d8_nored(r):
        r[0]["results"]["d8red"]["rounds"] = []

    def d9r(r, flagged):
        return next(x for x in r[0]["results"]["d9"]["rounds"] if x["flagged"] == flagged and x["key"] == "Ctrl+End")

    def m_d9_slow(r):
        d9r(r, True)["log"][-1]["t"] = 1615.0

    def m_d9_overlap(r):
        log = d9r(r, False)["log"]
        log.insert(2, {"k": "rq", "action": "move-document-end", "rq": 2, "s": 2.5})
        log.append({"k": "rs", "action": "move-document-end", "rq": 2, "t": 40.0, "s": 7})

    def m_d9_noflag(r):
        for e in d9r(r, True)["log"]:
            if e.get("k") == "kd":
                e["repeat"] = False

    def m_d9_nomove(r):
        d9r(r, False)["log"] = [e for e in d9r(r, False)["log"] if e.get("k") not in ("rq", "rs")]

    def d10r(r):
        return r[0]["results"]["d10"]["rounds"][0]

    def m_d10_below(r):
        d10r(r)["press"]["response"]["caret"] = dict(d10r(r)["press"]["response"]["caret"], y=d10r(r)["press"]["response"]["caret"]["y"] + 20000)
        d10r(r)["press"]["ask7"]["caret"] = d10r(r)["press"]["response"]["caret"]

    def m_d10_59(r):
        d10r(r)["read2"]["geometry"]["text"] = "第 59 頁，共 60 頁"

    def m_d10_hidden(r):
        d10r(r)["read1"]["psHidden"] = True

    def m_d10_fresh(r):
        d10r(r)["press"]["ask7"]["caret"] = {"x": 1, "y": 2, "width": 0, "height": 3}

    def m_d10_norects(r):
        d10r(r)["rects"] = {}

    def m_d11a_save(r):
        r[0]["results"]["d11a"]["rounds"][0]["requests"].append("save")

    def m_d11a_still(r):
        r[0]["results"]["d11a"]["rounds"][0]["press"]["ask7"]["caret"] = r[0]["results"]["d11a"]["rounds"][0]["start"]["caret"]

    def m_d11a_notview(r):
        r[0]["results"]["d11a"]["rounds"][0]["doc"] = "plain3.odt"

    def m_d11b_clean_save(r):
        r[0]["results"]["d11b"]["rounds"][0]["requests"].insert(0, {"op": "save"})

    def dirty(r):
        return r[0]["results"]["d11b"]["rounds"][1]

    def m_d11b_dirty_save_before_end(r):     # the withdrawn checkpoint (spec §12.3 (b)), before Ctrl+End
        dirty(r)["requests"].insert(1, {"op": "save"})

    def m_d11b_dirty_save_before_home(r):    # ... or before Ctrl+Home
        dirty(r)["requests"].insert(2, {"op": "save"})

    def m_d11b_dirty_checkpoint_shown(r):
        dirty(r)["presses"] = [dict(p, checkpoint="有（r1）") for p in dirty(r)["presses"]]

    def m_d11b_dirty_lost(r):
        dirty(r)["presses"] = [dirty(r)["presses"][0], dict(dirty(r)["presses"][1], unsavedAfter="false")]

    def m_d11b_dirty_no_moves(r):
        dirty(r)["requests"] = [q for q in dirty(r)["requests"] if q["op"] != "editorActionV2"]

    def d14r(r, fixture):
        return next(x for x in r[0]["results"]["d14"]["rounds"] if x["fixture"] == fixture)

    def m_d14_pre_move(r):
        docs.memory[d14r(r, "plain3")["save"]["file"]] = _plain3_odt(D14_PLAIN3_PRE_MOVE)

    def m_d14_pre_move_long(r):
        docs.memory[d14r(r, "long60")["save"]["file"]] = _long60_odt("ZQ", "")

    def m_d14_nosave(r):
        d14r(r, "plain3")["save"] = {"saved": False}

    def m_d14_zero(r):
        r[0]["results"]["d14"]["rounds"] = []

    def m_d14_fixture_missing(r):
        r[0]["results"]["d14"]["rounds"] = [x for x in r[0]["results"]["d14"]["rounds"] if x["fixture"] != "long60"]

    def m_d14_late(r):
        d14r(r, "plain3")["log"] = d14_log(30.5)

    def m_d14_before(r):
        d14r(r, "long60")["log"] = d14_log(-2.0)

    def m_d14_clean(r):
        d14r(r, "plain3")["unsavedAfterTyping"] = "false"

    def m_d14_unreadable(r):
        f = d14r(r, "plain3")["save"]["file"]
        docs.memory[f] = _rezip(docs.memory[f], lambda m: m.pop("content.xml"))

    def m_d14_no_dirty_char(r):
        docs.memory[d14r(r, "plain3")["save"]["file"]] = _plain3_odt(["Alpha first paragraph", "Bravo second paragraph",
                                                                       "Charlie third paragraphQ"])

    def m_d14_no_keydown(r):
        d14r(r, "long60")["log"] = [e for e in d14r(r, "long60")["log"] if e.get("k") != "kd"]

    def entries(r, arm):
        return [x["start"]["entry"] for x in r[0]["results"][arm]["rounds"]]

    def m_e0_visible(r):
        entries(r, "d10")[0].update(hidden=False, hiddenAttr=False,
                                    visibleOpeners=[{"tag": "button", "action": "paste-markdown", "text": "貼上為 Markdown…"}])

    def m_e0_other_opener(r):
        entries(r, "d11b")[1]["visibleOpeners"] = [{"tag": "button", "id": "md", "action": None, "text": "Markdown"}]

    def m_e0_no_read(r):
        for result in r[0]["results"].values():
            for x in result.get("rounds", []):
                x.get("start", {}).pop("entry", None)

    def m_e0_blind(r):
        entries(r, "d9")[0]["controlVisible"] = False

    def m_d11b_blind(r):
        r[0]["results"]["d11b"]["rounds"][1]["unsavedAfterTyping"] = "false"

    def m_d11c_stale(r):
        r[0]["results"]["d11c"]["rounds"][0]["calls"][0]["engine"] = [{"ok": False, "code": "STALE_REVISION"}]

    def m_d11c_differ(r):
        r[0]["results"]["d11c"]["rounds"][0]["calls"][1]["sdk"] = {"ok": True}

    def m_d11c_control(r):
        r[0]["results"]["d11c"]["rounds"][0]["calls"][2]["sdk"] = {"ok": True}

    def m_d12_completes(r):
        r[0]["results"]["d12"]["rounds"][0]["ranges"][0]["calls"][0]["sdk"] = {"ok": True}

    def m_d12_selection(r):
        r[0]["results"]["d12"]["rounds"][0]["ranges"][0]["calls"][1]["after"] = {"selectionType": "none", "selectionText": "", "rev": 0}

    def m_d12_collapsed(r):
        r[0]["results"]["d12"]["rounds"][0]["ranges"][0]["before"] = {"selectionType": "none", "selectionText": "", "rev": 0}

    def m_d12_control(r):
        r[0]["results"]["d12"]["rounds"][0]["control"]["sdk"] = {"ok": False}

    def m_d5w_taken(r):
        r[0]["results"]["d5w"]["rounds"][0]["chords"][0]["log"][1]["prevented"] = True

    def m_d5w_shift(r):
        r[0]["results"]["d5w"]["rounds"][1]["chords"][-1]["log"][1]["prevented"] = True

    def m_d5w_control(r):
        r[0]["results"]["d5w"]["rounds"][1]["chords"][0]["log"][1]["prevented"] = False

    def m_d5w_nokeys(r):
        r[0]["results"]["d5w"]["rounds"][0]["chords"][0]["log"] = []

    return [
        ("D1 marker shift", "D1", FAIL, m_shift), ("D1 duplicate marker", "D1", FAIL, m_dup),
        ("D1 missing XML", "D1", FAIL, m_noxml), ("D1 landing one paragraph off", "D1", FAIL, m_paragraph),
        ("D1 an arm missing", "D1", NE, m_missing_arm), ("D1 population not the tool's", "D1", NE, m_population),
        ("D1 control lands with its arm", "D1", NE, m_control_same), ("D1 zero instances", "D1", NE, m_zero),
        ("D4 no place-caret before the move", "D4", FAIL, m_d4_noplace), ("D4 the move refused", "D4", FAIL, m_d4_refused),
        ("D4 no range before the key", "D4", NE, m_d4_norange),
        ("D7 cursor press answered by readback", "D7", FAIL, m_d7_cursor_readback),
        ("D7 silent press answered by callback", "D7", FAIL, m_d7_silent_callback),
        ("D7 silent press at 520 ms", "D7", FAIL, m_d7_slow), ("D7 reply caret != read caret", "D7", FAIL, m_d7_caret),
        ("D7 read at +600 ms", "D7", NE, m_d7_late), ("D7 a press missing", "D7", NE, m_d7_missing),
        ("D7 foreign CPU over the limit", "D7", NE, m_d7_foreign), ("D7 zero presses (D1 empty)", "D7", NE, m_zero),
        ("D2' P2 list-header", "D2p", FAIL, m_d2p_header), ("D2' P1 and P2 merged", "D2p", FAIL, m_d2p_merged),
        ("D2' Backspace after the move's reply", "D2p", NE, m_d2p_late), ("D2' control unchanged", "D2p", NE, m_d2p_control),
        ("D8 (a) text unchanged", "D8", FAIL, m_d8a_unchanged), ("D8 (b) 3 deletes", "D8", FAIL, m_d8b_three),
        ("D8 (d) deleted at the start", "D8", FAIL, m_d8d_start), ("D8 (e) Delete as a real delete", "D8", FAIL, m_d8e_realdelete),
        ("D8 first Backspace not a no-op", "D8", NE, m_d8_notnoop), ("D8 key after the first answer", "D8", NE, m_d8_late),
        ("D8 0.2.24 red case missing", "D8", NE, m_d8_nored),
        ("D9 ready 600 ms after release", "D9", FAIL, m_d9_slow), ("D9 overlapping same-key moves", "D9", FAIL, m_d9_overlap),
        ("D9 flagged hold without repeat", "D9", NE, m_d9_noflag), ("D9 no move request", "D9", NE, m_d9_nomove),
        ("D10 caret below the region", "D10", FAIL, m_d10_below), ("D10 status 59 at read 2", "D10", FAIL, m_d10_59),
        ("D10 status hidden", "D10", FAIL, m_d10_hidden), ("D10 freshness mismatch", "D10", FAIL, m_d10_fresh),
        ("D10 no rectangles", "D10", NE, m_d10_norects),
        ("D11a a save request", "D11a", FAIL, m_d11a_save), ("D11a the caret did not move", "D11a", FAIL, m_d11a_still),
        ("D11a not view-only", "D11a", NE, m_d11a_notview),
        ("D11b clean took a save", "D11b", FAIL, m_d11b_clean_save),
        ("D11b dirty: a checkpoint save before Ctrl+End", "D11b", FAIL, m_d11b_dirty_save_before_end),
        ("D11b dirty: a checkpoint save before Ctrl+Home", "D11b", FAIL, m_d11b_dirty_save_before_home),
        ("D11b dirty: #s-checkpoint not 無", "D11b", FAIL, m_d11b_dirty_checkpoint_shown),
        ("D11b dirty: dirty lost after a move", "D11b", FAIL, m_d11b_dirty_lost),
        ("D11b dirty read blind", "D11b", NE, m_d11b_blind),
        ("D11b dirty: no move request in the log", "D11b", NE, m_d11b_dirty_no_moves),
        ("D11c move refused as stale", "D11c", FAIL, m_d11c_stale), ("D11c the two moves differ", "D11c", FAIL, m_d11c_differ),
        ("D11c mutating control not stale", "D11c", NE, m_d11c_control),
        ("D12 a range call completes", "D12", FAIL, m_d12_completes), ("D12 selection changed", "D12", FAIL, m_d12_selection),
        ("D12 no range before the call", "D12", NE, m_d12_collapsed), ("D12 collapsed control refused", "D12", NE, m_d12_control),
        ("D5w v20 chord taken", "D5w", FAIL, m_d5w_taken), ("D5w Shift taken on v21", "D5w", FAIL, m_d5w_shift),
        ("D5w v21 positive control not taken", "D5w", NE, m_d5w_control), ("D5w keys not reaching the sink", "D5w", NE, m_d5w_nokeys),
        ("D14 marker at the pre-move caret (plain3)", "D14", FAIL, m_d14_pre_move),
        ("D14 marker at the pre-move caret (long60)", "D14", FAIL, m_d14_pre_move_long),
        ("D14 a missing save", "D14", NE, m_d14_nosave), ("D14 zero rounds", "D14", NE, m_d14_zero),
        ("D14 a fixture's rounds missing", "D14", NE, m_d14_fixture_missing),
        ("D14 marker 30.5 ms after Ctrl+End", "D14", NE, m_d14_late),
        ("D14 marker keydown before Ctrl+End's", "D14", NE, m_d14_before),
        ("D14 the document not dirty", "D14", NE, m_d14_clean),
        ("D14 the saved document unreadable (no content.xml)", "D14", FAIL, m_d14_unreadable),
        ("D14 the dirtying Z not in the saved document", "D14", NE, m_d14_no_dirty_char),
        ("D14 no keydown on the page", "D14", NE, m_d14_no_keydown),
        ("E0 the entry visible in a report", "E0", FAIL, m_e0_visible),
        ("E0 another visible control opens the dialog", "E0", FAIL, m_e0_other_opener),
        ("E0 a report with no entry read", "E0", NE, m_e0_no_read),
        ("E0 the visibility read blind", "E0", NE, m_e0_blind),
    ]


def self_test(verbose: bool = True) -> int:
    reports, docs = synthetic()
    code, lines = judge_reports(reports, docs, PAGE_V21, rounds=1)
    green = code == 0
    print(f"green  the synthetic reports PASS every criterion: {green}")
    if not green:
        print("\n".join(line for line in lines if "PASS" not in line)[:4000])
    results = []
    for name, criterion, expected, mutate in mutations(docs):
        base, base_docs = synthetic()
        for m_name, m_criterion, m_expected, m_mutate in mutations(base_docs):
            if m_name == name:
                m_mutate(base)
        _, out = judge_reports(base, base_docs, PAGE_V21, rounds=1)
        row = next((line for line in out if line.startswith(f"{criterion:5s} chrome")), None)
        got = row.split()[-1] if row else "MISSING"
        ok = got == expected
        results.append((name, ok))
        if verbose:
            print(f"{'RED ok ' if ok else 'NOT RED'}  {name}: {got} (want {expected})")
    # exit rules
    rules = []
    _, out = judge_reports(reports, docs, None, rounds=1)
    rules.append(("no --expect-page -> no verdict", out[0].startswith("VERDICT NOT GIVEN")))
    other = copy.deepcopy(reports)
    other[0]["pages"]["v21"]["pageServedSha256"] = "0" * 64
    code, out = judge_reports(other, docs, PAGE_V21, rounds=1)
    rules.append(("another page -> refused, criteria NE", code != 0 and any("refused report" in l for l in out)))
    smoke = copy.deepcopy(reports)
    smoke[0]["smoke"] = True
    code, out = judge_reports(smoke, docs, PAGE_V21, rounds=1)
    rules.append(("a smoke report -> refused", code == 2))
    code, out = judge_reports(smoke, docs, PAGE_V21, rounds=1, smoke_preview=True)
    rules.append(("a smoke preview -> labelled, exit 3", code == 3 and all(l.startswith("SMOKE") or l.startswith("    ") for l in out)))
    dup = copy.deepcopy(reports) + [copy.deepcopy(reports[0])]
    code, out = judge_reports(dup, docs, PAGE_V21, rounds=1)
    rules.append(("a second report for one (browser, arm) -> FAIL", code != 0 and any("D1    chrome   FAIL" in l for l in out)))
    code, out = judge_reports(reports, docs, PAGE_V21, rounds=3)
    rules.append(("one round of three -> NOT_ESTABLISHED", code != 0 and any("D1    chrome   NOT_ESTABLISHED" in l for l in out)))
    code, out = judge_reports(reports[:1], docs, PAGE_V21, rounds=1)
    rules.append(("a browser missing -> not PASS", code != 0))
    _, out = judge_reports(reports, docs, PAGE_V21, rounds=1)
    rules.append(("D6 skipped (chrome) or absent (firefox) -> printed 未量 for both browsers",
                  all(any(l.startswith(f"record {b}: D6 未量") for l in out) for b in BROWSERS)))
    for name, ok in rules:
        results.append((name, ok))
        if verbose:
            print(f"{'RED ok ' if ok else 'NOT RED'}  rule: {name}")
    bad = [n for n, ok in results if not ok]
    print(f"self-test: {len(results) - len(bad)}/{len(results)} as required" + (f"; NOT: {bad}" if bad else ""))
    return 0 if green and not bad else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path)
    ap.add_argument("--expect-page")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--smoke-preview", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.dir:
        ap.error("--dir is required")
    code, lines = judge_reports(load(args.dir), Docs(args.dir), args.expect_page, args.rounds, args.smoke_preview)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
