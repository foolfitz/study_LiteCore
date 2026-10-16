#!/usr/bin/env python3
"""Item 1's populations, generated from the committed native evidence (ARMS-item1.md D1, D4, D7, R-xlc).

  D1     d1_population.classify(N142/out/arms.json): the IN arms and their d1Script / noCtrlScript;
         the two controls of d1-marker/out/runs.json
  D4     the IN arms whose script has a range step `s<a>:<b>`
  D7     every Ctrl press of every IN arm, classed from the native raw press records
         N142/out/<arm>/r{1,2,3}.jsonl: "cursor" if its callbacks include INVALIDATE_VISIBLE_CURSOR,
         "silent" if it had no callback.  The three rounds must agree; a press in neither class
         (callbacks, none a cursor) makes the tool red
  R-xlc  the arms of group "x-lc" with a Backspace press (x-indent-home, a D1 arm, has none)

  v21_item1_population.py            prints the populations as JSON
  v21_item1_population.py --self-test   the red cases (exit 1 if any is not red)
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v21_item1_marker as marker  # noqa: E402

N142 = marker.N142
CURSOR = "LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR"


class PopulationRed(ValueError):
    pass


def press_records(arm: str, round_no: int, root: Path = N142 / "out") -> list[dict]:
    path = root / arm / f"r{round_no}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if '"rec":"press"' in line]


def press_class(record: dict) -> str:
    types = [c.get("type") for c in record.get("callbacks") or []]
    if CURSOR in types:
        return "cursor"
    if not record.get("nCallbacks"):
        return "silent"
    raise PopulationRed(f"press {record.get('label')} has callbacks {types[:6]} but no cursor callback")


def d7_population(ins: list[dict], reader=press_records) -> list[dict]:
    out = []
    for arm in ins:
        rounds = []
        for r in (1, 2, 3):
            rounds.append([(p["label"], p["codes"], press_class(p)) for p in reader(arm["name"], r)])
        if any(r != rounds[0] for r in rounds):
            raise PopulationRed(f"{arm['name']}: native rounds disagree on the presses")
        ctrl = [(label, codes, cls) for label, codes, cls in rounds[0] if codes and codes[0] in (9220, 9221)]
        if len(ctrl) != arm["nCtrlPresses"]:
            raise PopulationRed(f"{arm['name']}: {len(ctrl)} Ctrl press records, script has {arm['nCtrlPresses']}")
        for index, (label, codes, cls) in enumerate(ctrl):
            out.append({"arm": arm["name"], "press": index, "label": label, "code": codes[0], "class": cls})
    if not out:
        raise PopulationRed("zero presses")
    return out


def populations(arms: list[dict] | None = None, reader=press_records) -> dict:
    arms = arms if arms is not None else json.loads((N142 / "out/arms.json").read_text())
    if not arms:
        raise PopulationRed("the arm table is empty")
    ins, outs, errors = marker.d1_population.classify(arms)
    if errors:
        raise PopulationRed(f"d1_population: {errors}")
    if not ins:
        raise PopulationRed("zero arms IN")
    runs = json.loads((marker.D1M / "out/runs.json").read_text())
    controls = [r for r in runs if r.get("role") == "control"]
    by_name = {a["name"]: a for a in ins}
    for control in controls:
        if by_name.get(control["pairedWith"], {}).get("noCtrlScript") != control["script"]:
            raise PopulationRed(f"control {control['name']} is not the no-Ctrl variant of {control['pairedWith']}")
    d4 = [a["name"] for a in ins if any(step.startswith("s") for step in a["d1Script"].split(","))]
    # R-xlc is "Backspace after Ctrl+Home" (ARMS-item1.md R-xlc names three arms): group x-lc AND a
    # Backspace press.  Group x-lc alone also holds x-indent-home, which is a D1 arm with no Backspace.
    xlc = [a["name"] for a in arms if a.get("group") == "x-lc"
           and any(step.startswith("Mbksp=") for step in a["script"].split(","))]
    if not d4 or not xlc:
        raise PopulationRed(f"empty sub-population: D4 {len(d4)}, x-lc {len(xlc)}")
    d7 = d7_population(ins, reader)
    return {"d1": ins, "controls": controls, "d4": d4, "d7": d7, "xlc": xlc,
            "counts": {"d1": len(ins), "out": len(outs), "d4": len(d4), "xlc": len(xlc), "d7": len(d7),
                       "d7Cursor": sum(1 for p in d7 if p["class"] == "cursor"),
                       "d7Silent": sum(1 for p in d7 if p["class"] == "silent")}}


def self_test() -> int:
    results = []
    real = populations()
    expected = {"d1": 38, "out": 43, "d4": 6, "xlc": 3, "d7": 64, "d7Cursor": 50, "d7Silent": 14}
    green = real["counts"] == expected
    print(f"green  populations {real['counts']} == ARMS-item1 {expected}: {green}")
    arms = json.loads((N142 / "out/arms.json").read_text())

    def red(name, fn):
        try:
            fn()
            results.append((name, False))
            print(f"NOT RED  {name}")
        except PopulationRed as error:
            results.append((name, True))
            print(f"RED ok   {name}: {str(error)[:100]}")

    def unknown_step():
        a = copy.deepcopy(arms)
        a[0]["script"] += ",X9"
        try:
            populations(a)
        except PopulationRed:
            raise
    red("unknown step kind", unknown_step)
    red("zero arms IN", lambda: populations([a for a in arms if not a["name"].startswith(("a", "t", "r-", "sec", "x-indent-home"))]))
    red("empty arm table", lambda: populations([]))

    def no_cursor(arm, r):
        recs = press_records(arm, r)
        if arm == "a1-home-mid":
            recs = copy.deepcopy(recs)
            recs[0]["callbacks"] = [{"type": "LOK_CALLBACK_STATE_CHANGED"}]
            recs[0]["nCallbacks"] = 1
        return recs
    red("a press with only STATE_CHANGED", lambda: populations(reader=no_cursor))

    def disagree(arm, r):
        recs = press_records(arm, r)
        if arm == "a3-home-twice" and r == 2:
            recs = copy.deepcopy(recs)
            recs[1]["callbacks"] = [{"type": CURSOR}]
            recs[1]["nCallbacks"] = 1
        return recs
    red("native rounds disagree", lambda: populations(reader=disagree))
    # Non-vacuity of the generation: a fictional arm with only product steps joins D1 (and D4) unedited.
    fictional = copy.deepcopy(arms) + [{"name": "r-fictional", "fixture": "plain3", "group": "6",
                                        "script": "k1024,k1027x2,rpa,k1027x2,rpb,spa:pb,Mch=9220,L"}]
    ins, _, errors = marker.d1_population.classify(fictional)
    joined = any(a["name"] == "r-fictional" for a in ins)
    print(f"green  a fictional product-only range arm joins D1 without an edit: {joined}")
    bad = [n for n, ok in results if not ok]
    print(f"self-test: {len(results) - len(bad)}/{len(results)} red as required" + (f"; NOT RED: {bad}" if bad else ""))
    return 1 if bad or not green or not joined or errors else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    p = populations()
    print(json.dumps({k: p[k] for k in ("counts", "d4", "xlc")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
