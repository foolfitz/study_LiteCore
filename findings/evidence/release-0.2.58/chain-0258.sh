#!/usr/bin/env bash
# The 0.2.58 hand-test slot's release regression (CLAUDE.md, cadence item 1), serial, both browsers, on dist:
#   Writer, shell generation 91 (e2-editor-v33): P5, P4, S1, Z (t3 and l1), P1, F4, F3 with the parametrised tools
#     (--generation 91), and KB (check_key_burst.py: source == dist == generation 91, so the default subject is dist's bytes).
#   Calc, the page on the frozen ods-editor-v6: C, CU, cell, range, autosave, P2 (host-0.2.56/release-inputs.json's nets),
#     and the two new features' page criteria on dist: check_calc_headers.py and check_calc_structure.py.
# V0' 91 ran before this, alone (gen-91/v0/).  Add no file under sdk/, editor-shell-v2/, web/ or spreadsheet-shell/ while it runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/release-0.2.58
LOG=$E/chain-0258.log
echo $$ > $E/chain-0258.pid
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN ${name#$E/}"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END ${name#$E/} exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
W=$E/gen-91
step $W/p5/final-91-log python3 -I tools/check_writer_enter_range.py --profile e2-editor-v33 --out $W/p5/final-91
step $W/p4/final-91-log python3 -I tools/check_writer_toggle.py --out $W/p4/final-91
step $W/shift-lines/live-page-91-log python3 -I tools/check_writer_shift_lines.py --out $W/shift-lines/live-page-91
step $W/writer-zoom/t3-log python3 -I tools/check_writer_zoom.py --out $W/writer-zoom/t3
step $W/writer-zoom/l1-log python3 -I tools/check_writer_zoom.py --document test-docs/r7-compat/l1-layout-table-image.odt --out $W/writer-zoom/l1
step $W/p1/final-91-log python3 -I tools/check_writer_align.py --out $W/p1/final-91
step $W/key-burst/kb-dist-log python3 -I tools/check_key_burst.py --out $W/key-burst/kb-dist
F4=$W/f4-91
for b in chrome firefox; do step $F4/$b-run python3 tools/run_four_arms.py --generation 91 --browser $b --out $F4/$b; done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_product_four_arms.py --generation 91 $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
F3=$W/f3-91
mkdir -p $F3/baseline-f3-83
ln -sfn ../../../../v29-177/f3-83/diag-single-press/chrome-1 $F3/baseline-f3-83/chrome
ln -sfn ../../../../v29-177/f3-83/diag-single-press/firefox-1 $F3/baseline-f3-83/firefox
for b in chrome firefox; do step $F3/run-01/$b python3 tools/run_f3_clipboard.py --generation 91 --browser $b --out $F3/run-01/$b; done
step $F3/equal python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83
step $F3/equal-self-test python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83 --self-test
C=$E/calc-v6
V6=dist/profiles/ods-editor-v6
step $C/calc-sheet-view-v6 python3 tools/check_calc_sheet_view.py --out $C/calc-sheet-view-v6
step $C/cu-v6 python3 tools/check_calc_undo_cu.py --engine $V6 --out $C/cu-v6
step $C/cell-v6 python3 tools/run_calc_editor_browser.py --profile $V6 --repeats 1 --out $C/cell-v6
step $C/range-v6 python3 tools/probe_calc_range_format.py --profile $V6 --repeats 1 --out $C/range-v6
step $C/auto-v6 python3 tools/probe_calc_autosave.py --repeats 1 --out $C/auto-v6
step $C/p2-v6 python3 tools/check_calc_style.py --engine $V6 --out $C/p2-v6
step $C/headers-v6 python3 tools/check_calc_headers.py --engine $V6 --out $C/headers-v6
step $C/structure-v6 python3 tools/check_calc_structure.py --engine $V6 --out $C/structure-v6
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
