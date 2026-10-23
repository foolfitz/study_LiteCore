#!/usr/bin/env python3
"""Read Phase E artifacts for SPEC-M4-viewer-v3 V3-NR; never run a browser.

The fixed aa576ce7 full-corpus report supplies every actually opened entry.
Each must still open under the existing E2 conditions on v3. Match staged
paths and their indexed case file URLs, not only hashes: the corpus contains
distinct entries with identical bytes. Candidate identity comes from the
archived v3 post-link record. Writes only an explicit --report, if supplied.

  check_ods_viewer_v3_nonregression.py REPORT.json ... [--report PATH]
  check_ods_viewer_v3_nonregression.py --selftest [--report PATH]

Self-test uses a clearly synthetic candidate made from the baseline, then
removes/fails tdf138507, changes an entry's bytes, and gives a wrong wasm ID.
Exit 0: every requested comparison/control passes; 1 otherwise.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from run_ods_viewer_phase_e import judge_e1, judge_e2, sha256_bytes

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "findings/evidence/m4-ods/viewer-v2/160-fix-phase-e/full-corpus/report-2026-10-22T032908Z.json"
IDENTITY = ROOT / "findings/evidence/m4-ods/viewer-v3/post-link/identity.json"
BASELINE_WASM = "aa576ce7bfdad404fdd23c0b7e22c0cbb57c2299515361de7cf9774bd4640c38"


def entries(report: dict) -> dict:
    cases = {}
    for case in report.get("cases", []):
        if case.get("kind") == "corpus":
            cases.setdefault(case.get("file"), []).append(case)
    result = {}
    for i, staged in enumerate(report.get("staged", [])):
        file = f"./ods-e-cases/{i:03d}/{Path(staged['path']).name}"
        matches = cases.get(file, [])
        if staged["path"] in result:
            raise ValueError(f"Duplicate staged path: {staged['path']}")
        result[staged["path"]] = (staged, matches[0] if len(matches) == 1 else None)
    return result


def judge(baseline: dict, candidate: dict, wasm: str) -> dict:
    errors, checks = [], []
    if baseline.get("probeWasmSha256") != BASELINE_WASM or not baseline.get("fullCorpus"):
        errors.append("Baseline must be the pinned aa576ce7 full-corpus report")
    if not all(v["ok"] for v in judge_e1(baseline)):
        errors.append("Baseline E1 does not hold")
    if candidate.get("profile") != "ods-viewer-v3" or candidate.get("probeWasmSha256") != wasm:
        errors.append("Candidate is not the recorded v3 identity")
    old, new = entries(baseline), entries(candidate)
    for path, (before, opened) in old.items():
        if not opened:
            errors.append(f"Baseline case missing or duplicated: {path}")
            continue
        if not opened.get("opened"):
            continue
        current, case = new.get(path, (None, None))
        detail = []
        if not current or not case:
            detail.append("Candidate entry/case missing or duplicated")
        elif current["sha256"] != before["sha256"] or case.get("inputSha256") != before["sha256"]:
            detail.append("Candidate bytes differ from baseline entry")
        else:
            mini = {"staged": [current], "cases": [case],
                    "profileCapabilities": candidate.get("profileCapabilities", [])}
            e2 = next(v for v in judge_e2(mini) if v["id"] == f"E2 {path}")
            if not case.get("opened") or not e2["ok"]:
                detail.append(e2["detail"])
        checks.append({"path": path, "sha256": before["sha256"], "ok": not detail, "detail": detail})
    if not checks:
        errors.append("Baseline supplies no opened entry")
    return {"ok": not errors and all(c["ok"] for c in checks), "errors": errors,
            "requiredEntries": len(checks), "failed": [c for c in checks if not c["ok"]], "checks": checks}


def selftest(baseline: dict, wasm: str) -> dict:
    control = copy.deepcopy(baseline)
    control.update(profile="ods-viewer-v3", probeWasmSha256=wasm)
    target = next(case for entry, case in entries(control).values() if entry["path"] == "upstream/tdf138507.ods")
    tests = [("synthetic-control", control, True)]
    broken = copy.deepcopy(control)
    broken["cases"] = [c for c in broken["cases"] if c.get("file") != target["file"]]
    tests.append(("missing-tdf138507", broken, False))
    broken = copy.deepcopy(control)
    next(c for c in broken["cases"] if c.get("file") == target["file"])["opened"] = None
    tests.append(("tdf138507-does-not-open", broken, False))
    broken = copy.deepcopy(control)
    next(s for s in broken["staged"] if s["path"] == "upstream/tdf138507.ods")["sha256"] = "0" * 64
    tests.append(("changed-entry-bytes", broken, False))
    broken = copy.deepcopy(control)
    broken["probeWasmSha256"] = "0" * 64
    tests.append(("wrong-candidate-identity", broken, False))
    results = {name: {"synthetic": True, "expected": expected, "verdict": judge(baseline, value, wasm)}
               for name, value, expected in tests}
    for result in results.values():
        result["verdict"].pop("checks")
    return {"selftest": True, "ok": all(v["verdict"]["ok"] == v["expected"] for v in results.values()),
            "cases": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="*")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not args.selftest and not args.reports:
        parser.error("Supply candidate report(s) or --selftest")
    baseline = json.loads(BASELINE.read_text())
    wasm = json.loads(IDENTITY.read_text())["files"]["probe.wasm"]["sha256"]
    if args.selftest:
        report = selftest(baseline, wasm)
    else:
        results = {str(path): judge(baseline, json.loads(path.read_text()), wasm) for path in args.reports}
        report = {"ok": all(v["ok"] for v in results.values()), "reports": results}
    report.update(baseline=str(BASELINE), baselineReportSha256=sha256_bytes(BASELINE.read_bytes()),
                  candidateWasmSha256=wasm)
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
