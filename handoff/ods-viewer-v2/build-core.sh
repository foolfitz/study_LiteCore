#!/usr/bin/env bash
# The ODS viewer v2 core build (specs/SPEC-M4-viewer-v2.md section 2), run by the owner:
#
#   bash handoff/ods-viewer-v2/build-core.sh              # autogen, K-1, make, K-2
#   bash handoff/ods-viewer-v2/build-core.sh --make-only  # the one finding-003 retry
#
# It stops at the first red and says where to look.  Nothing outside
# wasm-lite/build-ods-viewer-v2 and findings/evidence/m4-ods/viewer-v2/core is written.
# autogen.input and env.sh in this directory are copies of the build dir's, for the record.
set -uo pipefail
ROOT=/home/jiajun/LibreOffice/study_LiteCore
BUILD=$ROOT/wasm-lite/build-ods-viewer-v2
CHECK=$ROOT/wasm_sdk_probe/tools/check_ods_viewer_v2_core.py
EVIDENCE=$ROOT/findings/evidence/m4-ods/viewer-v2/core
JOBS=${JOBS:-12}
mkdir -p "$EVIDENCE"

# shellcheck disable=SC1091
source "$BUILD/env.sh"
case "$(emcc --version 2>/dev/null | head -1)" in
  *4.0.10*) ;;
  *) echo "STOP: emcc is not 4.0.10 (the system emscripten?)"; exit 2 ;;
esac
cd "$BUILD" || exit 2

if [ "${1:-}" != --make-only ]; then
  echo "== autogen (about 40 s)"
  if ! "$LO_SRC/autogen.sh" > configure.log 2>&1; then
    tail -20 configure.log
    echo "STOP: autogen failed; the whole log is $BUILD/configure.log"
    exit 3
  fi
  echo "== K-1 (the falsifier, before make)"
  if ! python3 "$CHECK" --stage configure --report "$EVIDENCE/k1-configure.json" > /dev/null; then
    echo "STOP: K-1 is red; see $EVIDENCE/k1-configure.json"
    exit 4
  fi
  echo "K-1 green"
fi

# One log per run (2026-10-22: a single build.log lost the second run's), build.log -> the latest.
log=build-$(date +%Y%m%dT%H%M%S).log
echo "== make -j$JOBS (40-80 min or more); the log is $BUILD/$log"
start=$(date +%s)
make -j"$JOBS" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
ln -sf "$log" build.log
minutes=$(( ($(date +%s) - start) / 60 ))
echo "$(date -Is) make exit $status after $minutes min (${1:-full}) $log" >> "$EVIDENCE/timing.txt"
if [ "$status" -ne 0 ]; then
  tail -200 "$log" > "$EVIDENCE/${log%.log}-tail200.txt"
  echo "STOP: make failed after $minutes min; its last 200 lines are in $EVIDENCE/${log%.log}-tail200.txt"
  echo "If it died within seconds inside workdir/UnpackedTarball, that is finding 003:"
  echo "  bash handoff/ods-viewer-v2/build-core.sh --make-only   (once)"
  echo "Otherwise just tell Claude; it reads the log itself."
  exit 5
fi

echo "== K-2 (after make, before any link)"
if ! python3 "$CHECK" --stage built --report "$EVIDENCE/k2-built.json" > /dev/null; then
  echo "STOP: K-2 is red; see $EVIDENCE/k2-built.json"
  exit 6
fi
du -sh "$BUILD" >> "$EVIDENCE/timing.txt"
echo "DONE: K-1 and K-2 green after $minutes min of make. Tell Claude."
