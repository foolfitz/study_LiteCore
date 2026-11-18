#!/usr/bin/env python3
"""Finding 159: judge probe_159.js runs against PREDICTIONS.txt.

Expected outcome of every case is derived, not written by hand:
  core cell (method null)            -> error 0 and the oracle's value
  add-in cell, signature IN_TABLE    -> error 0 and the oracle's value (ROT13: the oracle's string)
  add-in cell, signature ABSENT      -> error 519 (#VALUE!)
  direct call, IN_TABLE              -> returns the value (or string) of its oracle cell
  direct call, ABSENT                -> throws; the exception or one it wraps has the message
                                        "Wasm bridge cannot call virtual function with signature <sig>"
IN_TABLE / ABSENT and <sig> come from the signature TSV given (addin_signatures.py output for the build under test),
so the same reader judges a build whose table has been fixed.

usage: read_159.py <cases.json> <oracle-native.json> <signatures.tsv> <run.json>...
Exit 0 if every case in every run is as expected, 1 if any is not, 2 if the inputs are vacuous (no cases of a kind,
a run with missing rows).
"""
import json
import sys

BRIDGE_MSG = "Wasm bridge cannot call virtual function with signature "


def close(a, b):
    return abs(a - b) <= 1e-9 * max(1.0, abs(b))


def is_text(o):
    """The oracle cell's result is text (ROT13), not a number: value 0 and a string that is not a number."""
    if o["value"] != 0:
        return False
    try:
        float(o["string"])
        return False
    except ValueError:
        return True


def main():
    cases = json.load(open(sys.argv[1]))
    oracle = {c["id"]: c for c in json.load(open(sys.argv[2]))["cells"]}
    sigs = {}
    for line in open(sys.argv[3]):
        iface, name, sig, where = line.rstrip("\n").split("\t")
        sigs[f"{iface}.{name}"] = (sig, where)
    runs = sys.argv[4:]

    def expect_cell(c):
        if c["method"] is None:
            return "core", "value"
        sig, where = sigs[c["method"]]
        return (f"{sig} {where}", "value" if where == "IN_TABLE" else "519")

    kinds = {"core": 0, "IN_TABLE": 0, "ABSENT": 0}
    for c in cases["cells"]:
        k = "core" if c["method"] is None else sigs[c["method"]][1]
        kinds[k] += 1
    dkinds = {"IN_TABLE": 0, "ABSENT": 0}
    for d in cases["direct"]:
        dkinds[sigs[d["method"]][1]] += 1
    print(f"# cases: cells core={kinds['core']} IN_TABLE={kinds['IN_TABLE']} ABSENT={kinds['ABSENT']}; "
          f"direct IN_TABLE={dkinds['IN_TABLE']} ABSENT={dkinds['ABSENT']}; signatures from {sys.argv[3]}")
    vacuous = [k for k, n in kinds.items() if n == 0 and k != "ABSENT"]
    if vacuous or not runs:
        print(f"VACUOUS: no cases of kind {vacuous} or no runs", file=sys.stderr)
        sys.exit(2)

    bad = 0
    for run_path in runs:
        run = json.load(open(run_path))
        rows = {r["id"]: r for r in (run.get("cells") or {}).get("cells", [])}
        direct = {d["id"]: d for d in (run.get("direct") or [])}
        if len(rows) != len(cases["cells"]) or len(direct) != len(cases["direct"]):
            print(f"VACUOUS: {run_path} has {len(rows)} rows and {len(direct)} direct results", file=sys.stderr)
            sys.exit(2)
        print(f"\n## {run_path}  (navigator.language={run.get('navigatorLanguage')})")
        print(f"{'id':4} {'signature':18} {'expect':6} {'typed: err value/string':34} {'API: err value/string':34} ok")
        for c in cases["cells"]:
            label, want = expect_cell(c)
            o = oracle[c["id"]]
            r = rows[c["id"]]
            oks = []
            shown = []
            for path in ("typed", "api"):
                got = r[path]
                if want == "519":
                    ok = got["error"] == 519
                elif is_text(o):
                    ok = got["error"] == 0 and got["string"] == o["string"]
                else:
                    ok = got["error"] == 0 and close(got["value"], o["value"])
                oks.append(ok)
                shown.append(f"{got['error']:>3} {got['string'][:28]!r}")
            ok = all(oks) and r["label"] == c["id"]
            bad += not ok
            print(f"{c['id']:4} {label:18} {want:6} {shown[0]:34} {shown[1]:34} {'yes' if ok else 'NO'}")
        print(f"{'id':4} {'signature':18} {'expect':6} result")
        for d in cases["direct"]:
            sig, where = sigs[d["method"]]
            r = direct[d["id"]]
            if where == "IN_TABLE":
                o = oracle[d["oracle_cell"]]
                res = r.get("result")
                ok = "exception" not in r and (res == o["string"] if isinstance(res, str) else
                                              isinstance(res, (int, float)) and close(res, o["value"]))
                shown = f"returned {res!r}"
            else:
                msgs = []
                e = r.get("exception")
                while e:
                    msgs.append(e.get("message"))
                    e = e.get("target")
                ok = (BRIDGE_MSG + sig) in msgs
                shown = " / ".join(repr(m) for m in msgs) if msgs else f"no exception: {r!r}"
            bad += not ok
            print(f"{d['id']:4} {sig + ' ' + where:18} {'value' if where == 'IN_TABLE' else 'throw':6} {shown}  "
                  f"{'yes' if ok else 'NO'}")
    print(f"\n# not as expected: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
