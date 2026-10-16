#!/usr/bin/env python3
"""C2: the structure reader must go red where the structure differs, and only there.

Usage: check_reader_red.py OUT_DIR
Writes OUT_DIR/C2-reader-red/result.txt and exits 1 if any expectation fails.

  a  M1 (markdown) vs C1 (the same text as text/plain)    -> DIFFERENT (the red control)
  b  M1 run 1 vs M1 run 2                                 -> SAME (positive control)
  c  M2 run 1 vs M2 run 1 with every bold attribute removed -> DIFFERENT
  d  M1 run 1 vs M1 run 1 with its headings turned into plain paragraphs -> DIFFERENT
  e  P5-M4 run 1 vs the same file with its list-item style-overrides removed -> DIFFERENT
     (added with the reader fix: the numbered items pasted into a bullet list are
     written as text:style-override on the list item; the first reader ignored it)
(The undo comparison -- undo-k vs before, SAME -- is made per run by run_arms.py.)
"""

import gzip
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import md_structure  # noqa: E402


def text_of(path):
    with gzip.open(path, "rb") as handle:
        return handle.read().decode("utf-8")


def sig(path):
    return md_structure.signature(md_structure.summarize(path))


def write_tmp(text, directory, name):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def main(argv):
    out = argv[1]
    dest = os.path.join(out, "C2-reader-red")
    os.makedirs(dest, exist_ok=True)
    m1 = os.path.join(out, "P1-M1", "run1", "after.fodt.gz")
    m1b = os.path.join(out, "P1-M1", "run2", "after.fodt.gz")
    c1 = os.path.join(out, "P1-C1-plain", "run1", "after.fodt.gz")
    m2 = os.path.join(out, "P1-M2", "run1", "after.fodt.gz")
    before = os.path.join(out, "P1-M1", "run1", "before.fodt.gz")
    lines = []
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        no_bold = re.sub(r'\s(fo:font-weight|style:font-weight-asian|style:font-weight-complex)="bold"',
                         "", text_of(m2))
        m2_mut = write_tmp(no_bold, tmp, "m2-no-bold.fodt")
        no_head = re.sub(r"<text:h\b[^>]*>", '<text:p text:style-name="Standard">', text_of(m1))
        no_head = no_head.replace("</text:h>", "</text:p>")
        m1_mut = write_tmp(no_head, tmp, "m1-no-headings.fodt")
        p5 = os.path.join(out, "P5-M4", "run1", "after.fodt.gz")
        no_override = re.sub(r'\stext:style-override="[^"]*"', "", text_of(p5))
        p5_mut = write_tmp(no_override, tmp, "p5-m4-no-override.fodt")
        cases = [
            ("a", "M1 vs C1 (red control)", m1, c1, False),
            ("b", "M1 run1 vs M1 run2", m1, m1b, True),
            ("c", "M2 vs M2 without bold attributes", m2, m2_mut, False),
            ("d", "M1 vs M1 with headings as plain paragraphs", m1, m1_mut, False),
            ("e", "P5-M4 vs P5-M4 without list-item overrides", p5, p5_mut, False),
        ]
        for key, label, a, b, want_same in cases:
            same = sig(a) == sig(b)
            ok = same == want_same
            failures += not ok
            lines.append("%s %-48s %s (expected %s) %s" % (
                key, label, "SAME" if same else "DIFFERENT", "SAME" if want_same else "DIFFERENT",
                "ok" if ok else "FAIL"))
        lines.append("")
        lines.append("--- M1 run1 after ---")
        lines.append(md_structure.human(md_structure.summarize(m1)))
        lines.append("--- C1 run1 after ---")
        lines.append(md_structure.human(md_structure.summarize(c1)))
        lines.append("--- M2 run1 after ---")
        lines.append(md_structure.human(md_structure.summarize(m2)))
        lines.append("--- M2 run1 after, bold attributes removed ---")
        lines.append(md_structure.human(md_structure.summarize(m2_mut)))
        lines.append("--- M1 run1 after, headings as plain paragraphs ---")
        lines.append(md_structure.human(md_structure.summarize(m1_mut)))
        lines.append("--- P5-M4 run1 after ---")
        lines.append(md_structure.human(md_structure.summarize(p5)))
        lines.append("--- P5-M4 run1 after, list-item overrides removed ---")
        lines.append(md_structure.human(md_structure.summarize(p5_mut)))
        lines.append("--- P1 before ---")
        lines.append(md_structure.human(md_structure.summarize(before)))
    text = "\n".join(lines) + "\n"
    with open(os.path.join(dest, "result.txt"), "w") as handle:
        handle.write(text)
    print(text)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
