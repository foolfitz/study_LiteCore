#!/usr/bin/env python3
"""Judge a probe_held_into_refusal.py report against finding 134's acceptance
(SPEC-M3-held-key §14; ruling-1 condition 3).

Per round over report["runs"]; per arm over the probe's own ARMS tuple, read
from its source (tool-closed: an arm the probe declares with no rule here is a
FAIL, and so is a required browser with fewer rounds of an arm than the
minimum).  Exit 0 only when every arm passes on every required browser and the
served page is the one named.

  judge_held_into_refusal.py REPORT --page SHA256 [--browsers chrome,firefox]

`#desk.scrollTop` is reported, never judged (ruling-1 condition 7).
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Callable

PROBE = Path(__file__).resolve().parent / "probe_held_into_refusal.py"
STATIC_KEYS = ("hostVersion", "hostCommit", "buildId", "servedPage", "distPage")


def probe_arms() -> tuple[str, ...]:
    for node in ast.parse(PROBE.read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ARMS" for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise SystemExit(f"ARMS not found in {PROBE}")


def one_reopen(run: dict[str, Any]) -> list[str]:
    s = run["summary"]
    failed = []
    if s["refusals"] != 1:
        failed.append(f"refusals {s['refusals']} != 1")
    if s["generations"] != ["1", "2"]:
        failed.append(f"generations {s['generations']} != ['1', '2']")
    if s["limitSavedMs"] is not None or (run.get("limit") or {}).get("limit") is not None:
        failed.append(f"limit notice {(run.get('limit') or {}).get('limit')!r}")
    return failed


def document_kept(run: dict[str, Any]) -> list[str]:
    srv = run.get("server") or {}
    failed = []
    if srv.get("sameAsOriginal") is not True:
        failed.append(f"server differs: firstDiff {srv.get('firstDiffFromOriginal')} charDelta {srv.get('charDelta')} "
                      f"paragraphs {srv.get('paragraphs')}/{srv.get('paragraphsOriginal')}")
    if srv.get("marks") != 1:
        failed.append(f"marks {srv.get('marks')} != 1")
    return failed


def mark_at_end(run: dict[str, Any]) -> list[str]:
    srv = run.get("server") or {}
    if "markParagraphs" not in srv:
        return ["markParagraphs not recorded"]
    last = srv["paragraphs"] - 1
    return [] if srv["markParagraphs"] == [last] else [f"mark in paragraphs {srv['markParagraphs']}, last is {last}"]


RULES: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "start-press": lambda run: one_reopen(run) + document_kept(run),
    "start-hold": lambda run: one_reopen(run) + document_kept(run),
    "end-hold": lambda run: one_reopen(run) + document_kept(run),
    "end-press-type": lambda run: one_reopen(run) + document_kept(run) + mark_at_end(run),
}
MIN_ROUNDS = {"start-press": 1, "start-hold": 2, "end-hold": 2, "end-press-type": 1}


def scroll_series(run: dict[str, Any]) -> list[float]:
    out: list[float] = []
    for e in run.get("log") or []:
        if e.get("what") == "state" and "scroll" in e and (not out or out[-1] != e["scroll"]):
            out.append(e["scroll"])
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--page", required=True, help="sha256 the served and dist page must both be")
    parser.add_argument("--browsers", default="chrome,firefox")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    arms = probe_arms()
    failures: list[str] = []

    static, after = report.get("static") or {}, report.get("staticAfter") or {}
    print("static", {k: static.get(k) for k in STATIC_KEYS})
    for key in ("servedPage", "distPage"):
        if static.get(key) != args.page:
            failures.append(f"static: {key} {static.get(key)} != {args.page}")
    if any(static.get(k) != after.get(k) for k in STATIC_KEYS):
        failures.append(f"static: staticAfter differs {[k for k in STATIC_KEYS if static.get(k) != after.get(k)]}")

    for run in report["runs"]:
        if run["arm"] not in arms:
            failures.append(f"{run['browser']} {run['arm']} r{run['round']}: arm not in the probe's ARMS")
    for arm in arms:
        rule = RULES.get(arm)
        if rule is None or arm not in MIN_ROUNDS:
            failures.append(f"{arm}: no rule for an arm the probe declares")
            continue
        for browser in args.browsers.split(","):
            runs = [r for r in report["runs"] if r["arm"] == arm and r["browser"] == browser]
            if len(runs) < MIN_ROUNDS[arm]:
                failures.append(f"{browser} {arm}: {len(runs)} rounds < {MIN_ROUNDS[arm]}")
            for run in runs:
                head = f"{browser} {arm} r{run['round']}"
                if run.get("fatal"):
                    failures.append(f"{head}: fatal {run['fatal'].strip().splitlines()[-1]}")
                    print(head, "FAIL fatal")
                    continue
                failed = rule(run)
                s, srv = run["summary"], run.get("server") or {}
                print(head, "FAIL" if failed else "PASS",
                      f"refusals {s['refusals']} gens {s['generations']} limit {(run.get('limit') or {}).get('limit')}",
                      f"| server same {srv.get('sameAsOriginal')} marks {srv.get('marks')} "
                      f"markParagraphs {srv.get('markParagraphs')} paragraphs {srv.get('paragraphs')}",
                      f"| scroll {scroll_series(run)[:8]}")
                failures.extend(f"{head}: {f}" for f in failed)
    for f in failures:
        print("FAIL", f)
    print("verdict", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
