#!/usr/bin/env python3
"""The round-2 reader must reproduce round 1 exactly on round 1's data.

Usage: check_reader_compat.py ROUND1_DIR WORK_DIR REPORT_FILE

  ROUND1_DIR  findings/evidence/link-batch-v21/native/markdown-paste (read only)
  WORK_DIR    an empty scratch directory (outside the repo)
  REPORT_FILE where to write the report

What it does:
  1. copies ROUND1_DIR/out/*/run*/{summary.json,before.fodt.gz,after.fodt.gz}
     into WORK_DIR/out (round 1's own files are never written);
  2. for every run with an after.fodt.gz, recomputes the fields round 1's
     resummarize.py derives from the reader -- after, afterSignatureSha256,
     afterHuman, before, afterSameAsBefore -- with THIS folder's md_structure.py
     (the extended reader), and compares each with the value round 1 stored;
  3. runs round 1's own aggregate.py (unchanged, from ROUND1_DIR/tool) on the
     copy and compares out/RESULTS.md and out/results.json byte for byte with
     round 1's.
Exit 0 only if every comparison is equal and at least 100 runs were compared
(so a renamed folder cannot pass by comparing nothing).
"""

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import md_structure  # noqa: E402  (the extended reader)


def compact(summary, keep=60):
    """Round 1's run_arms.compact, verbatim (not imported: run_arms imports the old reader)."""
    if summary["paragraphCount"] <= keep:
        return summary
    shapes = {}
    for t in summary["tables"]:
        key = "%dx%d(h%d)" % (t["rows"], t["cols"], t["headerRows"])
        shapes[key] = shapes.get(key, 0) + 1
    return {"paragraphCount": summary["paragraphCount"], "truncatedTo": keep,
            "paragraphs": summary["paragraphs"][:keep], "tableShapes": shapes,
            "links": len(summary["links"]), "images": len(summary["images"])}


def sha_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main(argv):
    round1, work, report = argv[1:4]
    src_out = os.path.join(round1, "out")
    dst_out = os.path.join(work, "out")
    if os.path.exists(dst_out):
        shutil.rmtree(dst_out)
    copied = 0
    for path in glob.glob(os.path.join(src_out, "*", "run*", "*")):
        if os.path.basename(path) not in ("summary.json", "before.fodt.gz", "after.fodt.gz"):
            continue
        rel = os.path.relpath(path, src_out)
        os.makedirs(os.path.dirname(os.path.join(dst_out, rel)), exist_ok=True)
        shutil.copyfile(path, os.path.join(dst_out, rel))
        copied += 1
    lines = ["copied %d files from %s" % (copied, src_out)]
    compared = 0
    kept = 0
    mismatches = []
    for path in sorted(glob.glob(os.path.join(dst_out, "*", "run*", "summary.json"))):
        run_dir = os.path.dirname(path)
        with open(path) as handle:
            s = json.load(handle)
        after_gz = os.path.join(run_dir, "after.fodt.gz")
        if not os.path.exists(after_gz):
            kept += 1
            continue
        full = md_structure.summarize(after_gz)
        sig = hashlib.sha256(json.dumps(md_structure.signature(full), ensure_ascii=False,
                                        sort_keys=True).encode()).hexdigest()
        new = {"after": compact(full), "afterSignatureSha256": sig,
               "afterHuman": "\n".join(md_structure.human(full).splitlines()[:40])}
        before_gz = os.path.join(run_dir, "before.fodt.gz")
        if os.path.exists(before_gz):
            before = md_structure.summarize(before_gz)
            new["before"] = compact(before)
            new["afterSameAsBefore"] = md_structure.signature(full) == md_structure.signature(before)
        for key, value in new.items():
            stored = s.get(key)
            if json.loads(json.dumps(value, ensure_ascii=False)) != stored:
                mismatches.append("%s: %s differs" % (os.path.relpath(run_dir, dst_out), key))
        if "headerFooter" in full:
            mismatches.append("%s: has headerFooter (round-1 data should have none)" % run_dir)
        s.update(new)
        s["summarizedBy"] = "round-2 check_reader_compat.py (extended md_structure.py)"
        with open(path, "w") as handle:
            json.dump(s, handle, ensure_ascii=False, indent=1)
        compared += 1
    lines.append("runs recomputed with the extended reader: %d; kept (no after.fodt.gz): %d"
                 % (compared, kept))
    lines.append("field mismatches (after, afterSignatureSha256, afterHuman, before, afterSameAsBefore): %d"
                 % len(mismatches))
    lines += ["  " + m for m in mismatches[:50]]
    agg = os.path.join(round1, "tool", "aggregate.py")
    proc = subprocess.run([sys.executable, "-I", agg, dst_out], capture_output=True, text=True)
    lines.append("round-1 aggregate.py on the copy: exit %d %s" % (proc.returncode, proc.stderr.strip()[:300]))
    same_files = True
    for name in ("RESULTS.md", "results.json"):
        a = os.path.join(src_out, name)
        b = os.path.join(dst_out, name)
        ha, hb = sha_file(a), sha_file(b)
        same = ha == hb
        same_files &= same
        lines.append("%-12s round 1 %s  recomputed %s  %s" % (name, ha, hb,
                                                             "BYTE-IDENTICAL" if same else "DIFFERENT"))
    ok = proc.returncode == 0 and same_files and not mismatches and compared >= 100
    lines.append("RESULT: %s" % ("PASS" if ok else "FAIL"))
    text = "\n".join(lines) + "\n"
    with open(report, "w") as handle:
        handle.write(text)
    print(text, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
