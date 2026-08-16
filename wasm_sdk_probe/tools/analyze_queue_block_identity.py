#!/usr/bin/env python3
"""Judge the block-identity native round against its registered predictions.

Written BEFORE the probe was run, so the criteria cannot be edited into
agreement with what came back.  The predictions are in
findings/evidence/queue-block-identity/native/PREDICTION.md; this file is only
their executable form.

Three outcomes per prediction, never two:

  HELD             the measurement is what was predicted
  FAILED           the measurement is the opposite -- which for P-BI-2a and
                   P-BI-4 would be GOOD NEWS for the queue item, and is
                   recorded as plainly as the other direction
  NOT_ESTABLISHED  the arm is missing, or its control did not hold, so the
                   round says nothing about it

`--self-test` flips each predicate and requires the verdict to move.  A check
that cannot be shown to fail is not a check.

Usage:
  analyze_queue_block_identity.py RUN_DIR
  analyze_queue_block_identity.py --self-test
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

HELD = "HELD"
FAILED = "FAILED"
NOT_ESTABLISHED = "NOT_ESTABLISHED"


def load(run: Path) -> list[dict]:
    rows = []
    for line in (run / "captures.jsonl").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def arms(rows: list[dict]) -> dict[str, dict]:
    return {row["arm"]: row for row in rows if row.get("probe") == "arm"}


def field(row: dict | None, name: str):
    """One field out of an arm's verbatim payload, or None."""
    if not row:
        return None
    try:
        return json.loads(row.get("payload") or "").get(name)
    except (ValueError, AttributeError):
        return None


def judge(rows: list[dict]) -> dict:
    by_arm = arms(rows)
    environment = next((r for r in rows if r.get("probe") == "environment"), {})
    results: list[dict] = []

    def record(name: str, outcome: str, detail: str) -> None:
        results.append({"prediction": name, "outcome": outcome, "detail": detail})

    # The control first.  If accessibility never came up, every "the payloads
    # are identical" prediction below would hold for the wrong reason.
    control = by_arm.get("control-anchor")
    control_content = field(control, "content")
    control_ok = control_content == "BI-ANCHOR-ONE"
    record("P-BI-0 control",
           HELD if control_ok else FAILED,
           f"control-anchor content={control_content!r}"
           f" (a11yAvailable={environment.get('a11yAvailable')})")

    def void(name: str, why: str) -> None:
        record(name, NOT_ESTABLISHED, why)

    # ---- P-BI-1: is finding 046's overshoot separable by content? ---------
    empty = by_arm.get("empty-caret")
    readback = by_arm.get("empty-after-bullet-readback")
    if not control_ok:
        void("P-BI-1", "the control did not hold")
    elif not empty or not readback:
        void("P-BI-1", "empty-caret or empty-after-bullet-readback is missing")
    else:
        dispatch_content = field(empty, "content")
        read_text = readback.get("plainText") or ""
        neighbour_in_read = "BI-AFTER-EMPTY" in read_text
        if dispatch_content == "" and neighbour_in_read:
            record("P-BI-1", HELD,
                   "caret paragraph reported content='' while the barrier's read"
                   f" returned {read_text!r} -- a comparison separates them")
        elif dispatch_content != "":
            record("P-BI-1", FAILED,
                   f"the empty paragraph reported content={dispatch_content!r},"
                   " not ''")
        else:
            record("P-BI-1", FAILED,
                   f"the read did not reach the neighbour: {read_text!r}")

    # ---- P-BI-2a: a repeated click below the text -------------------------
    first = by_arm.get("below-first")
    same_x = by_arm.get("below-second-same-x")
    other_x = by_arm.get("below-second-other-x")
    after = by_arm.get("below-control-on-text")
    clicks_still_delivered = (
        after is not None and first is not None
        and after.get("payload") != first.get("payload"))
    if not control_ok:
        void("P-BI-2a", "the control did not hold")
    elif not first or not same_x:
        void("P-BI-2a", "below-first or below-second-same-x is missing")
    elif not clicks_still_delivered:
        void("P-BI-2a",
             "below-control-on-text did not show a click still arriving, so"
             " 'nothing moved' is not distinguishable from 'nothing was sent'")
    elif first.get("payload") == same_x.get("payload"):
        record("P-BI-2a", HELD,
               "a second click below the text at the same x left the payload"
               " byte-for-byte identical")
    else:
        record("P-BI-2a", FAILED,
               f"the payload moved: {first.get('payload')!r} ->"
               f" {same_x.get('payload')!r}")

    # ---- P-BI-2b: the same click at a different x -------------------------
    #
    # Judged on the arm whose x is INSIDE the last line's text.  Round 1 had no
    # such arm -- it clicked at the end of the line and then further right, two
    # x on the same side of the text end -- so round 1 cannot answer this, and
    # says so rather than reporting the FAILED that a bare position comparison
    # would have produced.  The addendum in PREDICTION.md records that this
    # weakens the criterion, and why: it is a statement about the probe, not
    # about core.
    inside_x = by_arm.get("below-second-inside-x")
    if not control_ok:
        void("P-BI-2b", "the control did not hold")
    elif not first:
        void("P-BI-2b", "below-first is missing")
    elif not inside_x:
        void("P-BI-2b",
             "no arm clicked at an x inside the last line's text, so this round"
             " cannot distinguish 'x is ignored' from 'both x were past the"
             " end of the line'")
    else:
        before, later = field(first, "position"), field(inside_x, "position")
        if before is not None and later is not None and before != later:
            record("P-BI-2b", HELD,
                   f"position {before} -> {later} for a click below the text at"
                   " an x inside the line, which geometry cannot see")
        else:
            record("P-BI-2b", FAILED,
                   f"position did not move: {before} -> {later}")

    # ---- P-BI-2c: x separates only inside the line's text ------------------
    if not control_ok:
        void("P-BI-2c", "the control did not hold")
    elif not first or not inside_x or not other_x:
        void("P-BI-2c", "round 2's below-* arms are not all present")
    else:
        end_offset = field(first, "position")
        saturates = field(other_x, "position") == end_offset
        separates = field(inside_x, "position") != end_offset
        if saturates and separates:
            record("P-BI-2c", HELD,
                   f"past the end of the line every x reads {end_offset};"
                   f" inside it reads {field(inside_x, 'position')}")
        else:
            record("P-BI-2c", FAILED,
                   f"saturatesPastTheEnd={saturates} separatesInside={separates}")

    # ---- P-BI-3: same line, different x -----------------------------------
    left, right = by_arm.get("long-left"), by_arm.get("long-right")
    if not control_ok:
        void("P-BI-3", "the control did not hold")
    elif not left or not right:
        void("P-BI-3", "long-left or long-right is missing")
    elif not (left.get("caretValid") and right.get("caretValid")):
        void("P-BI-3",
             "one of the two arms has no caret rectangle, so 'the same line'"
             " is not established")
    elif left.get("caretY") != right.get("caretY"):
        void("P-BI-3",
             f"the two x landed on different lines (y {left.get('caretY')} vs"
             f" {right.get('caretY')}), so the fixture wrapped and this arm"
             " measures something else")
    else:
        same_content = field(left, "content") == field(right, "content")
        moved = field(left, "position") != field(right, "position")
        if same_content and moved:
            record("P-BI-3", HELD,
                   f"one paragraph, position {field(left, 'position')} ->"
                   f" {field(right, 'position')}")
        else:
            record("P-BI-3", FAILED,
                   f"sameContent={same_content} positionMoved={moved}")

    # ---- P-BI-4: two paragraphs with identical text ------------------------
    twin_a, twin_b = by_arm.get("twin-first"), by_arm.get("twin-second")
    if not control_ok:
        void("P-BI-4", "the control did not hold")
    elif not twin_a or not twin_b:
        void("P-BI-4", "twin-first or twin-second is missing")
    elif not (twin_a.get("caretValid") and twin_b.get("caretValid")):
        void("P-BI-4",
             "one of the twins has no caret rectangle, so 'the caret moved'"
             " is not established and an identical payload says nothing")
    elif twin_a.get("caretY") == twin_b.get("caretY"):
        void("P-BI-4",
             "the caret did not move between the twins, so an identical payload"
             " would say nothing")
    elif twin_a.get("payload") == twin_b.get("payload"):
        record("P-BI-4", HELD,
               "two different paragraphs, one byte-for-byte payload"
               f" (caret y {twin_a.get('caretY')} -> {twin_b.get('caretY')})")
    else:
        record("P-BI-4", FAILED,
               f"the payloads differ: {twin_a.get('payload')!r} vs"
               f" {twin_b.get('payload')!r}")

    # ---- P-BI-5: is the click below the text delivered at all? -------------
    from_elsewhere = by_arm.get("below-from-elsewhere")
    before_below = by_arm.get("before-below-from-elsewhere")
    if not control_ok:
        void("P-BI-5", "the control did not hold")
    elif not from_elsewhere:
        void("P-BI-5", "below-from-elsewhere is missing")
    elif not before_below:
        # Adversarial review, 2026-08-16: without this the arm's whole premise
        # -- "from a caret on ANOTHER paragraph" -- was the probe's word for it.
        # A caret already on BI-LAST and a click that never arrived produce the
        # same row.
        void("P-BI-5",
             "no arm records where the caret was immediately before the click,"
             " so 'from elsewhere' is the probe's claim rather than a reading")
    elif field(before_below, "content") == "BI-LAST":
        void("P-BI-5",
             "the caret was already in the last paragraph before the click, so"
             " landing there afterwards shows nothing")
    elif field(from_elsewhere, "content") == "BI-LAST":
        record("P-BI-5", HELD,
               "from a caret on another paragraph, a click below the text"
               " reports the last paragraph, so it arrives and clamps")
    else:
        record("P-BI-5", FAILED,
               "the click below the text left the caret on"
               f" {field(from_elsewhere, 'content')!r}")

    # ---- P-BI-6: x on the line, x below it ---------------------------------
    on_line = by_arm.get("on-line-inside-x")
    below_inside = by_arm.get("below-from-elsewhere-inside-x")
    if not control_ok:
        void("P-BI-6", "the control did not hold")
    elif not on_line or not below_inside or not from_elsewhere:
        void("P-BI-6", "the line/below pair is not all present")
    elif on_line.get("clickX") != below_inside.get("clickX"):
        void("P-BI-6",
             f"the two arms did not use the same x ({on_line.get('clickX')} vs"
             f" {below_inside.get('clickX')}), so 'the same x' is not what was"
             " measured")
    elif not (isinstance(on_line.get("clickY"), int)
              and isinstance(below_inside.get("clickY"), int)
              and on_line["clickY"] < below_inside["clickY"]):
        void("P-BI-6",
             "the arm named 'on the line' was not clicked above the one named"
             f" 'below it' (y {on_line.get('clickY')} vs"
             f" {below_inside.get('clickY')})")
    else:
        end_offset = field(from_elsewhere, "position")
        on_line_moved = field(on_line, "position") != end_offset
        below_saturated = field(below_inside, "position") == end_offset
        if on_line_moved and below_saturated:
            record("P-BI-6", HELD,
                   f"the same x reads {field(on_line, 'position')} on the line"
                   f" and {end_offset} below it")
        else:
            record("P-BI-6", FAILED,
                   f"onLineMoved={on_line_moved}"
                   f" belowSaturated={below_saturated}"
                   f" (line={field(on_line, 'position')},"
                   f" below={field(below_inside, 'position')},"
                   f" end={end_offset})")

    # ---- P-BI-7: does the SHIPPED barrier's read escape? -------------------
    shipped = by_arm.get("empty-after-selecttext")
    bulleted = by_arm.get("empty-after-bullet")
    if not control_ok:
        void("P-BI-7", "the control did not hold")
    elif not shipped or not bulleted:
        void("P-BI-7", "empty-after-selecttext or empty-after-bullet is missing")
    else:
        dispatch_content = (field(bulleted, "content") or "").strip()
        read_text = (shipped.get("plainText") or "").strip()
        # Named, not merely different.  Adversarial review, 2026-08-16: a read
        # of the SAME paragraph that differed only in whitespace, indentation or
        # serialisation would have satisfied `read_text != dispatch_content`,
        # and the predicate would have reported an overshoot that did not
        # happen.  The neighbour has a name in the fixture; require it.
        escaped = (bool(read_text) and read_text != dispatch_content
                   and "BI-AFTER-EMPTY" in read_text)
        if escaped:
            record("P-BI-7", HELD,
                   f"the caret paragraph read {dispatch_content!r} while"
                   f" .uno:SelectText returned {read_text!r}")
        else:
            record("P-BI-7", FAILED,
                   f"the shipped read returned {read_text!r}, which does not"
                   " contain the neighbouring paragraph -- no overshoot on"
                   " this fixture")

    outcomes = {r["prediction"]: r["outcome"] for r in results}
    return {
        "schemaVersion": 1,
        "release": "queue-verify-caret-by-block-identity",
        "arm": "native",
        "environment": environment,
        "predictions": results,
        "held": sorted(k for k, v in outcomes.items() if v == HELD),
        "failed": sorted(k for k, v in outcomes.items() if v == FAILED),
        "notEstablished": sorted(
            k for k, v in outcomes.items() if v == NOT_ESTABLISHED),
        "controlHeld": control_ok,
    }


# --------------------------------------------------------------------- tests

def _row(arm: str, content: str, position: int, y: int, **extra) -> dict:
    payload = json.dumps({"content": content, "position": position,
                          "start": position, "end": position})
    return {"probe": "arm", "arm": arm, "payload": payload, "caretY": y,
            "caretValid": True, "clickX": -1, "clickY": -1, **extra}


def _fixture_rows() -> list[dict]:
    """A round where every prediction holds, so each flip has somewhere to fall."""
    return [
        {"probe": "environment", "a11yAvailable": True, "viewId": 0},
        _row("control-anchor", "BI-ANCHOR-ONE", 0, 100),
        _row("twin-first", "BI-TWIN", 0, 400),
        _row("twin-second", "BI-TWIN", 0, 500),
        _row("long-left", "BI-LONG-START wwww BI-LONG-END", 0, 600),
        _row("long-right", "BI-LONG-START wwww BI-LONG-END", 30, 600),
        # The end of `BI-LAST` is offset 7, and the first click below the text
        # lands there: that is what the run does, and the P-BI-2c arms are about
        # what happens on either side of it.
        _row("below-first", "BI-LAST", 7, 700),
        _row("below-second-same-x", "BI-LAST", 7, 700),
        _row("below-second-other-x", "BI-LAST", 7, 700),
        _row("below-second-inside-x", "BI-LAST", 5, 700),
        _row("below-control-on-text", "BI-ANCHOR-ONE", 0, 100),
        _row("on-line-inside-x", "BI-LAST", 5, 700, clickX=1900, clickY=3752),
        _row("before-below-from-elsewhere", "BI-ANCHOR-ONE", 13, 100),
        _row("below-from-elsewhere", "BI-LAST", 7, 700, clickX=2337, clickY=5000),
        _row("before-below-inside-x", "BI-ANCHOR-ONE", 13, 100),
        _row("below-from-elsewhere-inside-x", "BI-LAST", 7, 700,
             clickX=1900, clickY=5000),
        _row("empty-caret", "", 0, 200),
        _row("empty-after-bullet", "• ", 2, 200),
        dict(_row("empty-after-bullet-readback", "", 0, 200),
             plainText="\nBI-AFTER-EMPTY\n"),
        dict(_row("empty-after-selecttext", "• ", 2, 200),
             plainText="• \nBI-AFTER-EMPTY\n"),
    ]


def self_test() -> int:
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    base = judge(_fixture_rows())
    check("the fixture round holds every prediction",
          base["failed"] == [] and base["notEstablished"] == []
          and len(base["held"]) == 10, json.dumps(base["predictions"]))

    def rejudge(mutate) -> dict:
        rows = copy.deepcopy(_fixture_rows())
        mutate(rows)
        return judge(rows)

    def find(rows, arm):
        return next(r for r in rows if r.get("arm") == arm)

    def set_payload(row, **fields):
        payload = json.loads(row["payload"])
        payload.update(fields)
        row["payload"] = json.dumps(payload)

    check("a broken control voids every prediction",
          rejudge(lambda rows: set_payload(find(rows, "control-anchor"),
                                           content="something else"))
          ["notEstablished"] == ["P-BI-1", "P-BI-2a", "P-BI-2b", "P-BI-2c",
                                 "P-BI-3", "P-BI-4", "P-BI-5", "P-BI-6",
                                 "P-BI-7"])
    check("P-BI-1 fails when the read never reaches the neighbour",
          "P-BI-1" in rejudge(lambda rows: find(
              rows, "empty-after-bullet-readback").update(
                  {"plainText": "\n\n"}))["failed"])
    check("P-BI-1 fails when the empty paragraph is not reported empty",
          "P-BI-1" in rejudge(lambda rows: set_payload(
              find(rows, "empty-caret"), content="not empty"))["failed"])
    check("P-BI-2a fails when the repeated click does move the payload",
          "P-BI-2a" in rejudge(lambda rows: set_payload(
              find(rows, "below-second-same-x"), position=3))["failed"])
    check("P-BI-2a is void when the control click shows nothing arriving",
          "P-BI-2a" in rejudge(lambda rows: set_payload(
              find(rows, "below-control-on-text"),
              content="BI-LAST", position=7, start=7,
              end=7))["notEstablished"])
    check("P-BI-2b fails when an x inside the line does not move the position",
          "P-BI-2b" in rejudge(lambda rows: set_payload(
              find(rows, "below-second-inside-x"), position=7))["failed"])
    check("P-BI-2b is void with no arm inside the line -- round 1's shape",
          "P-BI-2b" in rejudge(lambda rows: rows.remove(
              find(rows, "below-second-inside-x")))["notEstablished"])
    check("P-BI-2c fails when the clamp does not saturate past the end",
          "P-BI-2c" in rejudge(lambda rows: set_payload(
              find(rows, "below-second-other-x"), position=9))["failed"])
    check("P-BI-3 is void when the fixture wrapped",
          "P-BI-3" in rejudge(lambda rows: find(rows, "long-right").update(
              {"caretY": 640}))["notEstablished"])
    check("P-BI-3 fails when one line does not distinguish two x",
          "P-BI-3" in rejudge(lambda rows: set_payload(
              find(rows, "long-right"), position=0))["failed"])
    check("P-BI-4 is void when the caret never left the first twin",
          "P-BI-4" in rejudge(lambda rows: find(rows, "twin-second").update(
              {"caretY": 400}))["notEstablished"])
    check("P-BI-4 fails when the twins are distinguishable after all",
          "P-BI-4" in rejudge(lambda rows: set_payload(
              find(rows, "twin-second"), position=1))["failed"])
    check("a missing arm is not established rather than passed",
          "P-BI-4" in rejudge(lambda rows: rows.remove(
              find(rows, "twin-second")))["notEstablished"])

    check("P-BI-5 fails when the click below the text lands nowhere new",
          "P-BI-5" in rejudge(lambda rows: set_payload(
              find(rows, "below-from-elsewhere"),
              content="BI-ANCHOR-ONE"))["failed"])
    check("P-BI-6 fails when the same x does not move the offset on the line",
          "P-BI-6" in rejudge(lambda rows: set_payload(
              find(rows, "on-line-inside-x"), position=7))["failed"])
    check("P-BI-6 fails when x is carried below the text as well",
          "P-BI-6" in rejudge(lambda rows: set_payload(
              find(rows, "below-from-elsewhere-inside-x"),
              position=5))["failed"])
    # Sub-clauses that the review of 2026-08-16 showed were unexercised: each
    # of these mutations moves ONLY the clause named, so removing that clause
    # from the predicate would make the self-test go green with it gone.
    check("P-BI-2c fails when an x inside the line does not separate",
          "P-BI-2c" in rejudge(lambda rows: set_payload(
              find(rows, "below-second-inside-x"), position=7))["failed"])
    check("P-BI-3 fails when the two x are in different paragraphs",
          "P-BI-3" in rejudge(lambda rows: set_payload(
              find(rows, "long-right"), content="a different paragraph"))["failed"])
    check("P-BI-3 is void when a caret rectangle is not valid",
          "P-BI-3" in rejudge(lambda rows: find(rows, "long-right").update(
              {"caretValid": False}))["notEstablished"])
    check("P-BI-4 is void when a caret rectangle is not valid",
          "P-BI-4" in rejudge(lambda rows: find(rows, "twin-second").update(
              {"caretValid": False}))["notEstablished"])
    check("P-BI-5 is void when the caret was already in the last paragraph",
          "P-BI-5" in rejudge(lambda rows: set_payload(
              find(rows, "before-below-from-elsewhere"),
              content="BI-LAST"))["notEstablished"])
    check("P-BI-5 is void with no arm recording where the caret was",
          "P-BI-5" in rejudge(lambda rows: rows.remove(
              find(rows, "before-below-from-elsewhere")))["notEstablished"])
    check("P-BI-6 is void when the two arms did not use the same x",
          "P-BI-6" in rejudge(lambda rows: find(
              rows, "on-line-inside-x").update({"clickX": 999}))["notEstablished"])
    check("P-BI-6 is void when the 'on the line' arm was not above the other",
          "P-BI-6" in rejudge(lambda rows: find(
              rows, "on-line-inside-x").update({"clickY": 9999}))["notEstablished"])
    check("P-BI-7 fails when the read differs only in whitespace",
          "P-BI-7" in rejudge(lambda rows: find(
              rows, "empty-after-selecttext").update(
                  {"plainText": "   \u2022   "}))["failed"])
    check("P-BI-7 fails when the shipped read stays in its own paragraph",
          "P-BI-7" in rejudge(lambda rows: find(
              rows, "empty-after-selecttext").update(
                  {"plainText": "• "}))["failed"])

    total = 27
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
        parser.error("RUN_DIR is required")
    report = judge(load(args.run))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["controlHeld"] else 1


if __name__ == "__main__":
    sys.exit(main())
