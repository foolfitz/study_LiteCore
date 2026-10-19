#!/usr/bin/env bash
# I1-rerun's re-run (SPEC-M3-link-batch-v22 §11.4.2; fable ruling 6 addendum 1 items 3 and 9): the arms of the four
# replaced reports, now in item1/superseded/.  Chrome d1; Firefox d1; Firefox d9,d10,d14; Firefox's rest as v21 W2's
# three fresh sessions A/B/C.  Every step --rounds 3 into item1/ and waits for the S-9 lock.  Before each step the
# desk gate (desk_gate.py) must read clean within 10 minutes, or the chain logs DESK DIRTY and stops; the session
# re-launches the remaining steps when the desk is clean.  Started detached (setsid nohup); appends to chain.log and
# desk.log as the first chain did.
set -u
REPO=/home/jiajun/LibreOffice/study_LiteCore
cd "$REPO/wasm_sdk_probe" || exit 1
OUT="$REPO/findings/evidence/link-batch-v22/shakedown"
LOG="$OUT/chain.log"
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
  echo "--- $(date '+%F %T %z') gate before $label" >> "$OUT/desk.log"
  if ! python3 -B "$OUT/desk_gate.py" --wait 600 >> "$OUT/desk.log" 2>&1; then
    echo "$(date '+%F %T') DESK DIRTY before $label (desk.log has the reasons); chain stopped" >> "$LOG"
    exit 2
  fi
  desk "$label"
  echo "$(date '+%F %T') START $label: $*" >> "$LOG"
  "$@" > "$OUT/$label.log" 2>&1
  echo "$(date '+%F %T') END $label exit $?" >> "$LOG"
}

R="tools/run_v21_shakedown_item1.py"
I1=(--rounds 3 --out "$OUT/item1" --wait-lock 1800)
echo "$(date '+%F %T') CHAIN START item1-rerun tree $(git -C "$REPO" rev-parse --short HEAD)" >> "$LOG"
step item1-chrome-d1-rerun python3 -B "$R" --browser chrome --arms d1 "${I1[@]}"
step item1-firefox-d1-rerun python3 -B "$R" --browser firefox --arms d1 "${I1[@]}"
step item1-firefox-d9-d10-d14-rerun python3 -B "$R" --browser firefox --arms d9,d10,d14 "${I1[@]}"
step item1-firefox-rest-A python3 -B "$R" --browser firefox --arms d2p,d8,d8red,d11b "${I1[@]}"
step item1-firefox-rest-B python3 -B "$R" --browser firefox --arms d11a,d11c,d12 "${I1[@]}"
step item1-firefox-rest-C python3 -B "$R" --browser firefox --arms d5w,xlc,table,d6 "${I1[@]}"
echo "$(date '+%F %T') CHAIN DONE item1-rerun" >> "$LOG"
