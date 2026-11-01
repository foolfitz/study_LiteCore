#!/usr/bin/env bash
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/v29-177/f3-83
D=$E/diag-single-press
for run in firefox-1 firefox-2 firefox-3 chrome-1; do
  b=${run%-*}
  echo "$(date +%T) $run" >> $D/log.txt
  python3 -I $E/diag_single_press.py --browser $b --out $D/$run > $D/$run.stdout.txt 2> $D/$run.stderr.txt
  echo "$(date +%T) $run exit $?" >> $D/log.txt
done
echo "$(date +%T) DONE" >> $D/log.txt
