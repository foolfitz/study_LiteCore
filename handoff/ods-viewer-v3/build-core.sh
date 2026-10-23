#!/usr/bin/env bash
# Owner-run incremental core build, SPEC-M4-viewer-v3 sections 2-3.
# From the repo root: bash handoff/ods-viewer-v3/build-core.sh --make-only
# No autogen, no viewer link, no ddev. Stop on failure; do not add patch chains.
set -uo pipefail

if [ "$#" -ne 1 ] || [ "$1" != --make-only ]; then
    echo "Usage: bash handoff/ods-viewer-v3/build-core.sh --make-only"
    exit 2
fi

ROOT=/home/jiajun/LibreOffice/study_LiteCore
BUILD=$ROOT/wasm-lite/build-ods-viewer-v2
CHECKS=$ROOT/wasm_sdk_probe/tools
EVIDENCE=$ROOT/findings/evidence/m4-ods/viewer-v3/core
JOBS=${JOBS:-12}
if ! [[ "$JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "STOP: JOBS must be a positive integer"
    exit 2
fi

# shellcheck disable=SC1091
source "$BUILD/env.sh" || exit 2
case "$(emcc --version 2>/dev/null | head -1)" in
    *' 4.0.10 '*) ;;
    *) echo "STOP: emcc is not 4.0.10"; exit 2 ;;
esac

mkdir -p "$EVIDENCE/runs" || exit 2
RUN=$(mktemp -d "$EVIDENCE/runs/$(date +%Y%m%dT%H%M%S)-XXXXXX") || exit 2
RUN_ID=${RUN##*/}
echo "== Evidence: $RUN"
echo "== K-1 (unchanged v2 configure checks; no autogen)"
if ! python3 "$CHECKS/check_ods_viewer_v2_core.py" --stage configure \
        --report "$RUN/k1-configure.json" > /dev/null; then
    echo "STOP: K-1 is red; see $RUN/k1-configure.json"
    exit 4
fi

cd "$BUILD" || exit 2
log=build-v3-$RUN_ID.log
printf '%s\n' "$BUILD/$log" > "$RUN/build-log.txt"
echo "== make -j$JOBS (estimated 15-40 min); log: $BUILD/$log"
start=$(date +%s)
make -j"$JOBS" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
make_status=${statuses[0]}
tee_status=${statuses[1]}
seconds=$(( $(date +%s) - start ))
printf '%s make exit %s, tee exit %s, %s seconds, --make-only, %s\n' \
    "$(date -Is)" "$make_status" "$tee_status" "$seconds" "$log" \
    | tee "$RUN/timing.txt" >> "$EVIDENCE/timing.txt"
ln -sf "$log" build-v3.log
if [ "$make_status" -ne 0 ] || [ "$tee_status" -ne 0 ]; then
    tail -200 "$log" > "$RUN/build-tail200.txt"
    echo "STOP: build/logging failed; full log: $BUILD/$log"
    echo "Last 200 lines: $RUN/build-tail200.txt"
    echo "If the failure is inside dba/dbahsql, F3-1 applies: stop and tell Codex."
    echo "Do not retry or add patches before the log is read."
    exit 5
fi

echo "== K3 (after make, before any viewer link)"
if ! python3 "$CHECKS/check_ods_viewer_v3_core.py" --stage built \
        --report "$RUN/k3-built.json" > /dev/null; then
    echo "STOP: K3 is red; see $RUN/k3-built.json"
    exit 6
fi

echo "== F3-2 (viewer gzip projection; actual viewer size is checked at link)"
python3 - "$RUN/k3-built.json" <<'PY'
import json
import sys
report = json.load(open(sys.argv[1]))
size = report["sizeRecord"]
print(f'Core wasm gzip: {size["gzipBytes"]:,} B')
print(f'Projected viewer gzip: {size["projectedViewerGzipBytes"]:,} B')
print(f'Cap: {size["viewerGzipCapBytes"]:,} B')
if not size["projectedWithinCap"]:
    print("STOP: F3-2 triggered; do not prepare a viewer link.")
    sys.exit(7)
PY
size_status=$?
if [ "$size_status" -ne 0 ]; then
    exit "$size_status"
fi

du -sh "$BUILD" >> "$RUN/timing.txt"
echo "DONE: K-1 and K3 green; projection within cap; make took $seconds seconds."
echo "Tell Codex this run path: $RUN"
echo "Next: read K3, then prepare the separate ods-viewer-v3 link."
