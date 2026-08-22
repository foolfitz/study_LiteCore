#!/usr/bin/env python3
"""Run the E2-C relink queue as a check instead of reading it as prose.

The queue in `handoff/PLAN-E2-C-relink-v3.md` was wrong twice: 3b was recorded
as written into the tree when grep found zero hits, and item 8 claimed both
selectionObserved gates were fixed when only one was.  Both were caught by a
human audit -- and a human audit does not run itself on the day of the link.

`e2/relink-queue-v3.json` is that queue as data.  This tool evaluates it.

**Fail closed.**  An item whose file is missing, whose check kind is unknown, or
whose expectation cannot be evaluated is NOT PASSING.  The failure mode this
exists to prevent is a check that quietly answers "fine" about something it
never looked at.

Expectations run in both directions: `present` items must stay present, and
`absent` items must stay absent.  An item that appears in the tree without its
expectation being flipped is drift in the direction nobody audits -- 3b landing
by accident is exactly as bad as 3b never landing.

Usage:
  check_relink_queue.py [--queue F] [--json] [--self-test]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = PROJECT / "e2" / "relink-queue-v3.json"
KINDS = ("contains", "absent", "line-equals", "file-exists")


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def evaluate_check(check: dict, root: Path) -> dict:
    """One check.  Returns satisfied True/False, never None.

    `line-equals` matches a WHOLE line, which is the difference between
    noticing `if (!gEditorState.selectionObserved) {` and being fooled by
    `if (false && !gEditorState.selectionObserved) {`.  The tree already
    recorded that lesson once; this is it written down as code.
    """
    kind = check.get("kind")
    target = root / str(check.get("file", ""))
    result = {"kind": kind, "file": check.get("file"), "satisfied": False}
    if kind not in KINDS:
        result["why"] = f"unknown check kind {kind!r}"
        return result
    if kind == "file-exists":
        result["satisfied"] = target.is_file()
        if not result["satisfied"]:
            result["why"] = "file does not exist"
        return result

    text = read(target)
    if text is None:
        result["why"] = "file could not be read"
        return result

    needle = str(check.get("text", ""))
    if not needle:
        result["why"] = "check has no text to look for"
        return result

    if kind == "contains":
        count = text.count(needle)
        result["count"] = count
        result["atLeast"] = check.get("atLeast", 1)
        result["satisfied"] = count >= result["atLeast"]
        if not result["satisfied"]:
            result["why"] = f"found {count}, wanted >= {result['atLeast']}"
    elif kind == "absent":
        count = text.count(needle)
        result["count"] = count
        result["satisfied"] = count == 0
        if not result["satisfied"]:
            result["why"] = f"found {count}, wanted none"
    elif kind == "line-equals":
        count = sum(1 for line in text.splitlines() if line == needle)
        result["count"] = count
        result["atLeast"] = check.get("atLeast", 1)
        result["satisfied"] = count >= result["atLeast"]
        if not result["satisfied"]:
            result["why"] = (f"{count} whole lines matched, wanted >= "
                             f"{result['atLeast']}")
    return result


def evaluate(queue: dict, root: Path) -> dict:
    items = []
    for item in queue.get("items") or []:
        checks = [evaluate_check(check, root) for check in item.get("checks") or []]
        expectation = item.get("expectation")
        # Two items with the same id is not a cosmetic problem: every tool that
        # updates this file finds an item by id and updates the FIRST match, so
        # a duplicate silently swallows edits -- which is how one of these was
        # left declaring `absent` for a thing that had shipped, on 2026-08-19.
        if expectation not in ("present", "absent"):
            items.append({"id": item.get("id"), "status": "UNEVALUABLE",
                          "why": f"unknown expectation {expectation!r}",
                          "checks": checks})
            continue
        if not checks:
            items.append({"id": item.get("id"), "status": "UNEVALUABLE",
                          "why": "item has no checks", "checks": []})
            continue
        satisfied = all(check["satisfied"] for check in checks)
        items.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "expectation": expectation,
            "blocksRelink": bool(item.get("blocksRelink")),
            # A queue item is "as declared" or it is not.  There is no partial
            # credit: half an item is a second relink.
            "status": "AS-DECLARED" if satisfied else "DRIFTED",
            "checks": checks,
        })

    drifted = [item for item in items if item["status"] != "AS-DECLARED"]
    declared_present = [item for item in items
                        if item.get("expectation") == "present"]
    declared_absent = [item for item in items
                       if item.get("expectation") == "absent"]
    duplicates = duplicate_ids(items)
    return {
        "schemaVersion": 1,
        "queue": str(queue.get("release")),
        "items": items,
        "counts": {
            "total": len(items),
            "declaredPresent": len(declared_present),
            "declaredAbsent": len(declared_absent),
            "drifted": len(drifted),
        },
        # The sentence the link decision actually needs, and the one place a
        # checker like this usually lies: "everything that is done is done" is
        # not the same as "the queue is finished".  An item that still BLOCKS
        # the relink keeps P1 incomplete even though it is exactly as declared.
        "p1Complete": (
            all(item["status"] == "AS-DECLARED" for item in declared_present)
            and not any(item["status"] == "UNEVALUABLE" for item in items)
            and not [item for item in declared_absent
                     if item.get("blocksRelink")]),
        "openItems": [item["id"] for item in declared_absent],
        "blockingOpenItems": [item["id"] for item in declared_absent
                              if item.get("blocksRelink")],
        # A duplicated id makes every by-id edit land on one copy and leave the
        # other declaring something that is no longer true, so it fails the
        # round rather than being reported as a note.
        "duplicateIds": duplicates,
        "verdict": ("DRIFTED" if drifted or duplicates else "AS-DECLARED"),
    }


def self_test() -> int:
    """Mutations, on a copy of the queue and a copy of the tree's answers.

    Each one turns a real item's outcome, because a checker that cannot be shown
    to fail is a checker that will report success about a tree it never read.
    """
    import copy
    import tempfile

    queue = json.loads(DEFAULT_QUEUE.read_text(encoding="utf-8"))
    failures: list[str] = []
    ran: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        ran.append(name)
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    baseline = evaluate(queue, PROJECT)
    check("the real tree is as the queue declares",
          baseline["verdict"] == "AS-DECLARED",
          str([item["id"] for item in baseline["items"]
               if item["status"] != "AS-DECLARED"]))

    def with_tree(mutate) -> dict:
        """Copy the files the queue names into a temp tree, mutate, re-evaluate."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for item in queue.get("items") or []:
                for entry in item.get("checks") or []:
                    source = PROJECT / str(entry.get("file", ""))
                    target = root / str(entry.get("file", ""))
                    if source.is_file():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if not target.exists():
                            target.write_bytes(source.read_bytes())
            mutate(root)
            return evaluate(queue, root)

    def status_of(report: dict, item_id: str) -> str:
        return next(item["status"] for item in report["items"]
                    if item["id"] == item_id)

    def comment_out_gate(root: Path):
        path = root / "src" / "probe_engine.cpp"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "  if (!gEditorState.selectionObserved) {",
            "  if (false && !gEditorState.selectionObserved) {"),
            encoding="utf-8")

    report = with_tree(comment_out_gate)
    check("disabling the selectionObserved gate with `if (false && ...)` is caught",
          status_of(report, "p1-8b-selection-observed") == "DRIFTED")
    check("and that alone fails P1", report["p1Complete"] is False)
    # Written as a MUTATION, not as an assertion about today's queue: the first
    # version asserted `baseline["p1Complete"] is False`, which was true only
    # while blockers happened to exist and went red the day the last one was
    # measured away.  A check that describes the data instead of the logic
    # stops working exactly when the data changes -- which is when it matters.
    def make_an_open_item_blocking(cloned_queue):
        for item in cloned_queue.get("items") or []:
            if item.get("expectation") == "absent":
                item["blocksRelink"] = True
                return

    blocked = copy.deepcopy(queue)
    make_an_open_item_blocking(blocked)
    blocked_report = evaluate(blocked, PROJECT)
    check("an open item marked blocking makes P1 incomplete",
          blocked_report["p1Complete"] is False
          and blocked_report["blockingOpenItems"] != [],
          f"blocking={blocked_report.get('blockingOpenItems')}")

    def clear_all_blocking(cloned_queue):
        for item in cloned_queue.get("items") or []:
            if item.get("expectation") == "absent":
                item["blocksRelink"] = False

    unblocked = copy.deepcopy(queue)
    clear_all_blocking(unblocked)
    check("and with none marked blocking, P1 can be complete",
          evaluate(unblocked, PROJECT)["p1Complete"] is True)

    def drop_itemcount(root: Path):
        path = root / "sdk" / "sdk-worker.js"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "itemCount: value.readback?.itemCount", "// removed"), encoding="utf-8")

    check("removing the itemCount projection is caught",
          status_of(with_tree(drop_itemcount),
                    "p1-3c-itemcount-projection") == "DRIFTED")

    def abi_back_a_version(root: Path):
        # Mutate FROM WHAT THE QUEUE DECLARES, not from a literal written down
        # when this self-test was.  Pinned to `3u`, this mutation silently
        # stopped biting the moment the constant went to 4: the replace found
        # nothing, the tree was left correct, the check passed, and the
        # self-test reported that its own mutation had not moved the verdict.
        # Measured 2026-08-22 -- and it is the same shape as the thing the
        # queue itself exists to catch, one level up.
        path = root / "src" / "editor_api.h"
        declared = next(item["checks"][0]["text"] for item in queue["items"]
                        if item["id"] == "p1-4-abi-3")
        path.write_text(path.read_text(encoding="utf-8").replace(
            declared, "#define OXSDK_EDITOR_ABI_VERSION 2u"), encoding="utf-8")

    check("an ABI constant back at an older version is caught",
          status_of(with_tree(abi_back_a_version), "p1-4-abi-3") == "DRIFTED")

    def delete_v3_target(root: Path):
        path = root / "Makefile"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "E2_C_BUILD := build/e2/editor-v3", "# gone"), encoding="utf-8")

    check("a missing v3 build variant is caught",
          status_of(with_tree(delete_v3_target), "p1-5-makefile-v3") == "DRIFTED")

    def drop_manifest_declaration(root: Path):
        path = root / "tools" / "build_e2_c_profile.py"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "inlineFormatEnabledIsHonoured", "somethingElse"), encoding="utf-8")

    check("dropping inlineFormatEnabledIsHonoured from the builder is caught",
          status_of(with_tree(drop_manifest_declaration),
                    "p1-9b-inline-honoured-declared") == "DRIFTED")

    def sneak_in_3b(root: Path):
        path = root / "src" / "probe_engine.cpp"
        path.write_text(path.read_text(encoding="utf-8")
                        + '\n// shape = "empty-readback";\n', encoding="utf-8")

    check("3b APPEARING without its expectation being flipped is caught too",
          status_of(with_tree(sneak_in_3b), "p1-3b-empty-readback") == "DRIFTED")

    def unreadable_file(root: Path):
        (root / "src" / "editor_api.h").unlink()

    check("a file the queue names but cannot read fails closed",
          status_of(with_tree(unreadable_file), "p1-4-abi-3") == "DRIFTED")

    # A duplicated id makes every by-id edit land on one copy and leave the
    # other declaring something that is no longer true.  It happened on
    # 2026-08-19 -- an item was appended twice and the update hit the first,
    # so the queue went on blocking a link for work that had shipped.
    check("a duplicated item id is caught",
          duplicate_ids([{"id": "a"}, {"id": "b"}, {"id": "a"}]) == ["a"])
    check("distinct ids are not",
          duplicate_ids([{"id": "a"}, {"id": "b"}]) == [])
    duplicated = copy.deepcopy(queue)
    duplicated["items"].append(copy.deepcopy(duplicated["items"][0]))
    check("a queue with a duplicated id fails the round",
          evaluate(duplicated, PROJECT)["verdict"] == "DRIFTED")

    print(f"\nself-test: {len(ran) - len(failures)}/{len(ran)} "
          "checks moved the verdict")
    return 1 if failures else 0


def duplicate_ids(items) -> list[str]:
    """Ids that appear more than once, which no tool that edits this file survives."""
    seen: dict[str, int] = {}
    for item in items:
        key = str(item.get("id"))
        seen[key] = seen.get(key, 0) + 1
    return sorted(key for key, count in seen.items() if count > 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--root", type=Path, default=PROJECT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    report = evaluate(queue, args.root)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for item in report["items"]:
            mark = {"AS-DECLARED": "ok  ", "DRIFTED": "DRIFT",
                    "UNEVALUABLE": "????"}[item["status"]]
            print(f"  {mark}  [{item.get('expectation', '?'):7s}] {item['id']}")
            for entry in item["checks"]:
                if not entry["satisfied"]:
                    print(f"          {entry['file']}: {entry.get('why')}")
        counts = report["counts"]
        print(f"\n{counts['total']} items, {counts['declaredPresent']} declared "
              f"present, {counts['declaredAbsent']} still open, "
              f"{counts['drifted']} drifted")
        print(f"P1 complete: {report['p1Complete']}")
        print(f"still open:  {', '.join(report['openItems']) or '(none)'}")
        print(f"  blocking:  "
              f"{', '.join(report['blockingOpenItems']) or '(none)'}")
    return 0 if report["verdict"] == "AS-DECLARED" else 1


if __name__ == "__main__":
    sys.exit(main())
