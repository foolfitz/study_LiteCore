#!/usr/bin/env bash
# The witness (SPEC-M3-production-ui §17.9 (b), (f), §17.11; ruling-1 condition 5; PREDICTION.md):
# the UNPORTED product-path net on the C′-only page.  Page = commit 57d21411 (cherry-picked to main as
# 90242ebc, dist/e2-editor-app.js f5121fd4…).  Runners = the pre-port commit 08d73cff, restored
# temporarily for these two runs only; HEAD's ported runners are put back on every exit path and their
# hashes checked.  v19 arm (no --candidate-profile), Chrome then Firefox, one run each.  Not a count.
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/c-prime/witness/product-path
T=wasm_sdk_probe/tools
LOG=$E/chain.log
FILES="run_e2_c_page_smoke.py run_e2_c_product_path.py check_m3_page_honesty.py"
mkdir -p $E
ts() { date -u '+%FT%TZ'; }
say() { echo "$(ts) $*" >> $LOG; }
h() { sha256sum "$1" | cut -c1-16; }

restore() {
  for f in $FILES; do git checkout HEAD -- $T/$f; done
  say "RESTORED smoke $(h $T/run_e2_c_page_smoke.py) pp $(h $T/run_e2_c_product_path.py) honesty $(h $T/check_m3_page_honesty.py) (expect cc38ee97ca20611d aa9a22806d10ed71 17a38fe756fe3e0b)"
  if [ "$(h $T/run_e2_c_page_smoke.py)" = cc38ee97ca20611d ] && [ "$(h $T/run_e2_c_product_path.py)" = aa9a22806d10ed71 ] \
     && [ "$(h $T/check_m3_page_honesty.py)" = 17a38fe756fe3e0b ]; then say "RESTORE OK"; else say "RESTORE MISMATCH"; fi
}
trap restore EXIT

D=$(h wasm_sdk_probe/dist/e2-editor-app.js); W=$(h wasm_sdk_probe/web/e2-editor-app.js)
if [ "$D" != f5121fd432ac02ea ] || [ "$W" != f5121fd432ac02ea ]; then say "REFUSED dist $D web $W (want f5121fd432ac02ea)"; exit 2; fi
for f in $FILES; do git show 08d73cff:$T/$f > $T/$f; done
S=$(h $T/run_e2_c_page_smoke.py); PP=$(h $T/run_e2_c_product_path.py); HN=$(h $T/check_m3_page_honesty.py)
if [ "$S" != 5f26e3bd1280b3a9 ] || [ "$PP" != a6e318966d50cf14 ] || [ "$HN" != 505f4f3a91ab93e5 ]; then
  say "REFUSED pre-port hashes smoke $S pp $PP honesty $HN"; exit 2; fi
say "START tree $(git rev-parse --short HEAD) page-commit 57d21411 (main 90242ebc) dist $D runners 08d73cff smoke $S pp $PP honesty $HN"
for B in chrome firefox; do
  OUT=$PWD/$E/e2-editor-v19-$B-witness
  CMD="python3 $T/run_e2_c_product_path.py --browser $B --out $OUT.json"
  say "START v19 $B :: $CMD"
  $CMD > $OUT.stdout.txt 2> $OUT.stderr.txt
  RC=$?
  say "END   v19 $B exit=$RC report_exists=$([ -s $OUT.json ] && echo yes || echo no)"
done
say "DONE"
