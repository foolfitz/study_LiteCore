#!/usr/bin/env python3
"""The owner's pasted text must not appear in this evidence folder.

Reads the git-ignored text (wasm_sdk_probe/build/paste-repro/owner-paste.txt)
and looks for every line of it (4+ characters), every 6-character window that
carries a non-ASCII character and every 12-character window of every line, in
every file under findings/evidence/paste-latency/.  Prints
the number of needles and the files that contain any; exit 1 on a hit.  The
needles never leave this process.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TEXT = REPO / "wasm_sdk_probe" / "build" / "paste-repro" / "owner-paste.txt"


def main() -> int:
    if not TEXT.is_file():
        print(f"no owner text at {TEXT}; nothing to check against", file=sys.stderr)
        return 2
    owner = TEXT.read_text(encoding="utf-8")
    needles = {line.strip() for line in owner.split("\n") if len(line.strip()) >= 4}
    # Windows: 6 characters when they carry a non-ASCII character, 12 when
    # ASCII only -- a 6-letter ASCII window is an ordinary word (the first run
    # of this check flagged a browser's name that both the text and the README
    # mention), and ordinary words are not the owner's content.
    for line in owner.split("\n"):
        stripped = line.strip()
        for width in (6, 12):
            for i in range(0, max(0, len(stripped) - width + 1)):
                window = stripped[i:i + width]
                if width == 12 or any(ord(c) > 127 for c in window):
                    needles.add(window)
    hits: dict[str, int] = {}
    files = 0
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path == Path(__file__).resolve():
            continue
        files += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        count = sum(1 for needle in needles if needle in text)
        if count:
            hits[str(path.relative_to(HERE))] = count
    print(f"needles {len(needles)} files {files} hits {hits}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
