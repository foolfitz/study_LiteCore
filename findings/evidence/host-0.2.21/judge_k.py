#!/usr/bin/env python3
"""Task 10-14o: read K2 and K4 off probe_10_14o.py reports.  Numbers from the
reports' own fields; the clauses are the brief's, pinned before any run.

  python3 -I judge_k.py --k2 DIR [--k2 DIR ...] --k4 DIR [--k4 DIR ...]

K2 (no host, the dist mirror with the 141 page), per report, both browsers:
  burst-1s at the document start of the 60-page fixture:
    (a) exactly 1 engine delete request;
    (b) 處理中 ends < 2,500 ms after the first keydown;
    (c) generation ['1'], the document unchanged (revision 0 before and after), no toast.
  burst-1s-in-text (control): every press deletes -- 18 requests, revision +18.
K4 (the current host with the 143 CSS), page-number arm, both browsers:
    (d) the page-number text's bottom edge <= #content's bottom edge;
    (e) font-size >= 13 px and contrast >= 4.5:1 (text colour on the element's background);
    (f) the text follows the wheel (every step shows a different-or-equal page text, never hidden);
    (g) the bar spans the editor root's full width at its bottom edge, and the page number is its
        leftmost visible text (added by the owner's ruling, before the run).
Exit 1 on any red.  Self-test: `--red-check` runs the clauses on the 10-14n reports, which must be red
on (a), (b) and (d), (e).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def luminance(rgb: str) -> float:
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", rgb or "")
    if not m:
        return float("nan")
    def f(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(int(m.group(i))) for i in (1, 2, 3))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def judge_k2(report: dict, lines: list[str]) -> bool:
    ok = True
    for run in report["runs"]:
        s = run.get("summary") or {}
        tag = f"K2 {report['browser']} {run['arm']}"
        if run.get("fatal"):
            lines.append(f"{tag}: FAIL fatal {run['fatal'].strip().splitlines()[-1]}")
            ok = False
            continue
        responses = [x for x in s.get("editorResponses", []) if (x.get("op") or "").startswith("editor")]
        requests = [x for x in s.get("nonPaintRequests", []) if (x.get("op") or "").startswith("editor")]
        ready = s.get("readyAgainMs") or []
        if run["arm"] == "burst-1s":
            a = len(requests) == 1 and len(responses) == 1
            b = bool(ready) and ready[-1] < 2500
            before = run.get("stateBeforeKey", {}).get("rev")
            after = (run.get("settle") or {}).get("last", {}).get("rev")
            c = s.get("generations") == ["1"] and str(before) == "0" and str(after) == "0" and not s.get("toasts")
            lines.append(f"{tag}: (a) requests {len(requests)} responses {len(responses)} -> {'PASS' if a else 'FAIL'}; "
                         f"(b) ready at {ready} ms -> {'PASS' if b else 'FAIL'}; "
                         f"(c) generations {s.get('generations')} rev {before}->{after} toasts {s.get('toasts')} -> {'PASS' if c else 'FAIL'}; "
                         f"keydowns {s.get('keydowns')} beforeinputs {s.get('beforeinputs')} completions {sorted({x.get('completion') for x in responses})}")
            ok &= a and b and c
        elif run["arm"] == "burst-1s-in-text":
            before = run.get("stateBeforeKey", {}).get("rev")
            after = (run.get("settle") or {}).get("last", {}).get("rev")
            deleted = sum(1 for x in responses if x.get("completion") == "verified-selection-delete" and x.get("changed") is True)
            d = len(requests) == 18 and deleted == 18 and before is not None and after is not None and int(after) - int(before) == 18
            lines.append(f"{tag} (control): requests {len(requests)} verified deletes {deleted} rev {before}->{after} "
                         f"ready at {ready} ms generations {s.get('generations')} -> {'PASS' if d else 'FAIL'}")
            ok &= d
    return ok


def judge_k4(report: dict, lines: list[str]) -> bool:
    ok = True
    for run in report["runs"]:
        if run["arm"] != "page-number":
            continue
        tag = f"K4 {report['browser']}"
        if run.get("fatal"):
            lines.append(f"{tag}: FAIL fatal {run['fatal'].strip().splitlines()[-1]}")
            ok = False
            continue
        g = run["geometryAtOpen"]
        text_rect = g.get("psTextRect") or [None] * 4
        content = (g.get("content") or {}).get("rect")
        rect = g.get("rect")
        text_bottom = text_rect[1] + text_rect[3] if text_rect[1] is not None else None
        content_bottom = content[1] + content[3] if content else None
        d = text_bottom is not None and content_bottom is not None and text_bottom <= content_bottom
        font = float(str(g.get("fontSize", "0")).replace("px", "") or 0)
        ratio = contrast(g.get("color"), g.get("background"))
        e = font >= 13 and ratio >= 4.5
        steps = run.get("steps", [])
        f = bool(steps) and all(x.get("hidden") is False and x.get("text") for x in steps) \
            and len({x["text"] for x in steps}) >= 10
        root_h = g.get("root")
        root_bottom = (50 + root_h) if root_h else None   # the root starts under the 50 px header
        bar_full_width = rect and content and rect[0] == content[0] and rect[2] == content[2]
        bar_at_bottom = rect and root_bottom is not None and abs((rect[1] + rect[3]) - root_bottom) <= 1 \
            and content_bottom is not None and rect[1] + rect[3] <= content_bottom
        leftmost = text_rect[0] is not None and rect and text_rect[0] - rect[0] <= 24 \
            and g.get("elementAtCentre") == "page-status"
        gg = bool(bar_full_width and bar_at_bottom and leftmost)
        lines.append(f"{tag}: (d) text bottom {text_bottom} <= content bottom {content_bottom} -> {'PASS' if d else 'FAIL'}; "
                     f"(e) font {font}px contrast {ratio:.2f} ({g.get('color')} on {g.get('background')}) -> {'PASS' if e else 'FAIL'}; "
                     f"(f) {len(steps)} steps, texts {[x.get('text') for x in steps][:4]}… -> {'PASS' if f else 'FAIL'}; "
                     f"(g) bar rect {rect} content {content} root bottom {root_bottom} text left {text_rect[0]} -> {'PASS' if gg else 'FAIL'}")
        ok &= d and e and f and gg
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k2", type=Path, action="append", default=[])
    parser.add_argument("--k4", type=Path, action="append", default=[])
    parser.add_argument("--red-check", action="store_true", help="run on the 10-14n reports; they must be red")
    args = parser.parse_args()
    lines: list[str] = []
    ok = True
    for d in args.k2:
        for path in sorted(d.glob("report-*.json")):
            ok &= judge_k2(json.loads(path.read_text()), lines)
    for d in args.k4:
        for path in sorted(d.glob("report-*.json")):
            ok &= judge_k4(json.loads(path.read_text()), lines)
    if args.red_check:
        base = Path(__file__).resolve().parent.parent / "host-0.2.20-hand-test"
        red_lines: list[str] = []
        r2 = judge_k2(json.loads((base / "nohost-v20-firefox-owner16630" / "report-nohost-firefox-owner16630.json").read_text()), red_lines)
        # the 10-14n page-number arm that carries the text rect and #content (the PMPC run; the
        # first long60 run predates those reads and is red only for lacking them)
        r4 = judge_k4(json.loads((base / "firefox-owner7340" / "report-host-firefox-owner7340.json").read_text()), red_lines)
        print("\n".join("RED-CHECK " + line for line in red_lines))
        red_ok = (not r2) and (not r4)
        print(f"RED-CHECK verdict: K2 red={not r2} K4 red={not r4} -> {'self-test PASS' if red_ok else 'self-test FAIL'}")
        if not red_ok:
            ok = False
    print("\n".join(lines))
    print("VERDICT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
