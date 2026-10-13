#!/usr/bin/env bash
# 2 repeats of the C2 Chrome ratio-2 owner-gap-80 cell on dist b24d754a (G6 of handoff/tasks/TASK-2026-10-13d-136-guard-chain.md).
# Copy of findings/evidence/134/c2-cell-repeat/repeat.sh with: E, PAGE, and the loop count (10 -> 2).
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/136/guard-r2/c2-extra
T=wasm_sdk_probe/tools
PAGE=b24d754a426706bb
D=$(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-16)
[ "$D" = $PAGE ] || { echo "REFUSED dist $D" >> $E/chain.txt; exit 2; }
for i in $(seq -w 01 02); do
  echo "$(date -u +%FT%TZ) run $i chrome-procs $(pgrep -fc '/chrome/chrome( |$)' || true) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $E/chain.txt
  timeout 600 python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser chrome --document owner \
    --gap 80 --chars 20 --out $E/run-$i.json > $E/run-$i.stdout.txt 2>&1
  echo "$(date -u +%FT%TZ) run $i exit $?" >> $E/chain.txt
done
echo "$(date -u +%FT%TZ) DONE" >> $E/chain.txt
