#!/usr/bin/env python3
"""T3's merge reading (SPEC-M3-v29-tick-pacing append 2): every case's `pass`, never `outcome`, on the reports the K wrapper wrote.

  read_merge.py                exit 0 iff MERGE_T3_HOLDS
  read_merge.py --self-test    each clause's mutation of the real reports must be red

Per report: on v29, keyed `ordered-abi6`, bound to binding.json on all nine keys, the unchanged runner, stderr empty, at least
the expected case count, every case `pass` true.  The pair: three pairs, same order, no difference.
"""
import copy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BINDING = json.loads((HERE / "binding.json").read_text())["proposedMergeBinding"]
RUNNER = "aaee0cda5be5ad84"
PROFILE = "e2-editor-v29"
EXPECT = {"full-chrome": ("shakedown", "chrome", 26), "full-firefox": ("shakedown", "firefox", 26),
          "instrumented": ("shakedown", "chrome", 3), "control": ("shakedown", "chrome", 3),
          "m2-4": ("m2-4", "chrome", 1), "m2-1b": ("m2-1b", "firefox", 20)}


def judge(reports, overrides, stderrs, pair):
    problems, rows = [], {}
    for name, (mode, browser, count) in EXPECT.items():
        r, o = reports.get(name) or {}, overrides.get(name) or {}
        cases = r.get("cases") or []
        failed = [f"{c.get('case')}-r{c.get('round')}" for c in cases if c.get("pass") is not True]
        rows[name] = {"cases": len(cases), "passed": len(cases) - len(failed), "failed": failed}
        for ok, what in ((r.get("mode") == mode, "mode"), (r.get("browser") == browser, "browser"),
                         ((r.get("candidate") or {}).get("profile") == PROFILE, "profile"),
                         (r.get("runner") == RUNNER, "runner"), (r.get("binding") == BINDING, "binding"),
                         (r.get("bound") == BINDING, "bound"),
                         ((o.get("keying") or {}).get("table") == "ordered-abi6", "keying"),
                         (len(cases) == count, f"case count {len(cases)} != {count}"), (not failed, f"failed {failed}"),
                         (stderrs.get(name, "x") == "", "stderr")):
            if not ok:
                problems.append(f"{name}: {what}")
    if not (pair.get("pairs") == 3 and pair.get("sameOrder") is True and pair.get("differ") == []):
        problems.append("pair differs")
    return {"verdict": "MERGE_T3_HOLDS" if not problems else "MERGE_T3_RED", "rows": rows, "pair": pair, "problems": problems}


def load():
    reports, overrides, stderrs = {}, {}, {}
    for name in EXPECT:
        path = HERE / f"{name}.json"
        reports[name] = json.loads(path.read_text()) if path.is_file() else {}
        over = path.with_name(path.name + ".binding-override.json")
        overrides[name] = json.loads(over.read_text()) if over.is_file() else {}
        err = HERE / f"{name}-run.stderr.txt"
        stderrs[name] = err.read_text() if err.is_file() else "x"
    pair_path = HERE / "pair.stdout.txt"
    return reports, overrides, stderrs, json.loads(pair_path.read_text()) if pair_path.is_file() else {}


def main():
    reports, overrides, stderrs, pair = load()
    if sys.argv[1:] != ["--self-test"]:
        result = judge(reports, overrides, stderrs, pair)
        print(json.dumps(result, indent=1, ensure_ascii=False))
        return 0 if result["verdict"] == "MERGE_T3_HOLDS" else 1
    if judge(reports, overrides, stderrs, pair)["verdict"] != "MERGE_T3_HOLDS":
        raise SystemExit("self-test needs reports that hold")

    def one_fail(r, o, s, p):
        r = copy.deepcopy(r); r["full-firefox"]["cases"][7]["pass"] = False; return r, o, s, p

    def outcome_only(r, o, s, p):
        r = copy.deepcopy(r); del r["m2-1b"]["cases"][0]["pass"]; return r, o, s, p

    def dropped(r, o, s, p):
        r = copy.deepcopy(r); r["full-chrome"]["cases"].pop(); return r, o, s, p

    def wrong_profile(r, o, s, p):
        r = copy.deepcopy(r); r["control"]["candidate"]["profile"] = "e2-editor-v28"; return r, o, s, p

    def wrong_binding(r, o, s, p):
        r = copy.deepcopy(r); r["m2-4"]["binding"] = dict(r["m2-4"]["binding"], wasmSha256="0" * 64); return r, o, s, p

    def wrong_table(r, o, s, p):
        o = copy.deepcopy(o); o["instrumented"]["keying"]["table"] = "refusal"; return r, o, s, p

    def stderr_noise(r, o, s, p):
        return r, o, dict(s, **{"full-chrome": "Traceback"}), p

    def pair_differs(r, o, s, p):
        return r, o, s, dict(p, differ=[{"case": "C15"}])
    fs = (one_fail, outcome_only, dropped, wrong_profile, wrong_binding, wrong_table, stderr_noise, pair_differs)
    results = {f.__name__: judge(*f(reports, overrides, stderrs, pair))["verdict"] for f in fs}
    red = all(v != "MERGE_T3_HOLDS" for v in results.values())
    print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_HELD", "results": results}, indent=1))
    return 0 if red else 1


if __name__ == "__main__":
    raise SystemExit(main())
