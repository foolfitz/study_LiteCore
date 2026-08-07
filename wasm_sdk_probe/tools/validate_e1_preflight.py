#!/usr/bin/env python3
"""Record E1 core workspace, toolchain and frozen R5 artifact integrity."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from e1_support import sha256, write_json


CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"
EXPECTED_STATUS = [
    " M desktop/CustomTarget_soffice_bin-emscripten-exports.mk",
    " M solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk",
    " M solenv/gbuild/platform/unxgcc.mk",
    " M static/CustomTarget_emscripten_fs_image.mk",
    " M vcl/qt5/QtFrame.cxx",
    "?? LibreOffice_VCL_Qt6_研究報告.md",
]
EXPECTED_ARTIFACTS = {
    "probe.js": "35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566",
    "probe.wasm": "ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6",
}


def run(command: list[str], cwd: Path | None = None, timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command, cwd=cwd, check=False, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": command, "available": False, "error": str(error)}
    return {
        "command": command,
        "available": completed.returncode == 0,
        "returnCode": completed.returncode,
        "stdout": completed.stdout.rstrip("\r\n"),
        "stderr": completed.stderr.rstrip("\r\n"),
    }


def artifact_inventory(profile: Path) -> list[dict[str, Any]]:
    manifest = json.loads((profile / "sdk-manifest.json").read_text(encoding="utf-8"))
    result = []
    for logical, expected in EXPECTED_ARTIFACTS.items():
        relative = manifest["artifactFiles"][logical]
        path = (profile / relative).resolve()
        actual = sha256(path) if path.is_file() else None
        result.append({
            "logicalName": logical,
            "path": str(path),
            "bytes": path.stat().st_size if path.is_file() else None,
            "sha256": actual,
            "expectedSha256": expected,
            "pass": actual == expected,
        })
    return result


def tool_inventory() -> dict[str, Any]:
    commands = {
        "chrome": [shutil.which("google-chrome") or "google-chrome", "--version"],
        "firefox": [shutil.which("firefox") or "firefox", "--version"],
        "geckodriver": [shutil.which("geckodriver") or "/snap/bin/geckodriver", "--version"],
        "node": [shutil.which("node") or "node", "--version"],
        "python": [shutil.which("python3") or "python3", "--version"],
        "soffice": [shutil.which("soffice") or "soffice", "--version"],
    }
    return {name: run(command) for name, command in commands.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parent.parent
    root = project.parent
    core = root / "libreoffice-26-8"
    evidence = (args.evidence_dir or root / "findings" / "evidence" / "sdk-e1" / "baseline").resolve()
    profile = project / "dist" / "profiles" / "writer-review"
    head_result = run(["git", "rev-parse", "HEAD"], cwd=core)
    status_result = run(
        ["git", "-c", "core.quotepath=false", "status", "--short", "--untracked-files=all"],
        cwd=core,
    )
    head = head_result.get("stdout", "")
    status = status_result.get("stdout", "").splitlines()
    artifacts = artifact_inventory(profile)
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "release": "E1-A-editing-discovery",
        "phase": args.phase,
        "core": {
            "head": head,
            "expectedHead": CORE_COMMIT,
            "status": status,
            "expectedStatus": EXPECTED_STATUS,
            "pass": head == CORE_COMMIT and status == EXPECTED_STATUS,
        },
        "artifacts": artifacts,
        "environment": tool_inventory(),
    }
    before_path = evidence / "preflight-before.json"
    if args.phase == "after" and before_path.is_file():
        before = json.loads(before_path.read_text(encoding="utf-8"))
        result["matchesBefore"] = {
            "core": result["core"] == before["core"],
            "artifacts": [
                (item["path"], item["bytes"], item["sha256"]) for item in artifacts
            ] == [
                (item["path"], item["bytes"], item["sha256"]) for item in before["artifacts"]
            ],
        }
    result["pass"] = (
        result["core"]["pass"]
        and all(item["pass"] for item in artifacts)
        and all(value["available"] for value in result["environment"].values())
        and all(result.get("matchesBefore", {}).values())
    )
    output = evidence / f"preflight-{args.phase}.json"
    write_json(output, result)
    (evidence / f"core-status-{args.phase}.txt").write_text(
        head + "\n" + "\n".join(status) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(output), "pass": result["pass"]}))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

