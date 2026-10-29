#!/usr/bin/env python3
"""Assemble profile e2-editor-v26 from the archived v25 profile (SPEC-M3-select-all-v26 4.1, 4.2).

A manifest successor, not a link: probe.wasm and probe.js are copied byte for byte from the v25 archive, the
worker is sdk/v26-select-all-worker.js (the v25 worker with featureExtendPermitted renamed), and the manifest
is the v25 manifest with exactly four values changed:

  profile                                 e2-editor-v25 -> e2-editor-v26
  sdkVersion                              ...+e2-editor-v25 -> ...+e2-editor-v26
  editorContract.workerSha256             the v26 worker's sha256
  editorContract.actions["select-all"]    granted collapsed, range-single, range-cross (SELECT_ALL below)

Reads only the archive (checked against its SHA256SUMS first) and the worker source; never build/e2/editor-v25,
never an object file, so it cannot trigger a link.  The judge of the result is tools/check_v26_profile.py (P1),
not this script.

  build_e2_v26_select_all_profile.py --archive DIR --worker FILE --output DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

V25_PROFILE, V26_PROFILE = "e2-editor-v25", "e2-editor-v26"
SELECT_ALL = {"id": 21, "gestures": ["collapsed", "range-single", "range-cross"],
              "limits": ["characterised-2026-10-30-select-all-v25", "copy-of-a-range-holding-a-frame-is-complex",
                         "caret-in-frame-or-note-not-characterised"]}
COPIED = ("probe.wasm", "probe.js")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def manifest_bytes(manifest: dict) -> bytes:
    # Reproduces the v25 manifest byte for byte when nothing is changed (checked 2026-10-30).
    return (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def successor_manifest(v25: dict, worker_sha256: str) -> dict:
    if v25.get("profile") != V25_PROFILE:
        raise SystemExit(f"source manifest is {v25.get('profile')!r}, not {V25_PROFILE}")
    if v25["editorContract"]["actions"]["select-all"].get("gestures") != []:
        raise SystemExit("source manifest does not withhold select-all")
    out = json.loads(json.dumps(v25))
    out["profile"] = V26_PROFILE
    if not out["sdkVersion"].endswith("+" + V25_PROFILE):
        raise SystemExit(f"unexpected sdkVersion {out['sdkVersion']!r}")
    out["sdkVersion"] = out["sdkVersion"][: -len(V25_PROFILE)] + V26_PROFILE
    out["editorContract"]["workerSha256"] = worker_sha256
    out["editorContract"]["actions"]["select-all"] = dict(SELECT_ALL)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sums = dict(line.split()[::-1] for line in (args.archive / "SHA256SUMS").read_text().splitlines() if line.strip())
    for name in (*COPIED, "sdk-worker.js", "sdk-manifest.json"):
        if sha256((args.archive / name).read_bytes()) != sums.get(name):
            raise SystemExit(f"archive member {name} differs from SHA256SUMS")
    worker = args.worker.read_bytes()
    manifest = successor_manifest(json.loads((args.archive / "sdk-manifest.json").read_bytes()), sha256(worker))
    args.output.mkdir(parents=True, exist_ok=True)
    for name in COPIED:
        shutil.copyfile(args.archive / name, args.output / name)
    (args.output / "sdk-worker.js").write_bytes(worker)
    (args.output / "sdk-manifest.json").write_bytes(manifest_bytes(manifest))
    print(json.dumps({name: sha256((args.output / name).read_bytes())
                      for name in (*COPIED, "sdk-worker.js", "sdk-manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
