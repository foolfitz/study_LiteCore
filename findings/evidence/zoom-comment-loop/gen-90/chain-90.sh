#!/usr/bin/env bash
# Generation 90's release regression (CLAUDE.md, cadence item 1: once per hand-test slot), serial, both browsers: the Writer nets
# P5, P4, S1, Z (t3, and l1 -- the document with a comment, the hand test's item 1), P1, F4 and F3, with the parametrised tools
# (--generation 90).  Calc's nets are not run: the Calc page and every module it serves are byte-identical to generation 89
# (the host delta shows it).  V0' 90 ran before this, alone (../v0/).
# Add no file under sdk/ or editor-shell-v2/ while it runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/zoom-comment-loop/gen-90
LOG=$E/chain-90.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
step $E/p5/final-90-log python3 -I tools/check_writer_enter_range.py --profile e2-editor-v33 --out $E/p5/final-90
step $E/p4/final-90-log python3 -I tools/check_writer_toggle.py --out $E/p4/final-90
step $E/shift-lines/live-page-90-log python3 -I tools/check_writer_shift_lines.py --out $E/shift-lines/live-page-90
step $E/writer-zoom/t3-log python3 -I tools/check_writer_zoom.py --out $E/writer-zoom/t3
step $E/writer-zoom/l1-log python3 -I tools/check_writer_zoom.py --document test-docs/r7-compat/l1-layout-table-image.odt --out $E/writer-zoom/l1
step $E/p1/final-90-log python3 -I tools/check_writer_align.py --out $E/p1/final-90
F4=$E/f4-90
for b in chrome firefox; do step $F4/$b-run python3 tools/run_four_arms.py --generation 90 --browser $b --out $F4/$b; done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_product_four_arms.py --generation 90 $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
F3=$E/f3-90
mkdir -p $F3/baseline-f3-83
ln -sfn ../../../../v29-177/f3-83/diag-single-press/chrome-1 $F3/baseline-f3-83/chrome
ln -sfn ../../../../v29-177/f3-83/diag-single-press/firefox-1 $F3/baseline-f3-83/firefox
for b in chrome firefox; do step $F3/run-01/$b python3 tools/run_f3_clipboard.py --generation 90 --browser $b --out $F3/run-01/$b; done
step $F3/equal python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83
step $F3/equal-self-test python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83 --self-test
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
