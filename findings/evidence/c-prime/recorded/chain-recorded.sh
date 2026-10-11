#!/usr/bin/env bash
# C1's runtime read and §17.4's recorded items on the final C′ page (PREDICTION.md, committed before this runs).
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/c-prime/recorded
T=wasm_sdk_probe/tools
B2=findings/evidence/typing-latency/r2-blit-bytes/blit_bytes_probe.py
LOG=$E/chain.txt
ts() { date -u '+%FT%TZ'; }
say() { echo "$(ts) $*" >> $LOG; }
h() { sha256sum "$1" | cut -c1-16; }
D=$(h wasm_sdk_probe/dist/e2-editor-app.js)
[ "$D" = 8909564eb2316afa ] || { say "REFUSED dist $D"; exit 2; }
say "START tree $(git rev-parse --short HEAD) dist $D recorded $(h $T/probe_c_prime_recorded.py) blit $(h $B2)"
for B in chrome firefox; do
  for spec in "2 1400x1000" "1 800x600"; do
    set -- $spec
    out=$E/recorded-$B-dpr$1-$2
    timeout 600 python3 $T/probe_c_prime_recorded.py --browser $B --dpr $1 --window $2 --out $out.json > $out.stdout.txt 2>&1
    say "recorded $B dpr$1 $2 exit $? :: $(tail -1 $out.stdout.txt | cut -c1-300)"
  done
  out=$E/h9-$B-dpr2-1400x1000-owner-gap80
  timeout 900 python3 $B2 --page current --dpr 2 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20 --out $out.json > $out.stdout.txt 2>&1
  say "h9 $B exit $? :: $(tail -1 $out.stdout.txt | cut -c1-200)"
done
say "DONE"
