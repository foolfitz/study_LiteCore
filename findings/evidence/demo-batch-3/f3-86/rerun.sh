#!/usr/bin/env bash
# Finding-180-adjacent read: the one moved F3-86 cell, repeated on the same bytes.  An intermittent cell's count is the measurement.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/demo-batch-3/f3-86/rerun
mkdir -p $E
for i in 1 2 3; do
  echo "$(date +%T) firefox-$i begin" >> $E/log.txt
  python3 tools/run_v86_f3_clipboard.py --browser firefox --out $E/firefox-$i > $E/firefox-$i.stdout.txt 2> $E/firefox-$i.stderr.txt
  echo "$(date +%T) firefox-$i exit=$?" >> $E/log.txt
done
echo DONE >> $E/log.txt
