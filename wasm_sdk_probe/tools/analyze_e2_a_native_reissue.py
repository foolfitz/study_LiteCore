#!/usr/bin/env python3
"""Judge the E2-A native re-issue run from the saved ODTs, not the callbacks.

Route C dispatches a closed action without reading any precondition, so the
second press reaches core exactly like the first.  The question this answers is
whether that is safe: a setter lands on the same state every time, a toggle
inverts, and only the saved documents can tell them apart -- the callbacks are
the thing under test (finding 020 showed their success/wasModified fields lie).

Verdict per case, from three consecutive presses after the paragraph was put in
the opposite state:

    setter    issue1 == issue2 == issue3, and issue1 differs from reset
    toggle    issue2 == reset and issue3 == issue1
    inert     nothing ever changed -- the command did not reach the paragraph
    other     anything else, which is a result to read, not to bucket
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"

# The three paragraphs the run never targets.  If one of them moves, the caret
# was not where the run assumed and the case's own reading is worthless -- a
# failure mode a per-case check alone cannot see.
WITNESSES = ("E1-STYLED-HEADING", "E1-LIST-ONE", "E1-STYLED-END")


def tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def list_style_kinds(root: ElementTree.Element) -> dict[str, str]:
    """Map each list style name to bullet or number.

    A paragraph's own markup says it is in a list but not which kind, and
    unordered vs ordered is precisely the distinction two of the closed actions
    promise.  Resolve it from the list style definition rather than from the
    command that was dispatched, which would assume the answer.
    """
    kinds: dict[str, str] = {}
    for style in root.iter(tag(TEXT_NS, "list-style")):
        name = style.get(tag(STYLE_NS, "name"))
        if not name:
            continue
        levels = {child.tag for child in style}
        if tag(TEXT_NS, "list-level-style-number") in levels:
            kinds[name] = "number"
        elif tag(TEXT_NS, "list-level-style-bullet") in levels:
            kinds[name] = "bullet"
        else:
            kinds[name] = "other"
    return kinds


def paragraph_style_parents(root: ElementTree.Element) -> dict[str, str]:
    """Map each automatic paragraph style to the named style it derives from.

    Joining a list gives the paragraph an automatic style (P1, P2, ...) whose
    number depends on how many other automatic styles the save happened to
    mint.  The named parent is what the paragraph is actually formatted as, and
    it is stable across snapshots; the generated name is not.
    """
    parents: dict[str, str] = {}
    for style in root.iter(tag(STYLE_NS, "style")):
        if style.get(tag(STYLE_NS, "family")) != "paragraph":
            continue
        name = style.get(tag(STYLE_NS, "name"))
        parent = style.get(tag(STYLE_NS, "parent-style-name"))
        if name and parent:
            parents[name] = parent
    return parents


def paragraph_text(element: ElementTree.Element) -> str:
    return "".join(element.itertext())


def describe(path: Path, anchor: str) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        content = archive.read("content.xml")
    root = ElementTree.fromstring(content)
    kinds = list_style_kinds(root)
    style_parents = paragraph_style_parents(root)

    parents = {child: parent for parent in root.iter() for child in parent}
    for name in ("p", "h"):
        for element in root.iter(tag(TEXT_NS, name)):
            if anchor not in paragraph_text(element):
                continue
            ancestors = []
            node = parents.get(element)
            while node is not None:
                ancestors.append(node)
                node = parents.get(node)
            containers = [node for node in ancestors
                          if node.tag == tag(TEXT_NS, "list")]
            list_style = (containers[0].get(tag(TEXT_NS, "style-name"))
                          if containers else None)
            style_name = element.get(tag(TEXT_NS, "style-name"))
            return {
                "found": True,
                "element": name,
                "styleName": style_name,
                "resolvedStyle": style_parents.get(style_name, style_name),
                "inList": bool(containers),
                "listStyle": list_style,
                "listKind": kinds.get(list_style) if list_style else None,
                "listDepth": len(containers),
            }
    return {"found": False}


def shape(reading: dict[str, Any]) -> tuple:
    """The comparable part of a reading.

    Automatic style names (P1/L1, P2/L2, ...) are minted per save and renumber
    whenever another automatic style appears, so comparing them reports a
    difference on every snapshot where the target paragraph joined a list.  The
    first version of this analyzer did compare them and duly announced that the
    untouched list items had changed; they had not.  The list *kind* is the
    promise, the generated name is not.
    """
    return (reading.get("found"), reading.get("element"),
            reading.get("resolvedStyle"), reading.get("inList"),
            reading.get("listKind"), reading.get("listDepth"))


def witness_shapes(path: Path) -> dict[str, list]:
    return {text: list(shape(describe(path, text))) for text in WITNESSES}


def classify(readings: dict[str, dict[str, Any]], steps: tuple) -> str:
    reset, one, two, three = (shape(readings[step]) for step in steps)
    if one == two == three == reset:
        return "inert"
    if one == two == three:
        return "setter"
    if two == reset and three == one:
        return "toggle"
    return "other"


def dispatch_records(run: Path) -> dict[str, dict[str, Any]]:
    """Group the raw callback stream by the label of the dispatch it followed.

    Recorded, not judged: finding 020 is exactly the reason the verdict above
    comes from the documents.  These fields are here so the browser round can be
    compared against native on the same terms.
    """
    labelled: dict[str, dict[str, Any]] = {}
    current: str | None = None
    path = run / "callbacks.jsonl"
    if not path.exists():
        return labelled
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("stage") == "dispatch-enter":
            current = record.get("label")
            labelled[current] = {"command": record.get("command"),
                                 "states": [], "results": []}
            continue
        if current is None:
            continue
        name = record.get("name")
        payload = record.get("payload") or ""
        if name == "LOK_CALLBACK_STATE_CHANGED":
            if payload.startswith((".uno:DefaultBullet", ".uno:DefaultNumbering",
                                   ".uno:StyleApply")):
                labelled[current]["states"].append(payload)
        elif name == "LOK_CALLBACK_UNO_COMMAND_RESULT":
            labelled[current]["results"].append(payload)
    return labelled


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads((args.run / "cases.json").read_text(encoding="utf-8"))
    anchor = manifest["anchor"]
    steps = tuple(manifest["steps"])
    plan = manifest["cases"]

    baseline = describe(args.fixture, anchor)
    callbacks = dispatch_records(args.run)

    def snapshot(item: dict[str, Any], step: str) -> Path:
        return args.run / item["group"] / f"{item['name']}-{step}.odt"

    # The witness baseline is the run's own first snapshot, not the fixture.
    # LibreOffice normalises on save -- a hand-authored bare <text:list> comes
    # back with an explicit list style, an unstyled paragraph comes back as
    # Standard -- so measuring collateral damage against the fixture reports a
    # difference that no dispatch caused.  What matters here is whether *our*
    # dispatches moved a paragraph nobody targeted, and the first snapshot is
    # already past the normalisation.
    first_snapshot = snapshot(plan[0], steps[0])
    baseline_witnesses = (witness_shapes(first_snapshot)
                          if first_snapshot.exists() else None)

    cases: dict[str, Any] = {}
    missing: list[str] = []
    for item in plan:
        key = f"{item['group']}/{item['name']}"
        readings: dict[str, Any] = {}
        for step in steps:
            path = snapshot(item, step)
            if not path.exists():
                missing.append(str(path.relative_to(args.run)))
                readings[step] = {"found": False, "missing": True}
                continue
            readings[step] = describe(path, anchor)
            readings[step]["witnessesUnchanged"] = (
                witness_shapes(path) == baseline_witnesses)
        verdict = "incomplete" if any(
            reading.get("missing") for reading in readings.values()
        ) else classify(readings, steps)
        cases[key] = {
            "dispatched": item,
            "verdict": verdict,
            "readings": readings,
            "witnessesUnchanged": all(
                reading.get("witnessesUnchanged", False)
                for reading in readings.values()),
            "callbacks": {step: callbacks.get(f"{key}-{step}", {})
                          for step in steps},
            # A repeat that lands on the right state but broadcasts nothing is
            # not a success for a postcondition-only barrier -- it is
            # indistinguishable from a command that never arrived.  Counted
            # separately from the verdict, because the document and the callback
            # stream disagree about whether anything happened.
            "silentRepeats": [
                step for step in steps[2:]
                if not callbacks.get(f"{key}-{step}", {}).get("states")
            ],
        }

    groups = sorted({item["group"] for item in plan})
    by_group = {
        group: {
            "allSetters": all(
                case["verdict"] == "setter" for key, case in cases.items()
                if case["dispatched"]["group"] == group),
            "silentRepeats": {
                key: case["silentRepeats"] for key, case in cases.items()
                if case["dispatched"]["group"] == group and case["silentRepeats"]
            },
        }
        for group in groups
    }

    summary = {
        "anchor": anchor,
        "fixtureBaseline": baseline,
        "witnessBaselineSnapshot": str(first_snapshot.relative_to(args.run)),
        "witnessBaseline": baseline_witnesses,
        "cases": cases,
        "missingSnapshots": missing,
        "verdicts": {key: case["verdict"] for key, case in cases.items()},
        "byGroup": by_group,
        # Route C is only safe if every closed action is a setter.  Say so as a
        # single field so a later run cannot pass by having most of them work.
        "allSetters": all(case["verdict"] == "setter"
                          for case in cases.values()),
        "allWitnessesUnchanged": all(case["witnessesUnchanged"]
                                     for case in cases.values()),
        # The postcondition-only barrier needs a state payload to complete.
        "anySilentRepeat": any(case["silentRepeats"] for case in cases.values()),
    }
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")

    print("-- re-issue verdict per closed action --")
    for key, case in cases.items():
        print(f"   {key:<42} {case['verdict']}")
        for step in steps:
            reading = case["readings"][step]
            states = case["callbacks"].get(step, {}).get("states") or []
            print(f"      {step:<7} element={reading.get('element')} "
                  f"style={reading.get('resolvedStyle')} "
                  f"inList={reading.get('inList')} "
                  f"kind={reading.get('listKind')} "
                  f"witnesses={'ok' if reading.get('witnessesUnchanged') else 'CHANGED'} "
                  f"states={states}")
    print()
    for group in groups:
        print(f"   {group:<8} allSetters={by_group[group]['allSetters']} "
              f"silentRepeats={by_group[group]['silentRepeats'] or 'none'}")
    print()
    print(f"   allSetters:              {summary['allSetters']}")
    print(f"   allWitnessesUnchanged:   {summary['allWitnessesUnchanged']}")
    print(f"   anySilentRepeat:         {summary['anySilentRepeat']}")
    print(f"   missing snapshots:       {missing or 'none'}")
    print(f"   written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
