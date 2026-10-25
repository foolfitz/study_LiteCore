#!/usr/bin/env bash
# Guarded local candidate installation, authorized by the autonomous feature task.
# Compiles nothing; exact archives and all acceptance readers precede mutation.
set -euo pipefail
if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != --preflight-only ]; }; then
    echo 'Usage: WINDOW_END="YYYY-MM-DD HH:MM" bash install-0.2.37.sh [--preflight-only]'
    exit 2
fi
: "${WINDOW_END:?set the end of the autonomous idle feature slot}"
END_EPOCH=$(date -d "$WINDOW_END" +%s)
R=/home/jiajun/LibreOffice/study_LiteCore
A=/home/jiajun/Projects/Nextcloud_Apps/litecore
OUT="$R/findings/evidence/host-0.2.37"
LOG="${INSTALL_LOG:-$OUT/install.txt}"
readarray -t INFO < <(python3 - "$OUT/release.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
for k in ['hostParent','hostCommit','buildId','archive','oldArchive']:print(r[k])
PY
)
[ "${#INFO[@]}" -eq 5 ] || { echo 'Incomplete release identity'; exit 1; }
PARENT=${INFO[0]}; CANDIDATE=${INFO[1]}; BUILD_ID=${INFO[2]}; NEW=${INFO[3]}; OLD=${INFO[4]}
say() { printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$LOG"; }
stop() { say "STOP: $*"; exit 1; }
run() { say "\$ $*"; "$@" 2>&1 | tee -a "$LOG"; }
say "# 0.2.37 pre-checks; window-end $WINDOW_END"
[ "$(date +%s)" -lt "$END_EPOCH" ] || stop 'feature slot closed'
[ -z "$(git -C "$A" status --short)" ] || stop 'live host tree is not clean'
[ "$(git -C "$A" branch --show-current)" = main ] || stop 'live host is not on main'
[ "$(git -C "$A" rev-parse HEAD)" = "$PARENT" ] || stop 'live host is not the recorded 0.2.36 parent'
[ "$(git -C "$A" rev-parse host-0.2.37)" = "$CANDIDATE" ] || stop 'candidate branch moved'
git -C "$A" merge-base --is-ancestor "$PARENT" "$CANDIDATE" || stop 'candidate is not descended from parent'
delta=$(diff -rq "$A/engine" "$OLD" || true)
[ "$delta" = "Only in $OLD: ATTRIBUTION.md" ] || stop "live engine differs from predecessor archive: $delta"
got=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["buildId"])' "$NEW/MANIFEST.json")
[ "$got" = "$BUILD_ID" ] || stop 'new archive build ID differs'
(cd "$NEW" && sha256sum -c "$OUT/archive.sha256") >> "$LOG" 2>&1 || stop 'archive checksum mismatch'
slot=$(timeout 45 ddev list -j 2>/dev/null | python3 -c '
import json,sys
rows=json.load(sys.stdin)["raw"]
state=next((p["status"] for p in rows if p["name"]=="litecore"),"absent")
busy=[p["name"] for p in rows if p["status"]=="running" and p["name"]!="litecore"]
print("OK" if state=="running" and not busy else json.dumps({"litecore":state,"otherRunning":busy}))')
[ "$slot" = OK ] || stop "shared slot unavailable: $slot"
python3 "$R/wasm_sdk_probe/tools/read_calc_range_format.py" "$R/findings/evidence/calc-range-autosave/range-browser-03" --red-cases >> "$LOG" 2>&1 || stop 'range acceptance reader failed'
python3 "$R/wasm_sdk_probe/tools/read_calc_autosave.py" "$R/findings/evidence/calc-range-autosave/auto-v2-02" --red-cases >> "$LOG" 2>&1 || stop 'successor autosave acceptance reader failed'
python3 "$OUT/offline-package-check.py" "$R/wasm_sdk_probe/build/host-0.2.37/litecore" >> "$LOG" 2>&1 || stop 'offline package verification failed'
say 'pre-checks hold: exact source, branch, archives, finite acceptance and shared slot'
if [ "${1:-}" = --preflight-only ]; then say 'PREFLIGHT ONLY: no live mutation'; exit 0; fi
[ "$(date +%s)" -lt "$END_EPOCH" ] || stop 'slot closed during pre-checks'
run git -C "$A" merge --ff-only host-0.2.37
run rsync -a --delete --exclude ATTRIBUTION.md "$NEW/" "$A/engine/"
delta=$(diff -rq "$A/engine" "$NEW" || true)
[ "$delta" = "Only in $NEW: ATTRIBUTION.md" ] || stop "installed archive mismatch: $delta"
cd "$A"
run ddev occ upgrade
run ddev occ maintenance:mode
base=$(ddev describe -j | python3 -c 'import json,sys;print(json.load(sys.stdin)["raw"]["primary_url"])')
for page in ods-viewer.html ods-editor.html e2-editor.html; do
    code=$(curl -sk -o /dev/null -w '%{http_code}' "$base/index.php/apps/litecore/r/$page?fileId=0")
    say "$page unauthenticated status $code"
    case "$code" in 401|302|303) ;; *) stop "unexpected route status $code" ;; esac
done
say "DONE: host 0.2.37 / $BUILD_ID installed; actual Files acceptance is next"
