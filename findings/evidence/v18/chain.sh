#!/bin/bash
# v18's W4 and W6 runs (PREDICTION.md), one tool at a time, in order: product-path net (v8/v18 interleaved,
# 3 rounds x Chrome/Firefox), merge shakedown + control + pair per browser, the owner's document (Chrome), the counted
# corpus comparison.  A missing product-path report aborts the chain (nothing after it runs).  No pgrep/pkill
# pattern is used anywhere (standing rule e): steps run one after another in this one script, so they cannot
# overlap; a `ps` snapshot is kept before and after each step instead.
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v18
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
PPLOG=$V/product-path/chain.log         # the product-path reader parses END lines in this format
ts() { date '+%F %T %z'; }
snap() { ps -eo pid,etime,pcpu,comm --sort=-pcpu | head -12 > "$V/$1"; }
echo "$(ts) CHAIN START tools: $(sha256sum tools/run_e2_c_product_path.py tools/run_merge_wasm_shakedown.py tools/compare_layout_corpus.py | awk '{print substr($1,1,16)" "$2}' | tr '\n' ' ')" | tee -a $LOG >> $PPLOG
pp() { # profile browser round
  local P=$1 B=$2 N=$3 OUT=$V/product-path/e2-editor-$1-$2-r$3 CMD
  if [ "$P" = v8 ]; then
    CMD="python3 tools/run_e2_c_product_path.py --browser $B --out $OUT.json"
  else
    CMD="python3 tools/run_e2_c_product_path.py --browser $B --candidate-profile e2-editor-v18 --out $OUT.json"
  fi
  echo "$(ts) START $P $B r$N :: $CMD" | tee -a $LOG >> $PPLOG
  $CMD > $OUT.stdout.txt 2> $OUT.stderr.txt
  local RC=$?
  echo "$(ts) END   $P $B r$N exit=$RC report_exists=$([ -s $OUT.json ] && echo yes || echo no)" | tee -a $LOG >> $PPLOG
  if [ ! -s $OUT.json ]; then echo "$(ts) CHAIN ABORT: no report for $P $B r$N" | tee -a $LOG >> $PPLOG; exit 2; fi
}
step() { # name, command...
  local name=$1; shift
  snap "$name.ps-before.txt"
  echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt
  local rc=$?
  echo "$(ts) END   $name exit=$rc" >> $LOG
  snap "$name.ps-after.txt"
}
for B in chrome firefox; do
  for N in 1 2 3; do
    pp v8 $B $N
    pp v18 $B $N
  done
done
echo "$(ts) PRODUCT-PATH DONE" | tee -a $LOG >> $PPLOG
for B in chrome firefox; do
  step merge/shakedown-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --candidate-profile e2-editor-v18 --frame-cell --rounds 2 --out $V/merge/shakedown-$B.json
  step merge/control-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --candidate-profile e2-editor-v18 --frame-cell --rounds 2 --control --out $V/merge/control-$B.json
  step merge/pair-$B python3 tools/run_merge_wasm_shakedown.py --pair $V/merge/shakedown-$B.json $V/merge/control-$B.json
done
step v5/shakedown-chrome-v18-v5 python3 tools/run_merge_wasm_shakedown.py --browser chrome --candidate-profile e2-editor-v18 --owner-document --out $V/v5/shakedown-chrome-v18-v5.json
C=$V/layout-corpus
date -u '+%FT%TZ' > $C/run-started-utc.txt
step layout-corpus/run python3 tools/compare_layout_corpus.py --profiles e2-editor-v18 e2-editor-v17-cjk-r5-ab --out $C
date -u '+%FT%TZ' > $C/run-finished-utc.txt
echo "$(ts) CHAIN DONE tools: $(sha256sum tools/run_e2_c_product_path.py tools/run_merge_wasm_shakedown.py tools/compare_layout_corpus.py | awk '{print substr($1,1,16)" "$2}' | tr '\n' ' ')" >> $LOG
