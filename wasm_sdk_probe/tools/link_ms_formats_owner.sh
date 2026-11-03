#!/usr/bin/env bash
# Owner-run product links (specs/SPEC-P-ms-formats.md 5.1): e2-editor-v33 (DOCX) then ods-editor-v5 (XLSX), development
# profiles under build/ (freezing into dist/ is a later step, after the criteria hold).  Agents may syntax-check this
# file, never execute it unless the owner asks.  About 3 minutes per link.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

writer_log=build/link-ms-formats-writer-01.log
calc_log=build/link-ms-formats-calc-01.log
for path in "$writer_log" "$calc_log" build/e2/editor-v33/probe.js build/ods/editor-v5/probe.js \
            dist/profiles/e2-editor-v33 dist/profiles/ods-editor-v5; do
  if [[ -e "$path" ]]; then
    echo "Existing attempt found ($path). Preserve its files and report it; do not retry or clean." >&2
    exit 1
  fi
done

# Keep these builds independent of another session's make overrides.
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX MAKEFLAGS MFLAGS GNUMAKEFLAGS
started=$(date +%s)
make -j1 ALLOW_FROZEN_RELINK=1 build/e2/editor-v33/profile/sdk-manifest.json 2>&1 | tee "$writer_log"
writer_done=$(date +%s)
make -j1 build/ods/editor-v5/profile/sdk-manifest.json 2>&1 | tee "$calc_log"
calc_done=$(date +%s)
python3 - "$((writer_done - started))" "$((calc_done - writer_done))" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
expected = {"e2-editor-v33": (2047 | (1 << 20) | (1 << 21), "docx"), "ods-editor-v5": (1046835 | (1 << 22) | (1 << 23), "xlsx")}
report = {}
for profile, seconds in (("build/e2/editor-v33/profile", sys.argv[1]), ("build/ods/editor-v5/profile", sys.argv[2])):
    root = Path(profile)
    manifest = json.loads((root / "sdk-manifest.json").read_text())
    bits, ms = expected[manifest["profile"]]
    report[manifest["profile"]] = {
        "seconds": int(seconds),
        "capabilityBits": manifest["expectedCapabilityBits"],
        "capabilityBitsAsSpecified": manifest["expectedCapabilityBits"] == bits,
        "msCapabilities": [c for c in manifest["capabilities"] if c.endswith(ms)],
        **{name.replace(".", "_") + "Sha256": sha(root / name) for name in ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")},
    }
print(json.dumps(report, indent=2))
ok = all(r["capabilityBitsAsSpecified"] and len(r["msCapabilities"]) == 2 for r in report.values())
print("LINKS_AS_SPECIFIED" if ok else "LINKS_NOT_AS_SPECIFIED")
sys.exit(0 if ok else 1)
PY
