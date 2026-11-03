#!/usr/bin/env python3
"""The ods-editor-v4 worker (SPEC-P-calc-undo 4.2): the frozen v3 worker plus the closed list in tests/ods-v4-worker-delta.json, each
replacement occurring exactly once, written to --out.

Derived at build time instead of living in sdk/: the Writer shell bundle scans sdk/*.js, and a new file there turns generation 88's
bundle check red ("in scope but neither included nor excluded") for a change that is Calc's alone.  tests/ods_v4_worker_test.cjs
exercises the same derivation.
  derive_ods_v4_worker.py --out build/ods/editor-v4/sdk-worker.js
"""
import argparse
import hashlib
import json
from pathlib import Path

SDK = Path(__file__).resolve().parents[1]
BASE = SDK / "dist/profiles/ods-editor-v3/sdk-worker.js"
BASE_SHA256 = "6df703229c9dea12efa9584df94f970bb0bb0a5d5787d0a43ce3052d1320f306"
DELTA = SDK / "tests/ods-v4-worker-delta.json"


def derive():
    base = BASE.read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA256:
        raise SystemExit("the frozen ods-editor-v3 worker moved")
    text = base.decode("utf-8")
    for hunk in json.loads(DELTA.read_text())["hunks"]:
        if text.count(hunk["old"]) != 1:
            raise SystemExit(f"hunk {hunk['item']!r} occurs {text.count(hunk['old'])} times")
        text = text.replace(hunk["old"], hunk["new"])
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    text = derive()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(json.dumps({"out": str(args.out), "sha256": hashlib.sha256(text.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
