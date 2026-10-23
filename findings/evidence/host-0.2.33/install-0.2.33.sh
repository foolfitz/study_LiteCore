#!/usr/bin/env bash
# Install the archived 0.2.33 candidate only in an owner-named ddev slot.
# WINDOW_END='YYYY-MM-DD HH:MM' bash .../install-0.2.33.sh [--preflight-only]
# No compilation; checks finish before changing the live app or engine.
set -uo pipefail
if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != --preflight-only ]; }; then
    echo "Usage: WINDOW_END='...' bash install-0.2.33.sh [--preflight-only]"
    exit 2
fi
: "${WINDOW_END:?set WINDOW_END to the end of the owner-named slot}"
END_EPOCH=$(date -d "$WINDOW_END" +%s) || exit 2
R=/home/jiajun/LibreOffice/study_LiteCore
A=/home/jiajun/Projects/Nextcloud_Apps/litecore
OUT="$R/findings/evidence/host-0.2.33"
LOG="${INSTALL_LOG:-$OUT/install.txt}"
OLD="$R/wasm_sdk_probe/build/archive/host-0.2.32-engine-80349a1a24cecb17"
NEW="$R/wasm_sdk_probe/build/archive/host-0.2.33-engine-a67beefefebe57d6"
BUILD_ID=a67beefefebe57d6
readarray -t HEADS < <(python3 - "$OUT/release.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print(r["hostParent"])
print(r["hostCommit"])
PY
)
say() { printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$LOG"; }
stop() { say "STOP: $*"; exit 1; }
run() {
    say "\$ $*"
    "$@" 2>&1 | tee -a "$LOG"
    local statuses=("${PIPESTATUS[@]}")
    if [ "${statuses[0]}" -ne 0 ]; then return "${statuses[0]}"; fi
    return "${statuses[1]}"
}

say "# 0.2.33 pre-checks; window-end $WINDOW_END"
[ "$(date +%s)" -lt "$END_EPOCH" ] || stop "owner-named window is closed"
[ -z "$(git -C "$A" status --short)" ] || stop "live host tree is not clean"
[ "$(git -C "$A" branch --show-current)" = main ] || stop "live host is not on main"
[ "$(git -C "$A" rev-parse HEAD)" = "${HEADS[0]}" ] || stop "live host is not the recorded 0.2.32 parent"
[ "$(git -C "$A" rev-parse host-0.2.33)" = "${HEADS[1]}" ] || stop "candidate branch moved"
[ "$(git -C "$A" rev-parse host-0.2.33^)" = "${HEADS[0]}" ] || stop "candidate parent differs"
delta=$(diff -rq "$A/engine" "$OLD" 2>&1)
[ "$delta" = "Only in $OLD: ATTRIBUTION.md" ] || stop "live engine differs from 0.2.32 archive: $delta"
got=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["buildId"])' "$NEW/MANIFEST.json") || stop "new archive unreadable"
[ "$got" = "$BUILD_ID" ] || stop "new archive has buildId $got"
if ! (cd "$NEW" && sha256sum -c "$OUT/archive.sha256") >> "$LOG" 2>&1; then
    stop "new archive checksum mismatch (see $LOG)"
fi
slot=$(timeout 60 ddev list -j 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin); rows=d.get("raw",d)
state=next((p.get("status") for p in rows if p.get("name")=="litecore"),"absent")
busy=[p["name"] for p in rows if p.get("status")=="running" and p.get("name")!="litecore"]
print("OK" if state=="running" and not busy else json.dumps({"litecore":state,"otherRunning":busy}))
') || stop "ddev list could not be read"
[ "$slot" = OK ] || stop "ddev slot unavailable: $slot"
say "pre-checks hold: recorded host/branch/archives; only litecore running"
if [ "${1:-}" = --preflight-only ]; then
    say "PREFLIGHT ONLY: no live mutation performed"
    exit 0
fi
[ "$(date +%s)" -lt "$END_EPOCH" ] || stop "window closed during pre-checks"

run git -C "$A" merge --ff-only host-0.2.33 || stop "merge failed"
run rsync -a --delete --exclude ATTRIBUTION.md "$NEW/" "$A/engine/" || stop "engine copy failed"
delta=$(diff -rq "$A/engine" "$NEW" 2>&1)
[ "$delta" = "Only in $NEW: ATTRIBUTION.md" ] || stop "installed engine copy differs: $delta"
say "live buildId now $BUILD_ID"
cd "$A" || stop "cannot enter live app"
run ddev occ upgrade || stop "occ upgrade failed"
run ddev occ maintenance:mode || stop "maintenance status failed"
base=$(ddev describe -j | python3 -c 'import json,sys; print(json.load(sys.stdin)["raw"]["primary_url"])') || stop "cannot read base URL"
for page in ods-viewer.html e2-editor.html; do
    code=$(curl -sk -o /dev/null -w '%{http_code}' "$base/index.php/apps/litecore/r/$page?fileId=0") || stop "curl failed: $page"
    say "$page unauthenticated status $code"
    case "$code" in 401|302|303) ;; *) stop "unexpected route response $code" ;; esac
done
say "DONE: host 0.2.33 / $BUILD_ID installed; next Phase H in the same slot"
