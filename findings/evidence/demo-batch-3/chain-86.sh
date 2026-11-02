#!/usr/bin/env bash
# SPEC-P-demo-batch-3 section 3: generation 86 on e2-editor-v31 and Calc on ods-editor-v3, serial; V0' last and alone, it swaps files under dist/.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/demo-batch-3
LOG=$E/chain-86.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
step $E/shift-lines/live-page-86-log python3 -I tools/check_writer_shift_lines.py --out $E/shift-lines/live-page-86
step $E/writer-zoom/run-86-log python3 -I tools/check_writer_zoom.py --out $E/writer-zoom/run-86
step $E/p1/final-86-log python3 -I tools/check_writer_align.py --out $E/p1/final-86
step $E/calc-sheet-view/run-86-log python3 tools/check_calc_sheet_view.py --out $E/calc-sheet-view/run-86
F4=$E/f4-86
for b in chrome firefox; do step $F4/$b-run python3 tools/run_v86_four_arms.py --browser $b --out $F4/$b; done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_v86_product_four_arms.py $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
F3=$E/f3-86
mkdir -p $F3/baseline-f3-83
ln -sfn ../../../v29-177/f3-83/diag-single-press/chrome-1 $F3/baseline-f3-83/chrome
ln -sfn ../../../v29-177/f3-83/diag-single-press/firefox-1 $F3/baseline-f3-83/firefox
for b in chrome firefox; do step $F3/run-01/$b python3 tools/run_v86_f3_clipboard.py --browser $b --out $F3/run-01/$b; done
step $F3/equal python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83
step $F3/equal-self-test python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83 --self-test
step $E/v0-86/run python3 -I $E/v0-86/run_v0_prime.py
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
