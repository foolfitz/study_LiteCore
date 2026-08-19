#!/usr/bin/env python3
"""Finding 059's negative arm and its state-cache priming, judged offline.

Reads a round from tools/run_f059_native_negative_arm.sh and answers the two
questions that were owed before the engine's predicate could change:

  1. CAN THE PREDICATE SAY NO?  Ten arms on 2026-08-18 showed it agreeing nine
     times and disagreeing never, because the intended refusal (setViewReadOnly)
     did not refuse.  A predicate seen only to agree is not yet a predicate.

  2. IS THE CACHE PRIMED?  `formatBarrierPostconditionMet()` returns false both
     when the state is UNKNOWN and when it is known and wrong
     (probe_engine.cpp:1189).  Those are not the same verdict, and if nothing
     has ever broadcast the slot then every "failed" it reports is really "I
     don't know" (finding 021's shape).

The document is the oracle, and it is read by resolving the marker's own
`text:style-name` to its `<style:style>`, never by grepping for
`fo:font-weight`.  A marker that is ABSENT is its own answer -- in a protected
section not even the typing takes -- and is reported as absent rather than as
unstyled, because "nothing was typed" and "text was typed and left normal" are
different observations.

Usage:
  analyze_f059_negative_arm.py ROUND_DIR
  analyze_f059_negative_arm.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

# The four slots the engine dispatches, and the state name core broadcasts.
SLOTS = {".uno:Bold": "bold", ".uno:Italic": "italic",
         ".uno:Underline": "underline", ".uno:Strikeout": "strikeout"}

STATE = re.compile(r"^(\.uno:\w+)=(true|false)$")


def apply_state(cache: dict, entries) -> None:
    """Fold broadcasts into the cache the engine would keep."""
    for entry in entries or []:
        match = STATE.match(entry.strip())
        if match and match.group(1) in SLOTS:
            cache[SLOTS[match.group(1)]] = match.group(2) == "true"


def marker_weight(content: str, marker: str) -> str | None:
    """'bold' / 'normal' / 'inherited', or None when the marker is not there."""
    span = re.search(
        r'<text:span text:style-name="([^"]+)">' + re.escape(marker)
        + r"</text:span>", content)
    if not span:
        return None if marker not in content else "inherited"
    style = re.search(
        r'<style:style style:name="' + re.escape(span.group(1))
        + r'"[^>]*>(.*?)</style:style>', content, re.S)
    if not style:
        return "inherited"
    weight = re.search(r'fo:font-weight="([^"]+)"', style.group(1))
    return weight.group(1) if weight else "inherited"


def load(round_dir: Path) -> tuple[list[dict], str]:
    arms = []
    for line in (round_dir / "arms.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("probe") == "arm":
            arms.append(record)
    with zipfile.ZipFile(round_dir / "negative-arms.odt") as archive:
        content = archive.read("content.xml").decode("utf-8")
    return arms, content


def analyse(arms: list[dict], content: str) -> dict:
    cache: dict = {}
    rows = []
    priming = None
    for arm in arms:
        apply_state(cache, arm.get("fromCaretMove"))
        if priming is None:
            # What was known BEFORE anything was dispatched: this is the answer
            # to the priming question, and it is taken from the first arm
            # because that arm's caret move is the only thing that has happened.
            priming = {"slotsKnownBeforeAnyDispatch": sorted(cache),
                       "values": dict(cache)}
        apply_state(cache, arm.get("stateChanges"))
        requested = arm.get("requested")
        weight = marker_weight(content, arm["marker"])
        observed = cache.get("bold")
        known = "bold" in cache
        # The engine's predicate, spelled out: KNOWN and equal.  Split into two
        # fields so "unknown" never wears the word "failed".
        predicate = ("unknown" if not known
                     else "met" if observed == requested
                     else "not-met")
        document = ("not-typed" if weight is None
                    else "applied" if weight == "bold"
                    else "not-applied")
        rows.append({
            "arm": arm["arm"],
            "arguments": arm.get("arguments"),
            "requested": requested,
            "commandSucceeded": ('"success": true' in (arm.get("result") or "")),
            "broadcastAfterDispatch": [e for e in arm.get("stateChanges") or []
                                       if e.startswith(".uno:Bold=")],
            "observedAfterDispatch": observed,
            "known": known,
            "predicate": predicate,
            "markerWeight": weight,
            "document": document,
            # The only question that matters per arm: did the two agree?
            "agrees": (predicate == "met") == (document == "applied"),
        })
    negatives = [row for row in rows
                 if row["requested"] is not None and row["document"] != "applied"]
    positives = [row for row in rows
                 if row["requested"] is True and row["document"] == "applied"]
    disagreements = [row for row in rows if not row["agrees"]]
    report = {
        "schemaVersion": 1,
        "release": "f059-negative-arm",
        "arms": rows,
        "priming": priming,
        "negativeArms": [row["arm"] for row in negatives],
        "positiveArms": [row["arm"] for row in positives],
        "disagreements": [row["arm"] for row in disagreements],
        # The round is only worth reading if BOTH exist: without a positive the
        # probe measured nothing, and without a negative the predicate has still
        # never been seen to disagree -- which is the whole point of the round.
        "hasPositive": bool(positives),
        "hasNegative": bool(negatives),
        "predicateSaidNoOnEveryNegative":
            all(row["predicate"] == "not-met" for row in negatives),
        "predicateNeverGuessed": all(row["known"] for row in rows[1:]),
    }
    report["ok"] = bool(report["hasPositive"] and report["hasNegative"]
                        and not disagreements
                        and report["predicateSaidNoOnEveryNegative"]
                        and report["predicateNeverGuessed"])
    return report


def self_test() -> int:
    """Every rule has to be able to say the round failed."""
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    def doc(pairs: dict) -> str:
        """A content.xml carrying one span per marker, with resolvable styles."""
        styles = "".join(
            f'<style:style style:name="S{i}">'
            f'<style:text-properties fo:font-weight="{weight}"/></style:style>'
            for i, weight in enumerate(pairs.values()) if weight)
        body = "".join(
            f'<text:span text:style-name="S{i}">{marker}</text:span>'
            for i, (marker, weight) in enumerate(pairs.items()) if weight)
        return ("<office:automatic-styles>" + styles
                + "</office:automatic-styles><office:body>" + body
                + "</office:body>")

    def arm(name, marker, requested, caret=None, changes=None, result=""):
        return {"probe": "arm", "arm": name, "marker": marker,
                "requested": requested, "arguments": "",
                "fromCaretMove": caret or [], "stateChanges": changes or [],
                "result": result}

    # A round that should pass: primed at load, one positive, one negative.
    good = analyse([
        arm("control", "AAA", None, caret=[".uno:Bold=false"]),
        arm("positive", "BBB", True, changes=[".uno:Bold=true"]),
        arm("negative", "CCC", True, caret=[".uno:Bold=false"]),
    ], doc({"AAA": "normal", "BBB": "bold", "CCC": "normal"}))
    verify("a clean round passes", good["ok"], json.dumps(good["disagreements"]))
    verify("the negative arm is named", good["negativeArms"] == ["negative"])
    verify("the positive arm is named", good["positiveArms"] == ["positive"])

    # No negative: the predicate has still never disagreed, so the round is NOT
    # enough -- this is exactly the state 2026-08-18 left behind.
    no_negative = analyse([
        arm("control", "AAA", None, caret=[".uno:Bold=false"]),
        arm("positive", "BBB", True, changes=[".uno:Bold=true"]),
    ], doc({"AAA": "normal", "BBB": "bold"}))
    verify("a round with no negative arm does not pass",
           not no_negative["ok"] and not no_negative["hasNegative"])

    # No positive: the probe measured nothing and a negative read from it would
    # be indistinguishable from a broken probe.
    no_positive = analyse([
        arm("control", "AAA", None, caret=[".uno:Bold=false"]),
        arm("negative", "CCC", True),
    ], doc({"AAA": "normal", "CCC": "normal"}))
    verify("a round with no positive arm does not pass",
           not no_positive["ok"] and not no_positive["hasPositive"])

    # The document applied it and nothing broadcast: the predicate would call a
    # WORKING command failed.  This is the observation that would sink the
    # replacement predicate, so it must be reported and must fail the round.
    silent = analyse([
        arm("control", "AAA", None, caret=[".uno:Bold=false"]),
        arm("silent", "BBB", True),
    ], doc({"AAA": "normal", "BBB": "bold"}))
    verify("a command that applied without broadcasting is a disagreement",
           not silent["ok"] and silent["disagreements"] == ["silent"])

    # Never primed: every verdict is "unknown", and unknown must not be scored
    # as a refusal.
    unprimed = analyse([
        arm("control", "AAA", None),
        arm("negative", "CCC", True),
    ], doc({"AAA": "normal", "CCC": "normal"}))
    verify("an unprimed cache reports unknown, not not-met",
           unprimed["arms"][1]["predicate"] == "unknown"
           and not unprimed["predicateNeverGuessed"]
           and not unprimed["ok"])

    # A marker that was never typed is not the same as one left normal.  The
    # caret move away from the previous arm resets the cache, which is what the
    # real round does and what makes the arm readable at all.
    absent = analyse([
        arm("control", "AAA", None, caret=[".uno:Bold=false"]),
        arm("positive", "BBB", True, changes=[".uno:Bold=true"]),
        arm("refused", "GGG", True, caret=[".uno:Bold=false"]),
    ], doc({"AAA": "normal", "BBB": "bold"}))
    verify("an absent marker is reported as not-typed",
           absent["arms"][2]["document"] == "not-typed"
           and absent["arms"][2]["markerWeight"] is None
           and absent["ok"])

    # The hazard the case above was accidentally written as, kept because it is
    # real: if the caret move does NOT reset the cache, the predicate reads a
    # stale `true` and approves an arm on which nothing happened at all.  That
    # is the predicate agreeing with itself, and the round must not pass.
    stale = analyse([
        arm("control", "AAA", None, caret=[".uno:Bold=false"]),
        arm("positive", "BBB", True, changes=[".uno:Bold=true"]),
        arm("refused", "GGG", True),
    ], doc({"AAA": "normal", "BBB": "bold"}))
    verify("a stale cache approving an arm that typed nothing is a disagreement",
           not stale["ok"] and stale["disagreements"] == ["refused"]
           and stale["arms"][2]["predicate"] == "met")

    # The style has to be RESOLVED, not grepped: a document containing the word
    # bold somewhere else must not make an unstyled marker look applied.
    grep_bait = ('<office:automatic-styles>'
                 '<style:style style:name="S0">'
                 '<style:text-properties fo:font-weight="bold"/></style:style>'
                 '</office:automatic-styles><office:body>'
                 '<text:span text:style-name="S0">ZZZ</text:span>BBB'
                 '</office:body>')
    verify("a marker outside any span is not read as styled",
           marker_weight(grep_bait, "BBB") == "inherited"
           and marker_weight(grep_bait, "ZZZ") == "bold")

    print(f"\nself-test: {10 - len(failures)}/10 checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("round", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.round:
        parser.error("a round directory is required")
    arms, content = load(args.round)
    report = analyse(arms, content)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
