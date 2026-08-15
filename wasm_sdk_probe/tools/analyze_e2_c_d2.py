#!/usr/bin/env python3
"""Judge SPEC E2-C phase D2 -- recovery and no-replay.

Run before the round-two relink as a DEFECT SWEEP, which is why this judge is
build-aware instead of pretending the current artifact should pass cells written
for the next one.  Three cells are known to answer differently on v2, each with
a reason and a reference; the rest are judged outright.  A cell that "fails"
because it is measuring an artifact the fix has not reached yet is not a
finding, and reporting it as one teaches people to ignore the report.

Zero mutation is judged on `<office:body>` bytes between the saves the harness
took either side of the attempt, never on the refusal code alone: a cell that
only read the code would pass just as happily if the engine had refused loudly
and mutated anyway.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import zipfile
from pathlib import Path

BODY_OPEN, BODY_CLOSE = b"<office:body>", b"</office:body>"

# What each cell has to show.  `pre_dispatch` means the disposition must be
# refused-no-mutation AND the body must be untouched; `restart` means the
# session must end up asking for a fresh worker.
EXPECTED = {
    "d2-stale-revision": {
        "disposition": "refused-no-mutation",
        "zeroMutation": ("stale-revision-before", "stale-revision-after"),
        "why": "the revision gate runs before the action switch; nothing was "
               "dispatched",
    },
    "d2-stale-handle": {
        "rejected": True,
        "why": "a handle whose engine is gone cannot mutate anything",
    },
    "d2-refused-no-mutation-client": {
        "allAttemptsRefused": True,
        "disposition": "refused-no-mutation",
        "zeroMutation": ("client-refusal-before", "client-refusal-after"),
    },
    "d2-unknown-rollback-fallback": {
        "disposition": "unknown-rollback",
        "why": "fail closed survives the pre-dispatch code list",
    },
    # WRITTEN AFTER OBSERVATION, and said so on purpose.  The v2 pair below was
    # `EDITOR_FORMAT_POSTCONDITION_FAILED` / `postcondition-not-met`, measured
    # when the caret was formed by a bare `placeCaret` -- which returns before
    # the click lands (finding 048), so what that round actually measured was a
    # dispatch whose caret arrived during the intervening save.  With the caret
    # PROVED to be on the empty paragraph before dispatch, the same build
    # answers `MUTATION_OUTCOME_UNKNOWN` / `multi-block-readback` instead, in
    # Chrome and Firefox and through both positioning gestures.
    #
    # `multiBlock` is `blockCount > 1 || itemCount > 1` and the payload reports
    # `postBlocks: 0`, so this is an itemCount verdict -- and the product
    # projection does not carry itemCount, which is why the relink queue now has
    # an item for it (PLAN-E2-C-relink-v3 3c).  Until that lands, this cell can
    # say WHICH exit the engine took and not what the readback saw.
    "d2-refused-no-mutation-engine": {
        "v2": {"code": "MUTATION_OUTCOME_UNKNOWN",
               "shape": "multi-block-readback",
               "finding": "046 -- the empty paragraph's readback is classified "
                          "by a count the product payload does not report"},
        # The dispatch is real and its outcome is unknown, so the claim worth
        # checking is not "nothing changed" -- it is that the prescribed
        # recovery PUT IT BACK.  Compared after the rollback, byte for byte.
        "restoredAfterRecovery": ("engine-refusal-before", "engine-refusal-after"),
        "rollback": "ok",
        # Pending: 046's fix predicate is not decided, so neither is the shape
        # this becomes.  Left as the intended one and re-checked when 3b lands.
        "v3": {"code": "MUTATION_OUTCOME_UNKNOWN", "shape": "empty-readback"},
    },
    "d2-dispatched-rollback": {
        "code": "MUTATION_OUTCOME_UNKNOWN",
        "shape": "footnote-apparatus-readback",
        "dispatched": True,
        "requiresCheckpoint": True,
    },
    "d2-boundary-restart-required": {
        "code": "EDITOR_BOUNDARY_UNSUPPORTED",
        "state": "restart-required",
        "queuedRejected": "EDITOR_NOT_READY",
    },
    "d2-crash-unsaved-edit": {"restart": "ok", "stateAfterCrash": "recoverable-error"},
    "d2-crash-after-save": {"restart": "ok", "dirtyAfterSave": False},
    "d2-crash-after-checkpoint": {"restart": "ok", "dirtyAfterRestart": True},
    "d2-crash-queued-mutation": {"bothRejected": "WORKER_CRASHED", "restart": "ok"},
    "d2-generation-ceiling": {"ceilingCode": "WORKER_GENERATION_LIMIT",
                              "requiresPageReload": True},
}


def body_of(odt: Path) -> bytes | None:
    if not odt.is_file():
        return None
    with zipfile.ZipFile(odt) as archive:
        content = archive.read("content.xml")
    start, end = content.find(BODY_OPEN), content.find(BODY_CLOSE)
    return content[start:end + len(BODY_CLOSE)] if start >= 0 and end >= 0 else None


def zero_mutation(saved: Path, labels) -> tuple[bool | None, str]:
    before, after = (body_of(saved / f"{name}.odt") for name in labels)
    if before is None or after is None:
        return None, "one of the saves is missing"
    return before == after, "compared <office:body> byte for byte"


def judge_cell(cid: str, cell: dict, saved: Path, abi: int,
               expected: dict = EXPECTED) -> dict:
    spec = expected.get(cid)
    if spec is None:
        return {"pass": False, "problems": [f"{cid}: no expectation is declared"]}
    problems: list[str] = []
    notes: list[str] = []
    error = cell.get("error") or {}
    barrier = error.get("formatBarrier") or {}

    if cell.get("fatal"):
        return {"pass": False,
                "problems": [f"{cid}: the cell itself failed: "
                             f"{cell['fatal'].get('code')}"]}

    variant = spec.get("v3" if abi >= 3 else "v2")
    if variant:
        if error.get("code") != variant["code"]:
            problems.append(f"{cid}: code {error.get('code')}, expected "
                            f"{variant['code']} on this build")
        if barrier.get("failureShape") != variant["shape"]:
            problems.append(f"{cid}: shape {barrier.get('failureShape')}, "
                            f"expected {variant['shape']}")
        if "finding" in variant:
            notes.append(f"known on this build: finding {variant['finding']}")

    if "disposition" in spec and error:
        if error.get("disposition") != spec["disposition"]:
            problems.append(f"{cid}: disposition {error.get('disposition')}, "
                            f"expected {spec['disposition']}")
    if "disposition" in spec and not error and cid == "d2-unknown-rollback-fallback":
        if cell.get("disposition") != spec["disposition"]:
            problems.append(f"{cid}: disposition {cell.get('disposition')}")

    if spec.get("allAttemptsRefused"):
        for attempt in cell.get("attempts", []):
            if not attempt.get("error"):
                problems.append(f"{cid}: {attempt.get('label')} was accepted")
            elif attempt["error"].get("disposition") != spec["disposition"]:
                problems.append(f"{cid}: {attempt.get('label')} disposition "
                                f"{attempt['error'].get('disposition')}")

    if spec.get("rejected") and not error:
        problems.append(f"{cid}: the stale handle was accepted")

    if "zeroMutation" in spec:
        held, how = zero_mutation(saved, spec["zeroMutation"])
        if held is None:
            problems.append(f"{cid}: {how}")
        elif not held:
            problems.append(f"{cid}: <office:body> changed")
        notes.append(how)

    if "restoredAfterRecovery" in spec:
        held, how = zero_mutation(saved, spec["restoredAfterRecovery"])
        if held is None:
            problems.append(f"{cid}: {how} -- the recovery left nothing to compare")
        elif not held:
            problems.append(f"{cid}: the rollback did not restore <office:body>")
        notes.append(f"after the rollback: {how}")
    if "rollback" in spec and cell.get("rollback") != spec["rollback"]:
        problems.append(f"{cid}: rollback was {cell.get('rollback')!r}, "
                        f"expected {spec['rollback']!r}")

    if "code" in spec and error.get("code") != spec["code"]:
        problems.append(f"{cid}: code {error.get('code')}, expected {spec['code']}")
    if "shape" in spec and barrier.get("failureShape") != spec["shape"]:
        problems.append(f"{cid}: shape {barrier.get('failureShape')}, "
                        f"expected {spec['shape']}")
    if spec.get("dispatched") and barrier.get("dispatched") is not True:
        problems.append(f"{cid}: dispatched is {barrier.get('dispatched')}")
    if spec.get("requiresCheckpoint") and cell.get("hasCheckpoint") is not True:
        problems.append(f"{cid}: no checkpoint existed, so the rollback proves "
                        f"nothing")
    if "state" in spec and cell.get("state") != spec["state"]:
        problems.append(f"{cid}: state {cell.get('state')}, expected {spec['state']}")
    if "queuedRejected" in spec:
        queued = cell.get("queuedAfter") or {}
        if queued.get("code") != spec["queuedRejected"]:
            problems.append(f"{cid}: the queued operation returned "
                            f"{queued.get('code')}")
    if "restart" in spec and cell.get("restart") != spec["restart"]:
        problems.append(f"{cid}: restart {cell.get('restart')}")
    if "stateAfterCrash" in spec and cell.get("stateAfterCrash") != spec["stateAfterCrash"]:
        problems.append(f"{cid}: after the crash the state was "
                        f"{cell.get('stateAfterCrash')}")
    if "dirtyAfterSave" in spec and cell.get("dirtyAfterSave") is not spec["dirtyAfterSave"]:
        problems.append(f"{cid}: dirtyAfterSave {cell.get('dirtyAfterSave')}")
    if "dirtyAfterRestart" in spec and cell.get("dirtyAfterRestart") is not spec["dirtyAfterRestart"]:
        problems.append(f"{cid}: dirtyAfterRestart {cell.get('dirtyAfterRestart')}")
    if "bothRejected" in spec:
        for half in ("first", "second"):
            if (cell.get(half) or {}).get("code") != spec["bothRejected"]:
                problems.append(f"{cid}: {half} returned "
                                f"{(cell.get(half) or {}).get('code')}")
    if "ceilingCode" in spec:
        restarts = cell.get("restarts") or []
        refused = [r for r in restarts if not r.get("ok")]
        if not refused:
            problems.append(f"{cid}: the ceiling was never reached")
        else:
            last = refused[0]
            if (last.get("error") or {}).get("code") != spec["ceilingCode"]:
                problems.append(f"{cid}: the ceiling code was "
                                f"{(last.get('error') or {}).get('code')}")
            if last.get("requiresPageReload") is not True:
                problems.append(f"{cid}: requiresPageReload was not set")

    return {"pass": not problems, "problems": problems, "notes": notes}


def judge(result: dict, evidence: Path, expected: dict = EXPECTED) -> dict:
    saved = evidence / "saved"
    abi = int(((result.get("cells") or {}).get("d0-inventory") or {})
              .get("abiVersion") or 2)
    cells = {cid: judge_cell(cid, cell, saved, abi, expected)
             for cid, cell in (result.get("cells") or {}).items()
             if cid != "d0-inventory"}
    problems = [p for item in cells.values() for p in item["problems"]]
    if not result.get("complete") or result.get("error"):
        problems.append(f"run did not complete: {result.get('error')}")
    if (result.get("attribution") or {}).get("consistent") is not True:
        problems.append("attribution inconsistent")
    missing = sorted(set(expected) - set(cells))
    if missing:
        problems.append(f"cells never run: {missing}")
    return {"pass": not problems, "abiVersion": abi, "cells": cells,
            "problems": problems, "browser": result.get("browserName")}


# Two kinds of mutation: to the RESULT (did the judge notice a different
# observation) and to the EXPECTATION (is the predicate wired to anything at
# all).  The first version only mutated results, so the zero-mutation predicate
# -- which reads saved documents, not fields -- was never exercised and its
# self-test passed while proving nothing.
SELF_TESTS = [
    ("a client refusal that was accepted",
     lambda r: r["cells"]["d2-refused-no-mutation-client"]["attempts"][0]
     .update({"error": None})),
    ("fail-closed removed",
     lambda r: r["cells"]["d2-unknown-rollback-fallback"].update(
         {"disposition": "refused-no-mutation"})),
    ("a boundary that did not demand a restart",
     lambda r: r["cells"]["d2-boundary-restart-required"].update(
         {"state": "ready"})),
    ("a rollback with no checkpoint behind it",
     lambda r: r["cells"]["d2-dispatched-rollback"].update(
         {"hasCheckpoint": False})),
    ("a generation ceiling that never refused",
     lambda r: r["cells"]["d2-generation-ceiling"].update(
         {"restarts": [{"ok": True, "generation": 2}]})),
    ("a cell that never ran",
     lambda r: r["cells"].pop("d2-crash-after-save")),
]


EXPECTATION_TESTS = [
    # Two saves that genuinely differ: one is d1-anchors before anything
    # happened, the other is paragraph-content after text was committed.  The
    # first attempt at this test compared two saves that happened to be
    # identical -- both cells refused, so neither body moved -- and a mutation
    # that changes nothing tests nothing.
    ("the zero-mutation predicate compares real documents",
     lambda e: e["d2-stale-revision"].update(
         {"zeroMutation": ("stale-revision-before",
                           "dispatched-rollback-before")})),
    ("a missing save is reported, not ignored",
     lambda e: e["d2-stale-revision"].update(
         {"zeroMutation": ("no-such-save", "stale-revision-after")})),
    # The rollback-restored check has to be able to say the rollback did NOT
    # restore.  Pointed at two documents that really differ, it must complain;
    # a check that only ever sees a document compared with itself is not a
    # check.
    ("the rollback-restored predicate compares real documents",
     lambda e: e["d2-refused-no-mutation-engine"].update(
         {"restoredAfterRecovery": ("engine-refusal-before",
                                    "dispatched-rollback-before")})),
    ("a rollback that did not report ok is caught",
     lambda e: e["d2-refused-no-mutation-engine"].update({"rollback": "not-ok"})),
]


def self_test(evidence: Path) -> int:
    result = json.loads((evidence / "result.json").read_text(encoding="utf-8"))
    base = judge(result, evidence)
    base_problems = set(base["problems"])
    failures = []
    for label, mutate in EXPECTATION_TESTS:
        expected = copy.deepcopy(EXPECTED)
        mutate(expected)
        after = judge(result, evidence, expected)
        if set(after["problems"]) == base_problems:
            failures.append(f"{label}: the verdict did not change")
    for label, mutate in SELF_TESTS:
        mutated = copy.deepcopy(result)
        try:
            mutate(mutated)
        except Exception as error:                          # noqa: BLE001
            failures.append(f"{label}: could not apply ({error})")
            continue
        after = judge(mutated, evidence)
        if set(after["problems"]) == base_problems:
            failures.append(f"{label}: the verdict did not change")
    print(json.dumps({"selfTest": len(SELF_TESTS) + len(EXPECTATION_TESTS),
                      "baseVerdict": "pass" if base["pass"] else "fail",
                      "baseProblems": sorted(base_problems),
                      "failures": failures, "pass": not failures},
                     indent=2, ensure_ascii=False))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.evidence)
    result = json.loads((args.evidence / "result.json").read_text(encoding="utf-8"))
    verdict = judge(result, args.evidence)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
