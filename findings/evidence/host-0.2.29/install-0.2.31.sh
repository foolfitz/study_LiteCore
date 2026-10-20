#!/usr/bin/env bash
# Install host 0.2.31 = 0.2.30 + scopedStyle() admitting a comment before the page's :root/body rule
# (0.2.30 answered 500 on the viewer document -- Phase H run 2, H6; finding 162).  Only the app code moves:
# branch host-0.2.31 merged fast-forward, then `occ upgrade` for the version.  The engine package
# (buildId 1b4d6a1fc905fb8a) is not touched.  Nothing compiles.  Logged to install.txt.
#
#   bash /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.29/install-0.2.31.sh
set -u
A="$HOME/Projects/Nextcloud_Apps/litecore"
R=/home/jiajun/LibreOffice/study_LiteCore
LOG="$R/findings/evidence/host-0.2.29/install.txt"
BUILD_ID=1b4d6a1fc905fb8a

say() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
run() { say "\$ $*"; "$@" 2>&1 | tee -a "$LOG"; return "${PIPESTATUS[0]}"; }
stop() { say "STOP: $*"; exit 1; }

say "# install host 0.2.31 begins (code only; the package stays)"
[ -z "$(git -C "$A" status --short)" ] || stop "host tree not clean: $(git -C "$A" status --short | tr '\n' ' ')"
[ "$(git -C "$A" rev-parse --short HEAD)" = "e6e325a" ] || stop "host HEAD is $(git -C "$A" rev-parse --short HEAD), not e6e325a (0.2.30)"
got=$(python3 -c "import json;print(json.load(open('$A/engine/MANIFEST.json'))['buildId'])")
[ "$got" = "$BUILD_ID" ] || stop "live buildId $got != $BUILD_ID"
git -C "$A" rev-parse --verify -q host-0.2.31 >/dev/null || stop "branch host-0.2.31 missing"
say "pre-checks hold: tree clean, HEAD e6e325a, live buildId $BUILD_ID, branch host-0.2.31 present"

run git -C "$A" merge --ff-only host-0.2.31 || stop "merge failed"
run git -C "$A" log -1 --format='HEAD %h %s'
cd "$A" || stop "cd failed"
run ddev occ upgrade || stop "occ upgrade failed"
run ddev occ app:list | grep -A1 -i "litecore" | tee -a "$LOG"
run ddev occ maintenance:mode
say "# install 0.2.31 ends (expect litecore: 0.2.31; the routes are judged by the H runner, logged in)"
