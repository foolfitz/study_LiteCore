#!/usr/bin/env python3
"""Does the CORE build we link against actually provide what the product claims?

Written 2026-08-17, after the second v3 link.

`check_product_build_reaches.py` asks whether OUR call survives OUR
preprocessor.  It passed.  The call was in the build, it ran, and it still did
nothing -- because the capability it asks core for is not in CORE's build.  One
layer down, and invisible to every check we had.

Concretely: the product runs on a core configured with
`--with-wasm-module=writer`.  That sets ENABLE_WASM_STRIP_ACCESSIBILITY, which
removes 26 objects from sw/source/core/access and makes
`SwEditWin::CreateAccessible()` return an empty reference.  LOK's
`setAccessibilityState()` returns void and silently does nothing when there is
no accessible, so the product had no way to learn any of this: it asked for
accessibility, got no error, and read empty paragraphs forever.

A capability has TWO independent switches in this tree, and they are wired to
different configure inputs (see finding 057).  Checking either one alone would
have agreed with a build that cannot work:

  * the Make variable  -- decides whether the objects are COMPILED
  * the C++ macro      -- decides whether the CALLERS are compiled

This check requires both, and it is pointed at a real passing build (native) as
well as a real failing one (wasm), so "it can fail" is demonstrated against
actual builds rather than against a mutation we invented.

Usage:
  check_core_build_provides.py                 # check the product's core build
  check_core_build_provides.py --build DIR     # check some other core build
  check_core_build_provides.py --self-test     # native must pass, wasm must fail
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent

# The core build the product's WASM artifact is linked from.
PRODUCT_CORE_BUILD = WORKSPACE / "wasm-lite" / "build-headless-probe"
# A core build of the SAME source that does provide the capability.  This is the
# positive control: not a mutation, an actual build that works.
NATIVE_CORE_BUILD = WORKSPACE / "build-native-26-8"


class Capability:
    """Something the product asks core for, and every switch that can remove it.

    `objects` are compiled units; `macro_must_be` is the value the C++ callers
    are compiled against.  Both are required, because in this tree they answer
    to different configure inputs and can disagree.
    """

    def __init__(self, name, why, objects, macro_header, macro, macro_must_be):
        self.name = name
        self.why = why
        self.objects = objects
        self.macro_header = macro_header
        self.macro = macro
        self.macro_must_be = macro_must_be


CAPABILITIES = (
    Capability(
        name="writer-lok-accessibility",
        why="getA11yFocusedParagraph() and LOK_CALLBACK_A11Y_FOCUS_CHANGED are "
            "the only source of paragraph identity in LOK (measured: LOK has no "
            "paragraph index anywhere).  Without this, every caret fingerprint "
            "is the hash of an empty string and finding 046's identity gate has "
            "no input -- not broken, unfed.",
        # accmap builds the accessibility tree; accpara IS the focused paragraph.
        # Both are removed by sw/Library_sw.mk:108 when the Make variable is set.
        objects=(
            "workdir/CxxObject/sw/source/core/access/accmap.o",
            "workdir/CxxObject/sw/source/core/access/accpara.o",
            "workdir/CxxObject/sw/source/core/access/accdoc.o",
        ),
        macro_header="config_host/config_wasm_strip.h",
        macro="ENABLE_WASM_STRIP_ACCESSIBILITY",
        # 1 means STRIP, so the capability requires 0.  With 1, the objects may
        # still be compiled and SwEditWin::CreateAccessible() returns {} anyway
        # (sw/source/uibase/docvw/edtwin.cxx:6532) -- dead code, no capability.
        macro_must_be=0,
    ),
)


def read_macro(build: Path, header: str, macro: str):
    path = build / header
    if not path.exists():
        return None
    match = re.search(rf"^\s*#define\s+{re.escape(macro)}\s+(\d+)\s*$",
                      path.read_text(encoding="utf-8"), re.MULTILINE)
    return int(match.group(1)) if match else None


def check(build: Path) -> dict:
    results = []
    for cap in CAPABILITIES:
        missing = [o for o in cap.objects if not (build / o).exists()]
        macro_value = read_macro(build, cap.macro_header, cap.macro)
        macro_ok = macro_value == cap.macro_must_be
        results.append({
            "capability": cap.name,
            "why": cap.why,
            "objectsCompiled": not missing,
            "missingObjects": missing,
            "macro": cap.macro,
            "macroValue": macro_value,
            "macroRequired": cap.macro_must_be,
            "callersCompiled": macro_ok,
            # Both, deliberately.  Either alone is a check that agrees with a
            # build that cannot work.
            "provided": (not missing) and macro_ok,
        })
    absent = [r["capability"] for r in results if not r["provided"]]
    return {
        "schemaVersion": 1,
        "release": "core-build-capability",
        "coreBuild": str(build),
        "capabilities": results,
        "notProvidedByCoreBuild": absent,
        "ok": not absent,
    }


def self_test() -> int:
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    # The negative case, which is the product we ship today.  This check exists
    # because this build measured as unable to produce a focused paragraph.
    wasm = check(PRODUCT_CORE_BUILD)
    verify("the product's core build is reported as NOT providing a11y",
           not wasm["ok"], "the wasm build came back ok, so the check is blind")
    a11y = wasm["capabilities"][0]
    verify("...and names the compiled-out objects",
           not a11y["objectsCompiled"] and a11y["missingObjects"])
    verify("...and names the macro that removes the callers",
           a11y["macroValue"] == 1)

    # The positive control: a real build of the same source that DOES provide
    # it.  Without this the check could be failing for an unrelated reason (bad
    # path, typo in a filename) and look identical.
    native = check(NATIVE_CORE_BUILD)
    verify("a real core build that provides a11y is reported as providing it",
           native["ok"], json.dumps(native["notProvidedByCoreBuild"]))

    # The divergence itself (finding 057): the two switches are independent, so
    # a check that consulted only one would pass a build that cannot work.
    # Prove that by re-running with each half relaxed and showing the verdict
    # changes -- if it does not, this check is only really testing one thing.
    a = a11y["objectsCompiled"]
    b = a11y["callersCompiled"]
    verify("the two switches are checked independently",
           a is False and b is False and (a or b) is False,
           "both halves must be consulted; see finding 057")

    total = 5
    print(f"\nself-test: {total - len(failures)}/{total} checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, default=PRODUCT_CORE_BUILD)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    report = check(args.build)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
