#!/usr/bin/env python3
"""Compare the `a-boundary-arrow-press-does-not-cost-the-work` check's verdict
and observed ("boundary") payload cell-for-cell between two banked
run_e2_c_product_path.py reports.

Usage:
    python3 compare_b4_cells.py <report-a.json> <report-b.json>

Walks report["checks"] for the check named above in each file, deep-diffs the
check's `observed` dict (which carries `verdict` as one of its keys) plus the
check's own `ok`/`outcome`/`why`/`oracle` fields, and prints every path whose
value differs, one per line, sorted for determinism. A path is prefixed
`EXEMPT` when it matches one of the three cells T8b's brief allows to move
(the new `verdict.b4Inducer` cell, any `seconds` timing field, and
`savedBytes`) so a reader can see what moved without re-deriving which moves
were expected. Exit status is 0 regardless of what it finds -- this script
reports, it does not judge.
"""

import json
import sys

CHECK_ID = "a-boundary-arrow-press-does-not-cost-the-work"

# Paths (dotted, with [i] for list indices) exempt from being a "moved cell"
# surprise, per the T8b brief:
#   (a) the new b4Inducer cell -- did not exist before T8a
#   (b) timing cells -- presses[*].seconds, and any *.seconds/*.ms field
#   (c) savedBytes -- a byte count that may legitimately vary run to run
EXEMPT_EXACT = {
    "observed.verdict.b4Inducer",
    "observed.savedBytes",
}


def is_exempt(path):
    if path in EXEMPT_EXACT:
        return True
    # presses[i].seconds for any i
    if path.startswith("observed.presses[") and path.endswith("].seconds"):
        return True
    return False


def find_check(report, check_id):
    for check in report.get("checks", []):
        if check.get("id") == check_id or check.get("name") == check_id:
            return check
    return None


def flatten(obj, prefix=""):
    """Yield (path, value) for every leaf in a JSON-shaped structure."""
    if isinstance(obj, dict):
        for key in sorted(obj.keys()):
            yield from flatten(obj[key], f"{prefix}.{key}" if prefix else key)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from flatten(item, f"{prefix}[{i}]")
    else:
        yield (prefix, obj)


def diff_checks(check_a, check_b):
    scope_a = {
        "ok": check_a.get("ok"),
        "outcome": check_a.get("outcome"),
        "why": check_a.get("why"),
        "oracle": check_a.get("oracle"),
        "observed": check_a.get("observed"),
    }
    scope_b = {
        "ok": check_b.get("ok"),
        "outcome": check_b.get("outcome"),
        "why": check_b.get("why"),
        "oracle": check_b.get("oracle"),
        "observed": check_b.get("observed"),
    }
    flat_a = dict(flatten(scope_a))
    flat_b = dict(flatten(scope_b))
    all_paths = sorted(set(flat_a) | set(flat_b))
    diffs = []
    for path in all_paths:
        va = flat_a.get(path, "<MISSING>")
        vb = flat_b.get(path, "<MISSING>")
        if va != vb:
            diffs.append((path, va, vb))
    return diffs


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <report-a.json> <report-b.json>", file=sys.stderr)
        return 2

    path_a, path_b = sys.argv[1], sys.argv[2]
    with open(path_a, "r", encoding="utf-8") as f:
        report_a = json.load(f)
    with open(path_b, "r", encoding="utf-8") as f:
        report_b = json.load(f)

    check_a = find_check(report_a, CHECK_ID)
    check_b = find_check(report_b, CHECK_ID)

    if check_a is None or check_b is None:
        print(f"could not find check {CHECK_ID!r} in one or both reports "
              f"(a: {'found' if check_a else 'MISSING'}, "
              f"b: {'found' if check_b else 'MISSING'})")
        return 1

    diffs = diff_checks(check_a, check_b)

    print(f"comparing {path_a} (a) vs {path_b} (b), check {CHECK_ID!r}")
    print(f"{len(diffs)} differing path(s)")
    print()
    for path, va, vb in diffs:
        tag = "EXEMPT" if is_exempt(path) else "MOVED "
        print(f"[{tag}] {path}")
        print(f"    a: {va!r}")
        print(f"    b: {vb!r}")

    non_exempt = [d for d in diffs if not is_exempt(d[0])]
    print()
    print(f"non-exempt moved cells: {len(non_exempt)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
