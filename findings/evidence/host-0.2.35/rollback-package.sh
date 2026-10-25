#!/usr/bin/env bash
# Functional rollback only; retain host version label 0.2.35.
set -euo pipefail
A=/home/jiajun/Projects/Nextcloud_Apps/litecore
OLD=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/archive/host-0.2.34-engine-d308e0cc58958d85
[ -z "$(git -C "$A" status --short)" ]
python3 - "$A/engine/MANIFEST.json" "$OLD/MANIFEST.json" <<'CHECK'
import json,sys
assert json.load(open(sys.argv[1]))['buildId']=='b007f950b2e18cd2'
assert json.load(open(sys.argv[2]))['buildId']=='d308e0cc58958d85'
CHECK
rsync -a --delete --exclude ATTRIBUTION.md "$OLD/" "$A/engine/"
delta=$(diff -rq "$A/engine" "$OLD" || true)
[ "$delta" = "Only in $OLD: ATTRIBUTION.md" ]
echo '0.2.34 package restored; 0.2.35 host label retained, no downgrade.'
