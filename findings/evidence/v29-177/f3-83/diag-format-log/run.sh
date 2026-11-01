#!/usr/bin/env bash
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/v29-177/f3-83
D=$E/diag-format-log
for run in firefox-1 chrome-1 firefox-2 chrome-2; do
  b=${run%-*}
  echo "$(date +%T) $run" >> $D/log.txt
  python3 -I $E/diag_format_log.py --browser $b --out $D/$run > $D/$run.stdout.txt 2> $D/$run.stderr.txt
  echo "$(date +%T) $run exit $?" >> $D/log.txt
done
echo "$(date +%T) DONE" >> $D/log.txt
