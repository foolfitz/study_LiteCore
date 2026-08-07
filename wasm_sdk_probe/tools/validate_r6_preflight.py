#!/usr/bin/env python3
"""Record R6 workspace and R5 artifact integrity without rebuilding core."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"
EXPECTED_STATUS = [
    " M desktop/CustomTarget_soffice_bin-emscripten-exports.mk",
    " M solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk",
    " M solenv/gbuild/platform/unxgcc.mk",
    " M static/CustomTarget_emscripten_fs_image.mk",
    " M vcl/qt5/QtFrame.cxx",
    "?? LibreOffice_VCL_Qt6_研究報告.md",
]
EXPECTED_FIXED_HASHES = {
    "sdk-manifest.json": "3be540456854029ed65b96dd060d9bbdb2ed374e397a49bcd89c1449187621bc",
    "sdk-worker.js": "0c4103bd71fde8bc35c72ec0a5069a74e475e6047b11a818896aac0218efc20d",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*command: str, cwd: Path) -> str:
    return subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.rstrip("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    project = Path(__file__).resolve().parent.parent
    root = project.parent
    core = root / "libreoffice-26-8"
    profile = project / "dist" / "profiles" / "writer-review"
    manifest_path = profile / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_results = []
    for logical, relative in manifest["artifactFiles"].items():
        path = (profile / relative).resolve()
        actual = sha256(path)
        filename_tokens = path.name.split(".")
        filename_hash = filename_tokens[-2] if len(filename_tokens) >= 3 else None
        expected_fixed = EXPECTED_FIXED_HASHES.get(path.name)
        passed = path.is_file()
        if filename_hash and len(filename_hash) == 16:
            passed = passed and actual.startswith(filename_hash)
        if expected_fixed:
            passed = passed and actual == expected_fixed
        artifact_results.append({
            "logicalName": logical,
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": actual,
            "pass": passed,
        })
    for pack in manifest.get("resourcePacks", []):
        for key in ("data", "metadata"):
            path = (profile / pack[key]).resolve()
            actual = sha256(path)
            passed = actual.startswith(path.name.split(".")[-2])
            if key == "data":
                passed = passed and actual == pack["sha256"]
            artifact_results.append({
                "logicalName": f"{pack['id']}:{key}",
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": actual,
                "pass": passed,
            })

    head = run("git", "rev-parse", "HEAD", cwd=core)
    status = run(
        "git", "-c", "core.quotepath=false", "status", "--short",
        "--untracked-files=all", cwd=core,
    ).splitlines()
    result = {
        "schemaVersion": 1,
        "release": "R6",
        "phase": args.phase,
        "core": {
            "head": head,
            "expectedHead": CORE_COMMIT,
            "status": status,
            "expectedStatus": EXPECTED_STATUS,
            "pass": head == CORE_COMMIT and status == EXPECTED_STATUS,
        },
        "manifest": {
            "sdkVersion": manifest.get("sdkVersion"),
            "abiVersionText": manifest.get("abiVersionText"),
            "providerContractVersion": manifest.get("providerContractVersion"),
            "profile": manifest.get("profile"),
            "coreCommit": manifest.get("coreCommit"),
        },
        "artifacts": artifact_results,
    }
    result["pass"] = result["core"]["pass"] \
        and result["manifest"] == {
            "sdkVersion": "0.5.0-r5",
            "abiVersionText": "1.1",
            "providerContractVersion": "1.0",
            "profile": "writer-review",
            "coreCommit": CORE_COMMIT,
        } \
        and all(item["pass"] for item in artifact_results)
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    output = args.evidence_dir / f"preflight-{args.phase}.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
