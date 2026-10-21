#!/usr/bin/env bash
# Fallback F (specs/SPEC-M4-viewer-v2.md 2.5 and 7; the owner chose A on 2026-10-22): finding 159's
# bridge signatures in wasm-lite/build-a11y-gate0, incrementally.  Run by the owner:
#
#   bash handoff/ods-viewer-v2/build-core-fallback-gate0.sh
#
# The source tree already carries the bridge patch, but it does nothing to a built tree until the three
# generated files are deleted (scaddins.rdb is older than them; gbuild does not track the command line).
# configure.ac changed since this tree was configured, so make re-runs autogen first: the configuration
# before and after is kept and compared.  Nothing outside the build dir and the evidence dir is written.
set -uo pipefail
ROOT=/home/jiajun/LibreOffice/study_LiteCore
BUILD=$ROOT/wasm-lite/build-a11y-gate0
CHECK=$ROOT/wasm_sdk_probe/tools/check_ods_viewer_v2_core.py
EVIDENCE=$ROOT/findings/evidence/m4-ods/viewer-v2/fallback-core
JOBS=${JOBS:-12}
mkdir -p "$EVIDENCE/config-before"

# shellcheck disable=SC1091
source "$BUILD/env.sh"
case "$(emcc --version 2>/dev/null | head -1)" in
  *4.0.10*) ;;
  *) echo "STOP: emcc is not 4.0.10 (the system emscripten?)"; exit 2 ;;
esac
cd "$BUILD" || exit 2

cp -p config_host.mk config_host/*.h "$EVIDENCE/config-before/"
sha256sum workdir/CustomTarget/bridges/gcc3_wasm/* > "$EVIDENCE/bridge-before.sha256"
rm -f workdir/CustomTarget/bridges/gcc3_wasm/generated-cxx.cxx \
      workdir/CustomTarget/bridges/gcc3_wasm/generated-asm.s \
      workdir/CustomTarget/bridges/gcc3_wasm/exports

log=build-fallback-$(date +%Y%m%dT%H%M%S).log
echo "== make -j$JOBS in build-a11y-gate0 (autogen first, then incremental); the log is $BUILD/$log"
start=$(date +%s)
make -j"$JOBS" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
minutes=$(( ($(date +%s) - start) / 60 ))
echo "$(date -Is) make exit $status after $minutes min $log" >> "$EVIDENCE/timing.txt"
if [ "$status" -ne 0 ]; then
  tail -200 "$log" > "$EVIDENCE/${log%.log}-tail200.txt"
  echo "STOP: make failed after $minutes min; its last 200 lines are in $EVIDENCE/${log%.log}-tail200.txt"
  echo "If it died within seconds inside workdir/UnpackedTarball, that is finding 003: run this script once more."
  echo "Otherwise just tell Claude."
  exit 5
fi

{ for f in "$EVIDENCE"/config-before/*; do
    name=$(basename "$f")
    if [ "$name" = config_host.mk ]; then now=config_host.mk; else now=config_host/$name; fi
    cmp -s "$f" "$now" && echo "same $name" || echo "DIFFERS $name"
  done; } > "$EVIDENCE/config-after-autogen.txt"
python3 "$CHECK" --stage built --build "$BUILD" --report "$EVIDENCE/k2-gate0.json" > /dev/null
python3 - "$EVIDENCE/k2-gate0.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
c = {x["clause"]: x["ok"] for x in r["clauses"]}
ok = c.get("K-2a") and c.get("K-2b") and c.get("K-2e") and c.get("K-2c") is False
print(("DONE" if ok else "STOP") + f": K-2a {c.get('K-2a')}, K-2b {c.get('K-2b')}, K-2e {c.get('K-2e')}, "
      f"K-2c {c.get('K-2c')} (must be False on this core). Tell Claude.")
PY
grep -c DIFFERS "$EVIDENCE/config-after-autogen.txt" | sed 's/^/configuration files that changed under autogen: /'
