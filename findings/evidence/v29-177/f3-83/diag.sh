#!/usr/bin/env bash
# F4-83 again on the final page (its identity binds the HTML), then the F3 diagnostic, Firefox three times and Chrome once.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/v29-177
LOG=$E/f3-83/diag-log.txt
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END   $(basename "$name") exit $rc"; }
say "START tree $(git rev-parse --short HEAD)"
F4=$E/f4-83/final-page
for b in chrome firefox; do step $F4/$b-run python3 tools/run_v83_four_arms.py --browser $b --out $F4/$b; done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_v83_product_four_arms.py $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
D=$E/f3-83/diag-clear-wait
mkdir -p $D
for r in 1 2 3; do step $D/firefox-$r-run python3 -I $E/f3-83/diag_clear_wait.py --browser firefox --out $D/firefox-$r; done
step $D/chrome-1-run python3 -I $E/f3-83/diag_clear_wait.py --browser chrome --out $D/chrome-1
say DONE
