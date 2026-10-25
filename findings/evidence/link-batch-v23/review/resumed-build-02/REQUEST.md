# Bounded adversarial review: v23 diagnostic build support
Inspect only these two supplied source files; no tools. Report concrete correctness bugs, or state no findings. The base worker plus tail has passed its actual Node VM guards/delegation/submit-status tests. Existing handleRequest is a function declaration, accept registers pending and calls the submit lambda, callStatus calls ccall numeric status. SDK Engine._request defaults to30s timeout. This is diagnostic-only preparation, not a claim of engine wiring or successful native restoration. Keep response under300 words.

## wasm_sdk_probe/tools/build_e2_v23_diagnostic_profile.py
```
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

```

## wasm_sdk_probe/sdk/v23-diagnostic-worker-tail.js
```

// Concatenated only into e2-editor-v23-diag's worker. No public SDK method,
// action id or capability is added. The harness uses Engine._request so the
// existing SDK timeout/cancellation path, including its 30 s default, applies.
const v23ProductHandleRequest = handleRequest;
handleRequest = function handleV23DiagnosticRequest(request) {
  if (request.operation !== "v23Diagnostic")
    return v23ProductHandleRequest(request);
  if (!moduleInstance || activeManifest?.profile !== "e2-editor-v23-diag"
      || activeManifest?.editorContract?.abiVersion !== 5) {
    postResponse(request.requestId, false, {
      code: "UNSUPPORTED_OPERATION",
      message: "private v23 diagnostic requires the initialized diagnostic profile",
    });
    return;
  }
  const kind = request.payload?.kind;
  if (![1, 2, 3].includes(kind) || !Number.isInteger(request.requestId)
      || request.requestId <= 0 || request.requestId > 2147483647) {
    postResponse(request.requestId, false, {
      code: "INVALID_ARGUMENT", message: "invalid private v23 diagnostic request",
    });
    return;
  }
  // 1: queued never-return; 2: queued missing-proof; 3: direct JS-thread LOK.
  // The engine checks that kind 3 has an open document. It may never return.
  accept(request, () => callStatus("oxsdk_v23_diagnostic",
    ["number", "number"], [kind, request.requestId]));
};

```
