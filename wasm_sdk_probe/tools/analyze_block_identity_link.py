#!/usr/bin/env python3
"""Judge the v3 link against the predictions registered before it.

The predictions are in research/DESIGN-2026-08-16-caret-by-block-and-offset.md,
section 4 and the appendix.  The appendix, written before the link, records that
the implementation's deadline is 250 ms while D-BI-1 asks for 200, and that the
threshold was deliberately NOT moved -- so D-BI-1 is expected to fail by the
letter and hold by the substance, and both are reported.

Three outcomes, never two: HELD / FAILED / NOT_ESTABLISHED.

Usage:
  analyze_block_identity_link.py RUN.json
  analyze_block_identity_link.py --self-test
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

HELD, FAILED, NOT_ESTABLISHED = "HELD", "FAILED", "NOT_ESTABLISHED"

# The hash of an empty string under the engine's fingerprint function, both
# before and after the offset-basis typo was fixed.  A run whose paragraphs all
# report one of these measured no paragraph at all.
EMPTY_FINGERPRINTS = {"14650fb0739d0383", "cbf29ce484222325"}


def judge(run: dict) -> dict:
    cells = run.get("cells") or {}
    results: list[dict] = []

    def record(name: str, outcome: str, detail: str) -> None:
        results.append({"prediction": name, "outcome": outcome, "detail": detail})

    outside = cells.get("d-bi-1-outside-twice") or {}
    first = outside.get("outsideFirst") or {}
    second = outside.get("outsideSecond") or {}

    # ---- D-BI-1: the click that changes nothing still gets an answer -------
    if not first or not second:
        record("D-BI-1", NOT_ESTABLISHED, "the outside-click arms are missing")
    elif second.get("error"):
        record("D-BI-1", FAILED,
               f"the second click did not answer at all: {second['error']}")
    else:
        elapsed = second.get("elapsedMs")
        letter = isinstance(elapsed, int) and elapsed < 200
        record("D-BI-1", HELD if letter else FAILED,
               f"the second click at the same point answered in {elapsed} ms"
               f" via {second.get('completion')!r}"
               + ("" if letter else
                  " -- over the 200 ms registered, which the appendix said to"
                  " expect: the implementation's deadline is 250 ms and the"
                  " threshold was not moved to make this pass"))
        # Reported beside it, because the number that matters to a user is not
        # the threshold: the old path could not answer this click at all.
        record("D-BI-1 substance", HELD if isinstance(elapsed, int)
               and elapsed < 1000 else FAILED,
               f"bounded and small ({elapsed} ms) against the 30 s the caret"
               " confirmation used to wait out")

    # ---- D-BI-2: is the paragraph datum live in the PRODUCT build? ---------
    freshness = cells.get("d-bi-2-freshness") or {}
    on_anchor = (freshness.get("onAnchor") or {}).get("paragraph") or {}
    on_other = (freshness.get("onAnother") or {}).get("paragraph") or {}
    anchor_y = ((freshness.get("onAnchor") or {}).get("caret") or {}).get("y")
    other_y = ((freshness.get("onAnother") or {}).get("caret") or {}).get("y")
    if not on_anchor or not on_other:
        record("D-BI-2", NOT_ESTABLISHED, "the freshness arms are missing")
    elif anchor_y is None or other_y is None or anchor_y == other_y:
        record("D-BI-2", NOT_ESTABLISHED,
               "the two clicks did not land on different lines, so identical"
               " payloads would say nothing")
    elif on_anchor.get("fingerprint") in EMPTY_FINGERPRINTS:
        record("D-BI-2", FAILED,
               "every paragraph reports the fingerprint of an EMPTY string"
               f" ({on_anchor.get('fingerprint')}), so the datum is not stale --"
               " it is absent.  Accessibility is never enabled in this build.")
    elif on_anchor.get("fingerprint") == on_other.get("fingerprint"):
        record("D-BI-2", FAILED,
               "two different paragraphs report the same fingerprint while the"
               f" caret moved {anchor_y} -> {other_y}")
    else:
        record("D-BI-2", HELD,
               f"the reply named a different paragraph for each click"
               f" ({on_anchor.get('fingerprint')} vs"
               f" {on_other.get('fingerprint')}), with no wait of the caller's")

    # ---- D-BI-3: the barrier, and above all its CONTROL --------------------
    control = cells.get("d-bi-3-control") or {}
    empty = cells.get("d-bi-3-empty-paragraph") or {}
    if not control:
        record("D-BI-3 control", NOT_ESTABLISHED, "the control arm is missing")
    elif control.get("ok") is True:
        record("D-BI-3 control", HELD,
               "a list action on an ordinary paragraph still verifies"
               f" ({control.get('completion')}) -- the comparison introduces no"
               " false positive there")
    else:
        record("D-BI-3 control", FAILED,
               f"an ordinary list action stopped verifying: {control.get('code')}")

    shape = ((empty.get("formatBarrier") or {}).get("failureShape")
             if empty.get("reached") else None)
    if not empty or empty.get("reached") is not True:
        record("D-BI-3 empty", NOT_ESTABLISHED,
               f"the empty-paragraph cell was not reached: {empty.get('code')}")
    elif shape == "readback-is-a-different-paragraph":
        record("D-BI-3 empty", HELD,
               "the empty paragraph now reports that the read describes another"
               " paragraph, instead of claiming the document is in the wrong"
               " state")
    else:
        record("D-BI-3 empty", FAILED,
               f"the cell reported {shape!r}, not the new shape -- the"
               " comparison did not fire")

    outcomes = {r["prediction"]: r["outcome"] for r in results}
    return {
        "schemaVersion": 1,
        "release": "block-identity-after-link",
        "artifact": (run.get("manifest") or {}).get("wasmSha256"),
        "predictions": results,
        "held": sorted(k for k, v in outcomes.items() if v == HELD),
        "failed": sorted(k for k, v in outcomes.items() if v == FAILED),
        "notEstablished": sorted(
            k for k, v in outcomes.items() if v == NOT_ESTABLISHED),
    }


def _run(**over) -> dict:
    base = {
        "manifest": {"wasmSha256": "4dbe9b74"},
        "cells": {
            "d-bi-1-outside-twice": {
                "outsideFirst": {"elapsedMs": 39, "completion": "documented-callback-visible-cursor",
                                 "caret": {"y": 4812}, "paragraph": {"fingerprint": "aaa"}, "error": None},
                "outsideSecond": {"elapsedMs": 150, "completion": "verified-caret-readback",
                                  "caret": {"y": 4812}, "paragraph": {"fingerprint": "aaa"}, "error": None},
            },
            "d-bi-2-freshness": {
                "onAnchor": {"caret": {"y": 1999}, "paragraph": {"fingerprint": "aaa"}},
                "onAnother": {"caret": {"y": 2795}, "paragraph": {"fingerprint": "bbb"}},
            },
            "d-bi-3-control": {"ok": True, "completion": "verified-format-readback"},
            "d-bi-3-empty-paragraph": {
                "reached": True, "ok": False,
                "formatBarrier": {"failureShape": "readback-is-a-different-paragraph"}},
        },
    }
    for key, value in over.items():
        base["cells"][key.replace("_", "-")] = value
    return base


def self_test() -> int:
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    base = judge(_run())
    check("a round where everything holds has no failures",
          base["failed"] == [] and base["notEstablished"] == [],
          json.dumps(base))

    def rejudge(mutate):
        run = copy.deepcopy(_run())
        mutate(run["cells"])
        return judge(run)

    check("D-BI-1 fails when the second click is over the threshold",
          "D-BI-1" in rejudge(lambda c: c["d-bi-1-outside-twice"]["outsideSecond"]
                              .__setitem__("elapsedMs", 251))["failed"])
    check("D-BI-1's substance fails only when the answer is not bounded",
          "D-BI-1 substance" in rejudge(
              lambda c: c["d-bi-1-outside-twice"]["outsideSecond"]
              .__setitem__("elapsedMs", 30000))["failed"])
    check("D-BI-1 fails when the second click does not answer at all",
          "D-BI-1" in rejudge(lambda c: c["d-bi-1-outside-twice"]["outsideSecond"]
                              .__setitem__("error", {"code": "TIMEOUT"}))["failed"])
    check("D-BI-2 fails when every paragraph hashes to the empty string",
          "D-BI-2" in rejudge(lambda c: c["d-bi-2-freshness"]["onAnchor"]["paragraph"]
                              .__setitem__("fingerprint", "14650fb0739d0383"))["failed"])
    check("D-BI-2 fails when two paragraphs share a fingerprint",
          "D-BI-2" in rejudge(lambda c: c["d-bi-2-freshness"]["onAnother"]["paragraph"]
                              .__setitem__("fingerprint", "aaa"))["failed"])
    check("D-BI-2 is void when the caret never moved between the two clicks",
          "D-BI-2" in rejudge(lambda c: c["d-bi-2-freshness"]["onAnother"]["caret"]
                              .__setitem__("y", 1999))["notEstablished"])
    check("the control failing is a failure, not a footnote",
          "D-BI-3 control" in rejudge(
              lambda c: c["d-bi-3-control"].update(
                  {"ok": False, "code": "MUTATION_OUTCOME_UNKNOWN"}))["failed"])
    check("D-BI-3 fails when the empty cell reports the old shape",
          "D-BI-3 empty" in rejudge(
              lambda c: c["d-bi-3-empty-paragraph"]["formatBarrier"]
              .__setitem__("failureShape", "multi-block-readback"))["failed"])
    check("D-BI-3 is void when the cell was never reached",
          "D-BI-3 empty" in rejudge(
              lambda c: c["d-bi-3-empty-paragraph"].update(
                  {"reached": False, "code": "STALE_REVISION"}))["notEstablished"])

    total = 10
    print(f"\nself-test: {total - len(failures)}/{total} checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.run:
        parser.error("RUN.json is required")
    report = judge(json.loads(args.run.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
