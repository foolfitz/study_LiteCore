#!/usr/bin/env bash
# Install host 0.2.29 (the ODS viewer) on the owner's ddev instance: RUNBOOK-install-host-0.2.29.md
# steps 1-4, line by line, with the pre-checks of SPEC-M4 addendum 9 condition Q1-3 in front.
# Nothing here compiles.  Every line is appended to install.txt beside this script.
#
#   bash /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.29/install-0.2.29.sh
#
# Written 2026-10-20 23:5x after the same commands, issued from the Claude session, were refused by
# its auto-mode classifier ("Production Deploy").  The way back is in README.md (three commands).
set -u
A="$HOME/Projects/Nextcloud_Apps/litecore"
R=/home/jiajun/LibreOffice/study_LiteCore
OLD="$R/wasm_sdk_probe/build/archive/host-0.2.27-engine-817413d5ad5bd502"
NEW="$R/wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a"
LOG="$R/findings/evidence/host-0.2.29/install.txt"
BUILD_ID=1b4d6a1fc905fb8a

say() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
run() { say "\$ $*"; "$@" 2>&1 | tee -a "$LOG"; return "${PIPESTATUS[0]}"; }
stop() { say "STOP: $*"; exit 1; }

say "# install host 0.2.29 begins (runbook steps 1-4)"
# -- pre-checks (Q1-3): nothing is touched unless all three hold --
[ -z "$(git -C "$A" status --short)" ] || stop "host tree not clean: $(git -C "$A" status --short | tr '\n' ' ')"
[ "$(git -C "$A" rev-parse --short HEAD)" = "0870695" ] || stop "host HEAD is $(git -C "$A" rev-parse --short HEAD), not 0870695"
if [ "$(diff -rq "$A/engine" "$OLD" 2>&1)" != "Only in $OLD: ATTRIBUTION.md" ]; then
  stop "live engine/ differs from the 0.2.27 archive beyond ATTRIBUTION.md: $(diff -rq "$A/engine" "$OLD" 2>&1 | head -3 | tr '\n' ' ')"
fi
[ -f "$NEW/MANIFEST.json" ] || stop "archive $NEW missing"
say "pre-checks hold: tree clean, HEAD 0870695, live engine == 0.2.27 archive (+ATTRIBUTION.md only)"

# -- step 1: the code (from here the editor route 500s until step 2 is done) --
run git -C "$A" merge --ff-only host-0.2.29 || stop "merge failed"
run git -C "$A" log -1 --format='HEAD %h %s'

# -- step 2: the schema-3 package, from the archive (the branch-safe copy) --
[ ! -e "$A/engine.old" ] || stop "engine.old already exists; move it away first"
run mv "$A/engine" "$A/engine.old" || stop "mv failed"     # engine.old is git-ignored (the runbook said engine.0.2.28, which is not)
run rsync -a --exclude ATTRIBUTION.md "$NEW/" "$A/engine/" || stop "rsync failed"
got=$(python3 -c "import json;print(json.load(open('$A/engine/MANIFEST.json'))['buildId'])")
say "live buildId now $got"
[ "$got" = "$BUILD_ID" ] || stop "buildId $got != $BUILD_ID"
say "diff live engine vs 0.2.29 archive: $(diff -rq "$A/engine" "$NEW" 2>&1 | tr '\n' ' ')"
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
say "# install ends (expect 302 to .../r/${BUILD_ID}-<8 hex>/... or a login redirect; not 500)"
