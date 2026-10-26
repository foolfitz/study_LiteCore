#!/usr/bin/env python3
"""Read-only mechanical audit of the owner-produced ABI6 feature link."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
SDK = ROOT / "wasm_sdk_probe"
PROFILE = SDK / "dist/profiles/e2-editor-v23"
BUILD = SDK / "build/e2/editor-v23"
LOG = SDK / "build/link-v23-feature-01.log"
EXPECTED = {
    "probe.wasm": "fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658",
    "probe.js": "4d90d587cd24a2d75056e7e3400acce009f5841ae2e5df033adba3031a74578e",
    "sdk-worker.js": "3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5",
    "sdk-manifest.json": "2b23901ff94edd4c52611d03a31242c9ecfbf33fcf89835c1af13ac04a1e2a91",
    "exports.txt": "78d4750fd2f98747ac2c677d9459873d4cf253ba14cfc86aa3f05e76b178a2a6",
}
SHARED_WORKER = "0bed22bdb979138f1f0c23bd41bc05896e14f69e29fba10d4e42ccbcda5e1de9"
OLD_WORKER = "0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350"


def digest(path: Path) -> tuple[int, str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            h.update(chunk)
    return size, h.hexdigest(), path.stat().st_mtime_ns


def rows(paths):
    result = []
    for path in paths:
        if path.is_file():
            size, sha, mtime = digest(path)
            result.append({"path": path.relative_to(ROOT).as_posix(), "bytes": size,
                           "sha256": sha, "mtimeNs": mtime})
    return sorted(result, key=lambda x: x["path"])


def current_inventory(roots):
    paths = []
    for rel in roots:
        base = ROOT / rel
        paths.extend(path for path in base.rglob("*") if path.is_file())
    return rows(paths)


def run_reader(name: str, argv: list[str], cwd: Path):
    proc = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    stdout_path, stderr_path = f"{name}.stdout.txt", f"{name}.stderr.txt"
    (OUT / stdout_path).write_text(proc.stdout, encoding="utf-8")
    (OUT / stderr_path).write_text(proc.stderr, encoding="utf-8")
    return {"name": name, "argv": argv, "cwd": cwd.relative_to(ROOT).as_posix(),
            "exitCode": proc.returncode, "stdoutPath": stdout_path,
            "stderrPath": stderr_path, "stdout": proc.stdout, "stderr": proc.stderr}


def merge_rows(groups, tool):
    collected = []
    for key in ("allSourceFilesUnderSrc", "explicitFeatureAndBaseInputs", "frozenR2CoreInputs"):
        collected.extend(groups[key]["files"])
    local = groups["localPackagingPython"]
    collected.extend(local["files"])
    # These three metadata rows are explicitly included by the canonical collector.
    collected.extend([groups["frozenR2CoreInputs"]["baselineManifest"],
                      local["makefile"], local["collector"]])
    # The build-input collector itself is the top-level collector row in build-inputs.json.
    return collected + [BUILD_INPUTS["collector"]]


def main():
    if not OUT.is_dir():
        raise SystemExit(f"evidence output directory is missing: {OUT}")
    baseline_path = ROOT / "findings/evidence/link-batch-v23/pre-link/feature-01/frozen-before.json"
    build_inputs_path = ROOT / "findings/evidence/link-batch-v23/pre-link/feature-01/attempt-02/build-inputs.json"
    tooling_path = ROOT / "findings/evidence/link-batch-v23/pre-link/feature-01/tooling-inputs.json"
    baseline = json.loads(baseline_path.read_text())
    BUILD_INPUTS = json.loads(build_inputs_path.read_text())
    tooling = json.loads(tooling_path.read_text())

    if LOG.is_file():
        copied_log = OUT / "link-v23-feature-01.log"
        shutil.copyfile(LOG, copied_log)
        log_identity = {"path": LOG.relative_to(ROOT).as_posix(),
                        "bytes": LOG.stat().st_size,
                        "sha256": hashlib.sha256(LOG.read_bytes()).hexdigest(),
                        "mtimeNs": LOG.stat().st_mtime_ns,
                        "evidenceCopy": copied_log.name,
                        "copySha256": hashlib.sha256(copied_log.read_bytes()).hexdigest()}
    else:
        log_identity = {"path": LOG.relative_to(ROOT).as_posix(), "missing": True}

    commands = [
        run_reader("feature-build-log-check",
                   [sys.executable, "-I", "tools/check_v23_feature_contract.py",
                    "--build-log", "build/link-v23-feature-01.log"], SDK),
        run_reader("feature-manifest-binary-check",
                   [sys.executable, "-I", "tools/check_v23_feature_contract.py",
                    "--manifest", "dist/profiles/e2-editor-v23/sdk-manifest.json",
                    "--exports", "build/e2/editor-v23/exports.txt"], SDK),
        run_reader("frozen-v22-worker-base-check",
                   [sys.executable, "-I", "tools/check_v23_feature_contract.py",
                    "--check-worker-base"], SDK),
        run_reader("e1-c-bundle-guard",
                   [sys.executable, "-I", "tools/check_e1_c_bundle_intact.py"], SDK),
    ]

    expected_old = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]}
                    for row in baseline["files"]}
    actual_inventory = current_inventory(baseline["inventoryRoots"])
    actual_by_path = {row["path"]: row for row in actual_inventory}
    additions = sorted(set(actual_by_path) - set(expected_old))
    deletions = sorted(set(expected_old) - set(actual_by_path))
    byte_mismatches = []
    for path in sorted(set(expected_old) & set(actual_by_path)):
        actual = actual_by_path[path]
        expected = expected_old[path]
        if (actual["bytes"], actual["sha256"]) != (expected["bytes"], expected["sha256"]):
            byte_mismatches.append({"path": path, "expected": expected,
                                    "actual": {"bytes": actual["bytes"], "sha256": actual["sha256"]}})
    expected_additions = sorted(f"wasm_sdk_probe/dist/profiles/e2-editor-v23/{name}"
                                for name in ("probe.js", "probe.wasm", "sdk-manifest.json", "sdk-worker.js"))

    # Canonical 250-row compiled-input closure: source/explicit/core/tooling rows,
    # frozen core manifest, tooling Makefile+collector metadata, and build collector.
    groups = BUILD_INPUTS["groups"]
    canonical_rows = merge_rows(groups, tooling)
    canonical_by_path = {}
    canonical_conflicts = []
    for row in canonical_rows:
        path = row["path"]
        normalized = {"path": path, "bytes": row["bytes"], "sha256": row["sha256"]}
        previous = canonical_by_path.get(path)
        if previous is not None and previous != normalized:
            canonical_conflicts.append({"path": path, "first": previous, "later": normalized})
        canonical_by_path.setdefault(path, normalized)
    # Match the collector's exact input set, including the tooling collector and its own build collector.
    for row in tooling["files"]:
        normalized = {"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]}
        previous = canonical_by_path.get(row["path"])
        if previous is not None and previous != normalized:
            canonical_conflicts.append({"path": row["path"], "first": previous, "later": normalized})
        canonical_by_path.setdefault(row["path"], normalized)
    for row in (tooling["collector"], BUILD_INPUTS["collector"]):
        normalized = {"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]}
        previous = canonical_by_path.get(row["path"])
        if previous is not None and previous != normalized:
            canonical_conflicts.append({"path": row["path"], "first": previous, "later": normalized})
        canonical_by_path.setdefault(row["path"], normalized)
    canonical_checks = []
    for path, expected in sorted(canonical_by_path.items()):
        actual_path = ROOT / path
        size, sha, _ = digest(actual_path) if actual_path.is_file() else (None, None, None)
        canonical_checks.append({"path": path, "expectedBytes": expected["bytes"],
                                 "actualBytes": size, "expectedSha256": expected["sha256"],
                                 "actualSha256": sha,
                                 "matches": size == expected["bytes"] and sha == expected["sha256"]})

    # Second-pass reread of frozen artifacts and canonical compiled inputs to expose concurrent drift.
    reread_inventory = current_inventory(baseline["inventoryRoots"])
    reread_by_path = {row["path"]: row for row in reread_inventory}
    inventory_reread_changes = []
    if set(actual_by_path) != set(reread_by_path):
        inventory_reread_changes.append({"membershipBefore": sorted(actual_by_path),
                                         "membershipAfter": sorted(reread_by_path)})
    for path in sorted(set(actual_by_path) & set(reread_by_path)):
        if (actual_by_path[path]["bytes"], actual_by_path[path]["sha256"]) != \
                (reread_by_path[path]["bytes"], reread_by_path[path]["sha256"]):
            inventory_reread_changes.append({"path": path, "before": actual_by_path[path],
                                             "after": reread_by_path[path]})
    canonical_reread_changes = []
    for expected in canonical_checks:
        path = ROOT / expected["path"]
        size, sha, _ = digest(path) if path.is_file() else (None, None, None)
        if (size, sha) != (expected["actualBytes"], expected["actualSha256"]):
            canonical_reread_changes.append({"path": expected["path"],
                                             "before": {"bytes": expected["actualBytes"], "sha256": expected["actualSha256"]},
                                             "after": {"bytes": size, "sha256": sha}})

    outputs = []
    for path in sorted(BUILD.glob("*.o")) + [BUILD / name for name in ("probe.js", "probe.wasm", "sdk-worker.js", "exports.txt")]:
        if path.is_file():
            size, sha, mtime = digest(path)
            outputs.append({"path": path.relative_to(ROOT).as_posix(), "bytes": size,
                            "sha256": sha, "mtimeNs": mtime})
    profile_rows = rows(PROFILE.glob("*"))
    identities = {}
    for name, expected in EXPECTED.items():
        path = BUILD / name if name == "exports.txt" else PROFILE / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        identities[name] = {"path": path.relative_to(ROOT).as_posix(),
                            "expectedSha256": expected, "actualSha256": actual,
                            "matches": actual == expected,
                            "bytes": path.stat().st_size if path.is_file() else None}
    shared_path = SDK / "sdk/sdk-worker.js"
    shared_size, shared_sha, shared_mtime = digest(shared_path)
    old_worker_path = SDK / "build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/sdk-worker.js"
    old_worker_size, old_worker_sha, old_worker_mtime = digest(old_worker_path)

    # Independently parse actual manifest identity values after the contract reader has inspected them.
    manifest = json.loads((PROFILE / "sdk-manifest.json").read_text())
    contract = manifest.get("editorContract", {})
    summary = {
        "status": "PASS",
        "baseline": {"path": baseline_path.relative_to(ROOT).as_posix(),
                     "rowCount": len(expected_old), "actualCount": len(actual_inventory),
                     "additions": additions, "expectedOnlyAdditions": expected_additions,
                     "onlyExpectedFeatureFilesAdded": additions == expected_additions,
                     "deletions": deletions, "byteOrShaMismatches": byte_mismatches,
                     "rereadChanges": inventory_reread_changes},
        "canonicalInputs": {"buildInputSnapshot": build_inputs_path.relative_to(ROOT).as_posix(),
                            "toolingSnapshot": tooling_path.relative_to(ROOT).as_posix(),
                            "expectedUniqueCount": groups["reread"]["uniquePathCount"],
                            "actualUniqueCount": len(canonical_by_path),
                            "conflicts": canonical_conflicts,
                            "checkedCount": len(canonical_checks),
                            "mismatches": [x for x in canonical_checks if not x["matches"]],
                            "rereadChanges": canonical_reread_changes,
                            "coreInputCount": groups["frozenR2CoreInputs"]["expectedCount"],
                            "linkdeps": groups["frozenR2CoreInputs"]["linkdeps"]},
        "commands": [{k:v for k,v in c.items() if k not in ("stdout", "stderr")} for c in commands],
        "commandResults": commands,
        "buildLog": log_identity,
        "buildOutputs": outputs,
        "profileFiles": profile_rows,
        "identities": identities,
        "manifestIdentity": {"profile": manifest.get("profile"),
                             "editorAbi": contract.get("abiVersion"),
                             "actions": len(contract.get("actions", {})),
                             "withheld": manifest.get("withheld"),
                             "boundHashes": {k: contract.get(k) for k in ("loaderSha256", "wasmSha256", "workerSha256")}},
        "workerBase": {"path": old_worker_path.relative_to(ROOT).as_posix(),
                       "bytes": old_worker_size, "sha256": old_worker_sha, "mtimeNs": old_worker_mtime,
                       "expectedSha256": OLD_WORKER, "matches": old_worker_sha == OLD_WORKER},
        "sharedCalcWorker": {"path": shared_path.relative_to(ROOT).as_posix(),
                             "bytes": shared_size, "sha256": shared_sha, "mtimeNs": shared_mtime,
                             "expectedSha256": SHARED_WORKER, "matches": shared_sha == SHARED_WORKER},
        "e1cGuard": next((c for c in commands if c["name"] == "e1-c-bundle-guard"), None),
    }
    problems = []
    if log_identity.get("missing") or log_identity.get("copySha256") != log_identity.get("sha256"):
        problems.append("missing or unequal copied build log")
    if len(outputs) != 8:
        problems.append(f"expected eight actual build outputs, found {len(outputs)}")
    if len(profile_rows) != 4:
        problems.append(f"expected four profile files before archive, found {len(profile_rows)}")
    if additions != expected_additions:
        problems.append("frozen profile/archive membership differs from exactly the four expected feature files")
    if deletions or byte_mismatches or inventory_reread_changes:
        problems.append("frozen pre-link artifact inventory changed")
    if len(canonical_by_path) != groups["reread"]["uniquePathCount"] or canonical_conflicts:
        problems.append("canonical input closure membership/conflict differs from snapshot")
    if len(canonical_checks) != 250 or any(not x["matches"] for x in canonical_checks) or canonical_reread_changes:
        problems.append("canonical compiled input bytes changed")
    if groups["frozenR2CoreInputs"]["expectedCount"] != 189:
        problems.append("r2 core input population differs from 189")
    if any(c["exitCode"] != 0 for c in commands):
        problems.append("one or more actual post-link readers failed")
    if any(not x["matches"] for x in identities.values()):
        problems.append("one or more five identity pins differ")
    if manifest.get("profile") != "e2-editor-v23" or contract.get("abiVersion") != 6 or len(contract.get("actions", {})) != 23 or manifest.get("withheld") != ["select-all"]:
        problems.append("actual manifest identity differs from required ABI6 profile")
    if not summary["workerBase"]["matches"] or not summary["sharedCalcWorker"]["matches"]:
        problems.append("frozen v22 worker base or shared Calc worker changed")
    if commands[-1]["exitCode"] != 0:
        problems.append("E1-C guard did not pass")
    summary["problems"] = problems
    summary["status"] = "PASS" if not problems else "FAIL"
    (OUT / "audit.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "baseline": summary["baseline"],
                      "canonicalInputs": {k:v for k,v in summary["canonicalInputs"].items() if k not in ("linkdeps",)},
                      "commandExits": {c["name"]: c["exitCode"] for c in commands},
                      "log": log_identity, "buildOutputCount": len(outputs),
                      "profileFiles": profile_rows, "identities": identities,
                      "manifestIdentity": summary["manifestIdentity"],
                      "workerBase": summary["workerBase"],
                      "sharedCalcWorker": summary["sharedCalcWorker"],
                      "problems": problems}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    # Merge rows needs the loaded top-level snapshot while remaining a closed helper.
    BUILD_INPUTS = json.loads((ROOT / "findings/evidence/link-batch-v23/pre-link/feature-01/attempt-02/build-inputs.json").read_text())
    raise SystemExit(main())
