#!/usr/bin/env python3
"""E0-v22 (specs/SPEC-M3-link-batch-v22.md §11.4.1; fable ruling 5 addendum 1): the item-2 entry on the v22 page.

A reading of data the item-1 runner already records, not a new instrument: every `start.entry` (the runner's
ENTRY_READ, static, read at every arm's start state) of every round of every arm, per report.

  e0_v22.py REPORT [REPORT ...]          read the reports; exit 0 PASS, 1 FAIL, 2 NOT_ESTABLISHED
  e0_v22.py --red BASE_REPORT            the red cases on synthetic copies of BASE_REPORT (exit 0 = all as required)

Per read, by the page variant the runner tagged it with:
  v21, v21host, v21hook  (labels of the round's page; the profile is e2-editor-v22): exists, not hidden, no hidden
                         attribute, the control visible, the dialog present and closed, and EXACTLY ONE visible
                         opener: the toolbar button (action "paste-markdown", tag "button");
  v20                    (D5w's v20 page, no declaration): exists, hidden, no visible opener, the control visible;
  dist0224               not judged (0.2.24 has no dialog).
A read with `error`, or with the control not visible, is blind: NOT_ESTABLISHED.  No read at all: NOT_ESTABLISHED.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"
V22_PAGES = ("v21", "v21host", "v21hook")


def reads(report: dict):
    for arm, result in (report.get("results") or {}).items():
        for rec in (result or {}).get("rounds", []) or []:
            entry = (rec.get("start") or {}).get("entry") if isinstance(rec, dict) else None
            if isinstance(entry, dict):
                yield f"{arm} r{rec.get('round')}", entry


def judge_read(where: str, e: dict) -> tuple[str, str | None]:
    variant = e.get("variant")
    if variant == "dist0224":
        return "skip", None
    if e.get("error") or e.get("controlVisible") is not True:
        return NE, f"{where} [{variant}]: blind read (error {e.get('error')!r}, controlVisible {e.get('controlVisible')})"
    openers = e.get("visibleOpeners") or []
    if variant in V22_PAGES:
        ok = (e.get("exists") is True and e.get("hidden") is False and e.get("hiddenAttr") is False
              and e.get("dialogExists") is True and e.get("dialogOpen") is False and len(openers) == 1
              and openers[0].get("action") == "paste-markdown" and openers[0].get("tag") == "button")
        return (PASS, None) if ok else (FAIL, f"{where} [{variant}]: exists {e.get('exists')} hidden {e.get('hidden')} "
                                               f"hiddenAttr {e.get('hiddenAttr')} dialog {e.get('dialogExists')}/"
                                               f"{e.get('dialogOpen')} openers {openers}")
    if variant == "v20":
        ok = e.get("exists") is True and e.get("hidden") is True and openers == []
        return (PASS, None) if ok else (FAIL, f"{where} [v20]: exists {e.get('exists')} hidden {e.get('hidden')} "
                                               f"openers {openers}")
    return FAIL, f"{where}: a page variant this reading does not know: {variant!r}"


def judge(reports: list[dict]) -> tuple[str, list[str]]:
    lines, verdicts = [], []
    for report in reports:
        name = f"{report.get('browser')} {','.join(report.get('arms') or [])}"
        counted = {PASS: 0, FAIL: 0, NE: 0}
        for where, entry in reads(report):
            verdict, why = judge_read(where, entry)
            if verdict == "skip":
                continue
            counted[verdict] += 1
            if why:
                lines.append(f"  {verdict} {why}")
        verdict = FAIL if counted[FAIL] else NE if counted[NE] or not counted[PASS] else PASS
        lines.append(f"[{name}] {verdict}: {counted[PASS]} read(s) as required, {counted[FAIL]} red, {counted[NE]} blind")
        verdicts.append(verdict)
    if not verdicts:
        return NE, ["no report"]
    return (FAIL if FAIL in verdicts else NE if NE in verdicts else PASS), lines


SHOWN = {"exists": True, "hidden": False, "hiddenAttr": False, "candidates": 1, "controlVisible": True,
         "dialogExists": True, "dialogOpen": False,
         "visibleOpeners": [{"tag": "button", "id": None, "action": "paste-markdown", "text": "貼上為 Markdown…"}]}


def control_from(base: dict) -> dict:
    """A synthetic v22 report: BASE's rounds, every v22-page read in the shown shape, v20 reads as they were."""
    report = copy.deepcopy(base)
    for _, entry in reads(report):
        if entry.get("variant") in V22_PAGES:
            entry.update(copy.deepcopy(SHOWN))
    return report


def first(report: dict, variant: str) -> dict:
    return next(e for _, e in reads(report) if e.get("variant") == variant)


def red(base_path: Path) -> int:
    base = json.loads(base_path.read_text(encoding="utf-8"))
    control = control_from(base)
    cases = []

    def case(label: str, expect: str, mutate):
        report = copy.deepcopy(control)
        mutate(report)
        got, lines = judge([report])
        cases.append((label, expect, got, lines))

    case("control: every v22 read shown with one opener, v20 hidden", PASS, lambda r: None)
    case("a v22-profile read with hidden true (the v21 shape)", FAIL,
         lambda r: first(r, "v21").update(hidden=True, hiddenAttr=True, visibleOpeners=[]))
    case("a v22-profile read with two openers", FAIL,
         lambda r: first(r, "v21")["visibleOpeners"].append({"tag": "a", "id": None, "action": None, "text": "Markdown"}))
    case("a v20 read with hidden false", FAIL,
         lambda r: first(r, "v20").update(hidden=False, hiddenAttr=False))
    case("a read with controlVisible false", NE, lambda r: first(r, "v21host").update(controlVisible=False))
    case("no read at all", NE, lambda r: [res.update(rounds=[]) for res in (r.get("results") or {}).values()])
    case("the unchanged v21 report (every v22-page read hidden)", FAIL, lambda r: r.update(copy.deepcopy(base)))
    bad = 0
    for label, expect, got, lines in cases:
        ok = got == expect
        bad += not ok
        print(f"{'ok  ' if ok else 'BAD '} {label}: expected {expect}, got {got}")
        for line in lines[-2:]:
            print(f"       {line[:180]}")
    print(f"red cases: {len(cases) - bad}/{len(cases)} as required")
    return 0 if bad == 0 else 1


def main(argv: list[str]) -> int:
    if argv[:1] == ["--red"] and len(argv) == 2:
        return red(Path(argv[1]))
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    verdict, lines = judge([json.loads(Path(p).read_text(encoding="utf-8")) for p in argv])
    print("\n".join(lines))
    print(f"E0-v22 {verdict}")
    return {PASS: 0, FAIL: 1, NE: 2}[verdict]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
