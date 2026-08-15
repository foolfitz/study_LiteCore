#!/usr/bin/env python3
"""Create the E2-B fixtures: documents the frozen E1 corpus does not provide.

Separate from create_e1_corpus.py on purpose.  `dist/e1-fixtures/manifest.json`
carries `frozenDate: 2026-08-04` and `mutationPolicy: copy-only`; adding a file
to that directory would change a corpus that shipped verdicts are bound to.  So
this writes its own directory with its own manifest, and imports the XML
scaffolding from the E1 generator so the two are byte-comparable where they
overlap -- which matters, because the gate compares a saved document against a
save through the same engine, and the styles.xml the engine normalises against
has to be the same one.

Why this exists: SPEC E2-B section 3 arm G1 asks what happens when a format
action is dispatched on a range that spans more than one *visual line* inside a
single paragraph.  The 2026-08-15 gate run recorded that arm VOID -- the
paragraph it aimed at (`第三段跨行 gamma` in multi-paragraph.odt) is a tall
paragraph, not a wrapped one, and a selection across its full vertical extent
still reports one rectangle.  No fixture in the E1 corpus has a paragraph long
enough to wrap at the page width.

The wrapped paragraph is built out of a repeated token rather than prose for a
mechanical reason: the gate's survey selects a horizontal band at one y and
reads the text back, so it can only recognise the paragraph on a given visual
line if the anchor appears on *that* line.  A token repeated across the whole
paragraph puts the anchor on every line; prose would put it on the first one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from create_e1_corpus import create_odt  # noqa: E402
from e1_support import sha256, write_json  # noqa: E402

# 120 tokens, 1319 characters.  Sized to be unarguably longer than one line at
# any plausible font metric -- the failure this fixture exists to avoid is a
# paragraph that turns out not to wrap, and being too tall costs nothing: the
# survey sweep only needs two hits inside its window to establish a span.
WRAP_TOKENS = 120
WRAP_TEXT = " ".join(f"G1WRAP-{index:03d}" for index in range(1, WRAP_TOKENS + 1))

# The misfire-direction control for SPEC E2-B 9.9's identity gate: text a naive
# implementation would mangle.  Paragraph 2 opens with what looks exactly like
# list decoration, which is what a gate that strips decoration would eat;
# paragraph 3 carries characters the html serialiser has to escape, plus an
# outline-looking run that is not at the start of the line.
OUTLINE_PROSE = """
 <text:p>E2B-OUT-HEAD marker</text:p>
 <text:p><text:s text:c="4"/>OUT2 1. this line already looks numbered</text:p>
 <text:p>Ampersand &amp; less-than &lt; quote " and 12. mid-line</text:p>
 <text:p>E2B-OUT-TAIL marker</text:p>
"""

# SPEC E2-B 7.1: mid-list departure.  Five items so that leaving items 2-3
# SPLITS the list rather than truncating it -- the structurally riskiest ODT
# shape in the matrix, and the one that could fire the "list switching causes
# silent structure loss" stop condition.  It is also where an ordered list's
# numbering does not start at 1, which the adjudicator's contingency clause
# anticipated.
LIST_SPLIT = """
 <text:p>E2B-SPLIT-HEAD</text:p>
 <text:list text:style-name="E2BSplitBullet">
  <text:list-item><text:p>E2B-SPLIT-ONE</text:p></text:list-item>
  <text:list-item><text:p>E2B-SPLIT-TWO</text:p></text:list-item>
  <text:list-item><text:p>E2B-SPLIT-THREE</text:p></text:list-item>
  <text:list-item><text:p>E2B-SPLIT-FOUR</text:p></text:list-item>
  <text:list-item><text:p>E2B-SPLIT-FIVE</text:p></text:list-item>
 </text:list>
 <text:p>E2B-SPLIT-TAIL</text:p>
"""

# A crossing range whose two paragraphs are in DIFFERENT states: the first is
# already a list item, the second is plain.  Per-block extraction has only ever
# been measured on homogeneous pairs, so `<ul><li><p>...</li></ul><p>...` is a
# readback shape the gate has never seen.
MIXED_STATE = """
 <text:p>E2B-MIXED-HEAD</text:p>
 <text:list text:style-name="E2BMixedBullet">
  <text:list-item><text:p>E2B-MIXED-LISTED</text:p></text:list-item>
 </text:list>
 <text:p>E2B-MIXED-PLAIN</text:p>
 <text:p>E2B-MIXED-TAIL</text:p>
"""

FIXTURES = {
    "list-split": {
        "body": LIST_SPLIT,
        "anchors": ["E2B-SPLIT-HEAD", "E2B-SPLIT-TWO", "E2B-SPLIT-THREE",
                    "E2B-SPLIT-TAIL"],
        "minimum": {"paragraphs": 7, "headings": 0, "lists": 1, "tables": 0},
    },
    "mixed-state": {
        "body": MIXED_STATE,
        "anchors": ["E2B-MIXED-HEAD", "E2B-MIXED-LISTED", "E2B-MIXED-PLAIN",
                    "E2B-MIXED-TAIL"],
        "minimum": {"paragraphs": 4, "headings": 0, "lists": 1, "tables": 0},
    },
    "outline-prose": {
        "body": OUTLINE_PROSE,
        # OUT2 sits at the START of the decoration-looking run, on purpose.
        # The first build of this fixture had the anchor at "looks numbered",
        # which is AFTER the "1. " -- so the range began past the very shape the
        # fixture exists to put inside a selection, and the arm did not exercise
        # its case.  Same class of mistake as G1's first fixture.
        "anchors": ["E2B-OUT-HEAD", "OUT2", "mid-line", "E2B-OUT-TAIL"],
        "minimum": {"paragraphs": 4, "headings": 0, "lists": 0, "tables": 0},
    },
    "wrapped-paragraph": {
        "body": f"""
 <text:p>E2B-WRAP-HEAD single line</text:p>
 <text:p>{WRAP_TEXT}</text:p>
 <text:p>E2B-WRAP-TAIL single line</text:p>
 <text:p>E2B-WRAP-LAST single line</text:p>
""",
        # G1WRAP is the span anchor: it is on every visual line of the wrapped
        # paragraph.  E2B-WRAP-HEAD is the control anchor -- a paragraph that
        # does NOT wrap, so a span inside it must report exactly one rectangle.
        # Without that control, "G1 reported more than one rectangle" cannot be
        # distinguished from "this build reports more than one rectangle for
        # everything".
        "anchors": ["E2B-WRAP-HEAD", "G1WRAP", "E2B-WRAP-TAIL", "E2B-WRAP-LAST"],
        "minimum": {"paragraphs": 4, "headings": 0, "lists": 0, "tables": 0},
    },
}


def main() -> int:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=project / "test-docs" / "e2b")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    entries = []
    for identifier, definition in FIXTURES.items():
        path = output / f"{identifier}.odt"
        create_odt(path, definition["body"])
        entries.append({
            "id": identifier,
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "anchors": definition["anchors"],
            "minimum": definition["minimum"],
            "source": "project-generated deterministic ODT",
        })
    write_json(output / "manifest.json", {
        "schemaVersion": 1,
        "release": "E2-B-paragraph-format",
        "mutationPolicy": "copy-only",
        "fixtures": entries,
    })
    print(json.dumps({"manifest": str(output / "manifest.json"),
                      "fixtures": len(entries),
                      "wrappedCharacters": len(WRAP_TEXT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
