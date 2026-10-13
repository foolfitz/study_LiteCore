#!/usr/bin/env bash
# 10 repeats of the C2 Chrome ratio-2 owner-gap-80 cell on dist 6470dec0 (README.md here).
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/134/c2-cell-repeat
T=wasm_sdk_probe/tools
PAGE=6470dec0cb0e20db
D=$(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-16)
[ "$D" = $PAGE ] || { echo "REFUSED dist $D" >> $E/chain.txt; exit 2; }
for i in $(seq -w 1 10); do
  echo "$(date -u +%FT%TZ) run $i chrome-procs $(pgrep -fc '/chrome/chrome( |$)' || true) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $E/chain.txt
  timeout 600 python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser chrome --document owner \
    --gap 80 --chars 20 --out $E/run-$i.json > $E/run-$i.stdout.txt 2>&1
  echo "$(date -u +%FT%TZ) run $i exit $?" >> $E/chain.txt
done
echo "$(date -u +%FT%TZ) DONE" >> $E/chain.txt
