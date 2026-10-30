#!/usr/bin/env bash
# F3-82 then F4-82 (SPEC-M3-v28-last-line-fallback 7.3), both browsers, on frozen generation 82; then their readers.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
F3=../findings/evidence/v28-083/f3-82; F4=../findings/evidence/v28-083/f4-82
mkdir -p $F3/run-01
for b in chrome firefox; do
  python3 tools/run_v82_f3_clipboard.py --browser $b --out $F3/run-01/$b > $F3/run-01/$b.stdout.json 2> $F3/run-01/$b.stderr.txt
  echo "f3 $b exit=$?" > $F3/run-01/$b.exit.txt
done
for b in chrome firefox; do
  python3 tools/run_v82_four_arms.py --browser $b --out $F4/$b > $F4/$b.stdout.txt 2> $F4/$b.stderr.txt
  echo "f4 $b exit=$?" > $F4/$b.exit.txt
done
A=$(cd $F4 && pwd)
python3 tools/judge_v82_product_four_arms.py $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json > $F4/aggregate-judge.stdout.txt 2> $F4/aggregate-judge.stderr.txt
python3 tools/read_v82_f3_equal.py --v82 $F3/run-01 > $F3/equal-01.json 2> $F3/equal-01.stderr.txt; echo "exit=$?" > $F3/equal-01.exit.txt
python3 tools/read_v82_f3_equal.py --v82 $F3/run-01 --self-test > $F3/equal-01-self-test.json 2> $F3/equal-01-self-test.stderr.txt; echo "exit=$?" > $F3/equal-01-self-test.exit.txt
python3 tools/read_v25_f3.py --v25 $F3/run-01 > $F3/read-01.json 2> $F3/read-01.stderr.txt; echo "exit=$?" > $F3/read-01.exit.txt
