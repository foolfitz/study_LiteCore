#!/usr/bin/env python3
"""Match the nameless wait frames on ee185b3d against named ones on 150de122.

The engine thread parked during finding 037 was captured on the pre-guard
artifact, which has no name section: its stack is `$func15470` and friends.  The
diagnostic artifact does have names, but it carries the 037 guard, so the same
hang cannot be produced on it -- the two stacks can never be taken from one run.

What can be compared is the *shape* of the library call graph.  Both runs caught
several threads parked in the same condvar machinery, and those threads branch
apart at different depths: a pool thread doing a timed wait leaves the shared
prefix at one frame, a thread doing an untimed wait at another.  Every such
branch point is an independent constraint on the mapping.  If one assignment of
index to name satisfies all of them at once, that is worth more than eyeballing
one stack.

This is still an inference, and the script says so: it prints how many distinct
stacks each pairing rests on, and refuses to emit a mapping for any index that
only ever appeared in one stack.  The measurement that would replace it is a
relink of the pre-guard sources with --profiling-funcs.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
NAMELESS = (PROJECT / "findings" / "evidence" / "sdk-e2" / "discovery"
            / "proxy-trace" / "chrome" / "result.json")
NAMED = (PROJECT / "findings" / "evidence" / "sdk-e2" / "discovery"
         / "wait-primitive-names" / "chrome" / "result.json")


def nameless_stacks(path: Path) -> list[list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for column in ("pauseControl", "pauseDuringHang"):
        for worker in data.get(column, {}).get("workers", []):
            frames = [f["functionName"] for f in worker.get("callFrames", [])]
            if frames and frames[0].startswith("$func"):
                out.append(frames)
    return out


def named_stacks(path: Path) -> list[list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rounds = data.get("rounds") or [{"workers": data.get("workers", [])}]
    out = []
    for entry in rounds:
        for worker in entry.get("workers", []):
            frames = [f["functionName"] for f in worker.get("frames", [])]
            if frames and frames[0].startswith("$"):
                out.append(frames)
    return out


def role(stack: list[str]) -> tuple:
    """A cheap identity for "which kind of thread is this".

    Comparing every nameless stack against every named one is far too loose: a
    pool thread doing a timed wait and the engine thread doing an untimed one
    share only the first three frames, and cross-pairing them makes frame 3
    look ambiguous when it is not.  Two stacks constrain each other only if
    they are the same thread playing the same role, and depth plus the JS tail
    is the part of that which survives having no names on one side.
    """
    tail = tuple(f for f in stack if not f.startswith("$"))
    return (len(stack), tail)


def pair(nameless: list[list[str]], named: list[list[str]]) -> dict:
    """Align same-role stacks frame by frame and collect candidate names."""
    by_depth_index: dict[tuple[int, str], set[str]] = defaultdict(set)
    support: dict[tuple[int, str], set[tuple]] = defaultdict(set)
    pairings = []

    named_by_role: dict[tuple, list[list[str]]] = defaultdict(list)
    for right in named:
        named_by_role[role(right)].append(right)

    for left in nameless:
        partners = named_by_role.get(role(left), [])
        if len(partners) != 1:
            # No partner, or an ambiguous one -- contributes nothing rather
            # than contributing a guess.
            continue
        right = partners[0]
        pairings.append({"depth": len(left), "tail": list(role(left)[1])})
        for depth, (a, b) in enumerate(zip(left, right)):
            if not a.startswith("$func"):
                continue
            by_depth_index[(depth, a)].add(b)
            support[(depth, a)].add(tuple(left))

    resolved, ambiguous = {}, {}
    for (depth, index), names in sorted(by_depth_index.items()):
        agreeing = len(support[(depth, index)])
        record = {"depth": depth, "stacksAgreeing": agreeing}
        if len(names) == 1:
            resolved[index] = {**record, "name": next(iter(names))}
        else:
            ambiguous[index] = {**record, "candidates": sorted(names)}
    return {"resolved": resolved, "ambiguous": ambiguous, "pairings": pairings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nameless", type=Path, default=NAMELESS)
    parser.add_argument("--named", type=Path, default=NAMED)
    args = parser.parse_args()

    left = nameless_stacks(args.nameless)
    right = named_stacks(args.named)
    result = pair(left, right)
    print(json.dumps({
        "namelessStacks": len(left),
        "namedStacks": len(right),
        "pairings": result["pairings"],
        "resolved": result["resolved"],
        "ambiguousCount": len(result["ambiguous"]),
        "ambiguous": result["ambiguous"],
        "caveat": "inference from call-graph shape across two separate links; "
                  "the measurement that replaces it is a --profiling-funcs "
                  "relink of the pre-guard sources",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
