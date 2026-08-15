#!/usr/bin/env python3
"""Create E2's own deterministic fixtures.

SPEC E2-C 5, D3 cell L7: "leave the list from an interior item".  No existing
fixture can express it -- `list-contexts.odt`'s two lists have TWO items each,
and removing one item from a two-item list does not split anything.  A cell
whose fixture cannot produce the shape it is measuring is a cell that passes
without ever running, which is the 034/035/037/038 failure exactly.

A NEW directory rather than a new entry in create_e1_corpus.py, for the reason
SPEC E2-C section 3 states plainly: E2-C does not regenerate or rewrite the E1
corpus source bytes.  Their sha256s are recorded in E1-A's frozen fixture list
and in every E1 run's evidence, and a generator that rewrites all of them to
add one is a generator that can detach a verdict from the documents it was
measured on.  Importing that module is fine -- imports do not write files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from create_e1_corpus import create_odt, frozen_valid  # noqa: E402
from e1_support import sha256, write_json  # noqa: E402

# Both list kinds get three items.  The contract has set-list-ordered and
# set-list-unordered, and "the middle item leaves an ordered list" says nothing
# about what happens to a bulleted one -- numbering has to renumber, bullets do
# not, so they can fail differently.
FIXTURES = {
    # SPEC E2-C D1.  Every action gets its own anchor, because all four inline
    # formats return the same completion (`uno-command-result`): a mapping that
    # sent bold to italic would report the action asked for and still be wrong,
    # and a single shared anchor cannot tell those apart.  The `-OFF` anchors
    # start already formatted, so `enabled: false` has something to remove --
    # without them "turn it off" and "never turned it on" look identical.
    "d1-anchors": {
        "extra_automatic_styles": (
            '  <style:style style:name="E2Underline" style:family="text">'
            '<style:text-properties style:text-underline-style="solid"/>'
            "</style:style>\n"
            '  <style:style style:name="E2Strike" style:family="text">'
            '<style:text-properties style:text-line-through-style="solid"/>'
            "</style:style>\n"
        ),
        "extra_styles": (
            '  <text:list-style style:name="E2D1Number">'
            '<text:list-level-style-number text:level="1" style:num-format="1"'
            ' style:num-suffix="."/>'
            "</text:list-style>\n"
        ),
        "body": """
 <text:h text:outline-level="1" text:style-name="Heading_20_1">E2-D1-HEADING</text:h>
 <text:p>E2-D1-MOVE 游標移動</text:p>
 <text:p>E2-D1-BOLD-ON plain</text:p>
 <text:p>E2-D1-BOLD-OFF <text:span text:style-name="E1Bold">already</text:span></text:p>
 <text:p>E2-D1-ITALIC-ON plain</text:p>
 <text:p>E2-D1-ITALIC-OFF <text:span text:style-name="E1Italic">already</text:span></text:p>
 <text:p>E2-D1-UNDERLINE-ON plain</text:p>
 <text:p>E2-D1-UNDERLINE-OFF <text:span text:style-name="E2Underline">already</text:span></text:p>
 <text:p>E2-D1-STRIKE-ON plain</text:p>
 <text:p>E2-D1-STRIKE-OFF <text:span text:style-name="E2Strike">already</text:span></text:p>
 <text:p>E2-D1-DELBACK ABCDEF</text:p>
 <text:p>E2-D1-DELFWD ABCDEF</text:p>
 <text:p>E2-D1-BREAKPARA ALPHAOMEGA</text:p>
 <text:p>E2-D1-BREAKLINE ALPHAOMEGA</text:p>
 <text:p>E2-D1-LIST-UNORDERED</text:p>
 <text:p>E2-D1-LIST-ORDERED</text:p>
 <text:list text:style-name="E2D1Number"><text:list-item><text:p>E2-D1-LIST-NONE</text:p></text:list-item></text:list>
 <text:p>E2-D1-HEAD-TARGET</text:p>
 <text:h text:outline-level="1" text:style-name="Heading_20_1">E2-D1-BODY-TARGET</text:h>
 <text:p>E2-D1-RANGE-ONE 第一段</text:p>
 <text:p>E2-D1-RANGE-TWO 第二段</text:p>
 <text:list text:style-name="E2D1Number"><text:list-item><text:p>E2-D1-NUM-ONE</text:p></text:list-item><text:list-item><text:p>E2-D1-NUM-TWO</text:p></text:list-item></text:list>
 <text:p>E2-D1-INTERLEAVE 交錯</text:p>
 <text:p>E2-D1-INSERT 插入</text:p>
""",
        "anchors": [
            "E2-D1-HEADING", "E2-D1-MOVE 游標移動",
            "E2-D1-BOLD-ON plain", "E2-D1-BOLD-OFF",
            "E2-D1-ITALIC-ON plain", "E2-D1-ITALIC-OFF",
            "E2-D1-UNDERLINE-ON plain", "E2-D1-UNDERLINE-OFF",
            "E2-D1-STRIKE-ON plain", "E2-D1-STRIKE-OFF",
            "E2-D1-DELBACK ABCDEF", "E2-D1-DELFWD ABCDEF",
            "E2-D1-BREAKPARA ALPHAOMEGA", "E2-D1-BREAKLINE ALPHAOMEGA",
            "E2-D1-LIST-UNORDERED", "E2-D1-LIST-ORDERED", "E2-D1-LIST-NONE",
            "E2-D1-HEAD-TARGET", "E2-D1-BODY-TARGET",
            "E2-D1-RANGE-ONE 第一段", "E2-D1-RANGE-TWO 第二段",
            "E2-D1-NUM-ONE", "E2-D1-NUM-TWO",
            "E2-D1-INTERLEAVE 交錯", "E2-D1-INSERT 插入",
        ],
        "minimum": {"paragraphs": 24, "headings": 2, "lists": 2, "tables": 0},
        "listItems": {"E2D1Number": 3},
    },
    "list-split": {
        "extra_styles": (
            '  <text:list-style style:name="E2LSNumber">'
            '<text:list-level-style-number text:level="1" style:num-format="1"'
            ' style:num-suffix="."/>'
            "</text:list-style>\n"
            '  <text:list-style style:name="E2LSBullet">'
            '<text:list-level-style-bullet text:level="1" text:bullet-char="•"/>'
            "</text:list-style>\n"
        ),
        "body": """
 <text:h text:outline-level="1" text:style-name="Heading_20_1">E2-LS-HEADING</text:h>
 <text:p>E2-LS-BEFORE 這一段前面不是清單</text:p>
 <text:list text:style-name="E2LSNumber"><text:list-item><text:p>E2-LS-ONE</text:p></text:list-item><text:list-item><text:p>E2-LS-MID 中間那一項</text:p></text:list-item><text:list-item><text:p>E2-LS-THREE</text:p></text:list-item></text:list>
 <text:p>E2-LS-AFTER</text:p>
 <text:list text:style-name="E2LSBullet"><text:list-item><text:p>E2-LS-BULLET-ONE</text:p></text:list-item><text:list-item><text:p>E2-LS-BULLET-MID</text:p></text:list-item><text:list-item><text:p>E2-LS-BULLET-THREE</text:p></text:list-item></text:list>
 <text:p>E2-LS-END</text:p>
""",
        "anchors": [
            "E2-LS-HEADING", "E2-LS-BEFORE 這一段前面不是清單", "E2-LS-ONE",
            "E2-LS-MID 中間那一項", "E2-LS-THREE", "E2-LS-AFTER",
            "E2-LS-BULLET-ONE", "E2-LS-BULLET-MID", "E2-LS-BULLET-THREE",
            "E2-LS-END",
        ],
        "minimum": {"paragraphs": 10, "headings": 1, "lists": 2, "tables": 0},
        # Not decoration: the whole point of this fixture is that each list has
        # three items, and a generator edit that dropped one would otherwise
        # leave L7 measuring a two-item list again without saying so.
        "listItems": {"E2LSNumber": 3, "E2LSBullet": 3},
    },
}


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=project / "test-docs" / "e2")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = output / "manifest.json"
    if not args.force and frozen_valid(manifest_path):
        print(json.dumps({"manifest": str(manifest_path), "status": "frozen-valid"}))
        return
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for identifier, definition in FIXTURES.items():
        path = output / f"{identifier}.odt"
        create_odt(path, definition["body"],
                   extra_automatic_styles=definition.get(
                       "extra_automatic_styles", ""),
                   extra_styles=definition.get("extra_styles", ""))
        entries.append({
            "id": identifier,
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "anchors": definition["anchors"],
            "minimum": definition["minimum"],
            "listItems": definition["listItems"],
            "source": "project-generated deterministic ODT",
        })
    write_json(manifest_path, {
        "schemaVersion": 1,
        "release": "E2-C-paragraph-format-validation",
        "frozenDate": "2026-08-15",
        "mutationPolicy": "copy-only",
        "why": "SPEC E2-C D3 cell L7 needs a list with an interior item; the E1 "
               "corpus has none, and E2-C may not regenerate the E1 corpus.",
        "fixtures": entries,
    })
    print(json.dumps({"manifest": str(manifest_path),
                      "fixtures": len(entries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
