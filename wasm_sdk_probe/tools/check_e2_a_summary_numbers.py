#!/usr/bin/env python3
"""Does SPEC-E2-A's summary table still quote the artifact it claims to?

The A3/A4/A5 rows of section 10.10 were written when the evidence was bound to
25761ff0, kept through two rebinds, and read on 2026-08-13 as if they described
the current artifact.  Two of the three were wrong by then -- A3 had accumulated
more bound runs, A5 fewer -- and nothing in the tree could notice, because the
numbers live in prose and the counts live in JSON.

This recomputes the counts from summary.json, restricted to the artifact the
summary itself calls current, and compares them with the table.  It is not a
style check: a stale number here is a verdict quoting a build it was not
measured on, which is exactly what finding 027 is about.

  --self-test  perturbs each parsed row in turn and requires the comparison to
               report that row as a mismatch.  A checker that cannot fail has
               not checked anything.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
SPEC = PROJECT / "specs" / "SPEC-E2-A-paragraph-format-discovery.md"
SUMMARY = PROJECT / "findings" / "evidence" / "sdk-e2" / "summary.json"

# Each row: (phase, regex over the spec, unit label, how to count from JSON).
ROW_PATTERN = {
    "A3": re.compile(r"\|\s*A3\s*\|\s*\*\*(?P<decision>\w+)\*\*\s*\|\s*"
                     r"(?P<runs>\d+)\s*runs／(?P<units>\d+)\s*次派送\s*\|"),
    "A4": re.compile(r"\|\s*A4\s*\|\s*\*\*(?P<decision>\w+)\*\*\s*\|\s*"
                     r"(?P<runs>\d+)\s*runs／(?P<units>\d+)\s*次派送\s*\|"),
    "A5": re.compile(r"\|\s*A5\s*\|\s*\*\*(?P<decision>\w+)\*\*\s*\|\s*"
                     r"(?P<runs>\d+)\s*runs／(?P<units>\d+)\s*個案例\s*\|"),
}


def measured(summary: dict) -> dict:
    """Counts for the artifact the summary calls current, phase by phase.

    A run whose wasmSha256 is anything else is evidence about another engine
    (finding 027); it is deliberately not counted, which is the whole point.
    """
    current = summary["artifactBinding"]["currentProfileWasmSha256"]

    def count(runs, unit_key):
        bound = [r for r in runs if r.get("wasmSha256") == current]
        return {
            "runs": len(bound),
            "units": sum(len(r.get(unit_key) or []) for r in bound),
        }

    return {
        "A3": {"decision": summary["decision"],
               **count(summary.get("runs", []), "steps")},
        "A4": {"decision": summary["a4"]["decision"],
               **count(summary["a4"].get("runs", []), "steps")},
        "A5": {"decision": summary["a5"]["decision"],
               **count(summary["a5"].get("runs", []), "cases")},
        "currentProfileWasmSha256": current,
    }


def quoted(spec_text: str) -> dict:
    rows = {}
    for phase, pattern in ROW_PATTERN.items():
        found = pattern.search(spec_text)
        if found is None:
            rows[phase] = None
            continue
        rows[phase] = {
            "decision": found.group("decision"),
            "runs": int(found.group("runs")),
            "units": int(found.group("units")),
        }
    return rows


def compare(spec_rows: dict, json_rows: dict) -> list[dict]:
    problems = []
    for phase in ROW_PATTERN:
        row = spec_rows.get(phase)
        if row is None:
            problems.append({"phase": phase, "problem": "row-not-found"})
            continue
        for field in ("decision", "runs", "units"):
            if row[field] != json_rows[phase][field]:
                problems.append({
                    "phase": phase,
                    "problem": f"{field}-mismatch",
                    "spec": row[field],
                    "measured": json_rows[phase][field],
                })
    return problems


def self_test(json_rows: dict) -> list[str]:
    """Every row must be able to fail, one at a time.

    The baseline is the measured counts, not whatever the spec currently says.
    Mutating the spec's own rows would only be meaningful while the spec is
    already correct, and the first time this ran the spec was not -- every
    mutation then "also blamed" the rows that were independently stale, which
    says nothing about whether the checker discriminates.

    So: start from a table that agrees with the JSON, confirm it is clean, then
    perturb one field at a time and require a mismatch naming that row and no
    other.
    """
    clean = {p: {k: json_rows[p][k] for k in ("decision", "runs", "units")}
             for p in ROW_PATTERN}
    failures = []
    if compare(clean, json_rows):
        return ["baseline built from the JSON does not compare clean"]
    for phase in ROW_PATTERN:
        for field in ("runs", "units"):
            mutated = {p: dict(r) for p, r in clean.items()}
            mutated[phase][field] += 1
            named = {p["phase"] for p in compare(mutated, json_rows)}
            if phase not in named:
                failures.append(f"{phase}.{field}: mutation not caught")
            elif named != {phase}:
                failures.append(
                    f"{phase}.{field}: mutation also blamed {sorted(named)}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=SPEC)
    parser.add_argument("--summary", type=Path, default=SUMMARY)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    json_rows = measured(summary)
    spec_rows = quoted(args.spec.read_text(encoding="utf-8"))

    report = {
        "spec": str(args.spec),
        "summary": str(args.summary),
        "currentProfileWasmSha256": json_rows["currentProfileWasmSha256"][:16] + "…",
        "measured": {p: json_rows[p] for p in ROW_PATTERN},
        "quoted": spec_rows,
    }

    if args.self_test:
        failures = self_test(json_rows)
        report["selfTest"] = "pass" if not failures else failures
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if not failures else 1

    problems = compare(spec_rows, json_rows)
    report["problems"] = problems
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
