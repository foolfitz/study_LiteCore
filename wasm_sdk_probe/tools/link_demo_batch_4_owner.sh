#!/usr/bin/env bash
# Owner-run product build (SPEC-P-demo-batch-4): e2-editor-v32, H1 to H4, the toggles and the paragraph read.
# No core build: links on the existing core.  Agents may syntax-check this file, never execute it without the owner's word.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

writer=dist/profiles/e2-editor-v32
if [[ -e build/link-v32-paragraph-01.log || -e build/e2/editor-v32 || -e "$writer" ]]; then
  echo 'Existing attempt found. Preserve its files and report it; do not retry or clean.' >&2
  exit 1
fi

# Keep this build independent of another session's make overrides.
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX MAKEFLAGS MFLAGS GNUMAKEFLAGS
make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v32/sdk-manifest.json 2>&1 | tee build/link-v32-paragraph-01.log
python3 -I tools/check_v32_paragraph_contract.py --build-log build/link-v32-paragraph-01.log
python3 -I tools/check_v32_paragraph_contract.py --manifest "$writer/sdk-manifest.json" --exports build/e2/editor-v32/exports.txt
python3 - <<'PY'
import hashlib, json
from pathlib import Path
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
directory = Path('dist/profiles/e2-editor-v32')
print(json.dumps({'profile': 'e2-editor-v32', **{f: sha(directory / f) for f in ('probe.js', 'probe.wasm', 'sdk-worker.js', 'sdk-manifest.json')}}, indent=2))
PY
