#!/usr/bin/env python3
"""Record R7 workspace, toolchain and frozen writer-review artifact integrity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"
EXPECTED_STATUS = [
    " M desktop/CustomTarget_soffice_bin-emscripten-exports.mk",
    " M solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk",
    " M solenv/gbuild/platform/unxgcc.mk",
    " M static/CustomTarget_emscripten_fs_image.mk",
    " M vcl/qt5/QtFrame.cxx",
    "?? LibreOffice_VCL_Qt6_研究報告.md",
]
EXPECTED_MANIFEST = {
    "sdkVersion": "0.6.0-r6-worker",
    "abiVersionText": "1.1",
    "providerContractVersion": "1.0",
    "profile": "writer-review",
    "coreCommit": CORE_COMMIT,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command, cwd=cwd, check=False, capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": command, "available": False, "error": str(error)}
    return {
        "command": command,
        "available": completed.returncode == 0,
        "returnCode": completed.returncode,
        # Git porcelain status uses the leading column as data; never strip it.
        "stdout": completed.stdout.rstrip("\r\n"),
        "stderr": completed.stderr.rstrip("\r\n"),
    }


def artifact_inventory(profile: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    expected_by_path: dict[Path, str] = {}
    for pack in manifest.get("resourcePacks", []):
        expected_by_path[(profile / pack["data"]).resolve()] = pack["sha256"]

    pairs: list[tuple[str, Path]] = [
        (logical, (profile / relative).resolve())
        for logical, relative in manifest["artifactFiles"].items()
    ]
    pairs.extend(
        (f"{pack['id']}:{key}", (profile / pack[key]).resolve())
        for pack in manifest.get("resourcePacks", [])
        for key in ("data", "metadata")
    )
    for logical, path in pairs:
        exists = path.is_file()
        actual = sha256(path) if exists else None
        name_parts = path.name.split(".")
        name_hash = name_parts[-2] if len(name_parts) >= 3 else None
        expected = expected_by_path.get(path)
        passed = exists
        if actual and name_hash and len(name_hash) == 16:
            passed = passed and actual.startswith(name_hash)
        if actual and expected:
            passed = passed and actual == expected
        inventory.append(
            {
                "logicalName": logical,
                "path": str(path),
                "bytes": path.stat().st_size if exists else None,
                "sha256": actual,
                "pass": passed,
            }
        )
    return inventory


def tool_inventory() -> dict[str, Any]:
    commands = {
        "chrome": [shutil.which("google-chrome") or "google-chrome", "--version"],
        "firefox": [shutil.which("firefox") or "firefox", "--version"],
        "geckodriver": [shutil.which("geckodriver") or "/snap/bin/geckodriver", "--version"],
        "node": [shutil.which("node") or "node", "--version"],
        "python": [shutil.which("python3") or "python3", "--version"],
        "soffice": [shutil.which("soffice") or "soffice", "--version"],
        "fcitx5": [shutil.which("fcitx5") or "fcitx5", "--version"],
        "fcitx5Remote": [shutil.which("fcitx5-remote") or "fcitx5-remote", "-n"],
        "orca": [shutil.which("orca") or "orca", "--version"],
        "pdfinfo": [shutil.which("pdfinfo") or "pdfinfo", "-v"],
    }
    result = {name: run(command) for name, command in commands.items()}
    result["pythonModules"] = {
        module: run([commands["python"][0], "-c", f"import {module}; print({module}.__version__)" ])
        for module in ("psutil", "websockets")
    }
    result["session"] = {
        key: os.environ.get(key)
        for key in ("XDG_SESSION_TYPE", "DISPLAY", "WAYLAND_DISPLAY", "GTK_IM_MODULE", "QT_IM_MODULE")
    }
    fcitx_profile = Path.home() / ".config" / "fcitx5" / "profile"
    result["fcitxProfile"] = {
        "path": str(fcitx_profile),
        "exists": fcitx_profile.is_file(),
        "text": fcitx_profile.read_text(encoding="utf-8", errors="replace")
        if fcitx_profile.is_file()
        else None,
    }
    return result


def fixture_inventory(project: Path) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for path in sorted((project / "test-docs").glob("t[123]-*.odt")):
        fixtures.append(
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
        )
    return fixtures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()

    project = Path(__file__).resolve().parent.parent
    root = project.parent
    evidence = args.evidence_dir or root / "findings" / "evidence" / "sdk-r7" / "baseline"
    core = root / "libreoffice-26-8"
    profile = project / "dist" / "profiles" / "writer-review-r6"
    manifest_path = profile / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = artifact_inventory(profile, manifest)

    head = run(["git", "rev-parse", "HEAD"], cwd=core)["stdout"]
    status_result = run(
        ["git", "-c", "core.quotepath=false", "status", "--short", "--untracked-files=all"],
        cwd=core,
    )
    status = status_result.get("stdout", "").splitlines()
    manifest_summary = {key: manifest.get(key) for key in EXPECTED_MANIFEST}
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "release": "R7",
        "phase": args.phase,
        "core": {
            "head": head,
            "expectedHead": CORE_COMMIT,
            "status": status,
            "expectedStatus": EXPECTED_STATUS,
            "pass": head == CORE_COMMIT and status == EXPECTED_STATUS,
        },
        "manifest": manifest_summary,
        "manifestPass": manifest_summary == EXPECTED_MANIFEST,
        "artifacts": artifacts,
        "fixtures": fixture_inventory(project),
        "environment": tool_inventory(),
    }
    before_path = evidence / "preflight-before.json"
    if args.phase == "after" and before_path.is_file():
        before = json.loads(before_path.read_text(encoding="utf-8"))
        result["matchesBefore"] = {
            "core": result["core"] == before["core"],
            "artifacts": [
                (item["path"], item["bytes"], item["sha256"])
                for item in artifacts
            ]
            == [
                (item["path"], item["bytes"], item["sha256"])
                for item in before["artifacts"]
            ],
        }
    result["pass"] = (
        result["core"]["pass"]
        and result["manifestPass"]
        and all(item["pass"] for item in artifacts)
        and all(result.get("matchesBefore", {}).values())
    )

    evidence.mkdir(parents=True, exist_ok=True)
    output = evidence / f"preflight-{args.phase}.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (evidence / f"core-status-{args.phase}.txt").write_text(
        head + "\n" + "\n".join(status) + "\n", encoding="utf-8"
    )
    (evidence / f"artifacts-{args.phase}.sha256").write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in artifacts),
        encoding="utf-8",
    )
    if args.phase == "before":
        (evidence / "environment.json").write_text(
            json.dumps(result["environment"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"output": str(output), "pass": result["pass"]}, ensure_ascii=False))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
