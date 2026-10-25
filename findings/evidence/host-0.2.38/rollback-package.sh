#!/usr/bin/env bash
# Functional engine rollback; retain the monotonic host version 0.2.38.
set -euo pipefail
A=/home/jiajun/Projects/Nextcloud_Apps/litecore
OUT=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.38
OLD=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/archive/host-0.2.37-engine-754ae8eafd15edda
[ -z "$(git -C "$A" status --short)" ]
python3 - "$A/engine/MANIFEST.json" "$OLD/MANIFEST.json" "$OUT/release.json" <<'PY'
import json,sys
live,old,release=(json.load(open(p)) for p in sys.argv[1:])
assert live['buildId']==release['buildId']
assert old['buildId']=='754ae8eafd15edda'
PY
rsync -a --delete --exclude ATTRIBUTION.md "$OLD/" "$A/engine/"
delta=$(diff -rq "$A/engine" "$OLD" || true)
[ "$delta" = "Only in $OLD: ATTRIBUTION.md" ]
echo '0.2.37 engine restored; host label remains 0.2.38.'
