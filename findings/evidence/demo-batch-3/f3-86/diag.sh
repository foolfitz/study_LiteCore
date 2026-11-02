#!/usr/bin/env bash
# PREDICTION.md: Firefox three times and Chrome once, with the clear wait moved to the toast.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/demo-batch-3/f3-86
D=$E/diag-clear-wait
mkdir -p $D
for b in firefox-1 firefox-2 firefox-3 chrome-1; do
  echo "$(date +%T) $b begin" >> $D/log.txt
  python3 -I $E/diag_clear_wait.py --browser ${b%-*} --out $D/$b > $D/$b.stdout.txt 2> $D/$b.stderr.txt
  echo "$(date +%T) $b exit=$?" >> $D/log.txt
done
echo DONE >> $D/log.txt
