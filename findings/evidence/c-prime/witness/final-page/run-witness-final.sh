#!/usr/bin/env bash
# The witness on the final page (PREDICTION.md, committed in 0c9a8394 before any run): per browser, the
# UNPORTED product-path net (08d73cff's three runners, restored temporarily) and then the PORTED one (HEAD),
# v19 arm, one run each, on dist/e2-editor-app.js 8909564eb2316afa.  HEAD's runners are put back before each
# ported run and on every exit path, and their hashes checked.  Not a count.
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/c-prime/witness/final-page
T=wasm_sdk_probe/tools
LOG=$E/chain.log
FILES="run_e2_c_page_smoke.py run_e2_c_product_path.py check_m3_page_honesty.py"
HEAD_HASHES="cc38ee97ca20611d bd6fc0caf677ee9c 17a38fe756fe3e0b"
PRE_HASHES="5f26e3bd1280b3a9 a6e318966d50cf14 505f4f3a91ab93e5"
PAGE=8909564eb2316afa
mkdir -p $E
ts() { date -u '+%FT%TZ'; }
say() { echo "$(ts) $*" >> $LOG; }
h() { sha256sum "$1" | cut -c1-16; }
hashes() { echo "$(h $T/run_e2_c_page_smoke.py) $(h $T/run_e2_c_product_path.py) $(h $T/check_m3_page_honesty.py)"; }

to_head() {
  for f in $FILES; do git checkout HEAD -- $T/$f; done
  if [ "$(hashes)" = "$HEAD_HASHES" ]; then say "HEAD runners $(hashes) OK"; return 0; fi
  say "HEAD runners MISMATCH $(hashes) (want $HEAD_HASHES)"; return 1
}
to_preport() {
  for f in $FILES; do git show 08d73cff:$T/$f > $T/$f; done
  if [ "$(hashes)" = "$PRE_HASHES" ]; then say "pre-port runners $(hashes) OK"; return 0; fi
  say "pre-port runners MISMATCH $(hashes) (want $PRE_HASHES)"; return 1
}
trap 'to_head; say "EXIT restore done"' EXIT

D=$(h wasm_sdk_probe/dist/e2-editor-app.js); W=$(h wasm_sdk_probe/web/e2-editor-app.js)
if [ "$D" != $PAGE ] || [ "$W" != $PAGE ]; then say "REFUSED dist $D web $W (want $PAGE)"; exit 2; fi
to_head || exit 2
say "START tree $(git rev-parse --short HEAD) dist $D"
run() {  # $1 = unported|ported, $2 = browser
  OUT=$PWD/$E/e2-editor-v19-$2-$1
  CMD="python3 $T/run_e2_c_product_path.py --browser $2 --out $OUT.json"
  say "START $1 v19 $2 runners $(hashes) :: $CMD"
  $CMD > $OUT.stdout.txt 2> $OUT.stderr.txt
  RC=$?
  say "END   $1 v19 $2 exit=$RC report_exists=$([ -s $OUT.json ] && echo yes || echo no)"
}
for B in chrome firefox; do
  to_preport || exit 2
  run unported $B
  to_head || exit 2
  run ported $B
done
say "DONE"
