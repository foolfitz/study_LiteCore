#!/usr/bin/env python3
"""SPEC E2-C section 8: derive this round's verdict from the evidence.

Nothing here decides anything new.  The dispositions are in
`e2/validation-matrix-v1.json`, frozen before D0 ran; this reads what was saved
and applies them.  Writing a verdict by hand is how a verdict drifts from its
evidence without anyone noticing, which is what finding 044 records.

Every input is re-derived rather than trusted:

  * the four baseline hashes are recomputed from disk -- three artifact files
    and the shell bundle digest -- and compared with the frozen matrix, because
    a result that names an artifact it did not run on is not evidence
    (finding 027);
  * each phase's verdict is recomputed by that phase's analyzer, not read from
    a summary;
  * the two browsers' comparison projections are compared field by field, using
    the projection the matrix declares.

A phase that has not run is `NOT_RUN`, and a round with any phase not run
cannot reach GO -- said explicitly, so "no failures yet" can never be mistaken
for "passed".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
MATRIX = PROJECT / "e2" / "validation-matrix-v1.json"
EVIDENCE = PROJECT.parent / "findings" / "evidence" / "sdk-e2" / "e2-c-validation"
BROWSERS = ("chrome", "firefox")
PHASES = {
    "D0": ("d0", "tools/analyze_e2_c_d0.py"),
    "D1": ("d1", "tools/analyze_e2_c_d1.py"),
    "D2": ("d2", None),
    "D3": ("d3", None),
    "D4": ("d4", None),
    "D5": ("d5", None),
}


def run_tool(*argv: str) -> tuple[int, dict | None]:
    result = subprocess.run([sys.executable, *argv], cwd=PROJECT,
                            capture_output=True, text=True)
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.returncode, None


def sha256(path: Path) -> str | None:
    import hashlib
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def baseline_problems(matrix: dict) -> list[str]:
    baseline = matrix["baseline"]
    profile = PROJECT / "dist" / "profiles" / baseline["profile"]
    out = []
    for field, name in (("wasmSha256", "probe.wasm"),
                        ("loaderSha256", "probe.js"),
                        ("workerSha256", "sdk-worker.js")):
        if sha256(profile / name) != baseline[field]:
            out.append(f"baseline {field} is not the artifact on disk")
    code, bundle = run_tool("tools/build_e2_c_shell_bundle.py")
    if code != 0 or not bundle:
        out.append("the shell bundle no longer matches the tree")
    elif bundle.get("bundleSha256") != baseline["shellBundleSha256"]:
        out.append("baseline shellBundleSha256 is not the bundle on disk")
    return out


def phase_state(phase: str, matrix: dict) -> dict:
    directory, analyzer = PHASES[phase]
    wasm = matrix["baseline"]["wasmSha256"][:8]
    root = EVIDENCE / directory / f"{matrix['baseline']['profile']}-{wasm}"
    if analyzer is None or not root.is_dir():
        return {"state": "NOT_RUN"}

    per_browser: dict[str, dict] = {}
    failing_cells: set[str] = set()
    problems: list[str] = []
    for browser in BROWSERS:
        evidence = root / browser
        if not (evidence / "result.json").is_file():
            problems.append(f"{phase}: no {browser} result")
            continue
        code, verdict = run_tool(analyzer, str(evidence))
        if verdict is None:
            problems.append(f"{phase}: {browser} analyzer produced no verdict")
            continue
        per_browser[browser] = {"pass": verdict["pass"],
                                "problems": verdict["problems"]}
        failing_cells |= cells_that_failed(verdict)

    if len(per_browser) == len(BROWSERS):
        projections = {}
        for browser in BROWSERS:
            code, value = run_tool(analyzer, str(root / browser), "--projection")
            projections[browser] = value
        if projections["chrome"] != projections["firefox"]:
            problems.append(f"{phase}: the two browsers do not agree cell by cell")

    return {"state": "RUN", "browsers": per_browser,
            "failingCells": sorted(failing_cells), "problems": problems}


def cells_that_failed(verdict: dict) -> set[str]:
    out: set[str] = set()
    for item in verdict.get("cells", {}).items():
        cid, info = item
        if not info.get("pass"):
            out.add(cid)
    for entry in verdict.get("rounds", []):
        for cid, info in entry.get("cells", {}).items():
            if not info.get("pass"):
                out.add(cid)
    return out


def decide(matrix: dict, phases: dict, problems: list[str]) -> dict:
    disposition = {cell["id"]: cell for cell in matrix["cells"]}
    stop_cells, partial_cells, unknown = [], [], []
    for phase, state in phases.items():
        for cid in state.get("failingCells", []):
            spec = disposition.get(cid)
            if spec is None:
                unknown.append(cid)
            elif spec["onFailure"] == "STOP":
                stop_cells.append(cid)
            elif spec["onFailure"] == "PARTIAL":
                partial_cells.append(cid)
    not_run = [phase for phase, state in phases.items()
               if state["state"] == "NOT_RUN"]

    if problems or unknown or stop_cells:
        verdict = "E2_STOP_OR_RESCOPE"
    elif not_run:
        # No failures is not a pass.  A round with phases still to run cannot
        # reach GO, and saying so is the difference between "nothing has gone
        # wrong yet" and "it passed".
        verdict = "NOT_YET"
    elif partial_cells:
        verdict = "E2_PARTIAL_GO_PARAGRAPH_FORMAT"
    else:
        verdict = "E2_GO_PARAGRAPH_FORMAT"
    return {"verdict": verdict, "stopCells": sorted(set(stop_cells)),
            "partialCells": sorted(set(partial_cells)),
            "unknownCells": sorted(set(unknown)), "phasesNotRun": not_run}


def evaluate(matrix: dict) -> dict:
    problems = baseline_problems(matrix)
    phases = {phase: phase_state(phase, matrix) for phase in PHASES}
    for state in phases.values():
        problems += state.get("problems", [])
    outcome = decide(matrix, phases, problems)
    return {
        "schemaVersion": 1,
        "release": "E2-C-paragraph-format-validation",
        "round": 1,
        "matrix": str(MATRIX.relative_to(PROJECT)),
        "baseline": matrix["baseline"],
        "phases": phases,
        "problems": problems,
        **outcome,
    }


SELF_TESTS = [
    ("a matrix that is not the artifact on disk",
     lambda m: m["baseline"].update({"wasmSha256": "0" * 64})),
    ("a stop cell reclassified as partial",
     lambda m: [c.update({"onFailure": "PARTIAL"}) for c in m["cells"]
                if c["id"] == "d1-set-bold-false"]),
]


def self_test() -> int:
    """Two halves: the decision table, and the live evaluation.

    The decision table is exercised directly with synthetic inputs.  The first
    version tried to reach the GO branch by DELETING the failing cells from the
    matrix, which does not simulate them passing -- a cell the matrix does not
    declare is an unknown, and an unknown is a stop.  The tool was right and the
    self-test was wrong, which is the good direction for that to happen in.
    """
    import copy
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    failures = []

    all_run = {phase: {"state": "RUN", "failingCells": []} for phase in PHASES}
    some_run = dict(all_run, D5={"state": "NOT_RUN"})
    table = [
        ("no failures, a phase still to run", some_run, [], "NOT_YET"),
        ("no failures, every phase run", all_run, [], "E2_GO_PARAGRAPH_FORMAT"),
        ("a PARTIAL cell fails, every phase run",
         dict(all_run, D5={"state": "RUN", "failingCells": ["d5-ime-commit"]}),
         [], "E2_PARTIAL_GO_PARAGRAPH_FORMAT"),
        ("a STOP cell fails",
         dict(all_run, D1={"state": "RUN", "failingCells": ["d1-set-bold-false"]}),
         [], "E2_STOP_OR_RESCOPE"),
        ("a cell the matrix never declared",
         dict(all_run, D1={"state": "RUN", "failingCells": ["d1-invented"]}),
         [], "E2_STOP_OR_RESCOPE"),
        ("a baseline problem, nothing else", all_run, ["hash mismatch"],
         "E2_STOP_OR_RESCOPE"),
    ]
    for label, phases, problems, expected in table:
        got = decide(matrix, phases, problems)["verdict"]
        if got != expected:
            failures.append(f"{label}: said {got}, expected {expected}")

    base = evaluate(matrix)
    if base["verdict"] != "E2_STOP_OR_RESCOPE":
        failures.append(f"the round's verdict is {base['verdict']}, expected "
                        f"E2_STOP_OR_RESCOPE from the recorded evidence")
    if not base["stopCells"]:
        failures.append("the round is STOP but no stop cell is named")

    for label, mutate in SELF_TESTS:
        mutated = copy.deepcopy(matrix)
        mutate(mutated)
        after = evaluate(mutated)
        if after["problems"] == base["problems"] \
                and after["stopCells"] == base["stopCells"] \
                and after["partialCells"] == base["partialCells"]:
            failures.append(f"{label}: nothing about the verdict changed")

    print(json.dumps({"selfTest": len(table) + 2 + len(SELF_TESTS),
                      "failures": failures, "pass": not failures},
                     indent=2, ensure_ascii=False))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=EVIDENCE.parent / "e2-c-summary.json")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the verdict without writing the summary")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    summary = evaluate(matrix)
    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["verdict"].endswith("GO_PARAGRAPH_FORMAT") else 1


if __name__ == "__main__":
    sys.exit(main())
