#!/usr/bin/env bash
# One re-run step of SPEC-M3-link-batch-v22 §11.2.1 (fable ruling 6 item 7), detached like the chain: desk line, START/END
# with exit code in rerun.log, the runner's output in <label>.log.  Usage: step.sh <label> <runner args...>
set -u
REPO=/home/jiajun/LibreOffice/study_LiteCore
OUT="$REPO/findings/evidence/link-batch-v22/shakedown/item2-rerun"
cd "$REPO/wasm_sdk_probe" || exit 1
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX
label="$1"; shift
{
  echo "--- $(date '+%F %T %z') $label"
  echo "load $(cut -d' ' -f1-3 /proc/loadavg); chrome processes $(pgrep -c chrome || true); firefox $(pgrep -c firefox || true)"
  echo "ours: $(pgrep -af 'probe_|check_m3|run_e2_c|run_merge|run_v2|diag_v21' | grep -v pgrep | wc -l)"
} >> "$OUT/desk.log"
echo "$(date '+%F %T') START $label tree $(git -C "$REPO" rev-parse --short HEAD): $*" >> "$OUT/rerun.log"
python3 -B tools/run_v21_shakedown_item2.py "$@" > "$OUT/$label.log" 2>&1
echo "$(date '+%F %T') END $label exit $?" >> "$OUT/rerun.log"
