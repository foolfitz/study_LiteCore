#!/bin/bash
# After the v17 product-path chain: the merge shakedown (merge/PREDICTION.md) and then the counted corpus
# comparison (layout-corpus/PREDICTION.md), one tool at a time. Starts only on "CHAIN DONE"; on "CHAIN ABORT" it
# exits without running anything. Every step is logged to followon.log with its exit code.
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v17
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/followon.log
ts() { date '+%F %T %z'; }
echo "$(ts) FOLLOWON WAITING for the product-path chain" >> $LOG
until grep -qE 'CHAIN (DONE|ABORT)' $V/product-path/chain.log 2>/dev/null; do sleep 15; done
if grep -q 'CHAIN ABORT' $V/product-path/chain.log; then echo "$(ts) FOLLOWON NOT STARTED: chain aborted" >> $LOG; exit 2; fi
sleep 10
step() { # name, command...
  local name=$1; shift
  echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt
  local rc=$?
  echo "$(ts) END   $name exit=$rc" >> $LOG
}
echo "$(ts) FOLLOWON START runner_sha256=$(sha256sum tools/run_merge_wasm_shakedown.py | cut -d' ' -f1)" >> $LOG
for B in chrome firefox; do
  step merge/shakedown-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --candidate-profile e2-editor-v17 --frame-cell --rounds 2 --out $V/merge/shakedown-$B.json
  step merge/control-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --candidate-profile e2-editor-v17 --frame-cell --rounds 2 --control --out $V/merge/control-$B.json
  step merge/pair-$B python3 tools/run_merge_wasm_shakedown.py --pair $V/merge/shakedown-$B.json $V/merge/control-$B.json
done
C=$V/layout-corpus
sha256sum tools/compare_layout_corpus.py > $C/tool-sha-before.txt
ps -eo pid,etime,pcpu,comm --sort=-pcpu | head -15 > $C/ps-before.txt
date -u '+%FT%TZ' > $C/run-started-utc.txt
step layout-corpus/run python3 tools/compare_layout_corpus.py --profiles e2-editor-v17 e2-editor-v17-cjk-r5-ab --out $C
date -u '+%FT%TZ' > $C/run-finished-utc.txt
ps -eo pid,etime,pcpu,comm --sort=-pcpu | head -15 > $C/ps-after.txt
sha256sum tools/compare_layout_corpus.py > $C/tool-sha-after.txt
grep 'layout-corpus/run exit' $LOG | tail -1 > $C/run-exit.txt
echo "$(ts) FOLLOWON DONE" >> $LOG
