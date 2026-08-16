#!/usr/bin/env python3
"""Is this call actually IN the product build?

Written 2026-08-17, the day after a link shipped a mechanism that did nothing.

`refreshEditorAccessibility()` -- the only thing that switches accessibility on
-- had exactly one call site, and it sat inside `#ifdef OXSDK_EDITOR_DISCOVERY`
AND `#ifndef OXSDK_FINDING_016_SELECTION_BARRIER`.  The product profile defines
both, so the call was compiled out.  Every `getA11yFocusedParagraph()` in the
product returned an empty paragraph, and the block-identity half of the v3 link
was inert the moment it shipped.

Reading did not catch it and grep would not have either: the call IS in the
file, on a line that looks reachable, and the `#ifndef` that removes it is
thirty lines up.  What catches it is asking the PREPROCESSOR, with the product's
own define set -- the same question the compiler answers, asked before the link
instead of after it.

    em++ -E <the product's exact flags> src/probe_engine.cpp | grep

Usage:
  check_product_build_reaches.py              # check, exit 1 if unreachable
  check_product_build_reaches.py --self-test  # prove the check can fail
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
WORKSPACE = PROJECT.parent

# The product profile's compile line, from the Makefile's $(E2_C_BUILD)/%.o rule.
# Kept beside the check it feeds rather than derived from the Makefile: a
# derivation that silently produced the WRONG define set would make this check
# agree with whatever it was given, which is the failure mode it exists to
# prevent.  The self-test asserts these are the flags the Makefile still uses.
PRODUCT_DEFINES = ("-DOXSDK_EDITOR_DISCOVERY",
                   "-DOXSDK_FINDING_016_SELECTION_BARRIER",
                   "-DOXSDK_E2_FORMAT_BARRIER")

INCLUDES = (
    "-DLOK_USE_UNSTABLE_API",
    f"-I{WORKSPACE}/libreoffice-26-8/include",
    f"-I{WORKSPACE}/wasm-lite/build-headless-probe/config_host",
    f"-I{WORKSPACE}/wasm-lite/build-headless-probe/workdir/"
    "UnoApiHeadersTarget/udkapi/comprehensive",
    f"-I{WORKSPACE}/wasm-lite/build-headless-probe/workdir/"
    "UnoApiHeadersTarget/offapi/comprehensive",
    f"-I{WORKSPACE}/wasm-lite/build-headless-probe/workdir/UnpackedTarball/boost",
)
COMPILER = WORKSPACE / "wasm-lite" / "tools" / "emsdk" / "upstream" / "emscripten" / "em++"

# What the product must actually reach.  Each entry is a call as it appears in
# the source, and a reason -- because "this must be in the build" is a claim
# somebody has to make.
REQUIRED = (
    ("refreshEditorAccessibility();",
     "switches accessibility on; without it getA11yFocusedParagraph() returns "
     "an empty paragraph and every caret fingerprint is the hash of an empty "
     "string (measured, findings/evidence/queue-block-identity/after-link-v3/)"),
    ("handleEditorPlaceCaret(command);",
     "the click that answers with where the caret went; an entry point the "
     "product cannot reach is an entry point that is not there"),
    ("gFormatBarrier.readbackParagraphKnown = refreshCaretParagraph();",
     "finding 046's fix reads the paragraph the barrier's own selection landed "
     "on; taken at the read, not at the verdict"),
)


def preprocess(source: Path) -> str:
    result = subprocess.run(
        [str(COMPILER), *INCLUDES, *PRODUCT_DEFINES, "-E", str(PROJECT / source)],
        capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"preprocessing failed:\n{result.stderr[-2000:]}")
    return result.stdout


def check(source: Path = Path("src/probe_engine.cpp")) -> dict:
    expanded = preprocess(source)
    findings = []
    for call, why in REQUIRED:
        # The preprocessor keeps the source text of everything it did not
        # remove, so a call that survives appears verbatim.
        findings.append({
            "call": call,
            "reachable": call in expanded,
            "why": why,
        })
    unreachable = [f["call"] for f in findings if not f["reachable"]]
    return {
        "schemaVersion": 1,
        "release": "product-build-reachability",
        "source": str(source),
        "defines": list(PRODUCT_DEFINES),
        "required": findings,
        "unreachableInProductBuild": unreachable,
        "ok": not unreachable,
    }


def self_test() -> int:
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    makefile = (PROJECT / "Makefile").read_text(encoding="utf-8")
    rule = makefile.split("$(E2_C_BUILD)/%.o:", 1)
    verify("the Makefile still has the product object rule", len(rule) == 2)
    if len(rule) == 2:
        body = rule[1].split("\n\n", 1)[0]
        for define in PRODUCT_DEFINES:
            verify(f"the product build still passes {define}", define in body)

    report = check()
    verify("every required call is in the product build", report["ok"],
           json.dumps(report["unreachableInProductBuild"]))

    # The one that matters: this check must be able to say NO.  A symbol that is
    # deliberately excluded from the product -- the discovery-only entry point --
    # must come back unreachable, or the check is agreeing with everything.
    expanded = preprocess(Path("src/probe_engine.cpp"))
    verify("a discovery-only call is correctly reported as NOT in the product",
           "handleEditorDiscoverySelect(command);" not in expanded
           or "oxsdk_editor_discovery" not in expanded,
           "the negative control appeared in the product build")

    # And the historical case, exactly: the call site that WAS compiled out.
    # `#ifndef OXSDK_FINDING_016_SELECTION_BARRIER` still guards the search-time
    # refresh, so with the product's defines it must be absent -- while the open
    # one is present.  One name, two sites, opposite answers: that is what makes
    # counting call sites in the SOURCE the wrong check.
    verify("the search-time refresh is still excluded (the site that fooled us)",
           expanded.count("refreshEditorAccessibility();") == 1,
           f"found {expanded.count('refreshEditorAccessibility();')} call sites"
           " after preprocessing; the open one should be the only survivor")

    total = 4 + len(PRODUCT_DEFINES)
    print(f"\nself-test: {total - len(failures)}/{total} checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    report = check()
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
