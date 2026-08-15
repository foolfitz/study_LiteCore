#!/usr/bin/env python3
"""SPEC E2-B section 7: judge the positive matrix from the saved documents.

Reads only what the harness saved, so the verdict can be recomputed without a
browser.  The paragraph signature is the one the section-3 gate analyzer uses
and for the same reasons: automatic style names renumber on their own, so they
are folded to `(auto)`, and bullet-versus-number lives on the list style rather
than on the paragraph.

The load-bearing criterion is 7.1 item 5 -- the paragraphs the arm did NOT
target must be unchanged.  Every action here is paragraph-level, so a range that
silently collapsed to a caret would satisfy every other check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
AUTOMATIC_NAME = re.compile(r"^(P|L|T|Sect|fr|Mfr)\d+$")

BODY_OPEN = b"<office:body>"
BODY_CLOSE = b"</office:body>"


def opaque(name: str | None) -> str | None:
    if name is None:
        return None
    return "(auto)" if AUTOMATIC_NAME.match(name) else name


def list_kinds(root) -> dict[str, str]:
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


def body_bytes(odt: Path) -> bytes | None:
    with zipfile.ZipFile(odt) as archive:
        content = archive.read("content.xml")
    start = content.find(BODY_OPEN)
    end = content.find(BODY_CLOSE)
    if start < 0 or end < 0:
        return None
    return content[start:end + len(BODY_CLOSE)]


def signature(row: dict[str, Any]) -> tuple:
    return (row["kind"], row["style"], row["outline"], row["list"])


def changed_rows(before: list[dict], after: list[dict]) -> list[dict] | None:
    if len(before) != len(after):
        return None
    out = []
    for index, (b, a) in enumerate(zip(before, after)):
        if b["text"] != a["text"] or signature(b) != signature(a):
            out.append({"index": index, "text": b["text"][:40],
                        "before": signature(b), "after": signature(a)})
    return out


# What each action must make true of a paragraph it targeted.
def reached_target(action: str, row: dict[str, Any], self_red: str | None) -> bool:
    listing = row["list"]
    if self_red:
        # 9.9's self-red arm: the judge is told to expect the other list kind.
        # The document will show what was actually dispatched, so this must come
        # out FALSE -- a state check that cannot report a mismatch is not a
        # check, and this arm is how that is demonstrated rather than asserted.
        return listing == ("number" if self_red == "ol" else "bullet")
    if action == "set-list-unordered":
        return listing == "bullet"
    if action == "set-list-ordered":
        return listing == "number"
    if action == "set-list-none":
        return listing is None
    # The two paragraph-style actions are judged on the STYLE NAME, not on the
    # ODF element.  `.uno:StyleApply` applies `Heading_20_1` to the existing
    # `<text:p>`; it does not rewrite the element as `<text:h>`.  That is
    # measured, not assumed -- SPEC E2-A 10.2 records correcting exactly this
    # expectation ("期望值錯，不是產品錯"), and the first version of this
    # analyzer made the same guess and failed all three heading arms with it.
    #
    # Recorded consequence, because it is a real difference and not a
    # formality: a paragraph carrying the heading style but exported as
    # `<text:p>` has no `text:outline-level`, so it does not take part in the
    # document outline the way an authored `<text:h>` does.  The contract
    # promises the heading STYLE (narrowing 2, H1 only); it has never promised
    # outline participation, and now says so out loud.
    if action == "set-paragraph-heading":
        return row["kind"] == "h" or row["style"] == "Heading_20_1"
    if action == "set-paragraph-body":
        return row["kind"] == "p" and row["style"] != "Heading_20_1"
    return False


def judge(arm: dict, record: dict, evidence: Path) -> dict[str, Any]:
    name = arm["arm"]
    verdict = {"arm": name, "round": record.get("round"),
               "gesture": arm.get("gesture"), "action": arm.get("action")}
    if record.get("void"):
        verdict["void"] = record["void"]
        return verdict
    if record.get("fatal"):
        verdict["void"] = ["fatal", record["fatal"]]
        return verdict

    before_path = evidence / "saved" / f"{name}-round{record['round']}-before.odt"
    after_path = evidence / "saved" / f"{name}-round{record['round']}-after.odt"
    if not before_path.exists() or not after_path.exists():
        verdict["void"] = "a saved document is missing"
        return verdict

    problems: list[str] = []

    # 1. the route the ENGINE reported is the class the arm intended
    intended = {"collapsed": "collapsed", "range-single": "range-single",
                "range-single-reverse": "range-single",
                "range-single-wrapped": "range-single",
                "range-cross": "range-cross"}[arm["gesture"]]
    verdict["route"] = record.get("route")
    if record.get("route") != intended:
        problems.append(f"routed {record.get('route')}, the arm intended {intended}")

    # 2 and 3. completion shape and the revision equation
    if record.get("actionStatus") != "completed":
        problems.append(f"action {record.get('actionStatus')}: "
                        f"{json.dumps(record.get('actionError'), ensure_ascii=False)}")
    else:
        if record.get("changed") is not None:
            problems.append(f"changed was {record.get('changed')}, route C reports null")
        if record.get("completion") != "verified-format-readback":
            problems.append(f"completion was {record.get('completion')}")

    # 6. the crossing route must have verified both halves
    if intended == "range-cross" and record.get("actionStatus") == "completed":
        if record.get("crossIdentityHeld") is not True:
            problems.append("crossIdentityHeld is not true")
        if record.get("crossStateHeld") is not True:
            problems.append("crossStateHeld is not true")

    # 4 and 5. the document
    before = paragraphs(before_path)
    after = paragraphs(after_path)
    changed = changed_rows(before, after)
    if changed is None:
        problems.append(f"paragraph count changed: {len(before)} -> {len(after)}")
        verdict["fail"] = problems
        return verdict

    verdict["changedParagraphs"] = [c["text"] for c in changed]
    targeted = [row for row in after if arm["anchor"] in row["text"]]
    if not targeted:
        problems.append(f"no paragraph carries the anchor {arm['anchor']}")
    for row in targeted:
        if not reached_target(arm["action"], row, arm.get("selfRed")):
            problems.append(
                f"{row['text'][:30]!r} did not reach the target state for "
                f"{arm['action']} (list={row['list']}, kind={row['kind']})")

    # Anything that changed and is not the anchor's paragraph, nor -- for the
    # crossing route -- the paragraph after it, is a paragraph this arm did not
    # target.  That is criterion 5, and it is the one that makes the rest mean
    # anything.
    allowed_texts = {row["text"] for row in targeted}
    if intended == "range-cross":
        indexes = [i for i, row in enumerate(after) if arm["anchor"] in row["text"]]
        for index in indexes:
            if index + 1 < len(after):
                allowed_texts.add(after[index + 1]["text"])
    stray = [c for c in changed
             if not any(c["text"].startswith(text[:40]) for text in allowed_texts)]
    if stray:
        problems.append(f"paragraphs the arm did not target changed: "
                        f"{[c['text'] for c in stray]}")

    # The no-op arm: the repeat must advance the revision and change nothing.
    if arm.get("repeat"):
        middle_path = evidence / "saved" / f"{name}-round{record['round']}-middle.odt"
        if not middle_path.exists():
            problems.append("no middle save: the repeat cannot be judged")
        else:
            same = body_bytes(middle_path) == body_bytes(after_path)
            verdict["repeatBodyIdentical"] = same
            verdict["repeatRevision"] = record.get("repeatRevision")
            if not same:
                problems.append("the repeat CHANGED the document")
            if record.get("repeatStatus") != "completed":
                problems.append(f"the repeat did not complete: {record.get('repeatStatus')}")
            elif record.get("repeatRevision") != (record.get("revision") or 0) + 1:
                problems.append(
                    f"the repeat did not advance the revision by one: "
                    f"{record.get('revision')} -> {record.get('repeatRevision')}")

    verdict["pass" if not problems else "fail"] = problems or True
    return verdict


# --- self test -------------------------------------------------------------
#
# SPEC E2-B 7.1 requires every validator that produces a verdict to ship a
# mutation test: flip each criterion and assert it goes red.  The reason is
# written in this session's error table -- an analyzer written after a
# prediction once replaced a pre-registered criterion, and the replacement made
# the arm pass.  Ad hoc mutation checks catch that once; a --self-test whose
# output goes into the freeze evidence catches it every time.

MINIMAL_ODT_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<office:document-content '
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0">'
    "<office:automatic-styles>{styles}</office:automatic-styles>"
    "<office:body><office:text>{body}</office:text></office:body>"
    "</office:document-content>"
)

BULLET_STYLE = ('<text:list-style style:name="LB">'
                '<text:list-level-style-bullet text:level="1"/></text:list-style>')


def write_odt(path: Path, body: str, styles: str = BULLET_STYLE) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("content.xml",
                         MINIMAL_ODT_TEMPLATE.format(body=body, styles=styles))
    return path


def self_test() -> int:
    import tempfile

    failures: list[str] = []

    def expect(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    plain = "<text:p>ANCHOR one</text:p><text:p>OTHER two</text:p>"
    bulleted = ('<text:list text:style-name="LB"><text:list-item>'
                "<text:p>ANCHOR one</text:p></text:list-item></text:list>"
                "<text:p>OTHER two</text:p>")
    both_bulleted = ('<text:list text:style-name="LB">'
                     "<text:list-item><text:p>ANCHOR one</text:p></text:list-item>"
                     "<text:list-item><text:p>OTHER two</text:p></text:list-item>"
                     "</text:list>")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "saved").mkdir()
        arm = {"arm": "T", "gesture": "range-single", "action": "set-list-unordered",
               "anchor": "ANCHOR", "fixture": "x.odt"}
        good = {"round": 1, "route": "range-single", "actionStatus": "completed",
                "changed": None, "completion": "verified-format-readback",
                "revision": 1}

        def prepare(before_body: str, after_body: str) -> None:
            write_odt(root / "saved" / "T-round1-before.odt", before_body)
            write_odt(root / "saved" / "T-round1-after.odt", after_body)

        # The control: a correct run must PASS, or every red below is vacuous.
        prepare(plain, bulleted)
        expect(judge(arm, good, root).get("pass") is True,
               "control: a correct run does not pass")

        # Each criterion, flipped one at a time.
        expect(judge(arm, {**good, "route": "collapsed"}, root).get("fail"),
               "a wrong route is not caught")
        expect(judge(arm, {**good, "changed": True}, root).get("fail"),
               "changed=true is not caught")
        expect(judge(arm, {**good, "completion": "uno-command-result"},
                     root).get("fail"),
               "a v1-shaped completion is not caught")
        expect(judge(arm, {**good, "actionStatus": "failed"}, root).get("fail"),
               "a failed action is not caught")

        # The target paragraph did not reach the target state.
        prepare(plain, plain)
        expect(judge(arm, good, root).get("fail"),
               "a document that did not change is not caught")

        # THE load-bearing one: an untargeted paragraph moved too.
        prepare(plain, both_bulleted)
        expect(judge(arm, good, root).get("fail"),
               "a paragraph the arm did not target changing is not caught")

        # A paragraph appearing or vanishing.
        prepare(plain, "<text:p>ANCHOR one</text:p>")
        expect(judge(arm, good, root).get("fail"),
               "a changed paragraph count is not caught")

        # The crossing route must have verified both halves.
        cross_arm = {**arm, "gesture": "range-cross"}
        cross_good = {**good, "route": "range-cross",
                      "crossIdentityHeld": True, "crossStateHeld": True}
        prepare(plain, bulleted)
        expect(judge(cross_arm, cross_good, root).get("pass") is True,
               "control: a correct crossing run does not pass")
        expect(judge(cross_arm, {**cross_good, "crossIdentityHeld": False},
                     root).get("fail"),
               "crossIdentityHeld=false is not caught")
        expect(judge(cross_arm, {**cross_good, "crossStateHeld": False},
                     root).get("fail"),
               "crossStateHeld=false is not caught")

        # The no-op arm: a repeat that changed the document, and one that did
        # not advance the revision.
        repeat_arm = {**arm, "repeat": True}
        write_odt(root / "saved" / "T-round1-middle.odt", bulleted)
        prepare(plain, bulleted)
        repeat_good = {**good, "repeatStatus": "completed", "repeatRevision": 2}
        expect(judge(repeat_arm, repeat_good, root).get("pass") is True,
               "control: a correct repeat does not pass")
        expect(judge(repeat_arm, {**repeat_good, "repeatRevision": 1},
                     root).get("fail"),
               "a repeat that did not advance the revision is not caught")
        write_odt(root / "saved" / "T-round1-middle.odt", plain)
        expect(judge(repeat_arm, repeat_good, root).get("fail"),
               "a repeat that changed the document is not caught")

    # reached_target, including the self-red inversion.
    listed = {"kind": "p", "style": "(auto)", "outline": None,
              "list": "bullet", "text": "x"}
    heading = {"kind": "p", "style": "Heading_20_1", "outline": None,
               "list": None, "text": "x"}
    expect(reached_target("set-list-unordered", listed, None),
           "a bulleted paragraph is not recognised")
    expect(not reached_target("set-list-ordered", listed, None),
           "bullet is accepted where number was required")
    expect(reached_target("set-paragraph-heading", heading, None),
           "the heading STYLE is not recognised (SPEC E2-A 10.2)")
    expect(not reached_target("set-paragraph-body", heading, None),
           "a heading is accepted as body text")
    expect(not reached_target("set-list-unordered", listed, "ol"),
           "the self-red inversion does not invert")

    print(json.dumps({
        "selfTest": "analyze_e2b_matrix",
        "checks": 18,
        "failures": failures,
        "passed": not failures,
    }, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true",
                        help="flip each criterion and assert it goes red")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.evidence is None:
        parser.error("an evidence directory is required unless --self-test")

    result = json.loads((args.evidence / "result.json").read_text(encoding="utf-8"))
    verdicts = []
    for arm in result.get("arms") or []:
        for record in arm.get("rounds") or []:
            verdicts.append(judge(arm, record, args.evidence))

    by_arm: dict[str, dict] = {}
    for verdict in verdicts:
        entry = by_arm.setdefault(verdict["arm"], {"rounds": 0, "passed": 0,
                                                   "failed": 0, "void": 0})
        entry["rounds"] += 1
        entry["passed"] += 1 if verdict.get("pass") else 0
        entry["failed"] += 1 if verdict.get("fail") else 0
        entry["void"] += 1 if verdict.get("void") else 0

    # The self-red arm inverts: it passes the matrix by FAILING the judge.
    self_red = {arm["arm"] for arm in (result.get("arms") or []) if arm.get("selfRed")}
    self_red_ok = all(by_arm.get(name, {}).get("failed", 0)
                      == by_arm.get(name, {}).get("rounds", 0) and
                      by_arm.get(name, {}).get("rounds", 0) > 0
                      for name in self_red) if self_red else None

    summary = {
        "artifact": result.get("artifact"),
        "browser": result.get("browser"),
        "anchors": result.get("anchors"),
        "byArm": by_arm,
        "selfRedArms": sorted(self_red),
        "selfRedBehavedAsRequired": self_red_ok,
        "verdicts": verdicts,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    (args.evidence / "verdict.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ordinary = {k: v for k, v in by_arm.items() if k not in self_red}
    ok = (bool(ordinary)
          and all(v["rounds"] > 0 and v["failed"] == 0 and v["void"] == 0
                  for v in ordinary.values())
          and (self_red_ok is not False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
