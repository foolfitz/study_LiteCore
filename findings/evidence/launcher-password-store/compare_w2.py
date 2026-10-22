#!/usr/bin/env python3
"""W2 of SPEC-M3-production-ui 17.27: two Phase E reports, compared under the mask pinned there.

Compared: `verdicts`, `staged`, `cases`.  Masked: every value whose key ends in `Ms`, `At` or `Seconds`,
and `sbrk`.  `messages` (the engine's stderr warnings and their counts) is listed, not judged.  Every other
value must be equal.

  compare_w2.py REFERENCE.json CANDIDATE.json      exit 0: no difference; 1: differences (printed)
  compare_w2.py --selftest                          the two red cases of 17.27 on REFERENCE's copy
"""
from __future__ import annotations

import copy
import json
import re
import sys

MASKED = re.compile(r"(Ms|At|Seconds)$")
BLOCKS = ("verdicts", "staged", "cases")


def diff(a, b, path="", out=None, messages=None):
    out = [] if out is None else out
    messages = [] if messages is None else messages
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            sub = f"{path}.{key}"
            if MASKED.search(key) or key == "sbrk":
                continue
            if key == "messages":
                if a.get(key) != b.get(key):
                    messages.append(sub)
                continue
            if key not in a or key not in b:
                out.append((sub, a.get(key, "<absent>"), b.get(key, "<absent>")))
            else:
                diff(a[key], b[key], sub, out, messages)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((f"{path}[len]", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out, messages)
    elif a != b:
        out.append((path, a, b))
    return out, messages


def compare(ref: dict, cand: dict):
    out, messages = [], []
    for block in BLOCKS:
        diff(ref.get(block), cand.get(block), block, out, messages)
    return out, messages


def selftest(ref_path: str) -> int:
    ref = json.load(open(ref_path, encoding="utf-8"))
    ok = True
    one = copy.deepcopy(ref)
    sheet = next(s for c in one["cases"] for s in (c.get("sheets") or []) if s.get("text"))
    sheet["text"]["sha256"] = "0" * 64
    found, _ = compare(ref, one)
    print(f"red: one sheet's text.sha256 changed -> {len(found)} difference(s) (want 1)")
    ok &= len(found) == 1
    two = copy.deepcopy(ref)
    case = next(c for c in two["cases"] if c.get("viewReadyAtMs") is not None)
    case["viewReadyAtMs"] += 12345
    found, _ = compare(ref, two)
    print(f"mask: one viewReadyAtMs changed -> {len(found)} difference(s) (want 0)")
    ok &= len(found) == 0
    found, _ = compare(ref, ref)
    print(f"identity: the reference against itself -> {len(found)} difference(s) (want 0)")
    ok &= len(found) == 0
    print("selftest PASS" if ok else "selftest FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--selftest":
        return selftest(argv[1])
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    ref, cand = (json.load(open(p, encoding="utf-8")) for p in argv)
    found, messages = compare(ref, cand)
    for path, x, y in found:
        print(f"DIFF {path}: {json.dumps(x, ensure_ascii=False)[:120]} -> {json.dumps(y, ensure_ascii=False)[:120]}")
    for path in messages:
        print(f"messages differ (not judged): {path}")
    print(f"{len(found)} difference(s); W2 {'holds' if not found else 'does not hold'}")
    return 0 if not found else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
