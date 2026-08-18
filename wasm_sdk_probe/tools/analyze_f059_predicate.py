#!/usr/bin/env python3
"""Finding 059's replacement predicate, judged offline.

Reads a round produced by tools/run_f059_native_predicate.sh and answers, per
arm and per slot:

  * what core BROADCAST      (LOK_CALLBACK_STATE_CHANGED for that slot)
  * what the DOCUMENT SAYS   (the automatic style actually attached to that
                              arm's marker run, resolved through content.xml)
  * whether the two agree

The document side is the oracle. It is read by resolving the marker's own
`text:style-name` to its `<style:style>` and reading the property, never by
grepping for `fo:font-weight`: the E1 corpus declares styles it never uses and
carries a bold heading, so a document-wide grep passes on a document where the
marker is plainly normal.

Predictions this scores are in
findings/evidence/059/native/predicate/PREDICTION.md, committed before the probe
ran.

Usage:
  analyze_f059_predicate.py ROUND_DIR
  analyze_f059_predicate.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}

# What "the slot is on" looks like in the saved file, per slot.  `None` for the
# attribute value means "any value other than the off-value counts as on".
SLOT_PROPERTY = {
    "Bold": ("{%s}font-weight" % NS["fo"], "bold", "normal"),
    "Italic": ("{%s}font-style" % NS["fo"], "italic", "normal"),
    "Underline": ("{%s}text-underline-style" % NS["style"], None, "none"),
    "Strikeout": ("{%s}text-line-through-style" % NS["style"], None, "none"),
}


def marker_styles(content: bytes) -> dict[str, str | None]:
    """marker text -> the style name on the span carrying it."""
    root = ElementTree.fromstring(content)
    found: dict[str, str | None] = {}
    for span in root.iter("{%s}span" % NS["text"]):
        if span.text:
            found[span.text] = span.get("{%s}style-name" % NS["text"])
    return found


def automatic_styles(content: bytes) -> dict[str, dict[str, str]]:
    """style name -> its text properties, flattened."""
    root = ElementTree.fromstring(content)
    styles: dict[str, dict[str, str]] = {}
    for style in root.iter("{%s}style" % NS["style"]):
        name = style.get("{%s}name" % NS["style"])
        if not name:
            continue
        properties: dict[str, str] = {}
        for element in style.iter("{%s}text-properties" % NS["style"]):
            properties.update(element.attrib)
        styles[name] = properties
    return styles


def slot_is_on(properties: dict[str, str], slot: str) -> bool | None:
    """True/False, or None when the style says nothing about this slot.

    None is not False.  A style that carries no font-weight has not been made
    normal, it has been left alone -- and reporting that as "off" would let a
    command that did nothing look like a command that turned something off.
    """
    attribute, on_value, off_value = SLOT_PROPERTY[slot]
    value = properties.get(attribute)
    if value is None:
        return None
    if value == off_value:
        return False
    if on_value is None:
        return True
    return value == on_value


def broadcast_for(arm: dict, slot: str) -> bool | None:
    """What core broadcast for this slot during this arm, if anything."""
    prefix = f".uno:{slot}="
    seen = [entry for entry in arm.get("stateChanges") or []
            if entry.startswith(prefix)]
    if not seen:
        return None
    return seen[-1][len(prefix):] == "true"


def analyse(arms: list[dict], content: bytes) -> dict:
    styles = automatic_styles(content)
    markers = marker_styles(content)
    rows, problems = [], []

    for arm in arms:
        if arm.get("probe") != "arm":
            continue
        marker = arm["marker"]
        slot = arm.get("slot") or None
        style_name = markers.get(marker)
        properties = styles.get(style_name or "", {})
        row = {
            "arm": arm["arm"],
            "slot": slot,
            "requested": arm.get("requested"),
            "answered": arm.get("answered"),
            "readOnly": arm.get("readOnly"),
            "markerFound": marker in markers,
            "styleName": style_name,
            "broadcast": broadcast_for(arm, slot) if slot else None,
            "document": slot_is_on(properties, slot) if slot else None,
        }
        # An arm that never received a command result measured nothing and must
        # not be scored -- otherwise a silent arm reads as a pass.
        if slot and not arm.get("answered"):
            problems.append(f"{row['arm']}: no command result arrived; not scored")
            row["scored"] = False
        elif not row["markerFound"]:
            problems.append(f"{row['arm']}: marker {marker!r} is not in the document")
            row["scored"] = False
        else:
            row["scored"] = True
        rows.append(row)

    control = [r for r in rows if r["slot"] is None]
    scored = [r for r in rows if r["scored"] and r["slot"]]

    # The control has to exist and has to be clean, or "the marker is styled"
    # could be the fixture's own styling rather than the command's doing.
    if not control:
        problems.append("no control arm: the fixture's own styling is unexcluded")
    else:
        style_name = control[0]["styleName"]
        properties = styles.get(style_name or "", {})
        for slot in SLOT_PROPERTY:
            if slot_is_on(properties, slot):
                problems.append(
                    f"control arm's marker is already {slot}: the fixture styles "
                    "it and no arm can be read")

    # A field that never varies is not a predicate.  Checked separately for each
    # side, because either one being constant is fatal in a different way.
    broadcasts = {r["broadcast"] for r in scored}
    documents = {r["document"] for r in scored}
    if len(broadcasts) < 2:
        problems.append(
            f"the broadcast is constant across every scored arm ({broadcasts}); "
            "it cannot be a predicate")
    if len(documents) < 2:
        problems.append(
            f"the document outcome is constant across every scored arm "
            f"({documents}); the probe drove nothing")

    # The question the predicate has to answer: is the caret in the requested
    # state?  Compare what the document ended up with against what was asked.
    agree, disagree = [], []
    for row in scored:
        wanted = row["requested"]
        got = row["document"]
        # `None` in the document means the style says nothing about the slot,
        # which for a `false` request is the correct outcome: nothing was turned
        # on, so nothing is recorded.
        effective = False if got is None else got
        (agree if effective == wanted else disagree).append(row["arm"])

    return {
        "schemaVersion": 1,
        "release": "f059-predicate",
        "arms": rows,
        "documentMatchesRequest": {"agree": agree, "disagree": disagree},
        "problems": problems,
        "ok": not problems,
    }


def load(round_dir: Path) -> tuple[list[dict], bytes]:
    arms = [json.loads(line) for line in
            (round_dir / "arms.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    with zipfile.ZipFile(round_dir / "predicate-arms.odt") as archive:
        return arms, archive.read("content.xml")


def self_test() -> int:
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    def document(pairs: list[tuple[str, str, dict[str, str]]]) -> bytes:
        """(marker, style name, text properties) -> a minimal content.xml."""
        styles = "".join(
            f'<style:style style:name="{name}" style:family="text">'
            f'<style:text-properties {" ".join(f_(k, v) for k, v in props.items())}/>'
            f'</style:style>'
            for _, name, props in pairs)
        body = "".join(
            f'<text:p><text:span text:style-name="{name}">{marker}</text:span></text:p>'
            for marker, name, _ in pairs)
        return (
            '<?xml version="1.0"?><office:document-content '
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
            'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
            'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0">'
            f'<office:automatic-styles>{styles}</office:automatic-styles>'
            f'<office:body><office:text>{body}</office:text></office:body>'
            '</office:document-content>').encode("utf-8")

    def f_(key: str, value: str) -> str:
        return f'{key}="{value}"'

    bold = {"fo:font-weight": "bold"}
    plain: dict[str, str] = {}

    def armrec(name, slot, requested, marker, broadcasts, answered=True,
               read_only=False):
        return {"probe": "arm", "arm": name, "slot": slot or "",
                "requested": requested, "marker": marker, "answered": answered,
                "readOnly": read_only, "stateChanges": broadcasts}

    healthy_arms = [
        armrec("control", None, None, "AAA", []),
        armrec("bold-true", "Bold", True, "BBB", [".uno:Bold=true"]),
        armrec("bold-false", "Bold", False, "CCC", []),
    ]
    healthy_doc = document([("AAA", "T1", plain), ("BBB", "T2", bold),
                            ("CCC", "T3", plain)])
    report = analyse(healthy_arms, healthy_doc)
    verify("a healthy round is clean", report["ok"],
           json.dumps(report["problems"], ensure_ascii=False))
    verify("a healthy round scores every slot arm",
           len([r for r in report["arms"] if r["scored"] and r["slot"]]) == 2)
    verify("agreement is reported per arm",
           report["documentMatchesRequest"]["agree"] == ["bold-true", "bold-false"],
           json.dumps(report["documentMatchesRequest"]))

    # The style is resolved, not grepped: a document containing a bold style
    # that the marker does NOT use must not read as bold.
    unused_bold = document([("AAA", "T1", plain), ("BBB", "T2", plain),
                            ("CCC", "T3", plain), ("ZZZ", "E1Bold", bold)])
    grep_fooled = analyse(healthy_arms, unused_bold)
    verify("a bold style the marker does not use is not read as bold",
           grep_fooled["documentMatchesRequest"]["disagree"] == ["bold-true"],
           json.dumps(grep_fooled["documentMatchesRequest"]))

    # An arm with no command result measured nothing.
    silent = analyse([healthy_arms[0],
                      armrec("bold-true", "Bold", True, "BBB",
                             [".uno:Bold=true"], answered=False),
                      healthy_arms[2]], healthy_doc)
    verify("an arm that got no command result is not scored",
           not silent["ok"] and any("not scored" in p for p in silent["problems"]))

    # A constant on either side is not a predicate.
    constant_doc = document([("AAA", "T1", plain), ("BBB", "T2", plain),
                             ("CCC", "T3", plain)])
    constant = analyse([healthy_arms[0],
                        armrec("bold-true", "Bold", True, "BBB", []),
                        healthy_arms[2]], constant_doc)
    verify("a constant broadcast is caught",
           any("broadcast is constant" in p for p in constant["problems"]),
           json.dumps(constant["problems"], ensure_ascii=False))
    verify("a constant document outcome is caught",
           any("document outcome is constant" in p for p in constant["problems"]))

    # A fixture that styles the control makes every arm unreadable.
    dirty_control = document([("AAA", "T1", bold), ("BBB", "T2", bold),
                              ("CCC", "T3", plain)])
    dirty = analyse(healthy_arms, dirty_control)
    verify("a control marker that is already styled is caught",
           any("control arm's marker is already" in p for p in dirty["problems"]))

    # A marker missing from the document is not a silent pass.
    missing = analyse(healthy_arms,
                      document([("AAA", "T1", plain), ("CCC", "T3", plain)]))
    verify("a marker that never reached the document is caught",
           any("is not in the document" in p for p in missing["problems"]))

    total = 9
    print(f"\nself-test: {total - len(failures)}/{total} checks moved the verdict")
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
