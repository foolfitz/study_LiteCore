#!/usr/bin/env bash
# Owner-run product builds (SPEC-P-demo-batch-3 section 3): e2-editor-v31 (Writer alignment) and ods-editor-v3 (Calc styles).
# No core build: both link on the existing cores.  Agents may syntax-check this file, never execute it.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

writer=dist/profiles/e2-editor-v31
calc=build/ods/editor-v3/profile
if [[ -e build/link-v31-alignment-01.log || -e build/e2/editor-v31 || -e "$writer" || -e build/ods/editor-v3 ]]; then
  echo 'Existing attempt found. Preserve its files and report it; do not retry or clean.' >&2
  exit 1
fi

# Keep these builds independent of another session's make overrides.
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX MAKEFLAGS MFLAGS GNUMAKEFLAGS
make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v31/sdk-manifest.json 2>&1 | tee build/link-v31-alignment-01.log
python3 -I tools/check_v31_alignment_contract.py --build-log build/link-v31-alignment-01.log
python3 -I tools/check_v31_alignment_contract.py --manifest "$writer/sdk-manifest.json" --exports build/e2/editor-v31/exports.txt
make -j1 "$calc/sdk-manifest.json" 2>&1 | tee build/link-ods-editor-v3-01.log
python3 - <<'PY'
import hashlib, json
from pathlib import Path
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, directory in (('e2-editor-v31', Path('dist/profiles/e2-editor-v31')), ('ods-editor-v3 (development)', Path('build/ods/editor-v3/profile'))):
    print(json.dumps({'profile': name, **{f: sha(directory / f) for f in ('probe.js', 'probe.wasm', 'sdk-worker.js', 'sdk-manifest.json')}}, indent=2))
PY
