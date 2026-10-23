#!/usr/bin/env bash
# Functional rollback after reading a Phase H red in the owner-named slot.
# Leaves the host's version at 0.2.33; restores the known 0.2.32 engine only.
set -euo pipefail
R=/home/jiajun/LibreOffice/study_LiteCore
A=/home/jiajun/Projects/Nextcloud_Apps/litecore
OLD="$R/wasm_sdk_probe/build/archive/host-0.2.32-engine-80349a1a24cecb17"
python3 - "$OLD/MANIFEST.json" <<'PY'
import json, sys
assert json.load(open(sys.argv[1]))["buildId"] == "80349a1a24cecb17"
PY
rsync -a --delete --exclude ATTRIBUTION.md "$OLD/" "$A/engine/"
delta=$(diff -rq "$A/engine" "$OLD" || true)
test "$delta" = "Only in $OLD: ATTRIBUTION.md"
echo "Restored 0.2.32 engine 80349a1a24cecb17; host version unchanged; no occ needed."
