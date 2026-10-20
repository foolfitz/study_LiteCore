#!/usr/bin/env bash
# The host arm on 0.2.28 (SPEC-M3-link-batch-v22 §14.4 step 7): H-154c/H-154o/H-155 from one H-154 run, Chrome then
# Firefox, N=3, then each report judged with --require-h155 into judge-h155.txt.  Run only after §14.4 steps 1-6, in
# the window the owner names: WINDOW_END='YYYY-MM-DD HH:MM' (local time, required; any `date -d` form) is when it closes.  Before every step:
# the window is still open, `ddev list` shows no running project but litecore, and KWallet is unlocked (the runners' own
# refusal, v21_shakedown_common.pre_run_checks); otherwise the chain logs WINDOW CLOSED / DDEV BUSY / GUARD REFUSED and
# stops (a step in progress is never cut).  The desk gate was withdrawn here (SPEC-M3-link-batch-v22 §14.5, the owner's
# choice A): it guards timing cells and H-155 is a geometry reading.  OUT may be overridden (the guard's red case runs
# into the scratchpad).  The shape of ../host-0.2.27/chain-host-arms.sh.
set -u
: "${WINDOW_END:?set WINDOW_END='YYYY-MM-DD HH:MM', the end of the window the owner named}"
END_EPOCH=$(date -d "$WINDOW_END" +%s) || exit 1
REPO=/home/jiajun/LibreOffice/study_LiteCore
OUT="${OUT:-$REPO/findings/evidence/host-0.2.28}"
LOG="$OUT/chain.log"
BUILD_ID=817413d5ad5bd502
cd "$REPO/wasm_sdk_probe" || exit 1
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX

guard() {
  local label="$1"
  if [ "$(date +%s)" -ge "$END_EPOCH" ]; then
    echo "$(date '+%F %T') WINDOW CLOSED before $label ($WINDOW_END); chain stopped" >> "$LOG"; exit 3
  fi
  local busy
  busy=$(timeout 60 ddev list -j 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin); raw = d.get('raw', d)
print(' '.join(p['name'] for p in raw if p.get('status') == 'running' and p.get('name') != 'litecore'))" 2>&1)
  if [ -n "$busy" ]; then
    echo "$(date '+%F %T') DDEV BUSY before $label: $busy; chain stopped" >> "$LOG"; exit 4
  fi
  echo "--- $(date '+%F %T %z') guard before $label" >> "$OUT/guard.log"
  local refuse
  refuse=$(python3 -B -c "
import json, sys
sys.path.insert(0, 'tools')
import v21_shakedown_common as c
r = c.pre_run_checks()
print(json.dumps(r, ensure_ascii=False), file=sys.stderr)
print('; '.join(r['refuse']))" 2>> "$OUT/guard.log") || {
    echo "$(date '+%F %T') GUARD ERROR before $label (guard.log); chain stopped" >> "$LOG"; exit 2; }
  if [ -n "$refuse" ]; then
    echo "$(date '+%F %T') GUARD REFUSED before $label: $refuse; chain stopped" >> "$LOG"; exit 2
  fi
}

step() {
  local label="$1"; shift
  guard "$label"
  echo "$(date '+%F %T') START $label: $*" >> "$LOG"
  "$@" > "$OUT/$label.log" 2>&1
  echo "$(date '+%F %T') END $label exit $?" >> "$LOG"
}

H154="$REPO/findings/evidence/154/diag_markdown_dialog_on_host.py"
echo "$(date '+%F %T') CHAIN START h155 tree $(git -C "$REPO" rev-parse --short HEAD) buildId $BUILD_ID window-end $WINDOW_END" >> "$LOG"
for b in chrome firefox; do
  step "h155-$b" python3 -B "$H154" --h154 --browser "$b" --rounds 3 --expect-version 0.2.28 \
    --expect-build-id "$BUILD_ID" --out "$OUT/h155" --wait-lock 1800
done
for r in "$OUT"/h155/h154-*.json; do
  echo "## --judge ${r#$REPO/} --require-h155" >> "$OUT/judge-h155.txt"
  python3 -B "$H154" --judge "$r" --expect-version 0.2.28 --expect-build-id "$BUILD_ID" --require-h155 \
    >> "$OUT/judge-h155.txt" 2>&1
  echo "# exit $?" >> "$OUT/judge-h155.txt"
done
echo "$(date '+%F %T') CHAIN DONE h155" >> "$LOG"
