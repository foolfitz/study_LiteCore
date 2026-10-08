#!/bin/bash
# Finding 118 red cases P1 (v8, shipped page) and P2 (v18, cutover page before the fix), Chrome then Firefox.
# Detached (setsid nohup); no pgrep/pkill.
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v18/finding-118
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
ts() { date '+%F %T %z'; }
snap() { ps -eo pid,etime,pcpu,comm --sort=-pcpu | head -12 > "$V/$1"; }
R=tools/run_shrink_repaint.py
echo "$(ts) RED START runner $(sha256sum $R | cut -c1-16) page $(sha256sum web/e2-editor-app.js | cut -c1-16)" >> $LOG
step() { local name=$1; shift; snap "$name.ps-before.txt"; echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt; local rc=$?; echo "$(ts) END   $name exit=$rc" >> $LOG; snap "$name.ps-after.txt"; }
for B in chrome firefox; do
  step p1-v8-dist-$B python3 $R --browser $B --profile e2-editor-v8 --page dist --out $V/p1-v8-dist-$B.json
  step p2-v18-cutover-$B python3 $R --browser $B --profile e2-editor-v18 --page cutover --out $V/p2-v18-cutover-$B.json
done
echo "$(ts) RED DONE runner $(sha256sum $R | cut -c1-16) page $(sha256sum web/e2-editor-app.js | cut -c1-16)" >> $LOG
