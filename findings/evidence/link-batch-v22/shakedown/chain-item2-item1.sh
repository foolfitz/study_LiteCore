#!/usr/bin/env bash
# v22 evidence chain (SPEC-M3-link-batch-v22 §11.7 steps 5-6; fable ruling 5 §4 steps 5-6): item 2 (E2) then
# item 1 (I1-rerun), Chrome then Firefox, N=3, on the no-host mirror (no ddev, nothing under dist/ written).
# Started detached (setsid nohup) by the main session after F3 passed.  One browser at a time: every runner
# takes the S-9 lock and waits for it.  Each step's exit status is logged; a failing step does not stop
# the chain (each report is judged on its own afterwards).
set -u
REPO=/home/jiajun/LibreOffice/study_LiteCore
cd "$REPO/wasm_sdk_probe" || exit 1
OUT="$REPO/findings/evidence/link-batch-v22/shakedown"
LOG="$OUT/chain.log"
mkdir -p "$OUT/item2" "$OUT/item1"
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX

desk() {
  {
    echo "--- $(date '+%F %T %z') $1"
    echo "load $(cut -d' ' -f1-3 /proc/loadavg); chrome processes $(pgrep -c chrome || true); firefox $(pgrep -c firefox || true)"
    echo "ours: $(pgrep -af 'probe_|check_m3|run_e2_c|run_merge|run_v2|diag_v21' | grep -v pgrep | wc -l)"
  } >> "$OUT/desk.log"
}

step() {
  local label="$1"; shift
  desk "$label"
  echo "$(date '+%F %T') START $label: $*" >> "$LOG"
  "$@" > "$OUT/$label.log" 2>&1
  echo "$(date '+%F %T') END $label exit $?" >> "$LOG"
}

echo "$(date '+%F %T') CHAIN START tree $(git -C "$REPO" rev-parse --short HEAD)" >> "$LOG"
for browser in chrome firefox; do
  step "item2-$browser" python3 -B tools/run_v21_shakedown_item2.py --browser "$browser" --rounds 3 \
    --out "$OUT/item2" --wait-lock 1800
done
for browser in chrome firefox; do
  step "item1-$browser-d1" python3 -B tools/run_v21_shakedown_item1.py --browser "$browser" --arms d1 \
    --rounds 3 --out "$OUT/item1" --wait-lock 1800
  step "item1-$browser-d9-d10-d14" python3 -B tools/run_v21_shakedown_item1.py --browser "$browser" \
    --arms d9,d10,d14 --rounds 3 --out "$OUT/item1" --wait-lock 1800
  step "item1-$browser-rest" python3 -B tools/run_v21_shakedown_item1.py --browser "$browser" \
    --arms d2p,d8,d8red,d11a,d11b,d11c,d12,d5w,xlc,table,d6 --rounds 3 --out "$OUT/item1" --wait-lock 1800
done
echo "$(date '+%F %T') CHAIN DONE" >> "$LOG"
