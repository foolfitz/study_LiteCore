#!/usr/bin/env bash
# Replace only the unaccepted first-attempt package in the same idle feature slot.
set -euo pipefail
R=/home/jiajun/LibreOffice/study_LiteCore
A=/home/jiajun/Projects/Nextcloud_Apps/litecore
OUT="$R/findings/evidence/host-0.2.34"
OLD="$R/wasm_sdk_probe/build/archive/host-0.2.34-engine-df7f6fe14e395638"
NEW="$R/wasm_sdk_probe/build/archive/host-0.2.34-engine-d308e0cc58958d85"
test "$(date +%s)" -lt "$(date -d '2026-10-25 12:30' +%s)"
test -z "$(git -C "$A" status --short)"
test "$(git -C "$A" rev-parse --short=7 HEAD)" = db5139c
delta=$(diff -rq "$A/engine" "$OLD" || true)
test "$delta" = "Only in $OLD: ATTRIBUTION.md"
(cd "$NEW" && sha256sum -c "$OUT/archive.sha256")
ddev list -j | python3 -c '
import json,sys
p=json.load(sys.stdin)["raw"]
assert [r["name"] for r in p if r["status"]=="running"] == ["litecore"]
'
rsync -a --delete --exclude ATTRIBUTION.md "$NEW/" "$A/engine/"
delta=$(diff -rq "$A/engine" "$NEW" || true)
test "$delta" = "Only in $NEW: ATTRIBUTION.md"
echo 'Corrected unaccepted package d308e0cc58958d85 installed; host/profile identities unchanged.'
