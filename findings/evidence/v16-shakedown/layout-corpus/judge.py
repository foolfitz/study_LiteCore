#!/usr/bin/env python3
"""Reader for the layout-corpus dry run (PREDICTION.md: L1-L4; spec 21.2 for T).

Re-run in one line (from anywhere):
    python3 findings/evidence/v16-shakedown/layout-corpus/judge.py > findings/evidence/v16-shakedown/layout-corpus/judge-output.txt

It reads only the files the tool wrote (layout-0/1/2-*.json and comparison.json)
and the corpus documents (read-only, to tell "not a zip" from "no content.xml").
It recomputes every pair from the raw per-document `runs`, then cross-checks the
tool's own comparison.json.  Exit code 2 = non-vacuity failure (stop, do not judge).
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                       # repo root (findings/evidence/v16-shakedown/layout-corpus)
PROBE = ROOT / "wasm_sdk_probe"

EXPECT = {"documents": 76, "cjk_gt0": 44, "cjk_eq0": 27, "cjk_none": 5}
PROFILES = ["e2-editor-v16", "e2-editor-v16", "e2-editor-v15"]
MARGIN = 2  # px, spec 21.2 (not measured)


def load():
    files = sorted(HERE.glob("layout-[0-9]-*.json"))
    if len(files) != 3:
        print(f"STOP: expected 3 layout-N-*.json files, found {len(files)}")
        sys.exit(2)
    meas = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    return files, meas, json.loads((HERE / "comparison.json").read_text(encoding="utf-8"))


def tops_diff(x, y):
    """(band counts, max top difference or None if counts differ)."""
    rx, ry = x["runs"], y["runs"]
    if len(rx) != len(ry):
        return (len(rx), len(ry)), None
    return (len(rx), len(ry)), max((abs(p[0] - q[0]) for p, q in zip(rx, ry)), default=0)


def main() -> int:
    files, meas, comparison = load()
    out = []
    p = out.append

    p("== inputs ==")
    for f, m in zip(files, meas):
        p(f"{f.name}: profile={m['profile']} wasm={m['wasm']} boot={m.get('boot')} documents={len(m['documents'])}")
    if [m["profile"] for m in meas] != PROFILES:
        p(f"STOP: profiles {[m['profile'] for m in meas]} != expected {PROFILES}")
        print("\n".join(out)); return 2
    if len({m["wasm"] for m in meas}) != 1:
        p("NOTE: wasm prefix differs between measurements: " + ", ".join(m["wasm"] for m in meas))

    # ---- non-vacuity -------------------------------------------------------
    p("\n== non-vacuity (expected: 76 documents; cjk>0 44, cjk==0 27, None 5, in each measurement) ==")
    bad = False
    for i, m in enumerate(meas):
        d = m["documents"]
        cj = [e.get("cjkCharacters") for e in d.values()]
        got = {"documents": len(d), "cjk_gt0": sum(1 for c in cj if c is not None and c > 0),
               "cjk_eq0": sum(1 for c in cj if c == 0), "cjk_none": sum(1 for c in cj if c is None)}
        ok = got == EXPECT
        bad |= not ok
        p(f"measurement {i} ({m['profile']}): {got} -> {'OK' if ok else 'DIFFERS FROM PREDICTION'}")
    keysets = [set(m["documents"]) for m in meas]
    if not (keysets[0] == keysets[1] == keysets[2]):
        bad = True
        p("document key sets differ between measurements")
    cj_maps = [{k: e.get("cjkCharacters") for k, e in m["documents"].items()} for m in meas]
    if not (cj_maps[0] == cj_maps[1] == cj_maps[2]):
        bad = True
        p("cjkCharacters differs between measurements for the same document")
    if bad:
        p("STOP: counts differ from PREDICTION.md; not adjusting, not judging.")
        print("\n".join(out)); return 2

    keys = sorted(meas[0]["documents"])
    cjk = cj_maps[0]

    # ---- states, unsettled, comparable sets -------------------------------
    p("\n== per-measurement health ==")
    comp = []
    for i, m in enumerate(meas):
        d = m["documents"]
        c = {k for k, e in d.items() if "runs" in e}
        comp.append(c)
        states = {}
        for k, e in d.items():
            states[e.get("state")] = states.get(e.get("state"), 0) + 1
        unsettled = sorted(k for k, e in d.items() if e.get("unsettled"))
        empty = sorted(k for k, e in d.items() if "runs" in e and not e["runs"])
        p(f"measurement {i}: comparable={len(c)} notComparable={len(d) - len(c)} states={states}")
        p(f"  unsettled (canvas never gave two identical reads): {len(unsettled)} {unsettled}")
        p(f"  comparable but zero bands (blank canvas read): {len(empty)} {empty}")
        for k in sorted(set(d) - c):
            e = d[k]
            p(f"  not comparable: {k} state={e.get('state')} toast={e.get('toast')!r} cjk={e.get('cjkCharacters')} reboot={e.get('reboot')}")

    # ---- pairs -------------------------------------------------------------
    def pair(a, b):
        rows = {}
        for k in keys:
            if k in comp[a] and k in comp[b]:
                x, y = meas[a]["documents"][k], meas[b]["documents"][k]
                counts, top = tops_diff(x, y)
                rows[k] = {"counts": counts, "top": top, "identical": x["runs"] == y["runs"],
                           "canvas": [x["canvas"], y["canvas"]]}
        return rows

    P01, P02, P12 = pair(0, 1), pair(0, 2), pair(1, 2)

    # cross-check with the tool's own comparison.json
    p("\n== cross-check against comparison.json (tool's own numbers vs. recomputed) ==")
    for (a, b), rows, tool in (((0, 1), P01, comparison[0]), ((0, 2), P02, comparison[1]), ((1, 2), P12, comparison[2])):
        mine_differ = sorted(k for k, r in rows.items() if not r["identical"])
        tool_differ = sorted(r["document"] for r in tool["differ"])
        tool_nc = sorted(r["document"] for r in tool["notComparable"])
        mine_nc = sorted(set(keys) - (comp[a] & comp[b]))
        same = (tool["profiles"] == [meas[a]["profile"], meas[b]["profile"]] and tool["comparable"] == len(rows)
                and tool["identical"] == sum(r["identical"] for r in rows.values())
                and mine_differ == tool_differ and mine_nc == tool_nc)
        p(f"pair ({a},{b}) {tool['profiles']}: tool comparable={tool['comparable']} identical={tool['identical']} "
          f"differ={len(tool['differ'])} notComparable={len(tool['notComparable'])}; recomputed comparable={len(rows)} "
          f"identical={sum(r['identical'] for r in rows.values())} differ={len(mine_differ)} -> {'AGREE' if same else 'DISAGREE'}")
    if len(comparison) != 3:
        p(f"NOTE: comparison.json has {len(comparison)} pairs, expected 3")

    # ---- L1 ----------------------------------------------------------------
    p("\n== L1: v16 s1 vs v16 s2 (noise) ==")
    count_diff = {k: r for k, r in P01.items() if r["counts"][0] != r["counts"][1]}
    tops = {k: r["top"] for k, r in P01.items() if r["top"] is not None}
    M = max(tops.values(), default=0)
    nonzero = {k: v for k, v in tops.items() if v}
    not_identical = sorted(k for k, r in P01.items() if not r["identical"])
    p(f"comparable documents: {len(P01)}; band count equal: {len(P01) - len(count_diff)}; band count different: {len(count_diff)}")
    for k, r in sorted(count_diff.items()):
        p(f"  band count differs: {k} {r['counts']}")
    p(f"max top-edge difference M = {M} px (over documents with equal band count: {len(tops)})")
    for k, v in sorted(nonzero.items(), key=lambda kv: -kv[1]):
        p(f"  top diff {v:>4} px: {k} (cjk={cjk[k]})")
    p(f"documents with runs != runs (tops or bottoms): {len(not_identical)}")
    extra = [k for k in not_identical if k not in nonzero and k not in count_diff]
    for k in extra:
        p(f"  tops equal but a band bottom differs: {k}")
    L1 = (not count_diff) and M == 0 and not not_identical
    T = M + MARGIN
    p(f"L1 {'HIT' if L1 else 'MISS'} (prediction: every comparable document identical, maxTopDifference 0, same band count)")
    p(f"T = M + {MARGIN} = {T} px")
    if count_diff:
        p("NOTE: band-count differences in the noise pair; M covers only documents with equal band counts.")

    # ---- L2 / L3 -----------------------------------------------------------
    def red(rows, label):
        hits, near = [], []
        for k, r in sorted(rows.items()):
            if not (cjk[k] and cjk[k] > 0):
                continue
            if r["top"] is None:
                hits.append((k, f"band count {r['counts'][0]} vs {r['counts'][1]}", float("inf")))
            elif r["top"] > T:
                hits.append((k, f"max top diff {r['top']} px, band count {r['counts'][0]} vs {r['counts'][1]}", r["top"]))
            elif r["top"] > 0 or not r["identical"]:
                near.append((k, r["top"]))
        hits.sort(key=lambda h: -h[2])
        p(f"{label}: cjk>0 comparable documents: {sum(1 for k in rows if cjk[k] and cjk[k] > 0)}; differ by > T={T} or band count: {len(hits)}")
        for k, why, _ in hits:
            p(f"  {k} cjk={cjk[k]} {why}")
        if near:
            p(f"  (cjk>0 documents that differ but within T: {len(near)}: " + ", ".join(f'{k}={v}' for k, v in near) + ")")
        return hits

    p("\n== L2: cjkCharacters > 0, v16 vs v15 ==")
    h1 = red(P02, "(v16 s1, v15)")
    h2 = red(P12, "(v16 s2, v15)")
    L2 = bool(h1) and bool(h2)
    p(f"L2 {'HIT' if L2 else 'MISS'} (prediction: at least one document in each pair)")

    p("\n== L3: cjkCharacters == 0, v16 vs v15 ==")
    L3_list = []
    for label, rows in (("(v16 s1, v15)", P02), ("(v16 s2, v15)", P12)):
        z = {k: r for k, r in rows.items() if cjk[k] == 0}
        diff = {k: r for k, r in z.items() if not r["identical"]}
        p(f"{label}: cjk==0 comparable documents: {len(z)}; differ at all (runs != runs): {len(diff)}")
        for k, r in sorted(diff.items()):
            p(f"  {k} counts={r['counts']} maxTopDifference={r['top']} canvas={r['canvas']}")
            L3_list.append((label, k))
    L3 = not L3_list
    p(f"L3 {'HIT' if L3 else 'MISS'} (prediction: every cjk==0 document identical in both pairs)")

    # ---- L4 ----------------------------------------------------------------
    p("\n== L4: not-comparable sets ==")
    ncs = [sorted(set(keys) - comp[i]) for i in range(3)]
    for i, nc in enumerate(ncs):
        p(f"measurement {i}: {len(nc)} not comparable: {nc}")
    same = ncs[0] == ncs[1] == ncs[2]
    nonzip, nocontent = [], []
    for k in keys:
        if cjk[k] is None:
            path = PROBE / k
            (nonzip if not zipfile.is_zipfile(path) else nocontent).append(k)
    p(f"cjkCharacters is None: {len(nonzip) + len(nocontent)}; of which not a zip file: {len(nonzip)} {nonzip}; "
      f"zip without readable content.xml: {len(nocontent)} {nocontent}")
    includes = all(k in ncs[0] for k in nonzip) and len(nonzip) == 3
    extra_nc = sorted(set(ncs[0]) - set(nonzip) - set(nocontent))
    missing_none = sorted((set(nonzip) | set(nocontent)) - set(ncs[0]))
    p(f"not-comparable beyond the cjk-None documents (documents that failed to open): {extra_nc}")
    p(f"cjk-None documents that nevertheless measured: {missing_none}")
    L4 = same and includes
    p(f"L4 {'HIT' if L4 else 'MISS'} (prediction: identical in all three and includes the three non-zip documents; identical={same}, includes 3 non-zip={includes})")

    # ---- coverage: how many comparisons actually had ink to compare --------
    p("\n== coverage (a pair of blank reads is 'identical' too; this section counts how many comparisons saw ink) ==")
    for label, rows, a, b in (("(v16 s1, v16 s2)", P01, 0, 1), ("(v16 s1, v15)", P02, 0, 2), ("(v16 s2, v15)", P12, 1, 2)):
        def inked(k):
            return bool(meas[a]["documents"][k]["runs"]) and bool(meas[b]["documents"][k]["runs"])
        def blank_both(k):
            return not meas[a]["documents"][k]["runs"] and not meas[b]["documents"][k]["runs"]
        classes = (("cjk>0", lambda k: cjk[k] is not None and cjk[k] > 0), ("cjk==0", lambda k: cjk[k] == 0),
                   ("cjk None (opened)", lambda k: cjk[k] is None))
        for cname, pred in classes:
            ks = [k for k in rows if pred(k)]
            p(f"{label} {cname}: comparable {len(ks)}; both measurements have bands {sum(inked(k) for k in ks)}; "
              f"both blank (zero bands) {sum(blank_both(k) for k in ks)}; one blank one not {sum((not inked(k)) and (not blank_both(k)) for k in ks)}")
    allblank = sorted(k for k in P01 if all(not m["documents"][k]["runs"] for m in meas))
    p(f"documents with zero bands in all three measurements: {len(allblank)} (cjk>0: {sum(1 for k in allblank if cjk[k])}, cjk==0: {sum(1 for k in allblank if cjk[k] == 0)}, None: {sum(1 for k in allblank if cjk[k] is None)})")
    p("page-edge detection result (page field) for those: " + str(sorted({tuple(meas[0]['documents'][k]['page']) for k in allblank})))
    inked01 = {k: r["top"] for k, r in P01.items() if meas[0]["documents"][k]["runs"]}
    p(f"L1 restricted to documents that have bands: {len(inked01)} documents, max top diff {max(inked01.values(), default=0)} px")
    cdiff = [(k, meas[0]["documents"][k]["canvas"][1], meas[1]["documents"][k]["canvas"][1]) for k in P01
             if meas[0]["documents"][k]["canvas"] != meas[1]["documents"][k]["canvas"]]
    p(f"canvas size differs between the two v16 sessions for {len(cdiff)} documents (height s1 vs s2): " + ", ".join(f"{k.split('/')[-1]}={x}/{y}" for k, x, y in cdiff))
    p("(canvas size is not part of the 21.2 criterion; reported as observed)")

    # ---- summary -----------------------------------------------------------
    p("\n== verdict ==")
    p(f"L1 {'HIT' if L1 else 'MISS'}; L2 {'HIT' if L2 else 'MISS'}; L3 {'HIT' if L3 else 'MISS'}; L4 {'HIT' if L4 else 'MISS'}; M={M} px; T={T} px")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
