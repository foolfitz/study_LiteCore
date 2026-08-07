#!/usr/bin/env python3
"""Capture R8 core/artifact/tool baselines and pre-register thresholds."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from r8_release import write_json


EXPECTED_CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"
EXPECTED_CORE_STATUS = [
    " M desktop/CustomTarget_soffice_bin-emscripten-exports.mk",
    " M solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk",
    " M solenv/gbuild/platform/unxgcc.mk",
    " M static/CustomTarget_emscripten_fs_image.mk",
    " M vcl/qt5/QtFrame.cxx",
    "?? LibreOffice_VCL_Qt6_研究報告.md",
]
EXPECTED_ARTIFACTS = {
    "writerReviewLoader": (
        "dist/profiles/writer-review/probe.35d96f5fdcb9ed0c.js",
        "35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566",
    ),
    "writerReviewWasm": (
        "dist/profiles/writer-review/probe.ba257beb038b6a2d.wasm",
        "ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6",
    ),
}
THRESHOLDS = {
    "schemaVersion": 1,
    "release": "R8-A-delivery-discovery",
    "frozenBeforeBrowserRuns": True,
    "browserPhaseTimeoutMs": 600000,
    "faultDelayMinimumMs": 200,
    "manifestMaxBytes": 1048576,
    "artifactMaxRawBytes": 150000000,
    "requiredGraphMaxRawBytes": 200000000,
    "cacheProbeMinLargeArtifactBytes": 100000000,
    "storageHeadroomTargetBytes": 200000000,
    "cacheRetainedReleaseCeiling": 3,
    "firefoxWorkerGenerationBudgetPerPage": 3,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return (result.stdout or result.stderr).strip()


def capture(project: Path, core: Path, phase: str) -> dict[str, Any]:
    project = project.resolve()
    core = core.resolve()
    core_commit = command_output(["git", "-C", str(core), "rev-parse", "HEAD"])
    status_result = subprocess.run(
        [
            "git", "-C", str(core), "-c", "core.quotepath=false",
            "status", "--short", "--untracked-files=all",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    core_status = status_result.stdout.rstrip("\n").splitlines()
    artifacts = {}
    for name, (relative, expected_hash) in EXPECTED_ARTIFACTS.items():
        path = project / relative
        actual_hash = sha256_file(path) if path.is_file() else ""
        artifacts[name] = {
            "path": str(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else 0,
            "expectedSha256": expected_hash,
            "sha256": actual_hash,
            "pass": actual_hash == expected_hash,
        }
    checks = {
        "coreCommit": core_commit == EXPECTED_CORE_COMMIT,
        "coreStatus": core_status == EXPECTED_CORE_STATUS,
        "artifacts": all(item["pass"] for item in artifacts.values()),
        "gzip": shutil.which("gzip") is not None,
        "chrome": shutil.which("google-chrome") is not None or shutil.which("chromium") is not None,
        "firefox": shutil.which("firefox") is not None,
        "geckodriver": shutil.which("geckodriver") is not None,
    }
    return {
        "schemaVersion": 1,
        "release": "R8-A-delivery-discovery",
        "phase": phase,
        "core": {
            "path": str(core),
            "commit": core_commit,
            "expectedCommit": EXPECTED_CORE_COMMIT,
            "status": core_status,
            "expectedStatus": EXPECTED_CORE_STATUS,
        },
        "artifacts": artifacts,
        "tools": {
            "python": command_output(["python3", "--version"]),
            "node": command_output(["node", "--version"]),
            "gzip": command_output(["gzip", "--version"]).splitlines()[0] if shutil.which("gzip") else None,
            "brotli": command_output(["brotli", "--version"]) if shutil.which("brotli") else None,
            "chrome": command_output(["google-chrome", "--version"]) if shutil.which("google-chrome") else None,
            "firefox": command_output(["firefox", "--version"]) if shutil.which("firefox") else None,
            "geckodriver": command_output(["geckodriver", "--version"]).splitlines()[0]
            if shutil.which("geckodriver") else None,
        },
        "checks": checks,
        "pass": all(checks.values()),
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--core", type=Path, default=workspace / "libreoffice-26-8")
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8" / "discovery",
    )
    args = parser.parse_args()

    evidence_root = args.evidence_root.resolve()
    report = capture(args.project, args.core, args.phase)
    output = evidence_root / "baseline" / f"preflight-{args.phase}.json"
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if existing.get("pass") is not True:
            attempt = 1
            while (output.parent / f"preflight-{args.phase}-attempt-{attempt}.json").exists():
                attempt += 1
            output.replace(output.parent / f"preflight-{args.phase}-attempt-{attempt}.json")
    write_json(output, report)
    thresholds = evidence_root / "thresholds.json"
    if args.phase == "before":
        if thresholds.exists():
            existing = json.loads(thresholds.read_text(encoding="utf-8"))
            if existing != THRESHOLDS:
                raise SystemExit("R8-A thresholds already exist with different contents")
        else:
            write_json(thresholds, THRESHOLDS)
    print(json.dumps({"output": str(output), **report}, ensure_ascii=False, indent=2))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
