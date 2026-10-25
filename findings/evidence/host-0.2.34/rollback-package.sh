#!/usr/bin/env bash
# Functional rollback: retain 0.2.34 version label, restore 0.2.33 source and engine.
# Use only in the same exclusive feature slot, after inspecting a real H-write failure.
set -euo pipefail
R=/home/jiajun/LibreOffice/study_LiteCore
A=/home/jiajun/Projects/Nextcloud_Apps/litecore
OLD="$R/wasm_sdk_probe/build/archive/host-0.2.33-engine-a67beefefebe57d6"
[ -z "$(git -C "$A" status --short)" ]
[ "$(git -C "$A" rev-parse --short=7 HEAD)" = 2f3ef60 ]
python3 - "$OLD/MANIFEST.json" <<'CHECK'
import json,sys
assert json.load(open(sys.argv[1]))['buildId']=='a67beefefebe57d6'
CHECK
# Explicit source paths changed in this release; info.xml deliberately excluded.
git -C "$A" restore --source=4f7f870 --worktree --staged -- js/litecore-editor.js lib/Controller/EditorController.php src/files.js js/litecore-files.mjs
rsync -a --delete --exclude ATTRIBUTION.md "$OLD/" "$A/engine/"
delta=$(diff -rq "$A/engine" "$OLD" || true)
[ "$delta" = "Only in $OLD: ATTRIBUTION.md" ]
git -C "$A" commit -m "Restore host 0.2.33 behavior while retaining version 0.2.34" -m "Co-Authored-By: Codex <noreply@openai.com>"
echo 'Functional 0.2.33 source/package restored; installed version stays 0.2.34, no downgrade.'
