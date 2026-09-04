#!/usr/bin/env python3
"""The red cases the 2026-09-05 amendment owes before its judge changes.

`AGENTS.md` §6: a checker that has only ever returned green has shown that it
returns green.  Rulings 1 and 2 change what `axReading` means and where terms 4
and 8 take their expectation from, so each change needs a mutation that it, and
only it, catches.

Every case here MUTATES A HELD RECORD and hands the result to the real
`check_4a.judge` and the real `probe_aria_projection.reading_for_placement`.
Nothing re-implements a term: a red case judged by a second copy of the judge
proves something about the copy (this tree withdrew findings 064 and 065 over
exactly that).

ONE reconstruction is unavoidable.  Records taken before this amendment do not
carry `target.axNodeId`, because the probe did not record it until today, so
`hydrate()` recovers it from `activeDescendantRef` -- `a11y-node-N` is the Nth
structure leaf in tree order, which is the order the page assigns ids in.  That
is a replay's licence over records that already exist; runs taken from here
carry the field and need no reconstruction.
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "wasm_sdk_probe" / "tools"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load("check_4a", TOOLS / "check_4a.py")
PROBE = load("probe_aria", TOOLS / "probe_aria_projection.py")

GREEN = ROOT / "findings/evidence/088/4a-eight-terms-run1.json"
CONTROL = ROOT / "findings/evidence/gate-4a/control-v8.json"


def structure_leaves(nodes: list[dict]) -> list[dict]:
    index = {n["nodeId"]: n for n in nodes}
    group = next(n for n in nodes
                 if n.get("role") == "group" and n.get("name") == "文件內容")
    subtree = index[group["childIds"][-1]]
    leaves: list[dict] = []

    def walk(node):
        if node.get("role") in ("heading", "paragraph", "listitem"):
            leaves.append(node)
        for child in node.get("childIds") or []:
            if child in index:
                walk(index[child])

    walk(subtree)
    return leaves


def hydrate(record: dict) -> dict:
    """Give a pre-amendment record the `axNodeId` the amended probe records."""
    record = copy.deepcopy(record)
    leaves = structure_leaves(record["nodes"])
    for placement in record["placements"]:
        caret = placement.get("axCaretNode") or {}
        ref = caret.get("activeDescendantRef")
        target = caret.get("target")
        if ref and target is not None:
            n = int(ref.rsplit("-", 1)[1])
            if n < len(leaves):
                target["axNodeId"] = leaves[n]["nodeId"]
    return record


def reread(record: dict, name_only: bool = False, old_rule: bool = False,
           structure_first: bool = False) -> dict:
    """Recompute every `axReading` under one of the candidate rules."""
    record = copy.deepcopy(record)
    for placement in record["placements"]:
        carried = placement["axNodesCarryingText"]
        if structure_first:
            carried = ([n for n in carried if n.get("role") != "StaticText"]
                       + [n for n in carried if n.get("role") == "StaticText"])
        if old_rule:
            reading = carried[0].get("name") if carried else None
        elif name_only:
            target = (placement.get("axCaretNode") or {}).get("target") or {}
            reading = target.get("name") if target.get("axNodeId") else (
                carried[0].get("name") if carried else None)
        else:
            reading = PROBE.reading_for_placement(
                record["nodes"], placement.get("axCaretNode") or {}, carried)
        placement["axReading"] = reading
    record["axReadings"] = [p["axReading"] for p in record["placements"]]
    record["distinctAxReadings"] = len({r for r in record["axReadings"] if r})
    return record


def mispoint(record: dict, placement_index: int = 1, onto: int = 0) -> dict:
    record = copy.deepcopy(record)
    leaves = structure_leaves(record["nodes"])
    placement = record["placements"][placement_index]
    caret = placement["axCaretNode"]
    caret["activeDescendantRef"] = f"a11y-node-{onto}"
    caret["target"] = {
        "role": leaves[onto].get("role"),
        "name": leaves[onto].get("name"),
        "level": leaves[onto].get("level"),
        "axNodeId": leaves[onto]["nodeId"],
    }
    return record


def detach(record: dict) -> dict:
    """No pointer at all -- the shape of the tree before finding 087's fix."""
    record = copy.deepcopy(record)
    for placement in record["placements"]:
        placement["axCaretNode"] = {"focused": True, "activeDescendantRef": None,
                                    "target": None}
    return record


def silence(record: dict) -> dict:
    """The live region emptied: the 088 residue fix that was reverted."""
    record = copy.deepcopy(record)
    live = {n["nodeId"] for n in structure_leaves(record["nodes"])}
    for placement in record["placements"]:
        placement["axNodesCarryingText"] = [
            n for n in placement["axNodesCarryingText"]
            if n["nodeId"] in live or n.get("role") != "StaticText"]
    return record


def verdict(record: dict) -> tuple[bool, list[str]]:
    control = json.loads(CONTROL.read_text(encoding="utf-8"))
    result = CHECK.judge([record, record, record], control, None)
    return result["ok"], [k for k, v in result["terms"].items() if not v["ok"]]


def main() -> int:
    base = hydrate(json.loads(GREEN.read_text(encoding="utf-8")))
    green = reread(base)
    cases: list[tuple[str, dict, set[str]]] = [
        ("CONTROL: the held green record, reread under Ruling 1",
         green, set()),
        ("RED 1: name-only reading (no subtree fallback)",
         reread(base, name_only=True), {"4-focus"}),
        ("RED 2a: structure before the live region, OLD rule",
         reread(base, old_rule=True, structure_first=True), {"4-focus"}),
        ("GREEN 2b: the same reorder, Ruling 1's rule",
         reread(base, structure_first=True), set()),
        ("RED 3: placement 1's pointer redirected at the heading",
         reread(mispoint(base)), {"4-focus", "8-structure-on-the-caret-path"}),
        ("RED 4: live region silenced AND the pointer detached",
         reread(silence(detach(base))),
         {"4-focus", "8-structure-on-the-caret-path"}),
    ]
    failures = []
    for label, record, expect_red in cases:
        ok, red = verdict(record)
        got = set(red)
        agree = got == expect_red
        mark = "as expected" if agree else "*** WRONG ***"
        print(f"  {mark:14s} {label}")
        print(f"                 ok={ok} red={sorted(got) or 'none'} "
              f"readings={record['axReadings']}")
        if not agree:
            failures.append((label, sorted(got), sorted(expect_red)))
    if failures:
        print(f"\n{len(failures)} case(s) did not behave as the amendment says:")
        for label, got, want in failures:
            print(f"  {label}\n    got  {got}\n    want {want}")
        return 1
    print("\nall six cases behaved as the amendment says: the two rulings each "
          "have a mutation that catches them, and the reorder that reddened the "
          "old rule leaves the new one green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
