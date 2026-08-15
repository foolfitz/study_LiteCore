#!/usr/bin/env python3
"""Judge the finding 045 native probe against the registered predictions.

The predictions are in `findings/evidence/045/native/PREDICTION.md`, written
before the probe existed.  This applies them to the saved documents; it reads
files only, so the verdict can be recomputed without a LibreOffice build.

One thing worth stating because it bit the first version of the equivalent WASM
check: "off" is not the ABSENCE of the property.  LibreOffice writes an explicit
`fo:font-weight="normal"` and `style:text-underline-style="none"`, so a check
that only looks for the presence of "bold" reports "off" for a span that says
nothing at all -- including one that inherits the property from elsewhere.  Each
property therefore has an ON pattern and an OFF pattern, and a span matching
neither is `unknown`, not `off`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

# (on pattern, off pattern) per command.
PROPERTY = {
    "bold": (r'fo:font-weight="bold"', r'fo:font-weight="normal"'),
    "italic": (r'fo:font-style="italic"', r'fo:font-style="normal"'),
    "underline": (r'style:text-underline-style="(?!none)[a-z]+"',
                  r'style:text-underline-style="none"'),
    "strikethrough": (r'style:text-line-through-style="(?!none)[a-z]+"',
                      r'style:text-line-through-style="none"'),
}

MARKERS = {
    "bold": ("F45BOLDA", "F45BOLDB", "E2-D1-BOLD-ON"),
    "italic": ("F45ITALA", "F45ITALB", "E2-D1-ITALIC-ON"),
    "underline": ("F45UNDRA", "F45UNDRB", "E2-D1-UNDERLINE-ON"),
    "strikethrough": ("F45STRKA", "F45STRKB", "E2-D1-STRIKE-ON"),
}

# What each arm predicted, keyed by the prediction id in PREDICTION.md.
# "on" / "off" refer to the property, per text fragment.
ARMS = {
    "param-off": ("P1", {"first": "off"}),
    "param-on": ("P2", {"first": "on"}),
    "bare": ("P3", {"first": "on"}),
    "bare-twice": ("P4", {"first": "on", "second": "off"}),
    "param-off-then-on": ("P5", {"first": "off", "second": "on"}),
    "param-on-range": ("P6", {"anchor": "on"}),
    "param-off-range": ("P7", {"anchor": "off"}),
}


def content_of(path: Path) -> str | None:
    if not path.is_file():
        return None
    with zipfile.ZipFile(path) as archive:
        return archive.read("content.xml").decode("utf-8")


def state_of(content: str, fragment: str, command: str) -> str:
    """Is the property on, off, or unstated for the span holding `fragment`?"""
    on_pattern, off_pattern = PROPERTY[command]
    span = re.search(r'<text:span text:style-name="([^"]+)">([^<]*)'
                     + re.escape(fragment), content)
    if not span:
        # The fragment may be in the paragraph with no span at all, which means
        # it carries whatever the paragraph carries -- reported as `unspanned`
        # rather than silently as `off`.
        return "unspanned" if fragment in content else "missing"
    style = re.search(r'<style:style style:name="%s"[^>]*>(.*?)</style:style>'
                      % re.escape(span.group(1)), content, re.S)
    body = style.group(1) if style else ""
    if re.search(on_pattern, body):
        return "on"
    if re.search(off_pattern, body):
        return "off"
    return "unknown"


def judge(run: Path) -> dict:
    results = {}
    problems: list[str] = []
    for command, (first, second, anchor) in MARKERS.items():
        for arm, (prediction, expected) in ARMS.items():
            label = f"{command}-{arm}"
            content = content_of(run / f"after-{label}.odt")
            if content is None:
                problems.append(f"{label}: no saved document")
                continue
            observed = {}
            for key, want in expected.items():
                fragment = {"first": first, "second": second,
                            "anchor": anchor}[key]
                got = state_of(content, fragment, command)
                observed[key] = got
                if got != want:
                    problems.append(f"{label}: {key} is {got}, predicted {want} "
                                    f"({prediction})")
            results[label] = {"prediction": prediction, "expected": expected,
                              "observed": observed,
                              "held": all(observed[k] == v
                                          for k, v in expected.items())}
    by_prediction: dict[str, list[str]] = {}
    for label, item in results.items():
        by_prediction.setdefault(item["prediction"], []).append(
            "held" if item["held"] else "broken")
    return {
        "arms": results,
        "predictions": {key: ("held" if all(v == "held" for v in value)
                              else "broken")
                        for key, value in sorted(by_prediction.items())},
        "problems": problems,
        "pass": not problems,
    }


def self_test(run: Path) -> int:
    """The property detector has to distinguish on, off and unstated."""
    failures = []
    samples = [
        ('<text:span text:style-name="T1">XMARK</text:span>',
         '<style:style style:name="T1" style:family="text">'
         '<style:text-properties fo:font-weight="bold"/></style:style>',
         "bold", "on"),
        ('<text:span text:style-name="T1">XMARK</text:span>',
         '<style:style style:name="T1" style:family="text">'
         '<style:text-properties fo:font-weight="normal"/></style:style>',
         "bold", "off"),
        ('<text:span text:style-name="T1">XMARK</text:span>',
         '<style:style style:name="T1" style:family="text">'
         '<style:text-properties fo:font-style="italic"/></style:style>',
         "bold", "unknown"),
        ('<text:p>XMARK</text:p>', "", "bold", "unspanned"),
        ("", "", "bold", "missing"),
        ('<text:span text:style-name="T1">XMARK</text:span>',
         '<style:style style:name="T1" style:family="text">'
         '<style:text-properties style:text-underline-style="none"/></style:style>',
         "underline", "off"),
        ('<text:span text:style-name="T1">XMARK</text:span>',
         '<style:style style:name="T1" style:family="text">'
         '<style:text-properties style:text-underline-style="solid"/></style:style>',
         "underline", "on"),
    ]
    for markup, style, command, expected in samples:
        got = state_of(markup + style, "XMARK", command)
        if got != expected:
            failures.append(f"{command} {expected!r}: detector said {got!r}")
    # And the judge itself has to be able to report a broken prediction.
    verdict = judge(run)
    if not verdict["arms"]:
        failures.append("the judge found no arms to judge")
    print(json.dumps({"selfTest": len(samples) + 1, "failures": failures,
                      "pass": not failures}, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.run)
    verdict = judge(args.run)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
