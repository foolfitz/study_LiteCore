#!/usr/bin/env python3
"""Combine same-commit native LOK and existing diagnostic WASM evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from validate_finding_012_attribution import classify_native, load_results


DEFAULT_CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"


def decide_same_commit(
    native_decision: str,
    wasm_decisions: dict[str, str],
    native_core_commit: str,
    expected_core_commit: str,
) -> dict[str, Any]:
    common = {
        "fixed": False,
        "r7Pass": False,
        "notValidated": ["specific teardown subsystem inside LibreOfficeKitDocument::destroy"],
    }
    if native_core_commit != expected_core_commit:
        return {
            **common,
            "decision": "INCONCLUSIVE_VERSION_MISMATCH",
            "candidateLayer": None,
            "nextAction": "correct-native-build",
            "pass": False,
        }
    wasm_confirmed = set(wasm_decisions) == {"chrome", "firefox"} and all(
        value == "WASM_DOCUMENT_DESTROY_BLOCKED"
        for value in wasm_decisions.values()
    )
    if not wasm_confirmed:
        return {
            **common,
            "decision": "INCONCLUSIVE_WASM_CONTROL",
            "candidateLayer": None,
            "nextAction": "repair-diagnostic-control",
            "pass": False,
        }
    if native_decision == "NATIVE_LOK_REPRODUCED":
        return {
            **common,
            "decision": "CROSS_RUNTIME_DOCUMENT_DESTROY_REPRODUCED",
            "candidateLayer": "shared-libreofficekit-document-destroy",
            "nextAction": "core-fix",
            "pass": True,
        }
    if native_decision == "NOT_REPRODUCED_SYSTEM_NATIVE":
        return {
            **common,
            "decision": "EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY",
            "candidateLayer": "emscripten-document-teardown",
            "nextAction": "wasm-fix",
            "pass": True,
        }
    return {
        **common,
        "decision": "INCONCLUSIVE_NATIVE_CONTROL",
        "candidateLayer": None,
        "nextAction": "repair-native-control",
        "pass": False,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


def file_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "present": False}
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(path),
        "present": True,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--wasm-evidence-root", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--expected-core-commit", default=DEFAULT_CORE_COMMIT)
    args = parser.parse_args()

    native_summary = load_json(args.evidence_root / "native" / "summary.json")
    native = classify_native(load_results(args.evidence_root / "native"))
    wasm = load_json(args.wasm_evidence_root / "summary.json")
    wasm_decisions = {
        browser: wasm.get("wasm", {}).get(browser, {}).get("decision", "missing")
        for browser in ("chrome", "firefox")
    }
    native_core_commit = str(
        native_summary.get("runtimeSource", {}).get("coreCommit") or ""
    )
    decision = decide_same_commit(
        native["decision"], wasm_decisions, native_core_commit,
        args.expected_core_commit,
    )
    build_dir = args.build_dir.resolve()
    build_evidence = {
        "buildDir": str(build_dir),
        "autogenInput": file_evidence(build_dir / "autogen.input"),
        "configHost": file_evidence(build_dir / "config_host.mk"),
        "runtime": file_evidence(build_dir / "instdir" / "program" / "libmergedlo.so"),
        "configureLog": file_evidence(args.evidence_root / "configure.log"),
        "buildLog": file_evidence(args.evidence_root / "build.log"),
    }
    summary = {
        "schemaVersion": 1,
        "release": "finding-012-native-26-8-attribution",
        "verifiedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "expectedCoreCommit": args.expected_core_commit,
        "nativeCoreCommit": native_core_commit,
        "native": native,
        "nativeRuntime": native_summary,
        "buildEvidence": build_evidence,
        "wasm": wasm_decisions,
        "wasmEvidence": str(args.wasm_evidence_root / "summary.json"),
        **decision,
    }
    write_json(args.evidence_root / "summary.json", summary)
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
