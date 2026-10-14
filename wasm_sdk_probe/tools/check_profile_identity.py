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

Declared deltas (2026-10-14, ruling 6 condition 49; a NEW USE for a new identity, not a repair): v20's identity
claim is "v19 plus exactly three declared deltas", not "the reference with only the link's outputs changed".  Three
repeatable flags declare them; with none of them the tool behaves, and prints, exactly as above (re-run on v19's
committed inputs and diffed against findings/evidence/v19/post-link/x1-check-profile-identity.txt).  Each declared
delta must have moved EXACTLY as declared, an undeclared move still fails, and every leaf is still compared:

  --declared-worker SHA         worker clause becomes: sdk-worker.js hashes to SHA, which differs from the
                                reference's worker, and the manifest's
                                `.editorContract.workerSha256` is that hash (the one leaf this licenses);
  --declared-new-leaf PATH=VALUE
                                manifest leaf PATH is absent from the reference and present in the candidate with
                                exactly VALUE (parsed as JSON when it is JSON, else a string; `.a="123"` for the
                                string 123); clause `declared-leaf`; the leaf is exempt from the manifest clause;
  --declared-export SYMBOL      exports clause becomes: the candidate's list is the reference's bytes followed by
                                `SYMBOL\n` for each declared symbol in flag order, and no declared symbol is
                                already in the reference's list.

A declared delta that did not move fails its clause, like an undeclared one.
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
WORKER_LEAF = ".editorContract.workerSha256"
FILES = ("probe.js", "probe.wasm", "sdk-manifest.json", "sdk-worker.js")


def leaves(value, path=""):
    """Every scalar, AND every empty container as itself (review 2026-10-08, codex B6): `gestures: []` is how a
    withheld action is written, and it yielded nothing, so deleting it -- which opens the action -- moved no
    leaf."""
    if isinstance(value, dict) and value:
        for key, item in value.items():
            yield from leaves(item, f"{path}.{key}")
    elif isinstance(value, list) and value:
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


def same_leaf(a, b) -> bool:
    """Equal and of the same JSON type (True is not 1)."""
    return type(a) is type(b) and a == b


def check(candidate: Path, reference: Path, candidate_exports: Path, reference_exports: Path,
          declared_workers: tuple = (), declared_leaves: tuple = (), declared_exports: tuple = ()) -> tuple[int, list]:
    missing = [str(p) for p in [*(d / f for d in (candidate, reference) for f in FILES),
                                candidate_exports, reference_exports] if not p.is_file()]
    if missing:
        return 3, [f"VERDICT NOT DONE: missing {missing}"]
    mine = dict(leaves(json.loads((candidate / "sdk-manifest.json").read_text())))
    theirs = dict(leaves(json.loads((reference / "sdk-manifest.json").read_text())))
    moved = sorted(k for k in set(mine) | set(theirs) if mine.get(k, KeyError) != theirs.get(k, KeyError))
    licensed = (*LINK_OUTPUTS, *NAMING, *([WORKER_LEAF] if declared_workers else []),
                *(path for path, _ in declared_leaves))
    other = [k for k in moved if k not in licensed]
    name, their_name = candidate.name, theirs.get(".profile")
    wasm, loader = sha256(candidate / "probe.wasm"), sha256(candidate / "probe.js")
    worker, their_worker = sha256(candidate / "sdk-worker.js"), sha256(reference / "sdk-worker.js")
    names = sorted(p.name for p in candidate.iterdir()), sorted(p.name for p in reference.iterdir())
    if declared_workers:
        worker_ok = (all(worker == w.lower() for w in declared_workers) and worker != their_worker
                     and mine.get(WORKER_LEAF) == worker)
    else:
        worker_ok = worker == their_worker and mine.get(WORKER_LEAF) == worker
    mine_exports, their_exports = candidate_exports.read_bytes(), reference_exports.read_bytes()
    if declared_exports:
        already = set(their_exports.decode(errors="replace").splitlines())
        exports_ok = (mine_exports == their_exports + b"".join(f"{s}\n".encode() for s in declared_exports)
                      and not any(s in already for s in declared_exports))
    else:
        exports_ok = mine_exports == their_exports
    clauses = {
        "manifest": not other,
        "profile": (mine.get(".profile") == name and isinstance(theirs.get(".sdkVersion"), str)
                    and isinstance(their_name, str) and their_name != name
                    and mine.get(".sdkVersion") == theirs[".sdkVersion"].replace(their_name, name)),
        "wasm": (mine.get(".editorContract.wasmSha256") == wasm
                 and wasm != theirs.get(".editorContract.wasmSha256")
                 and wasm != sha256(reference / "probe.wasm")),
        "loader": mine.get(".editorContract.loaderSha256") == loader,
        "worker": worker_ok,
        "files": names[0] == names[1],
        "exports": exports_ok,
    }
    lines = [f"leaves: {len(mine)} candidate, {len(theirs)} reference; moved: {moved}",
             f"other than the link's outputs and the name: {other if other else 'none'}",
             f"wasm {wasm[:16]} (reference {str(theirs.get('.editorContract.wasmSha256'))[:16]})",
             f"loader {loader[:16]} (reference {str(theirs.get('.editorContract.loaderSha256'))[:16]}): "
             + ("equal" if loader == theirs.get(".editorContract.loaderSha256") else "differs (recorded, 32.1)"),
             f"worker {worker[:16]}; files {names[0]}; exports {sha256(candidate_exports)[:16]}"]
    if declared_workers or declared_leaves or declared_exports:
        lines.append(f"declared: workers {[w[:16] for w in declared_workers]} (candidate {worker[:16]}, "
                     f"reference {their_worker[:16]}); exports {list(declared_exports)}")
        for path, value in declared_leaves:
            lines.append(f"declared leaf {path} = {json.dumps(value)}: reference "
                         + (f"has {json.dumps(theirs[path])}" if path in theirs else "absent")
                         + f", candidate {json.dumps(mine[path]) if path in mine else 'absent'}")
    if declared_leaves:
        clauses["declared-leaf"] = all(path not in theirs and path in mine and same_leaf(mine[path], value)
                                       for path, value in declared_leaves)
    lines += [f"{k}: {'ok' if v else 'FAIL'}" for k, v in clauses.items()]
    failing = [k for k, v in clauses.items() if not v]
    return (1, lines + [f"VERDICT FAIL: {failing}"]) if failing else (0, lines + ["VERDICT PASS"])


def parse_leaf(item: str) -> tuple[str, object]:
    path, sep, value = item.partition("=")
    if not sep or not path.startswith(".") or not value:
        raise SystemExit(f"--declared-new-leaf {item!r}: expected .path.to.leaf=VALUE")
    try:
        return path, json.loads(value)
    except ValueError:
        return path, value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--candidate-exports", type=Path, required=True)
    ap.add_argument("--reference-exports", type=Path, required=True)
    ap.add_argument("--declared-worker", action="append", default=[], metavar="SHA",
                    help="the candidate's worker is NEW and has this sha256 (repeatable)")
    ap.add_argument("--declared-new-leaf", action="append", default=[], metavar="PATH=VALUE",
                    help="a manifest leaf absent from the reference and present with exactly VALUE (repeatable)")
    ap.add_argument("--declared-export", action="append", default=[], metavar="SYMBOL",
                    help="an export appended to the reference's list (repeatable, in order)")
    a = ap.parse_args()
    for w in a.declared_worker:
        if len(w) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in w):
            raise SystemExit(f"--declared-worker {w!r}: expected a 64-hex sha256")
    for sym in a.declared_export:
        if not sym or sym != sym.strip() or any(ch.isspace() for ch in sym):
            raise SystemExit(f"--declared-export {sym!r}: expected one symbol with no whitespace")
    code, lines = check(a.candidate, a.reference, a.candidate_exports, a.reference_exports,
                        tuple(a.declared_worker), tuple(parse_leaf(i) for i in a.declared_new_leaf),
                        tuple(a.declared_export))
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
