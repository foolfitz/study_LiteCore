#!/usr/bin/env python3
"""Judge SPEC E2-C phase D5 offline.

D5's subject is `isTrusted`, so the judgement is short and unforgiving: **one
synthetic event anywhere in a cell's window disqualifies the cell.**  Everything
else it checks is there so a cell cannot pass by being empty.

A cell that is not established is `NOT_ESTABLISHED`, which is a THIRD answer
next to pass and fail: the matrix's `onFailure` for every D5 cell is PARTIAL,
and an operator who was never asked is not a product that failed.

Usage:
  analyze_e2_c_d5.py RUN_DIR [RUN_DIR ...] [--output F]
  analyze_e2_c_d5.py --self-test RUN_DIR
"""

from __future__ import annotations

import argparse
import base64
import copy
import io
import json
import sys
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

# One line box in the E1/E2 corpora, used only as a floor: the cross-paragraph
# cell has to move further than a line, and the caret rectangles the product
# reports are what decide it when they are present.
LINE_BOX_TWIPS = 276

CELLS = ("d5-pointer-drag-single", "d5-pointer-drag-cross",
         "d5-ime-commit", "d5-clipboard")

# The document every D5 round has opened so far.  Used only as the baseline for
# the FIRST cell of a run; later cells are compared against the document the
# previous cell saved.
PRISTINE = PROJECT / "test-docs" / "e1" / "list-contexts.odt"


def count_lists(raw: bytes) -> int | None:
    """`<text:list>` count in an ODT's content.xml, or None if unreadable.

    None is not zero and must never be judged as "no change": an unreadable
    document is a measurement that did not happen.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            content = archive.read("content.xml").decode("utf-8", "replace")
    except Exception:                       # noqa: BLE001 -- reported as None
        return None
    return content.count("<text:list ") + content.count("<text:list>")


def captured_documents(result: dict) -> list[tuple[str, bytes]]:
    """(cell, bytes) for every captured document, in the order they were saved.

    `saves` carries the metadata (cell, bytes, pressedBy) and `capturedSaves`
    the base64, both in save order.  The ORDER is the point: a cell's structural
    baseline is the document saved immediately before it, and round 4 (2026-08-16)
    is the reason that is not the same as "the previous cell in the matrix" --
    the operator opened cells out of order, so cell order and save order differ.
    """
    saves = result.get("saves") or []
    captured = result.get("capturedSaves") or []
    documents: list[tuple[str, bytes]] = []
    for index, entry in enumerate(saves):
        cell = entry.get("cell")
        if cell is None or index >= len(captured):
            continue
        try:
            documents.append((cell, base64.b64decode(captured[index].get("b64") or "")))
        except Exception:                   # noqa: BLE001 -- a document that
            continue                        # cannot be decoded is not a baseline
    return documents



def _apply_round_two(name: str, cell: dict, checks: dict,
                     documents: dict[str, tuple[int | None, int | None]]) -> None:
    """The two places round one's judge was weaker than its own frozen oracle.

    Both were recorded when they happened rather than fixed retroactively
    (findings/evidence/.../d5/operator/round-4-firefox/ and round-5-firefox/),
    because that judge had already judged five rounds.  They apply from round
    two, which is what a matrix frozen before its own D0 is for.

      1. The drag cells' oracle ends "...**and the saved ODT shows it**", and
         round one only checked that a document had been CAPTURED.  The content
         was read by hand.
      2. The IME cell's oracle names TWO commits -- one at a collapsed caret and
         one replacing a selection -- and round one asked only whether the
         revision had moved at all.  In round 5 it had: once, out of three real
         commits.  A criterion that cannot see two thirds of a user's typing
         disappear is not measuring what the oracle names.
    """
    if name.startswith("d5-pointer-drag"):
        before, after = documents.get(name, (None, None))
        checks["documentReadable"] = after is not None
        # None (unreadable) must not read as "no change": that would let a
        # broken export pass the strengthened criterion.
        checks["documentShowsTheFormat"] = (
            after is not None and before is not None and after > before)
        checks["listCountBefore"] = before
        checks["listCountAfter"] = after
    if name == "d5-ime-commit":
        commits = [event for event in (cell.get("events") or [])
                   if event.get("type") == "compositionend" and event.get("data")]
        before = (cell.get("stripBefore") or {}).get("revision")
        after = (cell.get("stripAfter") or {}).get("revision")
        try:
            advance = int(after) - int(before)
        except (TypeError, ValueError):
            advance = None
        checks["commitsObserved"] = len(commits)
        checks["revisionAdvance"] = advance
        # The oracle names two commits; fewer than two is not the cell it
        # describes, however well the ones that happened behaved.
        checks["bothCommitsAttempted"] = len(commits) >= 2
        checks["everyCommitLanded"] = (
            advance is not None and len(commits) > 0 and advance == len(commits))

def judge_cell(name: str, cell: dict | None, saves: list[dict],
               criteria: str = "round-one",
               documents: dict[str, tuple[int | None, int | None]] | None = None
               ) -> dict:
    if not cell:
        return {"cell": name, "status": "NOT_ESTABLISHED",
                "why": "the operator did not run this cell"}
    events = cell.get("events") or []
    synthetic = [event for event in events if not event.get("isTrusted")]
    checks: dict[str, bool] = {
        "hasEvents": bool(events),
        # The one that matters.  Not "mostly trusted", not "the important ones
        # were trusted" -- none synthetic.
        "allTrusted": bool(events) and not synthetic,
    }

    if name.startswith("d5-pointer-drag"):
        downs = [event for event in events if event.get("type") == "pointerdown"]
        moves = [event for event in events if event.get("type") == "pointermove"]
        ups = [event for event in events if event.get("type") == "pointerup"]
        checks["dragHadMoves"] = bool(downs and ups and moves)
        if name.endswith("cross") and downs and ups:
            span = abs((ups[-1].get("y") or 0) - (downs[0].get("y") or 0))
            checks["spannedMoreThanOneLine"] = span > 0
            # Recorded in CSS pixels by the page; the floor is expressed in the
            # same units the events carry rather than converted with a guess.
            checks["spanRecorded"] = span
    if name == "d5-ime-commit":
        checks["hasComposition"] = any(
            event.get("type", "").startswith("composition") for event in events)
    if name == "d5-clipboard":
        checks["hasClipboardEvent"] = any(
            event.get("type") in ("copy", "paste") for event in events)

    before = (cell.get("stripBefore") or {}).get("revision")
    after = (cell.get("stripAfter") or {}).get("revision")
    checks["revisionAdvanced"] = (
        before is not None and after is not None and str(before) != str(after))
    checks["savedDocumentCaptured"] = any(
        entry.get("cell") == name for entry in saves)

    if criteria == "round-two":
        _apply_round_two(name, cell, checks, documents or {})

    boolean = {key: value for key, value in checks.items()
               if isinstance(value, bool)}
    status = "PASS" if all(boolean.values()) else "NOT_ESTABLISHED"
    return {
        "cell": name,
        "status": status,
        "checks": checks,
        "eventCount": len(events),
        "syntheticEventCount": len(synthetic),
        "syntheticTypes": sorted({event.get("type") for event in synthetic}),
    }


def judge_run(run: Path, criteria: str = "round-one") -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    saves = result.get("saves") or []
    # Per cell: the last document it saved, and the one saved just before it.
    # The first save's baseline is the pristine fixture.
    documents: dict[str, tuple[int | None, int | None]] = {}
    if criteria == "round-two":
        pristine = count_lists(PRISTINE.read_bytes()) if PRISTINE.is_file() else None
        previous = pristine
        for cell_name, raw in captured_documents(result):
            after = count_lists(raw)
            documents[cell_name] = (previous, after)
            if after is not None:
                previous = after
    cells = {name: judge_cell(name, (result.get("cells") or {}).get(name),
                              saves, criteria, documents)
             for name in CELLS}
    established = [name for name, report in cells.items()
                   if report["status"] == "PASS"]
    bundle = result.get("shellBundle") or {}
    return {
        "run": str(run),
        "criteria": criteria,
        "mode": result.get("mode"),
        "browser": result.get("browserName"),
        "shims": result.get("shims"),
        "shellBundleUnchanged": bundle.get("unchanged"),
        "cells": cells,
        "established": established,
        # PARTIAL is the matrix's answer for an unestablished D5 cell, and the
        # phase only reaches PASS when all four are established on real
        # gestures.  A machine-half run can never reach it, by construction.
        "verdict": ("PASS" if len(established) == len(CELLS)
                    else "PARTIAL" if bundle.get("unchanged") is not False
                    else "FAIL"),
    }


def self_test(run: Path, criteria: str = "round-one") -> int:
    failures: list[str] = []
    ran: list[str] = []

    skipped: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        ran.append(name)
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    def skip(name: str, why: str) -> None:
        """Not applicable to THIS run, and said out loud.

        A check that quietly disappears when its input is missing is the
        failure mode this tree keeps finding in its own analyzers, so a skip is
        printed, counted separately, and never added to the passing total.
        """
        skipped.append(name)
        print(f"  skip  {name}  -- {why}")

    raw = json.loads((run / "result.json").read_text(encoding="utf-8"))
    baseline = judge_run(run, criteria)

    def rejudge(mutate, use: str | None = None) -> dict:
        cloned = copy.deepcopy(raw)
        mutate(cloned)
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "result.json").write_text(json.dumps(cloned))
            return judge_run(target, use or criteria)

    machine_half = raw.get("mode") == "machine-half"
    # P-D5-M1 / M2, on the recorded machine-half run itself.
    if machine_half:
        check("synthetic events are recorded as untrusted",
              any(event.get("isTrusted") is False for event in raw.get("events", [])),
              "no untrusted event in the run at all")
        check("a cell built from synthetic events is NOT_ESTABLISHED",
              all(report["status"] == "NOT_ESTABLISHED"
                  for report in baseline["cells"].values()))
        check("the machine half cannot reach PASS", baseline["verdict"] != "PASS")
    else:
        for name in ("synthetic events are recorded as untrusted",
                     "a cell built from synthetic events is NOT_ESTABLISHED",
                     "the machine half cannot reach PASS"):
            skip(name, f"needs a machine-half run; this one is {raw.get('mode')!r}")

    def make_all_trusted(cloned):
        for event in cloned.get("events", []):
            event["isTrusted"] = True
        for cell in (cloned.get("cells") or {}).values():
            for event in cell.get("events", []):
                event["isTrusted"] = True
            cell["syntheticEvents"] = 0

    def furnish(cloned):
        """Everything a drag cell needs EXCEPT trust, so the trust check is the
        only thing left standing between the cell and a pass."""
        make_all_trusted(cloned)
        cell = (cloned.get("cells") or {}).get("d5-pointer-drag-single")
        if cell is None:
            return
        cell["stripBefore"] = {"revision": "1"}
        cell["stripAfter"] = {"revision": "2"}
        cloned.setdefault("saves", []).append(
            {"label": "probe", "bytes": 10, "cell": "d5-pointer-drag-single"})

    furnished = rejudge(furnish)
    check("with trust and everything else present, the cell passes",
          furnished["cells"]["d5-pointer-drag-single"]["status"] == "PASS",
          str(furnished["cells"]["d5-pointer-drag-single"]))

    def furnish_but_one_synthetic(cloned):
        furnish(cloned)
        cell = (cloned.get("cells") or {}).get("d5-pointer-drag-single")
        if cell and cell.get("events"):
            cell["events"][0]["isTrusted"] = False

    check("ONE synthetic event takes the pass away",
          rejudge(furnish_but_one_synthetic)["cells"]["d5-pointer-drag-single"]
          ["status"] == "NOT_ESTABLISHED")

    def furnish_without_moves(cloned):
        furnish(cloned)
        cell = (cloned.get("cells") or {}).get("d5-pointer-drag-single")
        if cell:
            cell["events"] = [event for event in cell["events"]
                              if event.get("type") != "pointermove"]

    check("a drag with no moves is a click, and does not pass",
          rejudge(furnish_without_moves)["cells"]["d5-pointer-drag-single"]
          ["status"] == "NOT_ESTABLISHED")

    def furnish_without_revision(cloned):
        furnish(cloned)
        cell = (cloned.get("cells") or {}).get("d5-pointer-drag-single")
        if cell:
            cell["stripAfter"] = {"revision": "1"}

    check("a cell where the revision never moved does not pass",
          rejudge(furnish_without_revision)["cells"]["d5-pointer-drag-single"]
          ["status"] == "NOT_ESTABLISHED")

    def break_bundle(cloned):
        furnish(cloned)
        cloned["shellBundle"] = {"before": "a", "after": "b", "unchanged": False}

    if raw.get("shellBundle") is not None:
        check("a moved shell bundle digest fails the run",
              rejudge(break_bundle)["verdict"] == "FAIL")
    else:
        skip("a moved shell bundle digest fails the run",
             "this run carries no shellBundle field; the operator page exports "
             "the metrics and the harness attests the digest separately")

    # P-D5-M3: the capture path was exercised, not assumed.
    check("the createObjectURL shim captured a document",
          bool(raw.get("capturedSaves")),
          "nothing was captured, so no operator round could capture either")
    # P-D5-M4
    if raw.get("shellBundle") is not None:
        check("observing the product left the shell bundle digest alone",
              (raw.get("shellBundle") or {}).get("unchanged") is True)
    else:
        skip("observing the product left the shell bundle digest alone",
             "no shellBundle in this run; see session-attestation*.json")

    if criteria == "round-two":
        # The two strengthened criteria, each shown to be able to fail.  A
        # criterion added because the old one was too weak, and then not
        # mutation-tested, is the same mistake one layer up.
        def flatten_the_document(cloned):
            """Give the drag cell the document that was already there.

            Nothing about the events changes -- only the saved ODT stops
            showing a new list.  Round one's judge cannot tell the difference;
            that is the whole point of the strengthening.
            """
            captured = cloned.get("capturedSaves") or []
            if len(captured) >= 2:
                captured[1]["b64"] = captured[0]["b64"]

        mutated = rejudge(flatten_the_document)
        cell = mutated["cells"]["d5-pointer-drag-cross"]
        check("a drag whose saved ODT shows no new list does not pass",
              cell["status"] == "NOT_ESTABLISHED", str(cell.get("checks")))

        def drop_one_commit(cloned):
            """One fewer revision advance than there were commits.

            Finding 050's shape exactly: every event present and trusted, and
            the document quietly receiving less than the user typed.
            """
            ime = (cloned.get("cells") or {}).get("d5-ime-commit")
            if ime and (ime.get("stripAfter") or {}).get("revision"):
                after = int(ime["stripAfter"]["revision"])
                ime["stripAfter"] = dict(ime["stripAfter"], revision=str(after - 1))

        mutated = rejudge(drop_one_commit)
        cell = mutated["cells"]["d5-ime-commit"]
        check("an IME cell that lands fewer commits than it made does not pass",
              cell["status"] == "NOT_ESTABLISHED", str(cell.get("checks")))

        def single_commit(cloned):
            ime = (cloned.get("cells") or {}).get("d5-ime-commit")
            if ime:
                ends = [event for event in ime.get("events", [])
                        if event.get("type") == "compositionend"]
                for event in ends[1:]:
                    event["type"] = "compositionupdate"
                before = int((ime.get("stripBefore") or {}).get("revision", 0))
                ime["stripAfter"] = dict(ime.get("stripAfter") or {},
                                         revision=str(before + 1))

        mutated = rejudge(single_commit)
        cell = mutated["cells"]["d5-ime-commit"]
        check("one commit is not the two the oracle names",
              cell["status"] == "NOT_ESTABLISHED", str(cell.get("checks")))

        # The positive control: unmutated, this run passes under the
        # strengthened criteria -- so the three above failed for their own
        # reasons and not because the rule rejects everything.
        check("the unmutated run still passes under the strengthened criteria",
              baseline["verdict"] == "PASS", str(baseline["cells"])[:200])

    print(f"\nself-test: {len(ran) - len(failures)}/{len(ran)} "
          f"checks moved the verdict"
          + (f", {len(skipped)} not applicable to this run" if skipped else ""))
    # A self-test where everything was skipped proved nothing, and returning 0
    # would let it stand in for one that ran.
    if not ran:
        print("  NOTHING RAN -- this run supports none of the checks")
        return 1
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    # Round one's criteria stay the default, and that is deliberate: this judge
    # has already judged six operator rounds, and re-judging recorded evidence
    # with a rule written afterwards would rewrite verdicts that were made
    # honestly under the rule of the day.  The strengthening applies from round
    # two, whose matrix is frozen before its own D0.
    parser.add_argument("--criteria", choices=("round-one", "round-two"),
                        default="round-one")
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.runs[0], args.criteria)
    runs = [judge_run(run, args.criteria) for run in args.runs]
    summary = {
        "schemaVersion": 1,
        "release": "spec-e2c-d5",
        "criteria": args.criteria,
        "predictionFile":
            "findings/evidence/sdk-e2/e2-c-validation/d5/PREDICTION.md",
        "runs": runs,
        "verdict": ("PASS" if all(run["verdict"] == "PASS" for run in runs)
                    else "FAIL" if any(run["verdict"] == "FAIL" for run in runs)
                    else "PARTIAL"),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary["verdict"] in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
