#!/usr/bin/env python3
"""The extended reader must go red where round 2 needs it, and the
compatibility check must go red when the reader changes round 1's output.

Usage: check_reader_red2.py ROUND1_DIR INPUTS_DIR WORK_DIR REPORT_FILE

  a  header-footer.fodt vs the same with the header text changed   -> DIFFERENT
  b  header-footer.fodt vs the same with the header removed        -> DIFFERENT
  c  cells.fodt with a table nested in A1 vs the same table placed
     after the outer table instead (same paragraphs, same text)     -> DIFFERENT
  c2 the nested document's summary vs the same with parentCell deleted -> DIFFERENT
  d  frame-protected.fodt vs the text box text changed             -> DIFFERENT
  e  header-footer.fodt vs itself re-serialised by ElementTree     -> SAME (positive control)
  f  check_reader_compat.py with a reader whose human() pads the style
     column by one less character                                  -> FAIL (exit 1)
  g  check_reader_compat.py with a reader whose signature drops the
     heading level                                                 -> FAIL (exit 1)
  h  check_reader_compat.py with the reader unchanged               -> PASS (exit 0)
Exit 1 if any expectation fails.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import md_structure  # noqa: E402


def sig(path):
    return md_structure.signature(md_structure.summarize(path))


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def compat_run(round1, work, reader_text, tag):
    tool = os.path.join(work, "tool-" + tag)
    os.makedirs(tool, exist_ok=True)
    write(os.path.join(tool, "md_structure.py"), reader_text)
    shutil.copyfile(os.path.join(HERE, "check_reader_compat.py"), os.path.join(tool, "check_reader_compat.py"))
    scratch = os.path.join(work, "compat-" + tag)
    os.makedirs(scratch, exist_ok=True)
    proc = subprocess.run([sys.executable, "-I", "-B", os.path.join(tool, "check_reader_compat.py"), round1,
                           scratch, os.path.join(work, "compat-%s.txt" % tag)], capture_output=True, text=True)
    last = [line for line in proc.stdout.splitlines() if line.startswith(("field mismatches", "RESULTS.md", "RESULT"))]
    return proc.returncode, last


def main(argv):
    round1, inputs, work, report = argv[1:5]
    os.makedirs(work, exist_ok=True)
    lines = []
    failures = 0
    with tempfile.TemporaryDirectory(dir=work) as tmp:
        hf = os.path.join(inputs, "header-footer.fodt")
        hf_text = read(hf)
        a = write(os.path.join(tmp, "a.fodt"), hf_text.replace("Header line text", "Header line TEXT"))
        b = write(os.path.join(tmp, "b.fodt"), re.sub(r"<style:header>.*?</style:header>", "", hf_text))
        cells = read(os.path.join(inputs, "cells.fodt"))
        inner = ('<table:table table:name="N1"><table:table-column table:number-columns-repeated="2"/>'
                 '<table:table-row><table:table-cell><text:p>n1</text:p></table:table-cell>'
                 '<table:table-cell><text:p>n2</text:p></table:table-cell></table:table-row></table:table>')
        nested = cells.replace("<text:p>A1 text</text:p>", "<text:p>A1 text</text:p>" + inner, 1)
        flat = cells.replace("</table:table>\n<text:p>After", "</table:table>\n" + inner + "\n<text:p>After", 1)
        # flat puts the inner table after the outer one; A1 keeps only its paragraph.
        c1 = write(os.path.join(tmp, "c-nested.fodt"), nested)
        c2 = write(os.path.join(tmp, "c-flat.fodt"), flat)
        frame = os.path.join(inputs, "frame-protected.fodt")
        d = write(os.path.join(tmp, "d.fodt"), read(frame).replace("Inside frame text", "Inside frame TEXT"))
        tree = ET.parse(hf)
        e = os.path.join(tmp, "e.fodt")
        tree.write(e, encoding="UTF-8", xml_declaration=True)
        cases = [("a", "header text changed", hf, a, False),
                 ("b", "header removed", hf, b, False),
                 ("c", "table nested in A1 vs after the outer table", c1, c2, False),
                 ("d", "text box text changed", frame, d, False),
                 ("e", "re-serialised (positive control)", hf, e, True)]
        # c2: the same nested document, its summary with parentCell deleted (what
        # round 1's reader would have produced for the nesting) -> must differ.
        nested_summary = md_structure.summarize(c1)
        stripped = {**nested_summary, "tables": [{k: v for k, v in t.items() if k != "parentCell"}
                                                 for t in nested_summary["tables"]]}
        same = md_structure.signature(nested_summary) == md_structure.signature(stripped)
        failures += same
        lines.append("%s %-46s %s (expected %s) %s" % ("c2", "nested: summary vs parentCell deleted",
                                                     "SAME" if same else "DIFFERENT", "DIFFERENT",
                                                     "FAIL" if same else "ok"))
        for key, label, x, y, want_same in cases:
            same = sig(x) == sig(y)
            ok = same == want_same
            failures += not ok
            lines.append("%s %-46s %s (expected %s) %s" % (key, label, "SAME" if same else "DIFFERENT",
                                                         "SAME" if want_same else "DIFFERENT", "ok" if ok else "FAIL"))
        lines.append("")
        lines.append("--- c, nested ---")
        lines.append(md_structure.human(md_structure.summarize(c1)))
        lines.append("--- c, flat ---")
        lines.append(md_structure.human(md_structure.summarize(c2)))
        lines.append("")
    reader = read(os.path.join(HERE, "md_structure.py"))
    pad = reader.replace('"%s[%d] %-22s %-28s %r%s%s"', '"%s[%d] %-21s %-28s %r%s%s"', 1)
    nolevel = reader.replace('return [p["kind"], p["level"], p["style"],', 'return [p["kind"], None, p["style"],', 1)
    assert pad != reader and nolevel != reader, "mutation did not apply"
    for key, label, text, want in (("f", "compat check, human() padding mutated", pad, 1),
                                   ("g", "compat check, signature drops heading level", nolevel, 1),
                                   ("h", "compat check, reader unchanged", reader, 0)):
        rc, last = compat_run(round1, work, text, key)
        ok = rc == want
        failures += not ok
        lines.append("%s %-46s exit %d (expected %d) %s" % (key, label, rc, want, "ok" if ok else "FAIL"))
        lines += ["    " + line for line in last]
    text = "\n".join(lines) + "\n"
    write(report, text)
    print(text, end="")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
