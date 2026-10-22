#!/usr/bin/env bash
# Install host 0.2.32 (the viewer's engine ods-viewer-v2 aa576ce7) on the owner's ddev instance:
# RUNBOOK-install-host-0.2.32.md steps 1-4, with the pre-checks of SPEC-M4-viewer-v2 §10.2 in front.
# Host code is 0.2.31's plus the version; only the engine package changes (buildId 1b4d6a1fc905fb8a
# -> 80349a1a24cecb17).  Nothing here compiles.  Every line is appended to install.txt beside this script.
# Run only in a ddev slot the owner names (ddev is shared).
#
#   bash /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.32/install-0.2.32.sh
#
# The way back (package only; the code may stay at 0.2.32): README.md beside this script.
set -u
A="$HOME/Projects/Nextcloud_Apps/litecore"
R=/home/jiajun/LibreOffice/study_LiteCore
OLD="$R/wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a"
NEW="$R/wasm_sdk_probe/build/archive/host-0.2.32-engine-80349a1a24cecb17"
LOG="$R/findings/evidence/host-0.2.32/install.txt"
BUILD_ID=80349a1a24cecb17

say() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
run() { say "\$ $*"; "$@" 2>&1 | tee -a "$LOG"; return "${PIPESTATUS[0]}"; }
stop() { say "STOP: $*"; exit 1; }

say "# install host 0.2.32 begins (runbook steps 1-4)"
# -- pre-checks: nothing is touched unless all of them hold --
[ -z "$(git -C "$A" status --short)" ] || stop "host tree not clean: $(git -C "$A" status --short | tr '\n' ' ')"
[ "$(git -C "$A" rev-parse --short HEAD)" = "421f4b8" ] || stop "host HEAD is $(git -C "$A" rev-parse --short HEAD), not 421f4b8 (0.2.31)"
[ "$(git -C "$A" rev-parse --short host-0.2.32 2>/dev/null)" = "bffc7dc" ] || stop "branch host-0.2.32 is not bffc7dc"
[ "$(git -C "$A" rev-parse --short host-0.2.32^)" = "421f4b8" ] || stop "host-0.2.32's parent is not 421f4b8"
if [ "$(diff -rq "$A/engine" "$OLD" 2>&1)" != "Only in $OLD: ATTRIBUTION.md" ]; then
  stop "live engine/ differs from the 0.2.29 archive beyond ATTRIBUTION.md: $(diff -rq "$A/engine" "$OLD" 2>&1 | head -3 | tr '\n' ' ')"
fi
got=$(python3 -c "import json;print(json.load(open('$NEW/MANIFEST.json'))['buildId'])") || stop "archive $NEW unreadable"
[ "$got" = "$BUILD_ID" ] || stop "archive buildId $got != $BUILD_ID"
say "pre-checks hold: tree clean, HEAD 421f4b8, host-0.2.32 = bffc7dc on 421f4b8, live engine == 0.2.29 archive (+ATTRIBUTION.md only), new archive $BUILD_ID"

# -- step 1: the code (the version only) --
run git -C "$A" merge --ff-only host-0.2.32 || stop "merge failed"
run git -C "$A" log -1 --format='HEAD %h %s'

# -- step 2: the package, from the archive, in place (no second copy in the app dir: the 0.2.29 archive is the way back) --
run rsync -a --delete --exclude ATTRIBUTION.md "$NEW/" "$A/engine/" || stop "rsync failed"
got=$(python3 -c "import json;print(json.load(open('$A/engine/MANIFEST.json'))['buildId'])")
say "live buildId now $got"
[ "$got" = "$BUILD_ID" ] || stop "buildId $got != $BUILD_ID"
say "diff live engine vs 0.2.32 archive: $(diff -rq "$A/engine" "$NEW" 2>&1 | tr '\n' ' ')"
say "host status after step 2: [$(git -C "$A" status --short | tr '\n' ' ')] (engine*/ are ignored)"

# -- step 3: tell Nextcloud --
cd "$A" || stop "cd failed"
run ddev occ upgrade || stop "occ upgrade failed"
run ddev occ app:list | grep -A1 -i "litecore" | tee -a "$LOG"
run ddev occ maintenance:mode

# -- step 4: smoke, no browser --
B=$(ddev describe -j | python3 -c "import json,sys;print(json.load(sys.stdin)['raw']['primary_url'])")
say "base $B"
say "viewer route: $(curl -sk -o /dev/null -w '%{http_code} %{redirect_url}' "$B/index.php/apps/litecore/r/ods-viewer.html?fileId=0")"
say "editor route: $(curl -sk -o /dev/null -w '%{http_code} %{redirect_url}' "$B/index.php/apps/litecore/r/e2-editor.html?fileId=0")"
say "# install ends (expect litecore: 0.2.32; an unauthenticated curl gets 401 or a login redirect, not 500)"
