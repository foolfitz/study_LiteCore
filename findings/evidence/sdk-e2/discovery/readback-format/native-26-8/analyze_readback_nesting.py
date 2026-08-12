#!/usr/bin/env python3
"""Audit tag nesting in the saved E2-A paragraph HTML readbacks."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    REPO_ROOT / "wasm_sdk_probe/build/e2-a-readback-format/results.jsonl"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "wasm_sdk_probe/build/e2-a-readback-format/nesting-audit.json"
)

# The block containers the serialiser was observed to write at body level, not
# the set the shipped engine currently accepts.  This audit measures documents,
# so its depth arithmetic has to match what the serialiser actually nests: with
# the engine's narrower set (p, h1, ul, ol, li) a heading stays at depth 0, and
# a bold word inside a Heading 2 would be reported as an inline tag at body
# level -- a false refutation of the very premise this audit exists to test.
#
# div is deliberately absent.  Its only measured occurrence is the footnote
# apparatus container, and whether it counts as a structural block is the open
# question; leaving it out keeps the footnote body's <p> visible at depth 0
# instead of hiding it one level down.
STRUCTURAL_TAGS = (
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote",
    "ul", "ol", "li",
)
STRUCTURAL_TAG_SET = set(STRUCTURAL_TAGS)
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body\s*>", re.IGNORECASE | re.DOTALL)


def location(parser: HTMLParser) -> dict[str, int]:
    line, column = parser.getpos()
    return {"bodyLine": line, "bodyColumn": column}


class BodyAuditParser(HTMLParser):
    """Collect literal tag forms while checking structural depth and nesting."""

    def __init__(self, anchor: str) -> None:
        super().__init__(convert_charrefs=False)
        self.anchor = anchor
        self.inventory: dict[str, Counter[str]] = defaultdict(Counter)
        self.non_structural_depths: dict[str, dict[str, Counter[int]]] = (
            defaultdict(lambda: defaultdict(Counter))
        )
        self.depth_zero_non_structural: list[dict[str, Any]] = []
        # The structural tags opened at depth 0, in order.  Without this the
        # report cannot tell a clean single-paragraph read from a selection that
        # quietly covered two paragraphs: both produce only <p> at depth 0, both
        # keep the anchor's own text in the readback, and both leave
        # depth_zero_non_structural empty.  A check that passes on either answer
        # is not a check, and reading the wrong paragraph is exactly the failure
        # findings 033 and 034 are about.
        self.depth_zero_structural: list[str] = []
        self.self_closing_structural: list[dict[str, Any]] = []
        self.void_spellings: dict[str, Counter[str]] = defaultdict(Counter)
        self.mismatched_closes: list[dict[str, Any]] = []
        self.stack: list[dict[str, Any]] = []
        self.structural_depth = 0
        self.minimum_structural_depth = 0
        self.went_negative = False
        self.tag_occurrences = 0

    def record_non_structural(self, tag: str, form: str) -> None:
        depth = self.structural_depth
        self.non_structural_depths[tag]["all"][depth] += 1
        self.non_structural_depths[tag][form][depth] += 1
        if depth == 0:
            self.depth_zero_non_structural.append({
                "anchor": self.anchor,
                "tag": tag,
                "form": form,
                **location(self),
            })

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        tag = tag.lower()
        self.tag_occurrences += 1
        self.inventory[tag]["open"] += 1

        if tag not in STRUCTURAL_TAG_SET:
            self.record_non_structural(tag, "open")
        elif self.structural_depth == 0:
            self.depth_zero_structural.append(tag)
        if tag in VOID_TAGS:
            self.void_spellings[tag]["withoutSlash"] += 1
            return

        self.stack.append({"tag": tag, **location(self)})
        if tag in STRUCTURAL_TAG_SET:
            self.structural_depth += 1

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        tag = tag.lower()
        self.tag_occurrences += 1
        self.inventory[tag]["selfClosing"] += 1

        if tag in STRUCTURAL_TAG_SET:
            # The net depth change is zero, but retain the literal occurrence.
            self.self_closing_structural.append({
                "anchor": self.anchor,
                "tag": tag,
                "raw": self.get_starttag_text(),
                **location(self),
            })
        else:
            self.record_non_structural(tag, "selfClosing")
        if tag in VOID_TAGS:
            self.void_spellings[tag]["withSlash"] += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        self.tag_occurrences += 1
        self.inventory[tag]["close"] += 1

        if tag in STRUCTURAL_TAG_SET:
            self.structural_depth -= 1
            self.minimum_structural_depth = min(
                self.minimum_structural_depth, self.structural_depth
            )
            self.went_negative = self.went_negative or self.structural_depth < 0
        else:
            self.record_non_structural(tag, "close")

        if self.stack and self.stack[-1]["tag"] == tag:
            self.stack.pop()
            return
        self.mismatched_closes.append({
            "anchor": self.anchor,
            "closeTag": tag,
            "topOfStack": self.stack[-1]["tag"] if self.stack else None,
            **location(self),
        })

    def result(self) -> dict[str, Any]:
        return {
            "anchor": self.anchor,
            "tagOccurrences": self.tag_occurrences,
            "finalDepth": self.structural_depth,
            "minimumDepth": self.minimum_structural_depth,
            "wentNegative": self.went_negative,
            "depthZeroStructural": list(self.depth_zero_structural),
            "depthZeroBlocks": sum(
                1 for tag in self.depth_zero_structural if tag not in ("li",)
            ),
            "unclosedTags": [
                {
                    "anchor": self.anchor,
                    "tag": entry["tag"],
                    "bodyLine": entry["bodyLine"],
                    "bodyColumn": entry["bodyColumn"],
                }
                for entry in self.stack
            ],
        }


def counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {str(depth): counter[depth] for depth in sorted(counter)}


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def flat_text(body: str) -> str:
    """The body's text with tags removed and whitespace collapsed.

    Tags have to go before any text comparison: the serialiser wraps every CJK
    run in <font><span>, so a contiguous search over the raw markup misses text
    that is really there.  That mistake produced a false negative on this corpus
    once already.
    """
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", body)).strip()


def anchor_token(anchor: str) -> str:
    """The bare anchor token, dropping any `fixture/` prefix."""
    return anchor.rsplit("/", 1)[-1]


def analyze(path: Path) -> dict[str, Any]:
    readback_records = 0
    skipped: list[dict[str, Any]] = []
    input_issues: list[dict[str, Any]] = []
    anchor_results: list[dict[str, Any]] = []

    inventory: dict[str, Counter[str]] = defaultdict(Counter)
    depth_distributions: dict[str, dict[str, Counter[int]]] = (
        defaultdict(lambda: defaultdict(Counter))
    )
    depth_zero_occurrences: list[dict[str, Any]] = []
    self_closing_structural: list[dict[str, Any]] = []
    void_spellings: dict[str, Counter[str]] = defaultdict(Counter)
    mismatched_closes: list[dict[str, Any]] = []
    unclosed_tags: list[dict[str, Any]] = []
    tag_occurrences = 0

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON on line {line_number}: {error}") from error
        if record.get("probe") != "readback":
            continue

        readback_records += 1
        anchor = record.get("anchor")
        if record.get("skipped") is True:
            skipped.append({
                "line": line_number,
                "anchor": anchor,
                "reason": "record has skipped=true",
            })
            continue

        html = record.get("html")
        if not isinstance(anchor, str) or not isinstance(html, str):
            input_issues.append({
                "line": line_number,
                "anchor": anchor,
                "reason": "readback record lacks a string anchor or html field",
            })
            continue
        body_match = BODY_RE.search(html)
        if body_match is None:
            input_issues.append({
                "line": line_number,
                "anchor": anchor,
                "reason": "html does not contain a complete body element",
            })
            continue

        parser = BodyAuditParser(anchor)
        parser.feed(body_match.group(1))
        parser.close()
        anchor_result = parser.result()
        anchor_result["inputLine"] = line_number
        anchor_result["flatText"] = flat_text(body_match.group(1))
        anchor_results.append(anchor_result)
        tag_occurrences += parser.tag_occurrences

        for tag, counts in parser.inventory.items():
            inventory[tag].update(counts)
        for tag, forms in parser.non_structural_depths.items():
            for form, counts in forms.items():
                depth_distributions[tag][form].update(counts)
        depth_zero_occurrences.extend(parser.depth_zero_non_structural)
        self_closing_structural.extend(parser.self_closing_structural)
        for tag, counts in parser.void_spellings.items():
            void_spellings[tag].update(counts)
        mismatched_closes.extend(parser.mismatched_closes)
        unclosed_tags.extend(anchor_result["unclosedTags"])

    forms = ("open", "close", "selfClosing")
    tag_inventory = {}
    for tag in sorted(inventory):
        counts = {form: inventory[tag][form] for form in forms}
        counts["total"] = sum(counts.values())
        tag_inventory[tag] = counts

    non_structural_depths = {}
    for tag in sorted(depth_distributions):
        non_structural_depths[tag] = {
            form: counter_dict(depth_distributions[tag][form])
            for form in ("all", *forms)
        }

    void_tag_spellings = {
        tag: {
            "withSlash": void_spellings[tag]["withSlash"],
            "withoutSlash": void_spellings[tag]["withoutSlash"],
        }
        for tag in sorted(void_spellings)
    }
    all_depths_zero = bool(anchor_results) and all(
        item["finalDepth"] == 0 for item in anchor_results
    )
    any_depth_negative = any(item["wentNegative"] for item in anchor_results)
    well_formed = not mismatched_closes and not unclosed_tags

    # Two independent ways for a row to be a read of more than one paragraph.
    # Neither is implied by the depth bookkeeping above: a two-paragraph read is
    # perfectly balanced and perfectly well formed.
    multi_block = [
        {
            "anchor": item["anchor"],
            "depthZeroStructural": item["depthZeroStructural"],
            "depthZeroBlocks": item["depthZeroBlocks"],
        }
        for item in anchor_results
        if item["depthZeroBlocks"] != 1
    ]
    tokens = {anchor_token(item["anchor"]) for item in anchor_results}
    foreign_text = []
    for item in anchor_results:
        mine = anchor_token(item["anchor"])
        others = sorted(
            token for token in tokens
            if token != mine and token in item["flatText"]
        )
        if others:
            foreign_text.append({"anchor": item["anchor"], "alsoCarries": others})
    for item in anchor_results:
        del item["flatText"]

    return {
        "schemaVersion": 1,
        "source": display_path(path),
        "scope": "markup between the opening and closing body tags",
        "structuralTags": list(STRUCTURAL_TAGS),
        "voidTagsNotPushed": sorted(VOID_TAGS),
        "input": {
            "readbackRecords": readback_records,
            "anchorsAnalyzed": len(anchor_results),
            "skippedRecords": len(skipped),
            "skipped": skipped,
            "otherUnanalyzedRecords": len(input_issues),
            "issues": input_issues,
        },
        "tagOccurrencesExamined": tag_occurrences,
        "tagInventory": tag_inventory,
        "voidTagSpellings": void_tag_spellings,
        "structuralDepth": {
            "allFinalDepthsZero": all_depths_zero,
            "anyWentNegative": any_depth_negative,
            "perAnchor": anchor_results,
        },
        "singleParagraphRead": {
            "everyAnchorExactlyOneBlockAtDepthZero": not multi_block,
            "anchorsWithOtherThanOneBlock": multi_block,
            "noAnchorCarriesAnotherAnchorsText": not foreign_text,
            "anchorsCarryingForeignAnchorText": foreign_text,
        },
        "selfClosingStructuralTags": self_closing_structural,
        "nonStructuralDepths": non_structural_depths,
        "nonStructuralAtDepthZero": depth_zero_occurrences,
        "nesting": {
            "wellFormed": well_formed,
            "mismatchedCloseTags": mismatched_closes,
            "unclosedTags": unclosed_tags,
        },
    }


def format_depths(distribution: dict[str, int]) -> str:
    return ", ".join(
        f"depth {depth}={count}" for depth, count in distribution.items()
    ) or "none"


def print_summary(result: dict[str, Any], output: Path) -> None:
    zero_depth = result["nonStructuralAtDepthZero"]
    if zero_depth:
        print(
            "*** NON-STRUCTURAL TAGS AT DEPTH 0: "
            f"{len(zero_depth)} OCCURRENCE(S) ***"
        )

    input_summary = result["input"]
    print("Readback nesting audit")
    print(
        f"Input: {input_summary['readbackRecords']} records, "
        f"{input_summary['anchorsAnalyzed']} analyzed, "
        f"{input_summary['skippedRecords']} skipped"
    )
    for item in input_summary["skipped"]:
        print(f"  skipped: {item['anchor']}")
    for item in input_summary["issues"]:
        print(f"  unanalyzed: {item['anchor']}: {item['reason']}")

    print(f"Tag occurrences examined: {result['tagOccurrencesExamined']}")
    print("Tag inventory (open/close/self-closing):")
    for tag, counts in result["tagInventory"].items():
        print(
            f"  {tag}: {counts['open']}/{counts['close']}/"
            f"{counts['selfClosing']}"
        )

    depth = result["structuralDepth"]
    nonzero = [
        item for item in depth["perAnchor"] if item["finalDepth"] != 0
    ]
    print(
        "Structural depth: "
        f"allFinalDepthsZero={depth['allFinalDepthsZero']}, "
        f"wentNegative={sum(item['wentNegative'] for item in depth['perAnchor'])}, "
        f"nonzeroFinal={len(nonzero)}"
    )
    print(
        "Self-closing structural tags: "
        f"{len(result['selfClosingStructuralTags'])}"
    )
    for item in result["selfClosingStructuralTags"]:
        print(f"  {item['anchor']}: {item['raw']}")

    print("Non-structural tag depths (all forms):")
    for tag, distributions in result["nonStructuralDepths"].items():
        print(f"  {tag}: {format_depths(distributions['all'])}")
    if not zero_depth:
        print("Non-structural tags at depth 0: none")

    nesting = result["nesting"]
    print(
        f"Nesting: wellFormed={nesting['wellFormed']}, "
        f"mismatchedCloses={len(nesting['mismatchedCloseTags'])}, "
        f"unclosedTags={len(nesting['unclosedTags'])}"
    )
    if result["voidTagSpellings"]:
        print("Void tag spellings:")
        for tag, counts in result["voidTagSpellings"].items():
            print(
                f"  {tag}: withSlash={counts['withSlash']}, "
                f"withoutSlash={counts['withoutSlash']}"
            )
    else:
        print("Void tag spellings: no void tags observed")
    print(f"Report: {display_path(output)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = analyze(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print_summary(result, args.output)


if __name__ == "__main__":
    main()
