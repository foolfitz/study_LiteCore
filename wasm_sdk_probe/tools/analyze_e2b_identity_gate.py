#!/usr/bin/env python3
"""SPEC E2-B 9.9: does the adjudicated identity gate hold on the native records?

The gate: a cross-paragraph format dispatch is verified by comparing the text of
each block in the html readback, before the dispatch against after.  Identity is
per-block TEXT; the list state is the STRUCTURE around it (ul/ol/li), which is
counted separately.

Why per block and not the whole body: stripping tags from the whole body does
NOT round-trip.  `</li>\\n<li>` leaves a tab between the paragraphs after the
dispatch that was not there before, so a whole-body comparison reports a
difference that is pure serialisation.  Per-block extraction has no such seam.
That is measured, not asserted -- run with --show-body.

Why text and not the plain-text readback: `getTextSelection("text/plain")`
injects list decoration ("    • ", "    1. ", incrementing), which makes every
SUCCESSFUL list dispatch compare unequal.  The html serialisation puts the
number in the `<ol>` and leaves the text alone.

The extractor's own controls run first and the tool exits non-zero if they fail:
a check that cannot fail is worse than no check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def blocks(html: str) -> list[str]:
    """Text of each <p>, concatenated across inline markup (<font>, <span>)."""
    at = html.find("<body")
    if at < 0:
        return []
    at = html.index(">", at) + 1
    end = html.find("</body>", at)
    body = html[at:end if end > 0 else len(html)]
    return [re.sub(r"<[^>]*>", "", m)
            for m in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S)]


def whole_body(html: str) -> str:
    at = html.find("<body")
    if at < 0:
        return ""
    at = html.index(">", at) + 1
    end = html.find("</body>", at)
    return re.sub(r"<[^>]*>", "", html[at:end if end > 0 else len(html)])


def controls() -> list[str]:
    """The extractor must be able to report a difference.  Failures are fatal."""
    failures = []
    if blocks("<body><p>a</p><p>b</p></body>") != ["a", "b"]:
        failures.append("two blocks are not extracted as two")
    if blocks("<body><p>a</p></body>") == blocks("<body><p>a</p><p>b</p></body>"):
        failures.append("a lost block is not visible")
    if blocks("<body><p>a<font><span>X</span></font></p></body>") != ["aX"]:
        failures.append("inline markup is not concatenated")
    if blocks("<body><p>a</p></body>") == blocks("<body><p>A</p></body>"):
        failures.append("a changed character is not visible")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arms", type=Path, help="arms.jsonl from the native probe")
    parser.add_argument("--show-body", action="store_true",
                        help="also report the whole-body comparison, which does "
                             "not round-trip -- the reason the gate is per block")
    args = parser.parse_args()

    failures = controls()
    if failures:
        print(json.dumps({"extractorControlsFailed": failures}, indent=2))
        return 2

    by_arm: dict[str, list[dict]] = {}
    for line in args.arms.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if "arm" not in record:
            continue
        before = blocks(record["check1"]["html"])
        after = blocks(record["check2"]["html"])
        row = {
            "round": record["round"],
            "blocksBefore": len(before),
            "blocksAfter": len(after),
            "itemsAfter": record["check2"]["items"],
            "perBlockTextIdentical": before == after,
            "text": before,
        }
        if args.show_body:
            row["wholeBodyIdentical"] = (whole_body(record["check1"]["html"])
                                         == whole_body(record["check2"]["html"]))
        by_arm.setdefault(record["arm"], []).append(row)

    summary = {
        "extractorControls": "passed",
        "byArm": {
            arm: {
                "rounds": len(rows),
                "perBlockTextIdenticalAll": all(r["perBlockTextIdentical"] for r in rows),
                "blocks": sorted({r["blocksBefore"] for r in rows}),
                "itemsAfter": sorted({r["itemsAfter"] for r in rows}),
                "rows": rows,
            }
            for arm, rows in by_arm.items()
        },
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    ok = all(v["perBlockTextIdenticalAll"] for v in summary["byArm"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
