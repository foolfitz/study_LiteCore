#!/bin/bash
# Shakedown of the merge runner's new modes (PREDICTION.md), one tool at a time, Chrome then Firefox.  Launched
# detached (setsid nohup) so it survives the launching session (handoff rule h).  No pgrep/pkill pattern (rule e).
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v18/m2-shakedown
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
ts() { date '+%F %T %z'; }
snap() { ps -eo pid,etime,pcpu,comm --sort=-pcpu | head -12 > "$V/$1"; }
R=tools/run_merge_wasm_shakedown.py
echo "$(ts) CHAIN START runner $(sha256sum $R | cut -c1-16)" >> $LOG
step() { # name, command...
  local name=$1; shift
  snap "$name.ps-before.txt"
  echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt
  echo "$(ts) END   $name exit=$?" >> $LOG
  snap "$name.ps-after.txt"
}
for B in chrome firefox; do
  step red-$B python3 $R --browser $B --mode m2-1-red --candidate-profile e2-editor-v8 --out $V/red-$B.json
  step m2-1b-$B python3 $R --browser $B --mode m2-1b --candidate-profile e2-editor-v18 --out $V/m2-1b-$B.json
  step m2-4-$B python3 $R --browser $B --mode m2-4 --candidate-profile e2-editor-v18 --out $V/m2-4-$B.json
  step m2-4-control-$B python3 $R --browser $B --mode m2-4 --candidate-profile e2-editor-v18 --control --out $V/m2-4-control-$B.json
  step pair-m2-4-$B python3 $R --pair $V/m2-4-$B.json $V/m2-4-control-$B.json
done
echo "$(ts) CHAIN DONE runner $(sha256sum $R | cut -c1-16)" >> $LOG
