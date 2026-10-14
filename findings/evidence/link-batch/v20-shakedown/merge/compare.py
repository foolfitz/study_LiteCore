#!/usr/bin/env python3
"""Descriptive read of the v20 merge shakedown reports against v19's X7 reports and v18's merge shakedown.

Not a judge: it prints, it decides nothing, and its exit code carries no verdict (exit 2 only when an input is
missing or empty, so a vacuous run cannot print "nothing differs").  The runner's own `pass` field is read verbatim.

    python3 compare.py [--v20 DIR] [--browsers chrome firefox] [--self-red]

`--self-red` feeds the v19 report in place of the v20 one and must show the identity block red (profile, page,
worker) -- the script's own red case (CLAUDE.md section 6).
"""
import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVID = HERE.parents[2]                      # findings/evidence
V19 = EVID / "v19" / "x7-counted-m2"
V18 = EVID / "v18" / "merge"
EXPECT = {"profile": "e2-editor-v20",
          "pageSha256": "53019168651b6b4686f1baaba9aa75e0b566d02a3e2cc8a8e8ed4339f360bfd7",
          "workerSha256": "478d0da1dbfcf93615a00025c3c2f9b72c3cfa486d04746f03dea5fcf757b099",
          "runner": "73b2e9ff4b1e6fbe"}


def load(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        print(f"MISSING INPUT {path}")
        sys.exit(2)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("cases"):
        print(f"EMPTY REPORT (no cases) {path}")
        sys.exit(2)
    return data


def shape(case: dict) -> tuple:
    return (case["outcome"], case.get("stage"), case.get("keyPosted"))


def identity(name: str, report: dict) -> list[str]:
    cand = report["candidate"]
    got = {"profile": cand["profile"], "pageSha256": cand["pageSha256"], "workerSha256": cand["workerSha256"],
           "runner": report["runner"]}
    lines = [f"  {name}: counted={report['counted']} mode={report['mode']} browser={report['browser']} "
             f"started={report['startedAt']} completed={report.get('completedAt')}"]
    for key, want in EXPECT.items():
        lines.append(f"    {'ok ' if got[key] == want else 'RED'} {key} {str(got[key])[:16]}"
                     + ("" if got[key] == want else f" (expected {want[:16]})"))
    unbound = sorted(k for k in report["bound"] if report["bound"][k] != (report.get("binding") or {}).get(k))
    lines.append(f"    bound values that differ from BINDING (v19's): {unbound}")
    lines.append(f"    restOfShellEqualsSource={report.get('restOfShellEqualsSource')} "
                 f"teardownError={report.get('teardownError')} observerAtEnd.error="
                 f"{(report.get('observerAtEnd') or {}).get('error')}")
    runner_errors = [c["case"] for c in report["cases"] if c["outcome"] == "runner-error"]
    lines.append(f"    runner-error cases: {runner_errors}; toast '重繪失敗' anywhere: "
                 f"{'重繪失敗' in json.dumps(report, ensure_ascii=False)}")
    return lines


def stats(values: list) -> str:
    values = [v for v in values if v is not None]
    return "n 0" if not values else (f"n {len(values)} min {min(values)} median {statistics.median(values)} "
                                      f"max {max(values)}")


def engine_ms(case: dict):
    ku = case.get("keyUndo") or {}
    return ku.get("keyToUndoMs")


def cases_table(v20: dict, ref: dict, ref_name: str) -> list[str]:
    new, old = collections.defaultdict(list), collections.defaultdict(list)
    for c in v20["cases"]:
        new[c["case"]].append(c)
    for c in ref["cases"]:
        old[c["case"]].append(c)
    out = [f"  v20 {len(v20['cases'])} records ({v20.get('rounds', 'n/a')} rounds) against {ref_name} "
           f"{len(ref['cases'])} records ({ref.get('rounds', 'n/a')} rounds)"]
    same, diff = 0, []
    for case in sorted(set(new) | set(old)):
        a = sorted({shape(c) for c in new.get(case, [])})
        b = sorted({shape(c) for c in old.get(case, [])})
        passes_new = [c["pass"] for c in new.get(case, [])]
        passes_old = [c["pass"] for c in old.get(case, [])]
        if a == b and set(passes_new) == set(passes_old):
            same += 1
        else:
            diff.append((case, a, passes_new, b, passes_old))
    out.append(f"  cases with the same (outcome, stage, keyPosted) and the same pass value: {same}")
    for case, a, pn, b, po in diff:
        out.append(f"  DIFFERS {case}: v20 {a} pass {pn}  |  {ref_name} {b} pass {po}")
    return out


def noop_detail(report: dict) -> list[str]:
    out = []
    for c in report["cases"]:
        if c["case"] in ("C29", "C30"):
            resp = c.get("response") or {}
            bad = sorted(k for k, v in c.get("clauses", {}).items() if v is False)
            out.append(f"  {c['case']} r{c['round']}: outcome {c['outcome']!r} pass {c['pass']} generation "
                       f"{c.get('generation')} keyToResponseMs {c.get('keyToResponseMs')} response "
                       f"{ {k: resp.get(k) for k in ('ok', 'completion', 'code', 'changed')} }")
            out.append(f"      clauses False: {bad}; not established: {c.get('notEstablished')}; "
                       f"toastWindow {c.get('toastWindow')}; reopenedDocument {c.get('reopenedDocument')}")
            if resp.get("boundaryNoop") is not None or c.get("boundaryNoop") is not None:
                out.append(f"      boundaryNoop: {resp.get('boundaryNoop') or c.get('boundaryNoop')}")
    return out


def pair_line(path: Path) -> str:
    if not path.is_file():
        return f"  pair: MISSING {path.name}"
    p = json.loads(path.read_text(encoding="utf-8"))
    return (f"  pair: {p['pairs']} pairs, sameOrder {p['sameOrder']}, differ "
            f"{[(d['case'], d['round'], [k for k, v in d.items() if v is False and k != 'same']) for d in p['differ']]}")


def doc_texts(directory: Path) -> dict:
    sys.path.insert(0, str(EVID.parents[1] / "wasm_sdk_probe" / "tools"))
    from run_merge_wasm_shakedown import odt_parts      # noqa: E402  (read-only import; the runner is not run)
    return {f.name: odt_parts(f.read_bytes())["paragraphs"] for f in sorted(directory.glob("*.odt"))}


def docs_line(v: Path, browser: str, side: str, ref_dir: Path, ref_name: str) -> str:
    a, b = doc_texts(v / f"{side}-{browser}.docs"), doc_texts(ref_dir)
    both = sorted(set(a) & set(b))
    differ = [n for n in both if a[n] != b[n]]
    return (f"  v20 {side} docs {len(a)} vs {ref_name} {len(b)}: both {len(both)}; paragraph text differs in "
            f"{differ or 'none'}; only in v20 {sorted(set(a) - set(b))}; only in {ref_name} {sorted(set(b) - set(a))}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v20", type=Path, default=HERE)
    ap.add_argument("--browsers", nargs="+", default=["chrome", "firefox"])
    ap.add_argument("--self-red", action="store_true")
    args = ap.parse_args()
    for browser in args.browsers:
        print(f"\n## {browser}")
        v = args.v20
        shake = load(v / f"shakedown-{browser}.json")
        if args.self_red:
            shake = load(V19 / f"counted-{browser}.json")
        control = load(v / f"control-{browser}.json")
        m21b, m24 = load(v / f"m2-1b-{browser}.json"), load(v / f"m2-4-{browser}.json")
        print("identity")
        for name, rep in (("shakedown", shake), ("control", control), ("m2-1b", m21b), ("m2-4", m24)):
            for line in identity(name, rep):
                print(line)
        print("shakedown cases against v19's counted run (no frame cell, 3 rounds)")
        v19 = load(V19 / f"counted-{browser}.json")
        for line in cases_table(shake, v19, "v19 counted"):
            print(line)
        print("shakedown cases against v18's shakedown (frame cell, 2 rounds)")
        v18 = load(V18 / f"shakedown-{browser}.json")
        for line in cases_table(shake, v18, "v18 shakedown"):
            print(line)
        print("records whose runner pass is False, v20 shakedown / control / v19 counted / v18 shakedown")
        for name, rep in (("v20 shakedown", shake), ("v20 control", control), ("v19 counted", v19), ("v18 shakedown", v18)):
            print(f"  {name}: {collections.Counter(c['case'] for c in rep['cases'] if not c['pass'])}")
        print("C29 / C30 verbatim (v20 shakedown)")
        for line in noop_detail(shake):
            print(line)
        print(pair_line(v / f"pair-{browser}.stdout.txt"))
        print("latency (listed, not judged)")
        print(f"  v20 shakedown keyToResponseMs {stats([c.get('keyToResponseMs') for c in shake['cases']])}")
        print(f"  v18 shakedown keyToResponseMs {stats([c.get('keyToResponseMs') for c in v18['cases']])}")
        print(f"  v20 shakedown M2-1 engine keyToUndoMs {stats([engine_ms(c) for c in shake['cases'] if c['criterion'] == 'M2-1'])}")
        print(f"  v19 counted   M2-1 engine keyToUndoMs {stats([engine_ms(c) for c in v19['cases'] if c['criterion'] == 'M2-1'])}")
        for label, rep, ref in (("M2-1b", m21b, load(V19 / f"m2-1b-{browser}.json")),):
            print(f"  {label} v20: {len(rep['cases'])} records, pass {sum(c['pass'] for c in rep['cases'])}, "
                  f"outcomes {dict(collections.Counter(c['outcome'] for c in rep['cases']))}, engine {stats([engine_ms(c) for c in rep['cases']])}, "
                  f"runner {stats([c.get('keyToResponseMs') for c in rep['cases']])}")
            print(f"  {label} v19: {len(ref['cases'])} records, pass {sum(c['pass'] for c in ref['cases'])}, "
                  f"engine {stats([engine_ms(c) for c in ref['cases']])}, runner {stats([c.get('keyToResponseMs') for c in ref['cases']])}")
        m4, m4_ref = m24["cases"][0], load(V19 / f"m2-4-{browser}.json")["cases"][0]
        for label, c in (("v20", m4), ("v19", m4_ref)):
            presses = c["presses"]
            print(f"  M2-4 {label}: outcome {c['outcome']} pass {c['pass']} presses {len(presses)}, "
                  f"completions {dict(collections.Counter(p.get('completion') for p in presses))}, "
                  f"engine keyToUndoMs {stats([p.get('keyToUndoMs') for p in presses])}, "
                  f"runner {stats([p.get('keyToResponseMs') for p in presses])}, "
                  f"slow(>=1000ms) {sum(1 for p in presses if (p.get('keyToUndoMs') or 0) >= 1000 or (p.get('keyToResponseMs') or 0) >= 1000)}, "
                  f"toastsAtEnd {c.get('toastsAtEnd')}")
            print(f"      clauses False: {sorted(k for k, v in c['clauses'].items() if v is False)}; "
                  f"not established {c.get('notEstablished')}")
        print("kept documents (paragraph text) against v18's shakedown docs")
        for side in ("shakedown", "control"):
            print(docs_line(v, browser, side, V18 / f"{side}-{browser}.docs", "v18"))
        ps = sorted(v.glob(f"*-{browser}.ps-after.txt.test-browsers"))
        print(f"  test-browser listings after each {browser} step: {len(ps)} files, "
              f"non-empty {[p.name for p in ps if p.stat().st_size]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
