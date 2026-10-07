#!/usr/bin/env python3
"""M2 of PREDICTION.md: the fixed-pitch probe on v17, the control and v8, one cold Chrome session each, one at a time.

Uses ../layout-corpus/fc-request/run.py's own `one_session` (same page, loader edit, band and Match-block readings),
with that module's DOCS/EXPECTED/HERE pointed at this probe and this directory for the call (module globals, set
before any session).  Writes fixed-probe.json, <profile>-P-fc-log.txt and summary-fixed.txt beside this file.  It
prints facts; the readings are applied in RESULT.md.
"""
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fcreq", HERE.parent / "layout-corpus/fc-request/run.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

PROBE_DOC = m.PROBE / "build/mono-reach-probe/fixed-pitch-probe.odt"
EXPECTED = (HERE / "probe.sha256").read_text().split()[0]
m.DOCS, m.EXPECTED, m.HERE = {"P": PROBE_DOC}, {"P": EXPECTED}, HERE
PROFILES = ("e2-editor-v17", "e2-editor-v17-cjk-r5-ab", "e2-editor-v8")
FIRST = ("細明體", "MingLiU", "新細明體", "Courier New", "Liberation Serif")


def target(block: dict) -> str | None:
    f = block["askedFamily"]
    if f[:1] and f[0] in FIRST:
        return f[0]
    if f[:1] == ["Noto Sans Mono"] and "monospace" in f:
        return "K1-shape"
    return None


def main() -> int:
    report = {"startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "runFixedSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "runSha256": hashlib.sha256((HERE.parent / "layout-corpus/fc-request/run.py").read_bytes()).hexdigest()}
    sessions = {p: m.one_session(p, "P") for p in PROFILES}
    report["sessions"] = list(sessions.values())
    report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (HERE / "fixed-probe.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = summarize(sessions)
    (HERE / "summary-fixed.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


def summarize(sessions: dict) -> list[str]:
    lines = []
    for p, r in sessions.items():
        runs = r.get("runs") or []
        lines.append(f"{p}: boot {r['boot']} state {r['state']} confd {len(r['confdLoaded'])} "
                     f"fixture blocks {sum(1 for b in r['matchBlocks'] if b['phase'] == 'fixture')} "
                     f"bands {len(runs)} unsettled {r.get('unsettled')} tops {[x[0] for x in runs]}")
    tops = {p: [x[0] for x in (r.get("runs") or [])] for p, r in sessions.items()}
    for a, b in (("e2-editor-v17", "e2-editor-v17-cjk-r5-ab"), ("e2-editor-v8", "e2-editor-v17-cjk-r5-ab")):
        d = [x - y for x, y in zip(tops[a], tops[b])] if len(tops[a]) == len(tops[b]) else None
        lines.append(f"tops {a} minus {b}: {d}")
    for p, r in sessions.items():
        lines.append(f"{p} requests by first family (fixture phase):")
        for b in r["matchBlocks"]:
            t = target(b)
            if b["phase"] == "fixture" and t:
                lines.append(f"  {t}: lang {b['askedLang']} charset {b['askedCharset']} "
                             f"monospace-in-list {'monospace' in b['askedFamily']} -> {m.answer(b)[0]}")
    cens = {p: {k: v for k, v in m.census(r).items() if target({"askedFamily": list(k[0])})}
            for p, r in sessions.items()}
    x, y = cens["e2-editor-v17"], cens["e2-editor-v17-cjk-r5-ab"]
    lines.append(f"v17 vs control on the targeted requests: shared {len(set(x) & set(y))}, "
                 f"only v17 {len(set(x) - set(y))}, only control {len(set(y) - set(x))}")
    for k in sorted(set(x) | set(y)):
        fx, fy = sorted({a[0] for a in x.get(k, [])}), sorted({a[0] for a in y.get(k, [])})
        mark = "SAME" if fx == fy else "DIFF"
        lines.append(f"  {mark} {target({'askedFamily': list(k[0])})} lang {list(k[1])} charset {k[2]}: "
                     f"v17 {fx} control {fy}")
    return lines


if __name__ == "__main__":
    sys.exit(main())
