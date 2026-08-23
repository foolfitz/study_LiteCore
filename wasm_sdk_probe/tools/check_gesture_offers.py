#!/usr/bin/env python3
"""Does the shipped manifest offer each action for the gestures we expect?

THE DEFECT THIS EXISTS FOR IS NOT A MISSING GESTURE. It is that the regression
net derives what it drives FROM THE MANIFEST -- `format_arm` uses a collapsed
caret because that was the only gesture `set-bold` was offered for, and the
runner says exactly that in its own comment. So an action that is UNDER-offered
is invisible to every check at once: the manifest narrows, the harness narrows
with it, and the two agree forever while the product loses an operation.

That is finding 078. The operator selected text, pressed bold, was refused, and
38 checks were green. A person found it in thirty seconds; nothing in the tree
could have.

So the expectation lives OUTSIDE the manifest, in `e2/expected-gesture-offers.json`,
where the two can disagree.

BOTH DIRECTIONS ARE FAILURES:

  * narrower than expected -- the product quietly lost a gesture, which is 078;
  * wider than expected -- the manifest offers something nobody characterised,
    which is the claim the whole contract exists to prevent.

Never edit the expectation to make this pass. Either the manifest is wrong, or
a measurement was taken and both move together with the evidence named.

Usage:
  check_gesture_offers.py [--profile P] [--expected F] [--self-test]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_EXPECTED = PROJECT / "e2" / "expected-gesture-offers.json"


def compare(actions: dict, expected: dict) -> list[str]:
    problems: list[str] = []
    for name, want in expected.items():
        if name not in actions:
            problems.append(f"{name}: expected in the manifest, absent")
            continue
        got = actions[name].get("gestures")
        if not isinstance(got, list):
            problems.append(f"{name}: manifest carries no gesture list")
            continue
        missing = [g for g in want if g not in got]
        extra = [g for g in got if g not in want]
        if missing:
            problems.append(
                f"{name}: NARROWER than expected -- missing {missing}. The "
                f"harness drives what the manifest offers, so nothing else in "
                f"this tree can see this")
        if extra:
            problems.append(
                f"{name}: WIDER than expected -- offers {extra} that the "
                f"expectation does not. A gesture nobody characterised is a "
                f"claim the evidence does not support")
    for name in actions:
        if name not in expected:
            problems.append(
                f"{name}: in the manifest and not in the expectation. A new "
                f"action must be added to the expectation deliberately, not "
                f"inherited by silence")
    return problems


def self_test() -> int:
    """The check has to be able to fail, in both directions."""
    base = {"set-bold": {"gestures": ["collapsed", "range-single"]}}
    want = {"set-bold": ["collapsed", "range-single"]}
    cases = [
        ("unchanged", base, want, 0),
        ("narrowed", {"set-bold": {"gestures": ["collapsed"]}}, want, 1),
        ("widened",
         {"set-bold": {"gestures": ["collapsed", "range-single", "range-cross"]}},
         want, 1),
        ("action absent", {}, want, 1),
        ("action unexpected",
         {**base, "set-magic": {"gestures": []}}, want, 1),
    ]
    failures = 0
    for label, actions, expectation, wanted in cases:
        found = len(compare(actions, expectation))
        ok = (found > 0) == (wanted > 0)
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: {found} problem(s)")
        failures += 0 if ok else 1
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        failures = self_test()
        print("self-test", "ok" if not failures else "FAILED")
        return 1 if failures else 0

    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    profile = args.profile or expected["profile"]
    manifest_path = (PROJECT / "dist" / "profiles" / profile
                     / "sdk-manifest.json")
    if not manifest_path.is_file():
        print(f"no manifest at {manifest_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actions = (manifest.get("editorContract") or {}).get("actions") or {}
    problems = compare(actions, expected["expected"])
    for problem in problems:
        print(f"  FAIL  {problem}")
    print(f"{profile}: {len(actions)} actions, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
