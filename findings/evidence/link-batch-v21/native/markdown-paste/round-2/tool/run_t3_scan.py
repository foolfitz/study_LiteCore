#!/usr/bin/env python3
"""T3: run the md4c harness over every Markdown corpus item and check its controls.

Usage: run_t3_scan.py MD4C_SCAN_BINARY OUT_DIR

Scans round 2's tool/corpus/*.md and round 1's tool/corpus/M*.md (round 1's C1
was pasted as text/plain and M8-utf16le is not UTF-8 Markdown: not scanned).
Writes OUT_DIR/scan.jsonl and OUT_DIR/controls.txt.

Controls (exit 1 if any fails):
  must be classified REMOTE (a non-data MD_SPAN_IMG): S01, M11, M11b
  must NOT be (no non-data image):                   S08, M10, S06
  S08 and M10 must have exactly one data: image (the classifier sees images at all)
  M13 (empty) and W1 (spaces) must have no text (the text count can be zero)
  M1 must have text (the text count can be non-zero)
"""

import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROUND1 = os.path.join(HERE, "..", "..", "tool", "corpus")


def main(argv):
    binary, out = argv[1:3]
    os.makedirs(out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(HERE, "corpus", "*.md"))) + \
        sorted(glob.glob(os.path.join(ROUND1, "M*.md")))
    proc = subprocess.run([binary] + files, capture_output=True, text=True, check=True)
    with open(os.path.join(out, "scan.jsonl"), "w") as handle:
        handle.write(proc.stdout)
    scans = {json.loads(line)["file"][:-3]: json.loads(line) for line in proc.stdout.splitlines()}
    checks = []
    for item in ("S01-inline-http", "M11", "M11b"):
        checks.append(("%s is REMOTE" % item, scans[item]["imagesNonData"] >= 1))
    for item in ("S08-data-only", "M10", "S06-fenced-lookalike"):
        checks.append(("%s is not REMOTE" % item, scans[item]["imagesNonData"] == 0))
    for item in ("S08-data-only", "M10"):
        checks.append(("%s has exactly one data: image" % item, scans[item]["imagesData"] == 1))
    for item in ("M13", "W1-spaces"):
        checks.append(("%s has no text" % item, scans[item]["textNonBlank"] == 0))
    checks.append(("M1 has text", scans["M1"]["textNonBlank"] > 0))
    lines = ["scanned %d files with %s" % (len(files), os.path.basename(binary))]
    lines += ["%-40s %s" % (label, "ok" if ok else "FAIL") for label, ok in checks]
    failed = sum(1 for _, ok in checks if not ok)
    lines.append("RESULT: %s" % ("PASS" if not failed else "FAIL (%d)" % failed))
    with open(os.path.join(out, "controls.txt"), "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
