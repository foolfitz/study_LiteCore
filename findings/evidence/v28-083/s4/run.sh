#!/usr/bin/env bash
# S4 (SPEC-M3-v28-last-line-fallback 7.3, append 1): run-01, then each mutation, then the self-test on run-01.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
E=../findings/evidence/v28-083/s4
T=tools/check_v82_last_line_bullet.py
python3 -I $T --out $E/run-01 > $E/run-01.stdout.txt 2> $E/run-01.stderr.txt; echo $? > $E/run-01.exit.txt
for m in press-list-none cosmetic-review wrong-button-b-number wrong-button-b-none wrong-button-b-heading wrong-button-b-body; do
  python3 -I $T --mutation $m --out $E/mutation-$m > $E/mutation-$m.stdout.txt 2> $E/mutation-$m.stderr.txt
  echo $? > $E/mutation-$m.exit.txt
done
python3 -I $T --self-test $E/run-01/report.json > $E/self-test-01.json 2> $E/self-test-01.stderr.txt; echo $? > $E/self-test-01.exit.txt
