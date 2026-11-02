#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 N1: the Calc style operations on the native bridge (build/calc-style-native), then the saved ODS.

The fixture and the cases are the range population's (create_calc_range_format_fixture).  Writes are one call per case on a fresh
document; the saved ODS is read for fo:color, fo:background-color and fo:text-align; undo is one step.  This script never compiles.
  probe_calc_style_native.py --out DIR
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import run_calc_cell_native as native
from create_calc_range_format_fixture import create, CASES

OPS = {"textColor": (10, "#c00000", "auto"), "backColor": (11, "#ffe599", "none"), "horizontalAlign": (12, "center", "standard")}
ALIGNS = ("left", "center", "right", "block", "standard")
NS = native.NAMES


def request(bounds, operation=6, part=0, value=None):
    c, r, ec, er = bounds
    text = dict(endColumn=ec, endRow=er)
    if value is not None:
        text["value"] = value
    return dict(part=part, column=c, row=r, operation=operation, enabled=0, text=json.dumps(text))


def cell_style(path, part, column, row):
    """The automatic style of one cell, resolved to the three properties."""
    content, cells = native.cells_from_xml(path)
    styles = {s.get(f"{{{NS['s']}}}name"): s for s in content.findall(".//s:style", NS)}
    name = cells[(part, column, row)].get(f"{{{NS['t']}}}style-name")
    style = styles.get(name)
    got = {"name": name}
    if style is None:
        return got
    for tag, key, attr in (("text-properties", "color", "color"), ("table-cell-properties", "background", "background-color"),
                           ("paragraph-properties", "align", "text-align")):
        node = style.find(f"s:{tag}", NS)
        if node is not None and node.get(f"{{{NS['f']}}}{attr}") is not None:
            got[key] = node.get(f"{{{NS['f']}}}{attr}")
    return got


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    native.BUILD = native.ROOT / "wasm_sdk_probe/build/calc-style-native"
    binary = native.BUILD / "calc-cell-native"
    if not binary.is_file():
        raise SystemExit("make build/calc-style-native/calc-cell-native first")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = create(out / "fixture")
    report = {"toolSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "binarySha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "checks": []}

    def check(name, passed, actual):
        report["checks"].append({"id": name, "pass": bool(passed), "actual": actual})

    for case in CASES:
        for key, (operation, value, _) in OPS.items():
            queries = [request(case["bounds"], part=case["part"]), request(case["bounds"], operation, case["part"], value),
                       request(case["bounds"], part=case["part"])]
            before, result, after = native.run(out, f"{case['id']}-{key}", fixture, queries)
            if case["code"]:
                passed = result.get("ok") == "false" and result.get("code") == case["code"] \
                    and result.get("mutationAttempted") == "false" and before == after
            else:
                passed = result.get("ok") == "true" and result.get("changed") == "true" and after.get(key) == value
            check(f"{case['id']}/{key}", passed, {"before": before, "result": result, "after": after})
    # Every property, saved: the cell and a cell outside the range.
    for name, requests, expected in (
            ("color", [request([0, 0, 1, 0], 10, 0, "#c00000")], {"color": "#c00000"}),
            ("fill", [request([0, 0, 1, 0], 11, 0, "#ffe599")], {"background": "#ffe599"}),
            *[(f"align-{a}", [request([0, 0, 1, 0], 12, 0, a)], {"align": {"left": "start", "right": "end", "block": "justify"}.get(a, a)})
              for a in ALIGNS if a != "standard"]):
        saved = out / f"{name}.ods"
        replies = native.run(out, name, fixture, requests + [{"action": "save", "url": saved.as_uri()}])
        inside, outside = cell_style(saved, 0, 1, 0), cell_style(saved, 0, 2, 0)
        check(f"saved/{name}", replies[-1].get("saved") is True and all(inside.get(k) == v for k, v in expected.items())
              and not any(k in outside for k in expected), {"inside": inside, "outside": outside})
    # Mixed, idempotent, back to none, undo one step.
    for key, (operation, value, unset) in OPS.items():
        r = [request([0, 0, 0, 0], operation, 0, value), request([0, 0, 1, 0]), request([0, 0, 1, 0], operation, 0, value),
             request([0, 0, 1, 0], operation, 0, value), request([0, 0, 1, 0], operation, 0, unset), request([0, 0, 1, 0]),
             request([0, 0, 1, 0], operation, 0, value), {"action": "uno", "command": ".uno:Undo"}, request([0, 0, 1, 0])]
        o = native.run(out, "sequence-" + key, fixture, r)
        check("sequence/" + key, o[1].get(key) == "mixed" and o[2].get(key) == value and o[3].get("changed") == "false"
              and o[5].get(key) == unset and o[8].get(key) == unset, o)
    # Closed spellings refused before mutation.
    bad = [(10, "#C00000"), (10, "red"), (10, "#c0000"), (10, "none"), (11, "auto"), (11, "#gggggg"), (12, "repeat"), (12, ""), (10, None)]
    o = native.run(out, "refused", fixture, [request([0, 0, 0, 0], op, 0, v) for op, v in bad])
    check("refused", all(x.get("code") == "INVALID_ARGUMENT" and x.get("mutationAttempted") == "false" for x in o), o)
    limit = native.run(out, "cap", fixture, [request([7, 0, 7, 65536], 11, 0, "#ffe599")])
    check("cap", limit[0].get("code") == "RANGE_TOO_LARGE" and limit[0].get("mutationAttempted") == "false", limit)
    cell = native.run(out, "cell-read", fixture, [request([1, 0, 1, 0], 10, 0, "#c00000"), dict(column=1, row=0, operation=0, enabled=0)])
    check("cell-read", cell[1].get("textColor") == "#c00000" and cell[1].get("backColor") == "none"
          and cell[1].get("horizontalAlign") == "standard", cell)
    report["pass"] = bool(report["checks"]) and all(c["pass"] for c in report["checks"])
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pass": report["pass"], "checks": len(report["checks"]),
                      "red": [c["id"] for c in report["checks"] if not c["pass"]]}))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
