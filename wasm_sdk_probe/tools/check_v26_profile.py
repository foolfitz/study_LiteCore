#!/usr/bin/env python3
"""P1 (SPEC-M3-select-all-v26 5.1): profile e2-editor-v26 is the v25 archive plus a closed list of changes.

  1. probe.wasm, probe.js equal the v25 archive byte for byte; exports.txt too when the checked directory has one
     (the v26 archive does, dist/profiles does not).
  2. sdk-worker.js differs from the v25 archive's worker by exactly WORKER_HUNK (computed diff vs the expectation
     written here).
  3. sdk-manifest.json differs from the v25 archive's manifest by exactly MANIFEST_PATHS; workerSha256 is the
     checked worker's real sha256; select-all equals SELECT_ALL (limits included).
  4. Every action name of the worker's own EDITOR_V2/V3/V4_ACTION_IDS tables (the population, read from the
     checked worker) is PRESENT in the manifest with a gestures list -- withheld is `gestures: []`, never
     omitted (the engine opens an omitted action wide).

The expectations are written here on purpose and NOT imported from build_e2_v26_select_all_profile.py: a typo in
the builder must turn this red, not travel into it.

  check_v26_profile.py --profile DIR [--archive DIR]          exit 0 iff P1_HOLDS
  check_v26_profile.py --profile DIR --red-cases OUT          each mutation of a copy of DIR must turn P1 red
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
ARCHIVE = PROJECT / "build/archive/e2-editor-v25-44cb15ea-worker-75557b22"
SELECT_ALL = {"id": 21, "gestures": ["collapsed", "range-single", "range-cross"],
              "limits": ["characterised-2026-10-30-select-all-v25", "copy-of-a-range-holding-a-frame-is-complex",
                         "caret-in-frame-or-note-not-characterised"]}
WORKER_HUNK = [
    "+// SPEC-M3-select-all-v26 4.2: the e2-editor-v26 worker is the archived v25 worker with only this name changed.",
    '-  return activeManifest?.profile === "e2-editor-v25"',
    '+  return activeManifest?.profile === "e2-editor-v26"',
]
MANIFEST_PATHS = {("profile",), ("sdkVersion",), ("editorContract", "workerSha256"),
                  ("editorContract", "actions", "select-all")}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def changed_paths(a, b, path=()) -> set[tuple]:
    """Paths at which two JSON values differ; select-all is compared whole (its own clause)."""
    if path == ("editorContract", "actions", "select-all") or type(a) is not type(b) or not isinstance(a, dict):
        return set() if a == b else {path}
    out = set()
    for key in set(a) | set(b):
        if key not in a or key not in b:
            out.add(path + (key,))
        else:
            out |= changed_paths(a[key], b[key], path + (key,))
    return out


def worker_population(source: str, table: str = "EDITOR_V4_ACTION_IDS") -> dict[str, int]:
    """name -> id of the worker's dispatch table, FOLLOWING its `...TABLE` spreads (V4 <- V3 <- V2 <- V1).

    The first version read only the literal pairs of V2/V3/V4 and missed V1's ten names (spread into V2): 13 of
    23, found by P1's own first run before use.  Hence the contiguity clause in check(): ids must be 1..N."""
    block = re.search(rf"const {table} = Object\.freeze\(\{{(.*?)\}}\);", source, re.S)
    if not block:
        raise ValueError(f"{table} not found in the worker")
    out: dict[str, int] = {}
    for spread in re.findall(r"\.\.\.(EDITOR_\w+_ACTION_IDS)", block.group(1)):
        out.update(worker_population(source, spread))
    out.update({name: int(n) for name, n in re.findall(r'"([a-z-]+)":\s*(\d+)', block.group(1))})
    return out


def check(profile: Path, archive: Path = ARCHIVE) -> dict:
    sums = dict(line.split()[::-1] for line in (archive / "SHA256SUMS").read_text().splitlines() if line.strip())
    checks, notes = {}, {}
    try:
        checks["archiveIsV25"] = all(sha256((archive / f).read_bytes()) == sums.get(f)
                                     for f in ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json",
                                               "exports.txt"))
        checks["wasmEqual"] = sha256((profile / "probe.wasm").read_bytes()) == sums["probe.wasm"]
        checks["loaderEqual"] = sha256((profile / "probe.js").read_bytes()) == sums["probe.js"]
        if (profile / "exports.txt").exists():
            checks["exportsEqual"] = sha256((profile / "exports.txt").read_bytes()) == sums["exports.txt"]
        worker_raw = (profile / "sdk-worker.js").read_bytes()
        old = (archive / "sdk-worker.js").read_text(encoding="utf-8").splitlines()
        new = worker_raw.decode("utf-8").splitlines()
        hunk = [line for line in difflib.unified_diff(old, new, n=0, lineterm="")
                if line[:1] in "+-" and not line.startswith(("+++", "---"))]
        notes["workerHunk"] = hunk
        checks["workerHunkIsTheClosedList"] = hunk == WORKER_HUNK
        v25 = json.loads((archive / "sdk-manifest.json").read_bytes())
        v26 = json.loads((profile / "sdk-manifest.json").read_bytes())
        paths = changed_paths(v25, v26)
        notes["manifestChangedPaths"] = sorted(".".join(p) for p in paths)
        checks["manifestChangesAreTheClosedList"] = paths == MANIFEST_PATHS
        checks["profileName"] = v26.get("profile") == "e2-editor-v26"
        checks["sdkVersion"] = v26.get("sdkVersion") == v25["sdkVersion"].replace("+e2-editor-v25", "+e2-editor-v26")
        checks["workerShaBound"] = v26.get("editorContract", {}).get("workerSha256") == sha256(worker_raw)
        checks["selectAllGrant"] = v26.get("editorContract", {}).get("actions", {}).get("select-all") == SELECT_ALL
        population = worker_population(worker_raw.decode("utf-8"))
        actions = v26.get("editorContract", {}).get("actions", {})
        notes["population"] = len(population)
        checks["populationContiguous"] = sorted(population.values()) == list(range(1, len(population) + 1))
        missing = [n for n in population if not isinstance((actions.get(n) or {}).get("gestures"), list)]
        notes["absentOrUngated"] = missing
        checks["everyWorkerActionPresent"] = bool(population) and not missing
    except Exception as error:  # noqa: BLE001 -- an unreadable profile is a red P1, with the reason
        checks["readable"] = False
        notes["error"] = f"{type(error).__name__}: {error}"
    return {"profile": str(profile), "checks": checks, "notes": notes,
            "verdict": "P1_HOLDS" if checks and all(checks.values()) else "P1_FAILS"}


def mutate(profile: Path, scratch: Path, name: str) -> Path:
    target = scratch / name
    target.mkdir()
    for f in profile.iterdir():
        if f.name != "probe.wasm":
            shutil.copyfile(f, target / f.name)
    wasm = target / "probe.wasm"
    manifest_path = target / "sdk-manifest.json"
    m = json.loads(manifest_path.read_bytes())
    if name == "wasm-replaced":
        wasm.write_bytes(b"\0asm-not-the-v25-binary")
    else:
        wasm.symlink_to((profile / "probe.wasm").resolve())
    actions = m["editorContract"]["actions"]
    if name == "select-all-omitted":
        del actions["select-all"]
    elif name == "select-all-collapsed-only":
        actions["select-all"]["gestures"] = ["collapsed"]
    elif name == "select-all-limit-missing":
        actions["select-all"]["limits"] = actions["select-all"]["limits"][:-1]
    elif name == "other-field-changed":
        actions["delete-selection"]["limits"] = []
    elif name == "worker-extra-byte":
        (target / "sdk-worker.js").write_bytes((target / "sdk-worker.js").read_bytes() + b" ")
        m["editorContract"]["workerSha256"] = sha256((target / "sdk-worker.js").read_bytes())
    elif name == "worker-sha-unbound":
        m["editorContract"]["workerSha256"] = "75557b220b0d29dfa222a3dd4c3fbde54403034676dc8b7b1a9b41934c218b0c"
    elif name == "other-action-omitted":
        del actions["move-document-end"]
    elif name == "v1-action-omitted":
        del actions["set-bold"]
    manifest_path.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


# Each mutation must turn P1 red AND fail this clause (red for the right reason).
MUTATIONS = {"select-all-omitted": "everyWorkerActionPresent", "select-all-collapsed-only": "selectAllGrant",
             "select-all-limit-missing": "selectAllGrant", "other-field-changed": "manifestChangesAreTheClosedList",
             "worker-extra-byte": "workerHunkIsTheClosedList", "worker-sha-unbound": "workerShaBound",
             "wasm-replaced": "wasmEqual", "other-action-omitted": "everyWorkerActionPresent",
             "v1-action-omitted": "everyWorkerActionPresent"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--red-cases", type=Path)
    args = parser.parse_args()
    if args.red_cases:
        args.red_cases.mkdir(parents=True, exist_ok=False)
        base = check(args.profile, args.archive)
        out = {"base": base, "mutations": {}}
        with tempfile.TemporaryDirectory() as tmp:
            for name in MUTATIONS:
                result = check(mutate(args.profile, Path(tmp), name), args.archive)
                failed = sorted(k for k, v in result["checks"].items() if not v)
                out["mutations"][name] = {"verdict": result["verdict"], "failed": failed,
                                          "expected": MUTATIONS[name], "rightReason": MUTATIONS[name] in failed}
        out["allRed"] = all(r["verdict"] == "P1_FAILS" and r["rightReason"] for r in out["mutations"].values())
        out["verdict"] = "RED_CASES_HOLD" if base["verdict"] == "P1_HOLDS" and out["allRed"] else "RED_CASES_FAIL"
        (args.red_cases / "red-cases.json").write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps({k: v for k, v in out.items() if k != "base"}, indent=1))
        sys.exit(0 if out["verdict"] == "RED_CASES_HOLD" else 1)
    result = check(args.profile, args.archive)
    print(json.dumps(result, indent=1))
    sys.exit(0 if result["verdict"] == "P1_HOLDS" else 1)


if __name__ == "__main__":
    main()
