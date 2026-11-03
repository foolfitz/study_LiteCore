#!/usr/bin/env bash
# SPEC-P-ms-formats step 4: generation 89 on e2-editor-v33, the Calc page on ods-editor-v5, serial; W on the frozen dist/ in both browsers;
# V0prime last and alone, it swaps files under web/, sdk/ and dist/.  Derived from ../demo-batch-5/chain-88.sh: the output folder; P5's
# --profile e2-editor-v33 (its default is v32); the generation-89 F4 and F3 tools; W --live; V0prime 89.
# Add no file under sdk/ or editor-shell-v2/ while it runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/ms-formats/gen-89
LOG=$E/chain-89.log
mkdir -p $E
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
step $E/p5/final-89-log python3 -I tools/check_writer_enter_range.py --profile e2-editor-v33 --out $E/p5/final-89
step $E/p4/final-89-log python3 -I tools/check_writer_toggle.py --out $E/p4/final-89
step $E/shift-lines/live-page-89-log python3 -I tools/check_writer_shift_lines.py --out $E/shift-lines/live-page-89
step $E/writer-zoom/run-89-log python3 -I tools/check_writer_zoom.py --out $E/writer-zoom/run-89
step $E/p1/final-89-log python3 -I tools/check_writer_align.py --out $E/p1/final-89
step $E/calc-sheet-view/run-89 python3 tools/check_calc_sheet_view.py --out $E/calc-sheet-view/run-89
F4=$E/f4-89
for b in chrome firefox; do step $F4/$b-run python3 tools/run_v89_four_arms.py --browser $b --out $F4/$b; done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_v89_product_four_arms.py $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
F3=$E/f3-89
mkdir -p $F3/baseline-f3-83
ln -sfn ../../../../v29-177/f3-83/diag-single-press/chrome-1 $F3/baseline-f3-83/chrome
ln -sfn ../../../../v29-177/f3-83/diag-single-press/firefox-1 $F3/baseline-f3-83/firefox
for b in chrome firefox; do step $F3/run-01/$b python3 tools/run_v89_f3_clipboard.py --browser $b --out $F3/run-01/$b; done
step $F3/equal python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83
step $F3/equal-self-test python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83 --self-test
M0=../findings/evidence/ms-formats/native-m0
for b in chrome firefox; do step $E/w-live/$b python3 tools/run_ms_formats_w.py --browser $b --live --native-m0 $M0 --harness build/msformat-native-2/msformat-native --out $E/w-live/$b; done
for b in chrome firefox; do step $E/w-live/read-$b python3 tools/run_ms_formats_w.py --read $E/w-live/$b/report.json; done
step ../findings/evidence/ms-formats/v0-89/run python3 -I ../findings/evidence/ms-formats/v0-89/run_v0_prime.py
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
