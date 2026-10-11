#!/usr/bin/env bash
# C5 (ii) on the final C′ page (PREDICTION.md, committed before this runs): one full --mutate run per mutation, Chrome.
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/c-prime/c5ii
T=wasm_sdk_probe/tools
LOG=$E/chain.txt
ts() { date -u '+%FT%TZ'; }
say() { echo "$(ts) $*" >> $LOG; }
h() { sha256sum "$1" | cut -c1-16; }
D=$(h wasm_sdk_probe/dist/e2-editor-app.js); W=$(h wasm_sdk_probe/web/e2-editor-app.js)
[ "$D" = 8909564eb2316afa ] && [ "$W" = 8909564eb2316afa ] || { say "REFUSED dist $D web $W"; exit 2; }
[ "$(h $T/run_e2_c_product_path.py)" = bd6fc0caf677ee9c ] || { say "REFUSED runner $(h $T/run_e2_c_product_path.py)"; exit 2; }
NAMES=$(cd wasm_sdk_probe/tools && python3 -I -c "import sys; sys.path.insert(0,'.'); import run_e2_c_product_path as pp; print(' '.join(pp.MUTATIONS))")
say "START tree $(git rev-parse --short HEAD) dist $D runner bd6fc0caf677ee9c mutations $(echo $NAMES | wc -w)"
for M in $NAMES; do
  case $M in
    structure-names-nothing-while-the-region-defers|the-region-defers-with-a-reason-it-owed-the-user|geometry-declared-but-not-delivered)
      FLAGS="--candidate-profile e2-editor-v14";;
    cut-swallows-the-refusal) FLAGS="--refusal-diagnostic";;
    *) FLAGS="";;
  esac
  OUT=$PWD/$E/mutation-$M-chrome
  timeout 1800 python3 $T/run_e2_c_product_path.py --browser chrome --mutate $M $FLAGS --out $OUT.json > $OUT.stdout.txt 2> $OUT.stderr.txt
  RC=$?
  say "$M exit $RC flags [$FLAGS] report $([ -s $OUT.json ] && echo yes || echo no)"
done
say "DONE"
