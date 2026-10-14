#!/usr/bin/env python3
"""Reads probe_bubble.py's reports against SPEC-M3-scroll-page-bubble §5 (N1-N6, D1, K1, Z1; on the host H1 = N1-N5 and H2).

  python3 -I judge_bubble.py --page ccb67a52 --dir n-nohost-v20/firefox --dir n-nohost-v20/chrome --dir n-nohost-v20/firefox-css-bar
  python3 -I judge_bubble.py --page ccb67a52 --dir ../host-0.2.23/h1-h2/firefox --dir ../host-0.2.23/h1-h2/chrome
  python3 -I judge_bubble.py --self-test --page ccb67a52 --dir ...   (red where it must be red: K4's bubble-less
                                                                     reports and mutated copies of the real runs)

Every clause prints its numbers; a clause with nothing to count is FAIL, not vacuous.
Three kinds of red are kept apart:
  FAIL             the product failed the clause;
  INSTRUMENT_RED   the instrument could not read what the clause needs (N2's thumb on
                   fewer than 15 of 17 steps) -- the spec's 儀器紅;
  NOT_ESTABLISHED  D1's drag moved nothing (allowed for Firefox only, spec §5 D1).
Every report-*.json in a --dir is read (`report-nohost-*` and `report-host-*`) and every
arm it lists is judged.  Verdicts are kept per (mode, browser, criterion): FAIL if any
run fails it, else PASS if any run passes it, else the weakest thing seen; a criterion no
run covers is MISSING.  What a mode must cover: nohost -- N1-N6, D1, K1, Z1; host --
N1-N5 (H1) and H2 (bubble rect inside the desk rect inside the host's #content rect,
and the bubble rect not intersecting the #page-status rect, on every wheel step and
after the drag); the other criteria on the host are judged when present but not
required.  The exit code is 0 only when every required (mode, browser, criterion) is PASS
or an allowed NOT_ESTABLISHED, nothing judged is FAIL, and every report served the pinned
page from start to end.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bubble_geometry import thumb_centre  # noqa: E402

TOLERANCE_PX = 24
SHOW_WITHIN_MS = 100
HIDE_WITHIN_MS = 1500
THUMB_READS_NEEDED = 15
PLAIN_TRANSITION_MAX_S = 0.2

CRITERIA = ("N1", "N2", "N3", "N4", "N5", "N6-plain", "N6-reduce", "D1", "K1", "Z1", "H2")
REQUIRED = {"nohost": ("N1", "N2", "N3", "N4", "N5", "N6-plain", "N6-reduce", "D1", "K1", "Z1"),
            "host": ("N1", "N2", "N3", "N4", "N5", "H2")}
NE_ALLOWED = {("firefox", "D1")}
ARM_CRITERIA = {"bubble-wheel": ("N1", "N2", "N3", "N4", "N5", "N6-plain"),
                "bubble-reduce": ("N1", "N3", "N4", "N5", "N6-reduce"),
                "bubble-drag": ("D1",), "bubble-keys": ("K1",), "bubble-short": ("Z1",)}
VERDICT_ORDER = ("FAIL", "PASS", "NOT_ESTABLISHED", "INSTRUMENT_RED")


class Book:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.verdicts: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
        self.subjects: list[tuple[str, str]] = []      # (mode, browser) in the order seen
        self.other_red: list[str] = []

    def say(self, mode: str, browser: str, crit: str, tag: str, verdict: str, text: str) -> None:
        self.lines.append(f"{tag}: {crit} {text} -> {verdict}")
        self.verdicts[(mode, browser, crit)].append((tag, verdict))

    def note(self, text: str) -> None:
        self.lines.append(text)

    def red(self, text: str) -> None:
        self.lines.append(text + " -> FAIL")
        self.other_red.append(text)


def page_part(status: str | None) -> str | None:
    if not isinstance(status, str):
        return None
    head = status.split("，")[0].strip()
    return head if head.startswith("第 ") and head.endswith(" 頁") else None


def run_of(report: dict, arm: str) -> dict | None:
    return next((r for r in report.get("runs", []) if r.get("arm") == arm), None)


def bubble_centre(bubble: dict | None) -> float | None:
    if not bubble or not bubble.get("rect"):
        return None
    left, top, width, height = bubble["rect"]
    return top + height / 2


def inside(bubble: dict | None, box: dict | None) -> bool:
    """bubble rect [left, top, width, height] inside a box {left, top, right, bottom}, half a pixel of slack."""
    if not bubble or not bubble.get("rect") or not box:
        return False
    left, top, width, height = bubble["rect"]
    return left >= box["left"] - 0.5 and left + width <= box["right"] + 0.5 and top >= box["top"] - 0.5 and top + height <= box["bottom"] + 0.5


def box_inside(inner: dict | None, outer: dict | None) -> bool:
    if not inner or not outer:
        return False
    return inner["left"] >= outer["left"] - 0.5 and inner["right"] <= outer["right"] + 0.5 \
        and inner["top"] >= outer["top"] - 0.5 and inner["bottom"] <= outer["bottom"] + 0.5


def intersects(bubble: dict | None, box: dict | None) -> bool:
    """A real overlap (edges touching is not one)."""
    if not bubble or not bubble.get("rect") or not box:
        return False
    left, top, width, height = bubble["rect"]
    return left < box["right"] and left + width > box["left"] and top < box["bottom"] and top + height > box["top"]


def seconds(value) -> float | None:
    try:
        return float(str(value).rstrip("s"))
    except ValueError:
        return None


def timing(log: list[dict], after: dict | None) -> dict:
    """N4's numbers from the log: per scroll event the first shown=1 state after it, and the hide after the last."""
    scrolls = [e for e in log if e.get("k") == "sc"]
    states = [e for e in log if e.get("k") == "st"]
    shown_at = [e["t"] for e in states if (e.get("bubble") or {}).get("shown") == "1"]
    late = []
    for s in scrolls:
        if not any(s["t"] - 50 <= t <= s["t"] + SHOW_WITHIN_MS for t in shown_at):
            late.append(s["t"])
    hide_ms = None
    if scrolls:
        last = scrolls[-1]["t"]
        hides = [e["t"] for e in states if e["t"] >= last and (e.get("bubble") or {}).get("shown") == "0"]
        hide_ms = round(hides[0] - last, 1) if hides else None
    visible_after = (after or {}).get("bubble", {}) or {}
    return {"scrollEvents": len(scrolls), "notShownWithin100ms": late, "hideAfterLastMs": hide_ms,
            "visibleAt2s": visible_after.get("visible"), "shownAt2s": visible_after.get("shown")}


def h2_instances(instances: list[tuple[str, dict]]) -> tuple[str, str]:
    """H2 over instances (label, {bubble, deskBox, content, pageStatusBox}): bubble ⊆ desk ⊆ #content,
    bubble ∩ #page-status = ∅.  Nothing to count (no #content box, no status box, a hidden bar) is FAIL."""
    no_boxes, bubble_out, desk_out, over_bar = [], [], [], []
    for label, s in instances:
        bubble, desk, content, bar = s.get("bubble"), s.get("deskBox"), s.get("content"), s.get("pageStatusBox")
        if not bubble or not bubble.get("rect") or not desk or not content or not bar or bar.get("hidden") is not False:
            no_boxes.append(label)
            continue
        if not inside(bubble, desk):
            bubble_out.append(label)
        if not box_inside(desk, content):
            desk_out.append((label, round(desk["bottom"] - content["bottom"], 1)))
        if intersects(bubble, bar):
            over_bar.append((label, round(bubble["rect"][1] + bubble["rect"][3] - bar["top"], 1)))
    ok = bool(instances) and not (no_boxes or bubble_out or desk_out or over_bar)
    first = next((s for _, s in instances if s.get("content")), {})
    text = (f"instances {len(instances)}, no boxes {no_boxes}, bubble outside desk {bubble_out}, desk outside #content {desk_out}, "
            f"bubble over #page-status {over_bar}; #content {first.get('content')}, bar {first.get('pageStatusBox')}")
    return ("PASS" if ok else "FAIL"), text


def judge_wheel(run: dict | None, folder: Path, book: Book, tag: str, mode: str, browser: str, reduce: bool = False) -> None:
    crits = ARM_CRITERIA["bubble-reduce" if reduce else "bubble-wheel"]
    if run is None or run.get("fatal"):
        for crit in crits + (("H2",) if mode == "host" and not reduce else ()):
            book.say(mode, browser, crit, tag, "FAIL", "no wheel run / fatal")
        return
    steps = run.get("steps") or []
    numbered = [s for s in steps if s.get("i") != "top"]
    # N1
    bad_text = [(s["i"], (s.get("bubble") or {}).get("text"), page_part((s.get("pageStatus") or {}).get("text")))
                for s in steps if not s.get("bubble") or s["bubble"].get("shown") != "1"
                or s["bubble"].get("text") != page_part((s.get("pageStatus") or {}).get("text"))
                or (s.get("pageStatus") or {}).get("hidden") is not False]
    n1 = bool(steps) and not bad_text
    book.say(mode, browser, "N1", tag, "PASS" if n1 else "FAIL",
             f"steps {len(steps)}, shown with the bar's page part and the bar not hidden at every step" + (f"; bad {bad_text[:4]}" if bad_text else ""))
    # N2 (the wheel arm only; the reduce arm takes no screenshots).  The desk and rail clauses count on every
    # step; the thumb clause on every step whose screenshot shows a thumb, and fewer than 15 such steps is
    # the instrument's red, not the product's.
    if not reduce:
        reads, far, outside, misplaced, no_rect, thumbs = 0, [], [], [], [], []
        for s in numbered:
            desk = s.get("deskBox")
            bubble = s.get("bubble") or {}
            if not desk or not bubble.get("rect"):
                no_rect.append(s.get("i"))
                continue
            if not inside(bubble, desk):
                outside.append(s["i"])
            right = bubble["rect"][0] + bubble["rect"][2]
            if not (desk["right"] - 60 <= right <= desk["right"] - 16):
                misplaced.append((s["i"], round(desk["right"] - right, 1)))
            shot = s.get("shot")
            png = folder / f"{run['browser']}-{run.get('arm', 'bubble-wheel')}-{shot}.png" if shot else None
            thumb = thumb_centre(png.read_bytes(), {"top": desk["top"], "bottom": desk["bottom"], "right": desk["right"]}) if png and png.exists() else None
            if thumb is None:
                continue
            reads += 1
            centre = bubble_centre(bubble)
            thumbs.append((s["i"], round(centre, 1), thumb["centre"]))
            if abs(centre - thumb["centre"]) > TOLERANCE_PX:
                far.append((s["i"], round(centre, 1), thumb["centre"]))
        if far or outside or misplaced or no_rect:
            n2 = "FAIL"
        elif reads < THUMB_READS_NEEDED:
            n2 = "INSTRUMENT_RED"
        else:
            n2 = "PASS"
        worst = max((abs(c - t) for _, c, t in thumbs), default=None)
        book.say(mode, browser, "N2", tag, n2,
                 f"thumb read on {reads}/{len(numbered)} steps (>= {THUMB_READS_NEEDED} needed, else the instrument is red), "
                 f"|bubble centre - thumb centre| max {worst} px, > {TOLERANCE_PX} px {far}, no rect {no_rect}, outside desk {outside}, not beside the rail {misplaced}")
    # N3
    log = run.get("scrollLog") or []
    non_paint = [e for e in log if e.get("k") == "rq" and (e.get("op") or "") != "paint"]
    paints = sum(1 for e in log if e.get("k") == "rq" and e.get("op") == "paint")
    n3 = not non_paint and len(log) > 0
    book.say(mode, browser, "N3", tag, "PASS" if n3 else "FAIL", f"non-paint requests {len(non_paint)} (paints {paints}, log entries {len(log)})"
             + (f" {[(e.get('op'), e.get('action')) for e in non_paint[:5]]}" if non_paint else ""))
    # N4
    t = timing(log, run.get("afterTwoSeconds"))
    n4 = t["scrollEvents"] > 0 and not t["notShownWithin100ms"] and t["hideAfterLastMs"] is not None \
        and t["hideAfterLastMs"] <= HIDE_WITHIN_MS and t["visibleAt2s"] is False
    book.say(mode, browser, "N4", tag, "PASS" if n4 else "FAIL", json.dumps(t))
    # N5
    states = [e for e in log if e.get("k") == "st"]
    focus = sorted({str(e.get("focus")) for e in states})
    a11y = sorted({str(e.get("a11y")) for e in states})
    toasts = [e.get("toast") for e in states if e.get("toast")]
    live_same = run.get("liveBefore") == run.get("liveAfter") and run.get("liveBefore") is not None
    n5 = run.get("activeBefore") == run.get("activeAfter") and run.get("activeBefore") is not None and len(focus) <= 1 \
        and len(a11y) <= 1 and not toasts and live_same
    book.say(mode, browser, "N5", tag, "PASS" if n5 else "FAIL",
             f"active {run.get('activeBefore')}->{run.get('activeAfter')}, focus values {focus}, a11y values {len(a11y)}, toasts {len(toasts)}, "
             f"live regions {len(run.get('liveBefore') or [])} same before/after {live_same}")
    # N6
    transitions = sorted({str((s.get("bubble") or {}).get("transition")) for s in steps})
    if reduce:
        matched = (run.get("geometryAtOpen") or {}).get("reducedMotion")
        n6 = matched is True and transitions == ["0s"]
        book.say(mode, browser, "N6-reduce", tag, "PASS" if n6 else "FAIL", f"matchMedia(reduce) {matched}, transition-duration {transitions} (must be 0s)")
    else:
        parsed = [seconds(v) for v in transitions]
        n6 = bool(transitions) and all(v is not None and v <= PLAIN_TRANSITION_MAX_S for v in parsed)
        book.say(mode, browser, "N6-plain", tag, "PASS" if n6 else "FAIL", f"no emulation, transition-duration {transitions} (<= {PLAIN_TRANSITION_MAX_S} s)")
    # H2 (host only; the wheel arm's every step)
    if mode == "host" and not reduce:
        verdict, text = h2_instances([(f"step {s.get('i')}", s) for s in steps])
        book.say(mode, browser, "H2", tag, verdict, text)
    attrs = {k: (steps[0].get("bubble") or {}).get(k) for k in ("ariaHidden", "role", "ariaLive", "tabindex", "pointerEvents", "position", "parent")} if steps else {}
    book.note(f"{tag}: bubble attributes {json.dumps(attrs)}")


def judge_drag(run: dict | None, book: Book, tag: str, mode: str, browser: str) -> None:
    if run is None or run.get("fatal"):
        book.say(mode, browser, "D1", tag, "FAIL", "no drag run / fatal")
        return
    if run.get("notEstablished"):
        book.say(mode, browser, "D1", tag, "NOT_ESTABLISHED", f"(instrument) {run['notEstablished']}")
        return
    before = ((run.get("geometryAtOpen") or {}).get("deskBox") or {}).get("scrollTop")
    after = (run.get("afterRelease") or {}).get("scrollTop")
    log = run.get("scrollLog") or []
    if after is None or before is None or after <= before:
        book.say(mode, browser, "D1", tag, "NOT_ESTABLISHED", f"the drag moved nothing (scrollTop {before} -> {after}; the thumb's hit target is the browser's)")
        return
    states = [e for e in log if e.get("k") == "st" and (e.get("bubble") or {}).get("shown") == "1"]
    texts_ok = [e for e in states if e["bubble"].get("text") == page_part(e.get("ps"))]
    t = timing(log, run.get("afterTwoSeconds"))
    d1 = len(states) >= 1 and len(texts_ok) == len(states) and t["hideAfterLastMs"] is not None and t["hideAfterLastMs"] <= HIDE_WITHIN_MS and t["visibleAt2s"] is False
    book.say(mode, browser, "D1", tag, "PASS" if d1 else "FAIL",
             f"pressed at {run.get('dragFrom')} (thumb read {run.get('thumbBefore')}), scrollTop {before} -> {after}, shown states during/after {len(states)} "
             f"(text = the bar's page part in {len(texts_ok)}), hide after the last scroll {t['hideAfterLastMs']} ms, visible at 2 s {t['visibleAt2s']}")
    if mode == "host":
        verdict, text = h2_instances([("after the drag", run.get("afterRelease") or {})])
        book.say(mode, browser, "H2", tag + " drag", verdict, text)


def judge_keys(run: dict | None, book: Book, tag: str, mode: str, browser: str) -> None:
    if run is None or run.get("fatal"):
        book.say(mode, browser, "K1", tag, "FAIL", "no keys run / fatal")
        return
    log = run.get("scrollLog") or []
    t = timing(log, run.get("afterTwoSeconds"))
    states = [e for e in log if e.get("k") == "st" and (e.get("bubble") or {}).get("shown") == "1"]
    texts_bad = [(e["t"], e["bubble"].get("text"), e.get("ps")) for e in states if e["bubble"].get("text") != page_part(e.get("ps"))]
    requests = sum(1 for e in log if e.get("k") == "rq" and (e.get("op") or "") != "paint")
    k1 = t["scrollEvents"] >= 1 and not t["notShownWithin100ms"] and not texts_bad and t["hideAfterLastMs"] is not None \
        and t["hideAfterLastMs"] <= HIDE_WITHIN_MS and t["visibleAt2s"] is False
    book.say(mode, browser, "K1", tag, "PASS" if k1 else "FAIL",
             f"ArrowDown x {run.get('pressed')} (caret requests {requests}; N3 not applicable) {json.dumps(t)}, text mismatches {texts_bad[:3]}")


def judge_short(run: dict | None, book: Book, tag: str, mode: str, browser: str) -> None:
    if run is None or run.get("fatal"):
        book.say(mode, browser, "Z1", tag, "FAIL", "no short run / fatal")
        return
    tall = (run.get("geometryTall") or {}).get("deskBox") or {}
    back = (run.get("geometryBack") or {}).get("deskBox") or {}
    tall_scroll = sum(1 for e in run.get("tallLog") or [] if e.get("k") == "sc")
    tall_shown = [s["i"] for s in run.get("tallSteps") or [] if (s.get("bubble") or {}).get("shown") == "1"]
    status = ((run.get("tallSteps") or [{}])[-1].get("pageStatus") or {}).get("text")
    back_step = run.get("backStep") or {}
    back_scroll = sum(1 for e in run.get("backLog") or [] if e.get("k") == "sc")
    not_scrollable = bool(tall) and tall["scrollHeight"] <= tall["clientHeight"]
    scrollable_back = bool(back) and back["scrollHeight"] > back["clientHeight"]
    control = (back_step.get("bubble") or {}).get("shown") == "1" and (back_step.get("bubble") or {}).get("text") == "第 1 頁" and back_scroll >= 1
    z1 = not_scrollable and tall_scroll == 0 and not tall_shown and status == "第 1 頁，共 1 頁" and scrollable_back and control
    book.say(mode, browser, "Z1", tag, "PASS" if z1 else "FAIL",
             f"tall desk scrollHeight {tall.get('scrollHeight')} <= clientHeight {tall.get('clientHeight')} ({not_scrollable}), scroll events {tall_scroll}, "
             f"shown {tall_shown}, bar {status!r}; back {back.get('scrollHeight')} > {back.get('clientHeight')} ({scrollable_back}), "
             f"positive control shown {(back_step.get('bubble') or {}).get('shown')} {(back_step.get('bubble') or {}).get('text')!r} scroll events {back_scroll}")


def served_pin(report: dict) -> tuple[str, str, dict]:
    pin = report.get("nohost") or report.get("host") or {}
    return str(pin.get("servedPage")), str(pin.get("servedPageAtEnd")), pin


def judge_report(report: dict, folder: Path, book: Book, page_prefix: str | None) -> None:
    mode = str(report.get("mode") or ("host" if report.get("host") else "nohost"))
    browser = str(report.get("browser"))
    tag = f"{browser} {mode} {folder.name}" + (" css-bar" if report.get("cssBar") else "")
    served, served_end, pin = served_pin(report)
    static = report.get("static") or {}
    book.note(f"{tag}: {report.get('doc', {}).get('name')} served page {served[:8]} .. at end {served_end[:8]}, "
              + (f"host {static.get('hostVersion')} {static.get('hostCommit')} buildId {static.get('buildId')} folder {pin.get('folder')} "
                 f"deleted {pin.get('deletedFolder')}, " if mode == "host" else f"profile {pin.get('profile')}, ")
              + f"arms {report.get('arms')}, cssBar {report.get('cssBar')!r}, started {report.get('startedAt')}")
    if page_prefix and not (served.startswith(page_prefix) and served_end.startswith(page_prefix)):
        book.red(f"{tag}: the served page is not the pinned {page_prefix} ({served[:8]} / {served_end[:8]})")
    if mode == "host":
        after = report.get("staticAfter") or {}
        moved = [k for k in ("hostVersion", "hostCommit", "buildId", "servedPage", "servedSession") if static.get(k) != after.get(k)]
        if moved or static.get("hostDirty") or after.get("hostDirty"):
            book.red(f"{tag}: the host moved or is dirty during the run: changed {moved}, dirty {static.get('hostDirty')} / {after.get('hostDirty')}")
    if (mode, browser) not in book.subjects:
        book.subjects.append((mode, browser))
    arms = report.get("arms") or []
    if not arms:
        book.red(f"{tag}: the report lists no arms")
    for arm in arms:
        run = run_of(report, arm)
        if arm == "bubble-wheel":
            judge_wheel(run, folder, book, tag, mode, browser)
        elif arm == "bubble-reduce":
            judge_wheel(run, folder, book, tag + " reduce", mode, browser, reduce=True)
        elif arm == "bubble-drag":
            judge_drag(run, book, tag, mode, browser)
        elif arm == "bubble-keys":
            judge_keys(run, book, tag, mode, browser)
        elif arm == "bubble-short":
            judge_short(run, book, tag, mode, browser)
        else:
            book.red(f"{tag}: unknown arm {arm!r}")


def judge_dir(folder: Path, book: Book, page_prefix: str | None) -> None:
    reports = sorted(folder.glob("report-*.json"))
    if not reports:
        book.red(f"{folder}: no report")
        return
    for path in reports:
        judge_report(json.loads(path.read_text()), folder, book, page_prefix)


def resolve(entries: list[tuple[str, str]]) -> str:
    seen = {v for _, v in entries}
    for v in VERDICT_ORDER:
        if v in seen:
            return v
    return "MISSING"


def summarize(book: Book) -> tuple[bool, dict]:
    ok = not book.other_red
    table: dict[str, dict[str, str]] = {}
    lines = []
    for mode, browser in book.subjects:
        key = f"{mode}/{browser}"
        table[key] = {}
        required = REQUIRED[mode]
        for crit in CRITERIA:
            entries = book.verdicts.get((mode, browser, crit), [])
            v = resolve(entries)
            if v == "MISSING" and crit not in required:
                continue
            green = v == "PASS" or (v == "NOT_ESTABLISHED" and (browser, crit) in NE_ALLOWED)
            ok &= green
            table[key][crit] = v
            lines.append(f"  {key:16s} {crit:10s} {v:16s} {'ok' if green else 'RED':3s} {'' if crit in required else '(not required here)'} "
                         + "; ".join(f"{t} = {vv}" for t, vv in entries))
    return ok, {"table": table, "lines": lines}


def judge(dirs: list[Path], page_prefix: str | None) -> tuple[bool, Book, dict]:
    book = Book()
    for folder in dirs:
        judge_dir(folder, book, page_prefix)
    ok, summary = summarize(book)
    return ok, book, summary


# ---------------------------------------------------------------- self-test

def _k4_as_wheel_run(k4: Path, browser: str) -> dict:
    """K4's page-number run (the old probe, 2026-10-14 host 0.2.21): no bubble fields, no sc entries, no shots."""
    report = json.loads((k4 / f"report-host-{browser}-long60.json").read_text())
    run = run_of(report, "page-number")
    return {**run, "arm": "bubble-wheel", "browser": browser,
            "steps": [{**s, "pageStatus": {"hidden": s.get("hidden"), "text": s.get("text")}, "deskBox": None} for s in run.get("steps", [])]}


def _verdict(book: Book, mode: str, browser: str, crit: str) -> str:
    return resolve(book.verdicts.get((mode, browser, crit), []))


def _with_host_boxes(run: dict) -> tuple[dict, bool]:
    """A copy with #content and #page-status boxes on every step: the run's own when it has them (a host run),
    else synthetic ones laid out like the host (the bar 32 px high right under the desk, #content 8 px above
    the desk and 40 px below it).  Returns (copy, synthetic)."""
    out = copy.deepcopy(run)
    synthetic = False
    for s in out.get("steps", []):
        d = s.get("deskBox")
        if not d:
            continue
        if not s.get("content"):
            synthetic = True
            s["content"] = {"left": d["left"], "top": d["top"] - 8, "right": d["right"], "bottom": d["bottom"] + 40}
        if not s.get("pageStatusBox"):
            synthetic = True
            s["pageStatusBox"] = {"hidden": False, "left": d["left"], "top": d["bottom"], "right": d["right"], "bottom": d["bottom"] + 32}
    return out, synthetic


def self_test(dirs: list[Path], page_prefix: str | None) -> int:
    here = Path(__file__).resolve().parent
    k4 = here.parent / "host-0.2.21" / "k4-host-css"
    cases: list[tuple[str, str, set[str], str]] = []   # (name, criterion, allowed verdicts, verdict)
    out: list[str] = []

    def case(name: str, crit: str, allowed: set[str], book: Book, mode: str, browser: str) -> None:
        v = _verdict(book, mode, browser, crit)
        cases.append((name, crit, allowed, v))
        out.extend(book.lines)
        out.append(f"  => {name}: {crit} {v} (must be {sorted(allowed)}) {'ok' if v in allowed else 'NOT RED WHERE IT MUST BE'}")

    for browser in ("firefox", "chrome"):
        book = Book()
        judge_wheel(_k4_as_wheel_run(k4, browser), k4, book, f"self-test K4 {browser} (no bubble)", "host", browser)
        case(f"K4 {browser} N1", "N1", {"FAIL"}, book, "host", browser)
        case(f"K4 {browser} N2", "N2", {"INSTRUMENT_RED", "FAIL"}, book, "host", browser)
        case(f"K4 {browser} N4", "N4", {"FAIL"}, book, "host", browser)
        case(f"K4 {browser} H2 (no boxes)", "H2", {"FAIL"}, book, "host", browser)
    shift_caught = 0
    for folder in dirs:
        for path in sorted(folder.glob("report-*.json")):
            report = json.loads(path.read_text())
            browser = str(report.get("browser"))
            mode = str(report.get("mode") or "nohost")
            label = f"{browser} {mode} {folder.name}" + (" css-bar" if report.get("cssBar") else "")
            wheel = run_of(report, "bubble-wheel")
            if wheel and not wheel.get("fatal"):
                baseline = Book()
                judge_wheel(wheel, folder, baseline, "baseline", mode, browser)
                thumb_read = _verdict(baseline, mode, browser, "N2") == "PASS"
                shifted = copy.deepcopy(wheel)
                for s in shifted["steps"]:
                    if s.get("bubble") and s["bubble"].get("rect"):
                        s["bubble"]["rect"][1] += 40
                book = Book()
                judge_wheel(shifted, folder, book, f"self-test {label} rect +40 px", mode, browser)
                case(f"{label} rect +40", "N2", {"FAIL"} if thumb_read else {"INSTRUMENT_RED"}, book, mode, browser)
                shift_caught += _verdict(book, mode, browser, "N2") == "FAIL"
                covered = copy.deepcopy(wheel)
                for s in covered["steps"]:
                    if s.get("bubble") and s["bubble"].get("rect"):
                        s["bubble"]["rect"][0] += 20
                book = Book()
                judge_wheel(covered, folder, book, f"self-test {label} rect 20 px right (over the rail)", mode, browser)
                case(f"{label} over the rail", "N2", {"FAIL"}, book, mode, browser)
                whole = copy.deepcopy(wheel)
                for s in whole["steps"]:
                    if s.get("bubble"):
                        s["bubble"]["text"] = (s.get("pageStatus") or {}).get("text")
                book = Book()
                judge_wheel(whole, folder, book, f"self-test {label} text = the whole bar", mode, browser)
                case(f"{label} whole text", "N1", {"FAIL"}, book, mode, browser)
                stuck = copy.deepcopy(wheel)
                stuck["scrollLog"] = [e for e in stuck["scrollLog"] if not (e.get("k") == "st" and (e.get("bubble") or {}).get("shown") == "0")]
                stuck["afterTwoSeconds"] = copy.deepcopy(stuck["afterTwoSeconds"])
                stuck["afterTwoSeconds"]["bubble"] = {**(stuck["afterTwoSeconds"].get("bubble") or {}), "visible": True, "shown": "1"}
                book = Book()
                judge_wheel(stuck, folder, book, f"self-test {label} never hides", mode, browser)
                case(f"{label} never hides", "N4", {"FAIL"}, book, mode, browser)
                spoke = copy.deepcopy(wheel)
                states = [e for e in spoke["scrollLog"] if e.get("k") == "st"]
                if states:
                    states[-1]["a11y"] = "第 5 頁的第一段"
                book = Book()
                judge_wheel(spoke, folder, book, f"self-test {label} a11y changed", mode, browser)
                case(f"{label} a11y spoke", "N5", {"FAIL"}, book, mode, browser)
                # H2: on a host run its own boxes, on a no-host run synthetic ones (so the clause is red before any host run exists)
                boxed, synthetic = _with_host_boxes(wheel)
                kind = "synthetic boxes" if synthetic else "the run's own boxes"
                book = Book()
                judge_wheel(boxed, folder, book, f"self-test {label} H2 control ({kind})", "host", browser)
                case(f"{label} H2 control ({kind})", "H2", {"PASS"}, book, "host", browser)
                below = copy.deepcopy(boxed)
                for s in below["steps"]:
                    if s.get("bubble") and s["bubble"].get("rect") and s.get("content"):
                        s["bubble"]["rect"][1] = s["content"]["bottom"] - 10      # the rect's bottom beyond #content's bottom
                book = Book()
                judge_wheel(below, folder, book, f"self-test {label} H2 rect bottom beyond #content ({kind})", "host", browser)
                case(f"{label} H2 beyond #content", "H2", {"FAIL"}, book, "host", browser)
                onbar = copy.deepcopy(boxed)
                for s in onbar["steps"]:
                    if s.get("bubble") and s["bubble"].get("rect") and s.get("pageStatusBox"):
                        s["bubble"]["rect"][1] = s["pageStatusBox"]["top"] - 5        # overlapping the status bar by 5 px of its height
                book = Book()
                judge_wheel(onbar, folder, book, f"self-test {label} H2 bubble over #page-status ({kind})", "host", browser)
                case(f"{label} H2 over the bar", "H2", {"FAIL"}, book, "host", browser)
                clipped = copy.deepcopy(boxed)
                for s in clipped["steps"]:
                    if s.get("content") and s.get("deskBox"):
                        s["content"]["bottom"] = s["deskBox"]["bottom"] - 10         # the desk's bottom beyond #content's bottom
                book = Book()
                judge_wheel(clipped, folder, book, f"self-test {label} H2 desk beyond #content ({kind})", "host", browser)
                case(f"{label} H2 desk beyond #content", "H2", {"FAIL"}, book, "host", browser)
            keys = run_of(report, "bubble-keys")
            if keys and not keys.get("fatal"):
                silent = copy.deepcopy(keys)
                silent["scrollLog"] = [e for e in silent["scrollLog"] if e.get("k") != "sc"]
                book = Book()
                judge_keys(silent, book, f"self-test {label} no scroll events", mode, browser)
                case(f"{label} keys no scroll", "K1", {"FAIL"}, book, mode, browser)
            short = run_of(report, "bubble-short")
            if short and not short.get("fatal"):
                nan = copy.deepcopy(short)
                nan["tallSteps"][0]["bubble"] = {**(nan["tallSteps"][0].get("bubble") or {}), "shown": "1", "text": "第 1 頁"}
                book = Book()
                judge_short(nan, book, f"self-test {label} shown while nothing scrolls", mode, browser)
                case(f"{label} Z1 shown", "Z1", {"FAIL"}, book, mode, browser)
            drag = run_of(report, "bubble-drag")
            if drag and not drag.get("fatal") and not drag.get("notEstablished"):
                still = copy.deepcopy(drag)
                still["afterRelease"] = {**(still.get("afterRelease") or {}), "scrollTop": ((still.get("geometryAtOpen") or {}).get("deskBox") or {}).get("scrollTop")}
                book = Book()
                judge_drag(still, book, f"self-test {label} drag moved nothing", mode, browser)
                case(f"{label} drag still", "D1", {"NOT_ESTABLISHED"}, book, mode, browser)
    print("\n".join(out))
    all_ok = bool(cases) and all(v in allowed for _, _, allowed, v in cases) and shift_caught >= 1
    print(json.dumps({"selfTest": "ok (red where it must be, green where it must be)" if all_ok else "NOT RED WHERE IT MUST BE",
                      "cases": {name: v for name, _, _, v in cases}, "shiftCaughtByThumbRuns": shift_caught}, ensure_ascii=False))
    return 0 if all_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, action="append", default=[])
    parser.add_argument("--page", default=None, help="sha256 prefix every report must have served, start to end")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.dir, args.page)
    ok, book, summary = judge(args.dir, args.page)
    print("\n".join(book.lines))
    print("verdicts per mode/browser (FAIL beats PASS beats NOT_ESTABLISHED beats INSTRUMENT_RED; MISSING = no run covers it):")
    print("\n".join(summary["lines"]))
    print(json.dumps({"ok": ok, "page": args.page, "verdicts": summary["table"], "otherRed": book.other_red}, ensure_ascii=False))
    print("ALL PASS" if ok else "RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
