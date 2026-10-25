#!/usr/bin/env python3
"""Run the owner-built native range bridge; this script never compiles."""
import argparse
import hashlib
import json
from pathlib import Path
import run_calc_cell_native as native
from create_calc_range_format_fixture import create, FORMATS, CASES


def request(bounds, operation=6, part=0, enabled=False):
    c, r, ec, er = bounds
    return dict(part=part, column=c, row=r, operation=operation, enabled=int(enabled),
                text=json.dumps(dict(endColumn=ec, endRow=er)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    native.BUILD = native.ROOT / "wasm_sdk_probe/build/calc-range-native"
    binary = native.BUILD / "calc-cell-native"
    if not binary.is_file():
        raise SystemExit("owner build required: make build/calc-range-native/calc-cell-native")
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    fixture = create(out / "fixture")
    report = {"toolSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "binarySha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "checks": []}
    def check(name, passed, actual):
        report["checks"].append({"id": name, "pass": bool(passed), "actual": actual})
    for case in CASES:
        for fmt, operation in FORMATS.items():
            # A fresh document for every case avoids results depending on order.
            queries = [request(case["bounds"], part=case["part"]),
                       request(case["bounds"], operation, case["part"], True),
                       request(case["bounds"], part=case["part"])]
            before, result, after = native.run(out, case["id"] + "-" + fmt, fixture, queries)
            if case["code"]:
                passed = result.get("ok") == "false" and result.get("code") == case["code"] and result.get("mutationAttempted") == "false" and before == after
            else:
                passed = result.get("ok") == "true" and after.get(fmt) == "on"
            check(case["id"] + "/" + fmt, passed, {"before": before, "result": result, "after": after})
    for fmt, operation in FORMATS.items():
        saved = out / (fmt + ".ods")
        observations = native.run(out, "mixed-" + fmt, fixture, [
            dict(column=1, row=1, operation=operation-5, enabled=1),
            request([0, 0, 2, 1]), request([0, 0, 2, 1], operation, enabled=True),
            request([0, 0, 2, 1], operation, enabled=True),
            request([0, 0, 2, 1], operation, enabled=False),
            request([0, 0, 2, 1]), {"action": "save", "url": saved.as_uri()}])
        check("mixed-on-off/" + fmt, observations[1].get(fmt) == "mixed"
              and observations[2].get(fmt) == "on" and observations[3].get("changed") == "false"
              and observations[5].get(fmt) == "off" and observations[6].get("saved") is True, observations)
    limit = native.run(out, "native-cap", fixture, [request([7, 0, 7, 65535]), request([7, 0, 7, 65536], 7, enabled=True)])
    check("native-cap", limit[0].get("ok") == "true" and limit[1].get("code") == "RANGE_TOO_LARGE"
          and limit[1].get("mutationAttempted") == "false", limit)
    wanted = {case["id"] + "/" + fmt for case in CASES for fmt in FORMATS} | {"mixed-on-off/" + fmt for fmt in FORMATS} | {"native-cap"}
    report["pass"] = bool(wanted) and {c["id"] for c in report["checks"]} == wanted and all(c["pass"] for c in report["checks"])
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pass": report["pass"], "checks": len(report["checks"])}))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
