#!/usr/bin/env python3
"""Reader for the COUNTED corpus layout comparison, spec 21.2 as amended by 27 (v17 vs v17-cjk-r5-ab, 26.3 V6).

Re-run in one line (from anywhere):
    python3 findings/evidence/v17/layout-corpus/judge.py > findings/evidence/v17/layout-corpus/judge-output.txt

Self-test (red cases), reading other files:
    python3 judge.py --files A.json B.json --profiles P Q [--no-comparison]

It reads only the two layout-N-*.json files the tool wrote and (when present) comparison.json. It writes nothing.

Criterion, per document (21.2 / 27.1 / 27.2):
  - not comparable (no `runs` key: the document did not open) -> the not-comparable sets of the two arms must be identical;
  - not measured (zero bands, or `unsettled`, in EITHER arm) -> neither "equal" nor "different"; the per-arm
    not-measured sets must be identical (an arm that draws where the other does not is a difference);
  - measured (comparable in both, measured in both) -> same band count and every band top differs by <= T = 2 px.
The verdict is PASS only if all three hold and at least one document was measured; the number measured is printed.
Exit codes: 0 PASS, 1 RED, 2 STOP (inputs not what this reader expects; nothing judged).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = 2  # px, spec 27.1 (M = 0 measured + 2) and 27.3 (carried to v17)
PROFILES = ["e2-editor-v17", "e2-editor-v17-cjk-r5-ab"]
DOCUMENTS = 76  # the corpus, spec 21.2
# Spec 27.3: if the not-measured set differs from the dry run's, look at the instrument first.
DRY_RUN = HERE.parent.parent / "v16-shakedown" / "layout-corpus" / "layout-0-e2-editor-v16.json"


def not_measured(entry: dict) -> bool:
    return (not entry["runs"]) or bool(entry.get("unsettled"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs=2, type=Path, default=None)
    ap.add_argument("--profiles", nargs=2, default=PROFILES)
    ap.add_argument("--no-comparison", action="store_true", help="skip the cross-check against comparison.json")
    a = ap.parse_args()
    out: list[str] = []
    p = out.append

    def stop(why: str) -> int:
        p("STOP: " + why + " Not judging.")
        print("\n".join(out))
        return 2

    files = a.files or sorted(HERE.glob("layout-[0-9]-*.json"))
    if len(files) != 2:
        return stop(f"expected 2 layout-N-*.json files, found {len(files)}.")
    meas = [json.loads(Path(f).read_text(encoding="utf-8")) for f in files]
    p("== inputs ==")
    for f, m in zip(files, meas):
        p(f"{Path(f).name}: profile={m['profile']} wasm={m['wasm']} boot={m.get('boot')} documents={len(m['documents'])}")
    if [m["profile"] for m in meas] != list(a.profiles):
        return stop(f"profiles {[m['profile'] for m in meas]} != expected {list(a.profiles)}.")
    if any(m.get("boot") != "ready" for m in meas):
        return stop("a measurement did not boot to `ready`.")
    if len({m["wasm"] for m in meas}) != 1:
        p("NOTE: wasm prefix differs between the arms: " + ", ".join(m["wasm"] for m in meas))
    d0, d1 = (m["documents"] for m in meas)
    if set(d0) != set(d1) or len(d0) != DOCUMENTS:
        return stop(f"document sets differ or are not {DOCUMENTS} ({len(d0)}, {len(d1)}).")
    if any(d0[k].get("cjkCharacters") != d1[k].get("cjkCharacters") for k in d0):
        return stop("cjkCharacters differs between the arms for the same document (the corpus changed?).")
    keys = sorted(d0)

    red: list[str] = []

    # ---- not comparable (21.2) -------------------------------------------------------------------
    nc = [{k for k in keys if "runs" not in d[k]} for d in (d0, d1)]
    p(f"\n== not comparable (did not open): arm0 {len(nc[0])}, arm1 {len(nc[1])} ==")
    for k in sorted(nc[0] | nc[1]):
        p(f"  {k}: arm0 {'NC' if k in nc[0] else 'ok'} state={d0[k].get('state')!r}; "
          f"arm1 {'NC' if k in nc[1] else 'ok'} state={d1[k].get('state')!r}")
    if nc[0] != nc[1]:
        red.append(f"not-comparable sets differ: only arm0 {sorted(nc[0] - nc[1])}, only arm1 {sorted(nc[1] - nc[0])}")
    comparable = [k for k in keys if k not in nc[0] and k not in nc[1]]

    # ---- not measured (27.2) ---------------------------------------------------------------------
    nm = [{k for k in comparable if not_measured(d[k])} for d in (d0, d1)]
    p(f"\n== not measured (zero bands or unsettled): arm0 {len(nm[0])}, arm1 {len(nm[1])} ==")
    for k in sorted(nm[0] | nm[1]):
        def why(e):
            return ("zero bands" if not e["runs"] else "") + (" unsettled" if e.get("unsettled") else "")
        p(f"  {k}: arm0 [{why(d0[k]).strip() or 'measured'}] arm1 [{why(d1[k]).strip() or 'measured'}]")
    if nm[0] != nm[1]:
        red.append(f"not-measured sets differ: only arm0 {sorted(nm[0] - nm[1])}, only arm1 {sorted(nm[1] - nm[0])}")
    if DRY_RUN.is_file():
        dry = json.loads(DRY_RUN.read_text(encoding="utf-8"))["documents"]
        dry_nm = {k for k, e in dry.items() if "runs" in e and not_measured(e)}
        here = nm[0] | nm[1]
        p(f"spec 27.3 note: dry run (v16, measurement 0) not measured {len(dry_nm)}; this run {len(here)}; "
          f"same set: {dry_nm == here}"
          + ("" if dry_nm == here else f" (only dry run {sorted(dry_nm - here)}, only here {sorted(here - dry_nm)})"))

    # ---- measured (21.2) -------------------------------------------------------------------------
    measured = [k for k in comparable if k not in nm[0] and k not in nm[1]]
    rows = []
    for k in measured:
        r0, r1 = d0[k]["runs"], d1[k]["runs"]
        if len(r0) != len(r1):
            rows.append((k, len(r0), len(r1), None, False))
            continue
        top = max(abs(x[0] - y[0]) for x, y in zip(r0, r1))
        rows.append((k, len(r0), len(r1), top, top <= T))
    over = [r for r in rows if not r[4]]
    cjk_measured = sum(1 for k in measured if (d0[k].get("cjkCharacters") or 0) > 0)
    p(f"\n== measured: {len(measured)} documents ({cjk_measured} with CJK characters) ==")
    p(f"band count equal: {sum(1 for r in rows if r[1] == r[2])}; max top difference over all measured: "
      f"{max((r[3] for r in rows if r[3] is not None), default=None)} px; over T={T}: {len(over)}")
    for k, n0, n1, top, ok in sorted(rows, key=lambda r: (r[4], -(r[3] or 10**6))):
        if not ok or top:
            p(f"  {'RED ' if not ok else 'ok  '} {k}: bands {n0}/{n1} maxTop={top} cjk={d0[k].get('cjkCharacters')}")
    for k, n0, n1, top, ok in over:
        red.append(f"{k}: bands {n0}/{n1}, max top difference {top} px (T={T})")
    if not measured:
        red.append("no document was measured (the criterion would hold vacuously)")

    # ---- cross-check with the tool's own comparison.json ----------------------------------------
    cmp_path = HERE / "comparison.json"
    if not a.no_comparison and a.files is None:
        if not cmp_path.is_file():
            return stop("comparison.json is missing.")
        tool = json.loads(cmp_path.read_text(encoding="utf-8"))
        if len(tool) != 1 or tool[0]["profiles"] != list(a.profiles):
            return stop(f"comparison.json has {len(tool)} pairs / profiles {[t['profiles'] for t in tool]}.")
        tool = tool[0]
        mine_identical = sum(1 for k in comparable if d0[k]["runs"] == d1[k]["runs"])
        tool_nc = sorted(r["document"] for r in tool["notComparable"])
        agree = (tool["comparable"] == len(comparable) and tool["identical"] == mine_identical
                 and tool_nc == sorted(set(keys) - set(comparable)))
        p(f"\n== cross-check: tool comparable={tool['comparable']} identical={tool['identical']} "
          f"notComparable={len(tool_nc)}; recomputed comparable={len(comparable)} identical={mine_identical} -> "
          f"{'AGREE' if agree else 'DISAGREE'} ==")
        if not agree:
            return stop("this reader and the tool disagree on the raw counts.")

    p("\n== verdict (spec 21.2 / 27) ==")
    p(f"documents {DOCUMENTS}; not comparable {len(nc[0] | nc[1])}; not measured {len(nm[0] | nm[1])}; "
      f"measured {len(measured)}")
    for r in red:
        p("  RED: " + r)
    p("VERDICT: " + ("PASS" if not red else "RED"))
    print("\n".join(out))
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main())
