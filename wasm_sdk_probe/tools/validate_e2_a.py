#!/usr/bin/env python3
"""Judge E2-A from the evidence tree against the frozen matrix.

Two rules shape this file.

The matrix is the authority for *how much* was required, not the evidence.  A
validator that iterates over the runs it finds can only ever report on what
happened to run, and a fixture nobody executed then looks the same as one that
passed.  So the required set is expanded from the matrix first and every cell is
resolved to covered or missing.

The document is the authority for *what happened*.  Every postcondition here is
read out of the saved ODT; the completion event says what the engine believed
and is recorded next to it, never in place of it (finding 020).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_e2_discovery import (  # noqa: E402
    A3_ANCHORS,
    EXPECTED_POSTCONDITIONS,
    inspect_target_paragraph,
    judge_postcondition,
)

# A3's positive matrix, in order.  Each entry is one dispatch whose document
# state is judged on its own -- a cycle that ends correctly after a step went
# the wrong way and was corrected is not a pass.
A3_STEPS = ("cycle-list-unordered", "cycle-list-ordered", "cycle-list-none",
            "roundtrip-heading", "roundtrip-body")

# A3 runs the positive matrix; the other two are A5's job and are named here so
# the coverage report can say they are absent rather than omit them.
A3_FIXTURES = ("styled-list", "multi-paragraph", "plain-grapheme")
A5_ONLY_FIXTURES = ("table-boundary",)

COMPLETION = "verified-format-readback"


def attempts(root: Path, browser: str, fixture: str) -> list[Path]:
    base = root / "browser" / browser / fixture
    if not base.is_dir():
        return []
    found = []
    if (base / "result.json").is_file():
        found.append(base)
    found.extend(sorted(path for path in base.glob("attempt-*")
                        if (path / "result.json").is_file()))
    return found


def judge_attempt(path: Path, fixture: str) -> dict[str, Any]:
    result = json.loads((path / "result.json").read_text(encoding="utf-8"))
    dispatch = {entry.get("label"): entry for entry in result.get("dispatch", [])}
    steps: list[dict[str, Any]] = []
    for label in A3_STEPS:
        entry = dispatch.get(label)
        if entry is None:
            steps.append({"label": label, "present": False, "pass": False,
                          "why": "step missing from the run"})
            continue
        completion = (entry.get("result") or {}).get("completion")
        readback = ((entry.get("result") or {}).get("formatBarrier") or {}).get(
            "readback") or {}
        document = path / f"after-{label}.odt"
        inspection = inspect_target_paragraph(document, A3_ANCHORS[fixture])
        verdict = judge_postcondition(label, inspection)
        # `changed` must not be claimed: the readback answers what the document
        # is, not who put it there (SPEC E2-A 2.9).
        claimed_changed = (entry.get("result") or {}).get("changed")
        steps.append({
            "label": label,
            "present": True,
            "completion": completion,
            "completionOk": completion == COMPLETION,
            "changedClaim": claimed_changed,
            "changedNotClaimed": claimed_changed is None,
            "restoreConfirmed": readback.get("restoreConfirmed"),
            "readback": {key: readback.get(key)
                         for key in ("listTag", "blockTag", "bytes")},
            "document": {key: inspection.get(key)
                         for key in ("insideList", "listKind", "listLevel",
                                     "paragraphStyle", "resolvedParagraphStyle")},
            "postcondition": verdict,
            "expected": EXPECTED_POSTCONDITIONS.get(label),
            "pass": bool(
                completion == COMPLETION
                and claimed_changed is None
                and readback.get("restoreConfirmed") is True
                and verdict.get("met") is True),
        })
    return {
        "path": str(path),
        "browser": result.get("browser"),
        "browserVersion": result.get("browserVersion"),
        "profile": result.get("profile"),
        "wasmSha256": (result.get("manifest") or {}).get(
            "diagnostic", {}).get("wasmSha256"),
        "steps": steps,
        "pass": all(step["pass"] for step in steps) and len(steps) == len(A3_STEPS),
    }


def main() -> int:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path,
                        default=project.parent / "findings" / "evidence"
                        / "sdk-e2" / "discovery")
    parser.add_argument("--matrix", type=Path,
                        default=project / "e2" / "discovery-matrix-v1.json")
    parser.add_argument("--output", type=Path,
                        default=project.parent / "findings" / "evidence"
                        / "sdk-e2" / "summary.json")
    args = parser.parse_args()

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    required = matrix["thresholds"]["positiveRepetitionsPerBrowser"]
    browsers = list(matrix["browsers"])

    coverage: dict[str, Any] = {}
    runs: list[dict[str, Any]] = []
    for browser in browsers:
        for fixture in A3_FIXTURES:
            found = attempts(args.evidence_root, browser, fixture)
            judged = [judge_attempt(path, fixture) for path in found]
            runs.extend(judged)
            passing = sum(1 for item in judged if item["pass"])
            coverage[f"{browser}/{fixture}"] = {
                "required": required,
                "found": len(found),
                "passing": passing,
                # Missing is a distinct state from failing, and the verdict has
                # to be able to say which one it is.
                "state": ("missing" if not found else
                          "short" if passing < required else "covered"),
            }

    covered = [key for key, value in coverage.items() if value["state"] == "covered"]
    gaps = {key: value for key, value in coverage.items()
            if value["state"] != "covered"}

    if not covered:
        decision = "A3_NOT_RUN"
    elif gaps:
        decision = "A3_PARTIAL_COVERAGE"
    else:
        decision = "A3_PASS"

    summary = {
        "schemaVersion": 1,
        "release": "E2-A",
        "phase": "A3",
        "decision": decision,
        "matrixStatus": matrix["status"],
        "requiredPerBrowserPerFixture": required,
        "coverage": coverage,
        "coveredCells": covered,
        "gaps": gaps,
        # Named so a reader does not have to infer why table-boundary is absent.
        "fixturesDeferredToA5": list(A5_ONLY_FIXTURES),
        "runs": runs,
        "narrowings": [
            "set-paragraph-body's postcondition is 'not a heading', not 'is Text body':"
            " the serialiser writes <p> for both Text body and the default style"
            " (SPEC E2-A 2.8 narrowing 2). The saved-ODT check here is stricter than"
            " the barrier's -- it compares the resolved paragraph style -- so the two"
            " are recorded separately rather than merged.",
            "The readback markup is a serialiser output, not a documented contract."
            " Matching it whole pins a serialiser; cross-version stability is A7's job"
            " and is not validated here.",
        ],
        "notValidated": [
            "A4 (repeat dispatch) has browser evidence under state-readback/wasm but no"
            " frozen matrix run of its own yet.",
            "A5 negative and boundary cases have not run.",
            "A6 secondary capabilities have not run.",
            "A7 round-trip and regression have not run.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")

    print(f"decision: {decision}")
    print(f"required per browser per fixture: {required}")
    for key, value in coverage.items():
        print(f"   {key:<28} {value['state']:<8} "
              f"found={value['found']} passing={value['passing']}")
    failing = [item for item in runs if not item["pass"]]
    if failing:
        print("\nfailing runs:")
        for item in failing:
            bad = [step["label"] for step in item["steps"] if not step["pass"]]
            print(f"   {item['path']}: {bad}")
    print(f"\nwritten: {args.output}")
    return 0 if decision == "A3_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
