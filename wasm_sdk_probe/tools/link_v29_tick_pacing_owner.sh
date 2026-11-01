#!/usr/bin/env bash
# Owner-run product build (SPEC-M3-v29-tick-pacing 6). Agents may
# syntax-check this file, never execute it.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

log=build/link-v29-tick-pacing-01.log
profile=dist/profiles/e2-editor-v29
if [[ -e "$log" || -e build/e2/editor-v29 || -e "$profile" ]]; then
  echo 'Existing v29 attempt found. Preserve its files and report it; do not retry or clean.' >&2
  exit 1
fi

# Keep this one build independent of another session's make overrides.
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX MAKEFLAGS MFLAGS GNUMAKEFLAGS
make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v29/sdk-manifest.json 2>&1 | tee "$log"
python3 -I tools/check_v29_tick_pacing_contract.py --build-log "$log"
python3 -I tools/check_v29_tick_pacing_contract.py \
  --manifest "$profile/sdk-manifest.json" --exports build/e2/editor-v29/exports.txt
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

profile = Path('dist/profiles/e2-editor-v29')
manifest = json.loads((profile / 'sdk-manifest.json').read_text())
contract = manifest['editorContract']
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
print(json.dumps({
    'profile': manifest['profile'],
    'abiVersion': contract['abiVersion'],
    'typedInsert': contract.get('typedInsert'),
    'selectAll': contract['actions']['select-all'].get('gestures'),
    'wasmSha256': sha(profile / 'probe.wasm'),
    'loaderSha256': sha(profile / 'probe.js'),
    'workerSha256': sha(profile / 'sdk-worker.js'),
    'manifestSha256': sha(profile / 'sdk-manifest.json'),
    'exportsSha256': sha(Path('build/e2/editor-v29/exports.txt')),
    'actions': len(contract['actions']),
    'withheld': [name for name, action in contract['actions'].items()
                 if action.get('gestures') == []],
}, indent=2))
PY
