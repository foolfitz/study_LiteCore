#!/usr/bin/env bash
# Second chain (PREDICTION.md addendum): the fixed fling timer and 125's positive control (--long-pages 80).
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/c-prime/recorded
T=wasm_sdk_probe/tools
LOG=$E/chain-2.txt
ts() { date -u '+%FT%TZ'; }
say() { echo "$(ts) $*" >> $LOG; }
h() { sha256sum "$1" | cut -c1-16; }
D=$(h wasm_sdk_probe/dist/e2-editor-app.js)
[ "$D" = 8909564eb2316afa ] || { say "REFUSED dist $D"; exit 2; }
say "START tree $(git rev-parse --short HEAD) dist $D recorded $(h $T/probe_c_prime_recorded.py)"
for B in chrome firefox; do
  for spec in "2 1400x1000" "1 800x600"; do
    set -- $spec
    out=$E/recorded2-$B-dpr$1-$2
    timeout 900 python3 $T/probe_c_prime_recorded.py --browser $B --dpr $1 --window $2 --long-pages 80 --out $out.json > $out.stdout.txt 2>&1
    say "recorded2 $B dpr$1 $2 exit $? :: $(tail -1 $out.stdout.txt | cut -c1-400)"
  done
done
say "DONE"
