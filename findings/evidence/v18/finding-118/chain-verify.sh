#!/bin/bash
# Finding 118 after the page fix: P3 (shrink, cutover page, v18) and P4 (M2-4, plain v18, fixed page), Chrome then
# Firefox.  Detached; exit codes captured before any substitution (rc first).  No pgrep/pkill.
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v18/finding-118
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
ts() { date '+%F %T %z'; }
snap() { ps -eo pid,etime,pcpu,comm --sort=-pcpu | head -12 > "$V/$1"; }
echo "$(ts) VERIFY START shrink $(sha256sum tools/run_shrink_repaint.py | cut -c1-16) merge $(sha256sum tools/run_merge_wasm_shakedown.py | cut -c1-16) page $(sha256sum web/e2-editor-app.js | cut -c1-16)" >> $LOG
step() { local name=$1; shift; snap "$name.ps-before.txt"; echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt; local rc=$?; echo "$(ts) END   $name exit=$rc" >> $LOG; snap "$name.ps-after.txt"; }
for B in chrome firefox; do
  step p3-v18-cutover-fixed-$B python3 tools/run_shrink_repaint.py --browser $B --profile e2-editor-v18 --page cutover --out $V/p3-v18-cutover-fixed-$B.json
  step p4-m2-4-fixed-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode m2-4 --candidate-profile e2-editor-v18 --out $V/p4-m2-4-fixed-$B.json
done
echo "$(ts) VERIFY DONE shrink $(sha256sum tools/run_shrink_repaint.py | cut -c1-16) merge $(sha256sum tools/run_merge_wasm_shakedown.py | cut -c1-16) page $(sha256sum web/e2-editor-app.js | cut -c1-16)" >> $LOG
