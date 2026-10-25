#!/usr/bin/env python3
"""Package candidate C on ABI 5 without changing the inherited public contract.

This wrapper is diagnostic-only. v5/v4 builders and their frozen users remain
unchanged; the private export is not an editor action or an SDK capability.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_editor_v5_profile as v5
from check_v23_diagnostic_build import read_wasm

PROFILE = "e2-editor-v23-diag"
PRIVATE_EXPORT = "_oxsdk_v23_diagnostic"


def contract_problems(candidate: dict, reference: dict) -> list[str]:
    problems = []
    if candidate.get("profile") != PROFILE:
        problems.append("candidate must be the exact v23 diagnostic profile")
    if reference.get("profile") != "e2-editor-v22":
        problems.append("reference must be the frozen v22 profile")
    if candidate.get("editorContract", {}).get("abiVersion") != 5:
        problems.append("diagnostic editor ABI must remain 5")
    if candidate.get("editorContract") != reference.get("editorContract"):
        problems.append("diagnostic public editor contract differs from v22")
    if candidate.get("capabilities") != reference.get("capabilities"):
        problems.append("diagnostic public capabilities differ from v22")
    return problems


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--exports", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    known, _ = parser.parse_known_args(argv[1:])
    if known.profile != PROFILE:
        raise SystemExit("this builder only packages " + PROFILE)
    problems = read_wasm(known.wasm.read_bytes())
    if PRIVATE_EXPORT not in known.exports.read_text().splitlines():
        problems.append("missing private diagnostic export")
    root = Path(__file__).resolve().parent.parent
    expected_worker = (root / "sdk/sdk-worker.js").read_bytes() + (
        root / "sdk/v23-diagnostic-worker-tail.js").read_bytes()
    if known.worker.read_bytes() != expected_worker:
        problems.append("worker is not the base worker plus diagnostic tail")
    if problems:
        raise SystemExit("; ".join(problems))
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        code = v5.main(argv)
    if code:
        return code
    manifest_path = known.output / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    reference = json.loads((root / "dist/profiles/e2-editor-v22/sdk-manifest.json").read_text())
    problems = contract_problems(manifest, reference)
    if problems:
        # Do not leave an invalid candidate manifest that make could accept.
        manifest_path.unlink()
        raise SystemExit("; ".join(problems))
    summary = json.loads(printed.getvalue())
    summary["diagnosticOnly"] = True
    summary["manifestSha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
