#!/usr/bin/env python3
"""Re-check the six saved ODTs in this directory.

Run it from anywhere:  python3 check.py

The claim being checked is "undo puts the document back", and the only way to
state that honestly is to compare what came out of the engine, not what the
status bar said.  Two things follow, and both were learned the hard way:

  * Compare the ``content.xml`` body, not the file.  Two ODTs with identical
    bodies have different sha256 -- the zip carries timestamps and meta.xml
    carries an editing-cycle counter, so whole-file equality is false for a
    successful undo.  SHA256SUMS in this directory is provenance for the files,
    NOT the criterion.

  * Keep the positive controls in the same run.  The first version of this
    comparison walked the wrong XML namespace, so every ``style-name`` lookup
    returned None and "after undo == pristine" passed -- but so did "after
    heading == pristine", which is impossible.  A comparison that cannot fail
    when the thing it checks is switched off is not a weak check, it is not a
    check.  The two CHANGED assertions below are that switch.
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BODY = re.compile(r"<office:body>.*</office:body>", re.S)


def body(name: str) -> str:
    with zipfile.ZipFile(io.BytesIO((HERE / name).read_bytes())) as archive:
        content = archive.read("content.xml").decode("utf-8")
    match = BODY.search(content)
    if match is None:
        raise SystemExit(f"{name}: no office:body in content.xml")
    return match.group(0)


PRISTINE = "00-pristine.odt"

# (file, must-equal-pristine, what the step was)
CASES = [
    ("01-after-heading.odt", False, "按「標題」之後"),
    ("02-after-undo.odt", True, "按「復原」之後"),
    ("03-after-list-none.odt", False, "按「移除清單」之後"),
    ("04-after-undo.odt", True, "按「復原」之後"),
    ("05-after-two-extra-undos.odt", True, "多按兩次「復原」（已經沒有東西可復原）之後"),
]


def main() -> int:
    base = body(PRISTINE)
    failures = []
    for name, same, label in CASES:
        observed = body(name) == base
        ok = observed == same
        expectation = "與原始相同" if same else "與原始不同"
        print(f"{'OK  ' if ok else 'FAIL'}  {name:32} {expectation:12} {label}")
        if not ok:
            failures.append(name)
    if failures:
        print(f"\n{len(failures)} 項不符：{', '.join(failures)}")
        return 1
    print("\n六份全部符合：復原把 body 還原成與原始逐位元組相同，"
          "而兩個正對照確實改動過文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
