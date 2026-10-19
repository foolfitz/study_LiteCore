#!/usr/bin/env bash
# The host arms on 0.2.27 (SPEC-M3-link-batch-v22 §11.7 step 9, §13.1 step 9; fable ruling 7 items 6-7): H-154c/H-154o,
# D2-v22, M11-autosave, each Chrome then Firefox, N=3.  Before every step: the window is still open (before 07:00),
# `ddev list` shows no running project but litecore, and the desk gate reads clean within 10 minutes; otherwise the
# chain logs WINDOW CLOSED / DDEV BUSY / DESK DIRTY and stops (a step in progress is never cut).  Started detached;
# the session stays idle while it runs.
set -u
REPO=/home/jiajun/LibreOffice/study_LiteCore
OUT="$REPO/findings/evidence/host-0.2.27"
LOG="$OUT/chain.log"
GATE="$REPO/findings/evidence/link-batch-v22/shakedown/desk_gate.py"
BUILD_ID=817413d5ad5bd502
cd "$REPO/wasm_sdk_probe" || exit 1
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX

guard() {
  local label="$1"
  if [ "$(date +%H%M)" -ge 0700 ] && [ "$(date +%H%M)" -lt 1200 ]; then
    echo "$(date '+%F %T') WINDOW CLOSED before $label (07:00, spec §13.1); chain stopped" >> "$LOG"; exit 3
  fi
  local busy
  busy=$(timeout 60 ddev list -j 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin); raw = d.get('raw', d)
print(' '.join(p['name'] for p in raw if p.get('status') == 'running' and p.get('name') != 'litecore'))" 2>&1)
  if [ -n "$busy" ]; then
    echo "$(date '+%F %T') DDEV BUSY before $label: $busy; chain stopped" >> "$LOG"; exit 4
  fi
  echo "--- $(date '+%F %T %z') gate before $label" >> "$OUT/desk.log"
  if ! python3 -B "$GATE" --wait 600 >> "$OUT/desk.log" 2>&1; then
    echo "$(date '+%F %T') DESK DIRTY before $label (desk.log has the reasons); chain stopped" >> "$LOG"; exit 2
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
M11="$REPO/findings/evidence/link-batch-v22/host/m11_autosave.py"
echo "$(date '+%F %T') CHAIN START host-arms tree $(git -C "$REPO" rev-parse --short HEAD) buildId $BUILD_ID" >> "$LOG"
for b in chrome firefox; do
  step "h154-$b" python3 -B "$H154" --h154 --browser "$b" --rounds 3 --expect-version 0.2.27 \
    --expect-build-id "$BUILD_ID" --out "$OUT/h154" --wait-lock 1800
done
for b in chrome firefox; do
  step "d2-$b" python3 -B tools/run_v21_d2.py --mode host --page v22 --browser "$b" --rounds 3 \
    --out "$OUT/d2" --wait-lock 1800
done
for b in chrome firefox; do
  step "m11-$b" python3 -B "$M11" --browser "$b" --rounds 3 --expect-version 0.2.27 \
    --expect-build-id "$BUILD_ID" --out "$OUT/m11" --wait-lock 1800
done
echo "$(date '+%F %T') CHAIN DONE host-arms" >> "$LOG"
