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
import tempfile
import os

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_editor_v5_profile as v5
from check_v23_diagnostic_build import read_wasm

PROFILE = "e2-editor-v23-diag"
PRIVATE_EXPORT = "_oxsdk_v23_diagnostic"
ROOT = Path(__file__).resolve().parent.parent
BASE_WORKER = ROOT / "build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/sdk-worker.js"
BASE_WORKER_SHA256 = "0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350"


def checked_base_worker(path=BASE_WORKER, expected=BASE_WORKER_SHA256):
    path = Path(path)
    if path.resolve() != BASE_WORKER.resolve() or expected != BASE_WORKER_SHA256:
        raise ValueError("diagnostic base must be the exact frozen v22 archive identity")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("frozen v22 worker hash mismatch")
    return data

# build_e2_b_profile.build_profile binds these to each candidate's own bytes.
ARTIFACT_BINDINGS = {"loaderSha256": "probe.js", "wasmSha256": "probe.wasm",
                     "workerSha256": "sdk-worker.js"}


def contract_problems(candidate: dict, reference: dict) -> list[str]:
    problems = []
    if candidate.get("profile") != PROFILE:
        problems.append("candidate must be the exact v23 diagnostic profile")
    if reference.get("profile") != "e2-editor-v22":
        problems.append("reference must be the frozen v22 profile")
    if candidate.get("editorContract", {}).get("abiVersion") != 5:
        problems.append("diagnostic editor ABI must remain 5")
    candidate_contract = {k: v for k, v in candidate.get("editorContract", {}).items()
                          if k not in ARTIFACT_BINDINGS}
    reference_contract = {k: v for k, v in reference.get("editorContract", {}).items()
                          if k not in ARTIFACT_BINDINGS}
    if candidate_contract != reference_contract:
        problems.append("diagnostic public editor contract differs from v22")
    if candidate.get("capabilities") != reference.get("capabilities"):
        problems.append("diagnostic public capabilities differ from v22")
    return problems


def binding_problems(candidate: dict, output: Path) -> list[str]:
    problems = []
    for key, filename in ARTIFACT_BINDINGS.items():
        actual = hashlib.sha256((output / filename).read_bytes()).hexdigest()
        if candidate.get("editorContract", {}).get(key) != actual:
            problems.append(f"{key} does not bind the packaged {filename}")
    return problems


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--check-worker-base" in argv[1:]:
        check = argparse.ArgumentParser(allow_abbrev=False)
        check.add_argument("--check-worker-base", action="store_true")
        check.add_argument("--base-worker", type=Path, required=True)
        check.add_argument("--base-worker-sha256", required=True)
        args = check.parse_args(argv[1:])
        checked_base_worker(args.base_worker, args.base_worker_sha256)
        print("frozen v22 diagnostic worker base verified")
        return 0
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
    expected_worker = checked_base_worker() + (
        root / "sdk/v23-diagnostic-worker-tail.js").read_bytes()
    if known.worker.read_bytes() != expected_worker:
        problems.append("worker is not the base worker plus diagnostic tail")
    if problems:
        raise SystemExit("; ".join(problems))
    printed = io.StringIO()
    manifest_path = known.output / "sdk-manifest.json"
    validated = False
    try:
        # Fail before packing if the inherited contract cannot be read. Keep
        # this read inside the cleanup boundary so a stale target cannot mask
        # the failed attempt on the next make invocation.
        reference = json.loads((root / "dist/profiles/e2-editor-v22/sdk-manifest.json").read_text())
        with contextlib.redirect_stdout(printed):
            code = v5.main(argv)
        if code:
            return code
        manifest = json.loads(manifest_path.read_text())
        problems = contract_problems(manifest, reference) + binding_problems(manifest, known.output)
        if problems:
            raise SystemExit("; ".join(problems))
        summary = json.loads(printed.getvalue())
        summary["diagnosticOnly"] = True
        summary["manifestSha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        print(json.dumps(summary, indent=2))
        validated = True
        return 0
    finally:
        if not validated:
            # Includes nonzero returns, SystemExit, parse/IO failures and
            # interruption after the underlying packer wrote the make target.
            # Keep partial non-manifest files for diagnosis; make must retry.
            try:
                if manifest_path.exists():
                    # Keep the exact rejected bytes without leaving a make target.
                    fd, failed = tempfile.mkstemp(prefix="sdk-manifest.failed-", suffix=".json",
                                                   dir=known.output)
                    os.close(fd)
                    os.replace(manifest_path, failed)
            finally:
                sys.stderr.write(printed.getvalue())



if __name__ == "__main__":
    raise SystemExit(main())
