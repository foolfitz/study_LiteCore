#!/usr/bin/env python3
"""SPEC E2-B section 3: judge the gate from the saved documents.

Separate from the runner on purpose.  The runner drives a browser and keeps
files; this reads only those files, so the verdict can be recomputed at any time
without a browser and without re-running anything.

The criteria are SPEC E2-B 3.4 and 3.5, and the predictions are in
findings/evidence/sdk-e2/discovery/e2b-gate/PREDICTION.md, committed before the
harness existed.

The load-bearing criterion is 3.4 item 6: the paragraphs the arm did NOT select
must be unchanged.  Every action here is paragraph-level, so without that a
range which silently collapsed to a caret would still satisfy every other check.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import re

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"

# P1, P2, L1 ... are generated per document and RENUMBER whenever the document
# changes: inserting one list paragraph pushes every later automatic name along
# by one.  Comparing them directly reports untouched paragraphs as changed --
# which is exactly what the first version of this analyzer did, and it reported
# five changed paragraphs for a one-paragraph action.  What the contract is
# about is the element kind, the outline level, whether the paragraph is in a
# list and what kind of list that is.
AUTOMATIC_NAME = re.compile(r"^(P|L|T|Sect|fr|Mfr)\d+$")


def opaque(name: str | None) -> str | None:
    if name is None:
        return None
    return "(auto)" if AUTOMATIC_NAME.match(name) else name

try:
    from xml.etree import ElementTree as ET
except ImportError:  # pragma: no cover
    raise SystemExit("ElementTree unavailable")


def list_kinds(root) -> dict[str, str]:
    """Map each list style name to "bullet" or "number".

    Bullet versus number is the thing set-list-unordered and set-list-ordered
    actually differ in, and it is not visible on the paragraph at all -- it
    lives on the list style in automatic-styles.
    """
    kinds: dict[str, str] = {}
    automatic = root.find(f"{{{OFFICE_NS}}}automatic-styles")
    if automatic is None:
        return kinds
    for style in automatic.findall(f"{{{TEXT_NS}}}list-style"):
        name = style.get(f"{{{STYLE_NS}}}name")
        for level in style:
            tag = level.tag.split("}")[1]
            if tag.startswith("list-level-style-"):
                kinds[name] = tag.rsplit("-", 1)[-1]
                break
    return kinds


def paragraphs(odt: Path) -> list[dict[str, Any]]:
    """One row per paragraph: element kind, named style, list kind, text.

    Deliberately not a byte comparison of content.xml, and deliberately not a
    comparison of automatic style names either -- both move on their own.
    """
    with zipfile.ZipFile(odt) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    body = root.find(f"{{{OFFICE_NS}}}body/{{{OFFICE_NS}}}text")
    kinds = list_kinds(root)
    rows: list[dict[str, Any]] = []

    def walk(node, in_list: str | None) -> None:
        for child in node:
            tag = child.tag.split("}")[1]
            if tag in ("p", "h"):
                rows.append({
                    "kind": tag,
                    "style": opaque(child.get(f"{{{TEXT_NS}}}style-name")),
                    "outline": child.get(f"{{{TEXT_NS}}}outline-level"),
                    "list": in_list,
                    "text": "".join(child.itertext()),
                })
            elif tag == "list":
                walk(child, kinds.get(child.get(f"{{{TEXT_NS}}}style-name"), "list"))
            elif tag in ("list-item", "list-header"):
                walk(child, in_list)

    walk(body, None)
    return rows


def signature(row: dict[str, Any]) -> tuple:
    return (row["kind"], row["style"], row["outline"], row["list"])


def compare(before: list[dict], after: list[dict]) -> dict[str, Any]:
    """Which paragraphs changed, keyed by their text so reordering is visible."""
    if len(before) != len(after):
        return {"paragraphCountChanged": {"before": len(before), "after": len(after)}}
    changed, unchanged = [], []
    for index, (b, a) in enumerate(zip(before, after)):
        entry = {"index": index, "text": b["text"][:40]}
        if b["text"] != a["text"]:
            entry["textChanged"] = {"before": b["text"][:40], "after": a["text"][:40]}
            changed.append(entry)
        elif signature(b) != signature(a):
            entry["before"] = signature(b)
            entry["after"] = signature(a)
            changed.append(entry)
        else:
            unchanged.append(index)
    return {"changed": changed, "unchangedIndexes": unchanged}


# Which paragraph each arm selected, by the anchor its range was aimed at, and
# how many paragraphs it is allowed to have changed.
ARM_TARGETS = {
    "A1-bullet-from-range": ("E1-LC-ISOLATED", 1),
    "A2-ordered-from-range": ("E1-LC-ISOLATED", 1),
    "A3-list-none-from-range": ("E1-LC-BULLET-ONE", 1),
    "A4-heading-from-range": ("E1-LC-ISOLATED", 1),
    "A5-body-from-range": ("E1-LC-HEADING", 1),
    "G1-wrapped-line-range": ("G1WRAP", 1),
    "G1c-single-line-control": ("E2B-WRAP-HEAD", 1),
    "G2-reverse-range": ("E1-LC-ISOLATED", 1),
    "G3-cross-paragraph-range": ("E1-MULTI-START", 2),
}


def judge_round(arm: str, record: dict, diff: dict) -> dict[str, Any]:
    anchor, allowed = ARM_TARGETS[arm]
    verdict: dict[str, Any] = {"arm": arm, "round": record.get("round")}

    # 3.4 pre-dispatch quartet.  Failing these makes the run VOID, not failed:
    # the arm did not put the engine in the state it claims to measure.
    reasons = []
    if record.get("selectStatus") != "completed":
        reasons.append(f"range select {record.get('selectStatus')}")
    if record.get("collapsedBeforeDispatch") is not False:
        reasons.append("selection was collapsed at dispatch")
    text = (record.get("selectionBeforeDispatch") or {}).get("text") or ""
    if anchor not in text:
        reasons.append(f"selection did not contain {anchor!r}")
    rectangles = record.get("rectanglesBeforeDispatch")
    if arm == "G1-wrapped-line-range" and (rectangles or 0) < 2:
        reasons.append(f"only {rectangles} rectangle: the fixture did not "
                       "provide a wrapped line, so this case was not exercised")
    # The control runs the same span mechanism over a paragraph that does not
    # wrap.  More than one rectangle there would mean the count is not reading
    # visual lines, and G1's own count would then say nothing -- so this is
    # VOID for the control, and the summary reports it next to G1.
    if arm == "G1c-single-line-control" and (rectangles or 0) != 1:
        reasons.append(f"{rectangles} rectangles on a paragraph that does not "
                       "wrap: the rectangle count is not reading visual lines, "
                       "so G1's count cannot be read either")
    if arm == "G3-cross-paragraph-range" and "\n" not in text:
        reasons.append("selection did not span a paragraph break")
    if reasons:
        verdict["void"] = reasons
        return verdict

    changed = diff.get("changed")
    if changed is None:
        verdict["fail"] = ["paragraph count changed", diff]
        return verdict
    verdict["changedParagraphs"] = [c["text"] for c in changed]
    verdict["changedCount"] = len(changed)

    problems = []
    if not any(anchor in c["text"] for c in changed):
        problems.append(f"the selected paragraph ({anchor}) did not change")
    if len(changed) > allowed:
        problems.append(f"{len(changed)} paragraphs changed, at most {allowed} "
                        "were selected")
    if arm != "G3-cross-paragraph-range" and record.get("collapsedAfterDispatch") is not True:
        problems.append("selection was not collapsed after the dispatch")

    if arm == "G3-cross-paragraph-range":
        # The pre-registered criterion, restored.
        #
        # The first version of this analyzer gave G3 allowed=2 and called two
        # changed paragraphs a pass -- which quietly replaced the criterion
        # PREDICTION.md had committed before the harness existed.  That
        # prediction says: reporting success while the barrier can only have
        # verified one paragraph is under-verification, and under-verification
        # is the failure this arm exists to find.  The document outcome is
        # recorded separately, because it is correct and that matters for
        # choosing the fix.
        verdict["documentOutcomeCorrect"] = len(changed) == allowed
        if record.get("actionStatus") == "completed" and len(changed) > 1:
            problems.append(
                "reported success while changing "
                f"{len(changed)} paragraphs; the barrier reads back exactly one "
                "(.uno:SelectText selects one paragraph), so the success claim "
                "covers less than the mutation")

    verdict["pass" if not problems else "fail"] = problems or True
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path,
                        help="directory holding result.json and saved/")
    parser.add_argument("--fixtures", type=Path,
                        default=Path(__file__).resolve().parent.parent
                        / "dist" / "e1-fixtures")
    args = parser.parse_args()

    result = json.loads((args.evidence / "result.json").read_text(encoding="utf-8"))
    # The baseline is a save through the same engine with no action, not the
    # authored fixture: the ODT export normalises what the fixture leaves
    # implicit, so the authored file reports every paragraph as changed.
    pristine = {}
    for arm in result.get("arms") or []:
        name = arm.get("arm") or ""
        if not name.startswith("BASELINE-"):
            continue
        saved = args.evidence / "saved" / f"{name}-round1.odt"
        if saved.exists():
            pristine[arm.get("fixture")] = paragraphs(saved)
    if not pristine:
        print(json.dumps({"error": "no BASELINE arm saved a document; "
                                   "without it there is nothing to compare against"},
                         ensure_ascii=False))
        return 1
    verdicts = []
    for arm in result.get("arms") or []:
        name = arm.get("arm")
        if name not in ARM_TARGETS:
            continue
        fixture = arm.get("fixture")
        if fixture not in pristine:
            verdicts.append({"arm": name, "round": None,
                             "void": [f"no baseline save for {fixture}"]})
            continue
        for record in arm.get("rounds") or []:
            saved = args.evidence / "saved" / f"{name}-round{record.get('round')}.odt"
            if not saved.exists():
                verdicts.append({"arm": name, "round": record.get("round"),
                                 "void": ["no saved document"]})
                continue
            diff = compare(pristine[fixture], paragraphs(saved))
            verdicts.append(judge_round(name, record, diff))

    summary: dict[str, Any] = {
        "artifact": result.get("artifact"),
        "browser": result.get("browser"),
        "verdicts": verdicts,
        "byArm": {},
    }
    for name in ARM_TARGETS:
        rows = [v for v in verdicts if v["arm"] == name]
        summary["byArm"][name] = {
            "rounds": len(rows),
            "passed": sum(1 for v in rows if v.get("pass")),
            "failed": sum(1 for v in rows if v.get("fail")),
            "void": sum(1 for v in rows if v.get("void")),
        }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    (args.evidence / "verdict.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Non-zero unless every arm has at least one round and none failed.  Void
    # rounds do not pass; they say the case was not exercised.
    ok = all(v["rounds"] > 0 and v["failed"] == 0 for v in summary["byArm"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
