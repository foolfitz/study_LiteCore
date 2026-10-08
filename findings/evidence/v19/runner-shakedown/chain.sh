#!/bin/bash
# PREDICTION.md steps 1-3, Chrome then Firefox.  Detached; rc captured first; no pgrep/pkill.
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v19/runner-shakedown
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
ts() { date '+%F %T %z'; }
snap() { ps -eo pid,ppid,etime,pcpu,comm --sort=-pcpu | head -15 > "$V/$1"
  ps -eo pid,etime,args | /usr/bin/grep -E -- '[-]-remote-debugging-port=|[g]eckodriver|[-]marionette' > "$V/$1.test-browsers"; }
echo "$(ts) START runner $(sha256sum tools/run_merge_wasm_shakedown.py | cut -c1-16) page $(sha256sum web/e2-editor-app.js | cut -c1-16)" >> $LOG
step() { local name=$1; shift; snap "$name.ps-before.txt"; echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt; local rc=$?; echo "$(ts) END   $name exit=$rc" >> $LOG; snap "$name.ps-after.txt"; }
for B in chrome firefox; do
  step cases-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --candidate-profile e2-editor-v18 --cases C01,C15,C29,Y01 --out $V/cases-$B.json
  step cases-control-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --candidate-profile e2-editor-v18 --cases C01,C15,C29,Y01 --control --out $V/cases-control-$B.json
  python3 tools/run_merge_wasm_shakedown.py --pair $V/cases-$B.json $V/cases-control-$B.json > $V/pair-$B.stdout.txt 2> $V/pair-$B.stderr.txt
  rc=$?; echo "$rc" > $V/pair-$B.exit; echo "$(ts) END   pair-$B exit=$rc" >> $LOG
  step m2-4-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode m2-4 --candidate-profile e2-editor-v18 --out $V/m2-4-$B.json
done
echo "$(ts) DONE runner $(sha256sum tools/run_merge_wasm_shakedown.py | cut -c1-16) page $(sha256sum web/e2-editor-app.js | cut -c1-16)" >> $LOG
