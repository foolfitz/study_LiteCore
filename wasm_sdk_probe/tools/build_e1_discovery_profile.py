#!/usr/bin/env python3
"""Assemble an isolated E1 editor discovery profile."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from e1_support import sha256, write_json


def build_profile(source_manifest: Path, loader: Path, wasm: Path, worker: Path, output: Path) -> dict[str, object]:
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(loader, output / "probe.js")
    shutil.copy2(wasm, output / "probe.wasm")
    shutil.copy2(worker, output / "sdk-worker.js")
    manifest["profile"] = "e1-editor-discovery"
    manifest["sdkVersion"] = f'{manifest["sdkVersion"]}+e1-editor-discovery'
    manifest["artifactFiles"] = {
        **manifest["artifactFiles"],
        "probe.js": "./probe.js",
        "probe.wasm": "./probe.wasm",
    }
    capabilities = list(manifest.get("capabilities", []))
    capabilities.extend([
        "editor-discovery-closed-actions",
        "verified-selection-delete",
    ])
    manifest["capabilities"] = capabilities
    manifest["diagnostic"] = {
        "scope": "e1-odt-editing-discovery",
        "contract": "closed-actions-v1-candidate-not-product-abi",
        "loaderSha256": sha256(output / "probe.js"),
        "wasmSha256": sha256(output / "probe.wasm"),
        "workerSha256": sha256(output / "sdk-worker.js"),
        "productionArtifactReplaced": False,
        "rawCallbackExposed": False,
        "arbitraryKeyCodeAccepted": False,
        "arbitraryUnoCommandAccepted": False,
        "automaticRetry": False,
        "selectionBarrier": "verified-single-writer-unit-v1",
        "stateWordCountUsedForCompletion": False,
        "boundaryReadbackDeadlineMs": 250,
        "deadlineCanDeclareMutationSuccess": False,
        "boundaryRejectionRequiresFreshWorker": True,
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
