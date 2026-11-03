#!/usr/bin/env python3
"""The Microsoft-formats workers (specs/SPEC-P-ms-formats.md 5.1 E4, E5): a frozen worker plus a closed list of replacements, each
occurring exactly once, written to --out.

  writer  dist/profiles/e2-editor-v32/sdk-worker.js + tests/v33-worker-delta.json   -> the e2-editor-v33 worker
  calc    dist/profiles/ods-editor-v4/sdk-worker.js + tests/ods-v5-worker-delta.json -> the ods-editor-v5 worker

Derived at build time instead of living in sdk/, as derive_ods_v4_worker.py: the Writer shell bundle scans sdk/*.js, and a new file
there turns generation 88's bundle check red.  tests/ms_formats_worker_test.cjs exercises the same derivation.
  derive_ms_formats_worker.py --profile writer|calc --out FILE
"""
import argparse
import hashlib
import json
from pathlib import Path

SDK = Path(__file__).resolve().parents[1]
BASES = {
    "writer": (SDK / "dist/profiles/e2-editor-v32/sdk-worker.js",
               "c394302c589baff3b40ff67a7579e07cf53fc7447dd3f04b26ff9c827280ff36", SDK / "tests/v33-worker-delta.json"),
    "calc": (SDK / "dist/profiles/ods-editor-v4/sdk-worker.js",
             "4a06fbe45c458b4c9aa60ab7bcd624894dace729a2b83f009f3e9008ccc8919c", SDK / "tests/ods-v5-worker-delta.json"),
}


def derive(profile):
    base, sha, delta = BASES[profile]
    data = base.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise SystemExit(f"the frozen {profile} base worker moved: {base}")
    text = data.decode("utf-8")
    for hunk in json.loads(delta.read_text())["hunks"]:
        if text.count(hunk["old"]) != 1:
            raise SystemExit(f"hunk {hunk['item']!r} occurs {text.count(hunk['old'])} times")
        text = text.replace(hunk["old"], hunk["new"])
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", choices=sorted(BASES), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    text = derive(args.profile)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(json.dumps({"profile": args.profile, "out": str(args.out), "sha256": hashlib.sha256(text.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
