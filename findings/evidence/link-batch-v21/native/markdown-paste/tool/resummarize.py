#!/usr/bin/env python3
"""Recompute the structure fields of every run's summary.json from its saved
after.fodt.gz with the current md_structure.py (after a reader fix).

Usage: resummarize.py OUT_DIR
Runs without a kept after.fodt.gz (M14b runs 2-3) keep their fields; the
script prints which ones and whether run 1 of that arm changed.
"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import md_structure  # noqa: E402
import run_arms  # noqa: E402


def main(argv):
    changed = []
    for path in sorted(glob.glob(os.path.join(argv[1], "*", "run*", "summary.json"))):
        run_dir = os.path.dirname(path)
        after_gz = os.path.join(run_dir, "after.fodt.gz")
        with open(path) as handle:
            s = json.load(handle)
        if not os.path.exists(after_gz):
            print("kept (no after.fodt.gz):", run_dir)
            continue
        full = md_structure.summarize(after_gz)
        sig = hashlib.sha256(json.dumps(md_structure.signature(full), ensure_ascii=False,
                                        sort_keys=True).encode()).hexdigest()
        if sig != s.get("afterSignatureSha256"):
            changed.append(run_dir)
        s["after"] = run_arms.compact(full)
        s["afterSignatureSha256"] = sig
        s["afterHuman"] = "\n".join(md_structure.human(full).splitlines()[:40])
        before_gz = os.path.join(run_dir, "before.fodt.gz")
        if os.path.exists(before_gz):
            before = md_structure.summarize(before_gz)
            s["before"] = run_arms.compact(before)
            s["afterSameAsBefore"] = md_structure.signature(full) == md_structure.signature(before)
        s["summarizedBy"] = "resummarize.py (md_structure.py with list-item style-override)"
        with open(path, "w") as handle:
            json.dump(s, handle, ensure_ascii=False, indent=1)
    print("signature changed in:", changed)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
