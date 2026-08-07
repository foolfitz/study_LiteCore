#!/usr/bin/env python3
"""Assemble the isolated Finding 016 scheduler-drain profile."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from e1_support import sha256, write_json


def build_profile(
    source_manifest: Path,
    loader: Path,
    wasm: Path,
    worker: Path,
    output: Path,
) -> dict[str, object]:
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(loader, output / "probe.js")
    shutil.copy2(wasm, output / "probe.wasm")
    shutil.copy2(worker, output / "sdk-worker.js")
    manifest["profile"] = "finding-016-scheduler"
    manifest["sdkVersion"] = f'{manifest["sdkVersion"]}+finding-016-scheduler'
    manifest["artifactFiles"] = {
        **manifest["artifactFiles"],
        "probe.js": "./probe.js",
        "probe.wasm": "./probe.wasm",
    }
    manifest["capabilities"] = [
        *manifest.get("capabilities", []),
        "editor-discovery-closed-actions",
        "finding-016-scheduler-probe",
    ]
    manifest["diagnostic"] = {
        "scope": "e1-odt-editing-discovery",
        "experiment": "finding-016-scheduler-drain",
        "contract": "single-process-events-to-idle-v1-not-product-abi",
        "loaderSha256": sha256(output / "probe.js"),
        "wasmSha256": sha256(output / "probe.wasm"),
        "workerSha256": sha256(output / "sdk-worker.js"),
        "productionArtifactReplaced": False,
        "rawCallbackExposed": False,
        "arbitraryKeyCodeAccepted": False,
        "arbitraryUnoCommandAccepted": False,
        "automaticRetry": False,
    }
    write_json(output / "sdk-manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_profile(args.source_manifest, args.loader, args.wasm, args.worker, args.output)


if __name__ == "__main__":
    main()
