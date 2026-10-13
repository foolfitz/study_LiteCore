#!/usr/bin/env bash
# DIAGNOSTIC A/B (ruling-2 conditions 2-3): 20 runs of the C2 cell interleaved 0.2.15, 0.2.16, ...
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/134/c2-cell-repeat/ab
NEW=6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b
OLD=abe93f4575c7797db97462f1f0e3a71cf5fc4063205cd6d5877093ca1c248fcf
SCRATCH=${AB_SCRATCH:?set AB_SCRATCH to a scratch directory}
mkdir -p "$SCRATCH"
git show 0e62a763:wasm_sdk_probe/web/e2-editor-app.js > "$SCRATCH/page-abe93f45.js"
cp wasm_sdk_probe/web/e2-editor-app.js "$SCRATCH/page-6470dec0.js"
sha() { sha256sum "$1" | cut -d' ' -f1; }
[ "$(sha "$SCRATCH/page-abe93f45.js")" = $OLD ] || { echo "REFUSED old bytes" >> $E/chain.txt; exit 2; }
[ "$(sha "$SCRATCH/page-6470dec0.js")" = $NEW ] || { echo "REFUSED new bytes" >> $E/chain.txt; exit 2; }
guard() {  # dist/ and web/ must still be the 0.2.16 page
  local d w; d=$(sha wasm_sdk_probe/dist/e2-editor-app.js); w=$(sha wasm_sdk_probe/web/e2-editor-app.js)
  if [ "$d" != $NEW ] || [ "$w" != $NEW ]; then echo "$(date -u +%FT%TZ) ABORT $1 dist $d web $w" >> $E/chain.txt; exit 3; fi
}
echo "$(date -u +%FT%TZ) START tree $(git rev-parse --short HEAD) wrapper $(sha $E/ab_wrapper.py | cut -c1-16)" >> $E/chain.txt
for n in $(seq -w 1 20); do
  if [ $((10#$n % 2)) -eq 1 ]; then P=abe93f45; else P=6470dec0; fi
  guard "before run $n"
  echo "$(date -u +%FT%TZ) run $n page $P chrome-procs $(pgrep -fc '/chrome/chrome( |$)' || true) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $E/chain.txt
  timeout 600 python3 $E/ab_wrapper.py --page-bytes "$SCRATCH/page-$P.js" --dpr 2 --window 1400x1000 --browser chrome \
    --document owner --gap 80 --chars 20 --out $E/run-$n-$P.json > $E/run-$n-$P.stdout.txt 2>&1
  echo "$(date -u +%FT%TZ) run $n exit $?" >> $E/chain.txt
  guard "after run $n"
done
echo "$(date -u +%FT%TZ) DONE" >> $E/chain.txt
