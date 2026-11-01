#!/usr/bin/env python3
"""K5 on the ordered engine (SPEC-M3-K-0.2.44 append 2, on K 0.2.45; derived from tools/judge_k_0244_merge.py): judge_counted_m2.py, unedited, on the table the engine is keyed to.

The arguments and the exit code are the judge's.  One keying line goes to stderr, so on an engine that keeps the old table
this tool's stdout equals the bare judge's (red case R2).
"""
import argparse
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
INVENTORY = TOOLS.parents[1] / "findings/evidence/k-0.2.45/k-binding-inventory.json"


def main() -> int:
    import judge_counted_m2 as judge
    import k_0244_merge_keying as keying
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--profile", default="e2-editor-v19")
    parser.add_argument("--wasm", type=Path)
    known, _ = parser.parse_known_args()
    wasm = known.wasm or judge.PROFILES / known.profile / "probe.wasm"
    bound = json.loads(INVENTORY.read_bytes())["proposedMergeBinding"]["wasmSha256"]
    key = keying.read_key(wasm, judge.m.BOUNDARY_NOOP_FRAGMENT, bound)
    print("keying " + json.dumps(key, sort_keys=True), file=sys.stderr)
    keying.install(judge.m, judge, key)
    return judge.main()


if __name__ == "__main__":
    raise SystemExit(main())
