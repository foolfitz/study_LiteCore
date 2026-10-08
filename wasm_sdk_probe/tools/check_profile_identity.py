#!/usr/bin/env python3
"""X1 (SPEC-M3-paragraph-merge 31.4 as corrected in 32.1): a newly linked profile is its reference profile
with only the link's own outputs changed.

Written 2026-10-08, before the v19 link.  Form two: every leaf of both manifests is compared by the tool, so
a field added to the builder later is compared without anyone listing it.

  check_profile_identity.py --candidate dist/profiles/e2-editor-v19 --reference dist/profiles/e2-editor-v18 \
      --candidate-exports build/e2/editor-v19/exports.txt \
      --reference-exports build/archive/e2-editor-v15-ad3f68bb-worker-00882139/exports.txt

Clauses:
  manifest   every manifest leaf equal, except LINK_OUTPUTS and the two that name the profile;
  profile    `profile` is the candidate directory's name, `sdkVersion` the reference's with that name swapped;
  wasm       `editorContract.wasmSha256` is the candidate's probe.wasm, and differs from the reference's (an
             equal wasm is not a new link: the fix is not in it);
  loader     `editorContract.loaderSha256` is the candidate's probe.js (equal to the reference's or not:
             printed, a one-time record, 32.1);
  worker     sdk-worker.js byte-identical to the reference's, and the manifest's workerSha256 is its hash;
  files      the same file names in both directories;
  exports    the two export lists byte-identical.
Exit 0 every clause holds; 1 one fails; 3 a file is missing (not done).  Last line `VERDICT ...`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# The link writes probe.wasm and probe.js; nothing else in a profile may move with it (32.1).
LINK_OUTPUTS = (".editorContract.wasmSha256", ".editorContract.loaderSha256")
NAMING = (".profile", ".sdkVersion")
FILES = ("probe.js", "probe.wasm", "sdk-manifest.json", "sdk-worker.js")


def leaves(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, f"{path}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from leaves(item, f"{path}[{i}]")
    else:
        yield path, value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(candidate: Path, reference: Path, candidate_exports: Path, reference_exports: Path) -> tuple[int, list]:
    missing = [str(p) for p in [*(d / f for d in (candidate, reference) for f in FILES),
                                candidate_exports, reference_exports] if not p.is_file()]
    if missing:
        return 3, [f"VERDICT NOT DONE: missing {missing}"]
    mine = dict(leaves(json.loads((candidate / "sdk-manifest.json").read_text())))
    theirs = dict(leaves(json.loads((reference / "sdk-manifest.json").read_text())))
    moved = sorted(k for k in set(mine) | set(theirs) if mine.get(k, KeyError) != theirs.get(k, KeyError))
    other = [k for k in moved if k not in LINK_OUTPUTS + NAMING]
    name, their_name = candidate.name, theirs.get(".profile")
    wasm, loader = sha256(candidate / "probe.wasm"), sha256(candidate / "probe.js")
    worker = sha256(candidate / "sdk-worker.js")
    names = sorted(p.name for p in candidate.iterdir()), sorted(p.name for p in reference.iterdir())
    clauses = {
        "manifest": not other,
        "profile": (mine.get(".profile") == name and isinstance(theirs.get(".sdkVersion"), str)
                    and isinstance(their_name, str) and their_name != name
                    and mine.get(".sdkVersion") == theirs[".sdkVersion"].replace(their_name, name)),
        "wasm": (mine.get(".editorContract.wasmSha256") == wasm
                 and wasm != theirs.get(".editorContract.wasmSha256")
                 and wasm != sha256(reference / "probe.wasm")),
        "loader": mine.get(".editorContract.loaderSha256") == loader,
        "worker": (worker == sha256(reference / "sdk-worker.js")
                   and mine.get(".editorContract.workerSha256") == worker),
        "files": names[0] == names[1],
        "exports": candidate_exports.read_bytes() == reference_exports.read_bytes(),
    }
    lines = [f"leaves: {len(mine)} candidate, {len(theirs)} reference; moved: {moved}",
             f"other than the link's outputs and the name: {other if other else 'none'}",
             f"wasm {wasm[:16]} (reference {str(theirs.get('.editorContract.wasmSha256'))[:16]})",
             f"loader {loader[:16]} (reference {str(theirs.get('.editorContract.loaderSha256'))[:16]}): "
             + ("equal" if loader == theirs.get(".editorContract.loaderSha256") else "differs (recorded, 32.1)"),
             f"worker {worker[:16]}; files {names[0]}; exports {sha256(candidate_exports)[:16]}",
             *(f"{k}: {'ok' if v else 'FAIL'}" for k, v in clauses.items())]
    failing = [k for k, v in clauses.items() if not v]
    return (1, lines + [f"VERDICT FAIL: {failing}"]) if failing else (0, lines + ["VERDICT PASS"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--candidate-exports", type=Path, required=True)
    ap.add_argument("--reference-exports", type=Path, required=True)
    a = ap.parse_args()
    code, lines = check(a.candidate, a.reference, a.candidate_exports, a.reference_exports)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
