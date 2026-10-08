#!/usr/bin/env python3
"""Copied from ../../v18/w3-w5/judge.py 2026-10-08 for X3 (spec 31.4); changed: the v18 session names -> v19.
Applies spec SPEC-M3-paragraph-merge 28.4 W3 and W5 to recorded sessions (no browser).

  judge.py sessions.json            the v18 run (run.py)
  judge.py --selftest               red cases on committed v17 data: W3 on v17's fc-request session must FAIL;
                                    W5 with v17's committed probe session standing in for v18 must FAIL; with the
                                    control's standing in for v18 it must PASS

W3: on v18 with document A, K1 (family list starting `Noto Sans Mono` and containing `monospace`, fixture phase)
    is answered Noto Sans Mono CJK KR; 21 conf.d files; the log scans the new font path.
W5: instrument = ready, settled, 21 conf.d (22 is v8's, not used here), fixture blocks, a request whose first
    family is each of 細明體, MingLiU, 新細明體, and one of K1's shape (PC-M2a' without Courier New), plus PC-M2b
    (K1's shape answered Liberation Mono on v17 and Noto Sans Mono CJK KR on the control).  Criterion: every
    fixture-phase request whose first family is 細明體 or MingLiU has, on v18, the same answer families as on the
    control (key by family list, language, charset); same band count; every band top within 2 px of the control's.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVID = HERE.parents[1]
NEW_PATH = "/instdir/share/fonts/truetype/NotoSansCJK-Regular-subset-E10.ttc"


def fixture(s):
    return [b for b in s["matchBlocks"] if b["phase"] == "fixture"]


def k1(b):
    return b["askedFamily"][:1] == ["Noto Sans Mono"] and "monospace" in b["askedFamily"]


def answers(s, first):
    out = {}
    for b in fixture(s):
        if b["askedFamily"][:1] and b["askedFamily"][0] in first:
            out.setdefault((tuple(b["askedFamily"]), tuple(b["askedLang"]), b["askedCharset"]), set()).add(
                b["bestFamily"][0] if b["bestFamily"] else None)
    return out


def w3(s, log_text):
    c = []
    got = sorted({b["bestFamily"][0] for b in fixture(s) if k1(b)})
    c.append(("K1 answered Noto Sans Mono CJK KR", got == ["Noto Sans Mono CJK KR"], got))
    c.append(("21 conf.d", len(s["confdLoaded"]) == 21, len(s["confdLoaded"])))
    c.append(("log scans the new font path", f"Scanning file {NEW_PATH}" in log_text, NEW_PATH))
    c.append(("ready and settled", s["boot"] == "ready" and s["state"] == "ready" and not s.get("unsettled"),
              (s["boot"], s["state"], s.get("unsettled"))))
    return c


def alive(s):
    firsts = {b["askedFamily"][0] for b in fixture(s) if b["askedFamily"]}
    ok = (s["boot"] == "ready" and s["state"] == "ready" and not s.get("unsettled")
          and len(s["confdLoaded"]) == 21 and fixture(s)
          and {"細明體", "MingLiU", "新細明體"} <= firsts and any(k1(b) for b in fixture(s)))
    return bool(ok)


def w5(v17, control, v18):
    c = [(f"instrument alive on {s['profile']}", alive(s), None) for s in (v17, control, v18)]
    a17 = sorted({b["bestFamily"][0] for b in fixture(v17) if k1(b)})
    ac = sorted({b["bestFamily"][0] for b in fixture(control) if k1(b)})
    c.append(("PC-M2b: K1 shape Liberation Mono on v17, Noto Sans Mono CJK KR on control",
              a17 == ["Liberation Mono"] and ac == ["Noto Sans Mono CJK KR"], (a17, ac)))
    x, y = answers(v18, {"細明體", "MingLiU"}), answers(control, {"細明體", "MingLiU"})
    diff = sorted((k[0][0], list(k[1]), k[2], sorted(map(str, x.get(k, set()))), sorted(map(str, y.get(k, set()))))
                  for k in set(x) | set(y) if x.get(k) != y.get(k))
    c.append(("細明體/MingLiU answers equal the control's", bool(x) and not diff, diff))
    t18, tc = [r[0] for r in v18.get("runs") or []], [r[0] for r in control.get("runs") or []]
    c.append(("same band count", len(t18) == len(tc), (len(t18), len(tc))))
    c.append(("every band top within 2 px", len(t18) == len(tc) and all(abs(a - b) <= 2 for a, b in zip(t18, tc)),
              [a - b for a, b in zip(t18, tc)]))
    return c


def show(name, clauses):
    ok = all(c[1] for c in clauses)
    print(f"{name}: {'PASS' if ok else 'FAIL'}")
    for label, good, detail in clauses:
        print(f"  {'ok  ' if good else 'MISS'} {label}" + (f": {detail}" if detail is not None else ""))
    return ok


def by(sessions, profile, variant):
    hits = [s for s in sessions if s["profile"] == profile and s["variant"] == variant]
    if len(hits) != 1:
        raise SystemExit(f"expected one {profile} {variant} session, found {len(hits)}")
    return hits[0]


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        fc = EVID / "v17/layout-corpus/fc-request"
        v17a = by(json.loads((fc / "fc-request.json").read_text())["sessions"], "e2-editor-v17", "A")
        probe = json.loads((EVID / "v17/mono-reach/fixed-probe.json").read_text())["sessions"]
        v17p, cp = by(probe, "e2-editor-v17", "P"), by(probe, "e2-editor-v17-cjk-r5-ab", "P")
        r1 = show("red case W3 on v17 (must FAIL)", w3(v17a, (fc / "e2-editor-v17-A-fc-log.txt").read_text()))
        r2 = show("red case W5 with v17 as v18 (must FAIL)", w5(v17p, cp, v17p))
        r3 = show("pass case W5 with control as v18 (must PASS)", w5(v17p, cp, cp))
        e5_line = "Scanning file /instdir/share/fonts/truetype/NotoSansCJK-Regular-subset-E.ttc"
        r4 = e5_line in (fc / "e2-editor-v17-A-fc-log.txt").read_text()
        print(f"pass case for the scan clause: v17's log contains its own e5 path line: {r4}")
        good = not r1 and not r2 and r3 and r4
        print("SELFTEST " + ("PASS" if good else "FAIL"))
        return 0 if good else 1
    path = Path(sys.argv[1])
    sessions = json.loads(path.read_text())["sessions"]
    a = by(sessions, "e2-editor-v19", "A")
    ok3 = show("W3", w3(a, (path.parent / "e2-editor-v19-A-fc-log.txt").read_text()))
    ok5 = show("W5", w5(by(sessions, "e2-editor-v17", "P"), by(sessions, "e2-editor-v17-cjk-r5-ab", "P"),
                        by(sessions, "e2-editor-v19", "P")))
    return 0 if ok3 and ok5 else 1


if __name__ == "__main__":
    sys.exit(main())
