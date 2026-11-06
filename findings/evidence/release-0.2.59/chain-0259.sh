#!/usr/bin/env bash
# The 0.2.59 hand-test slot's release regression (CLAUDE.md, cadence item 1), serial, both browsers, on dist.
# Only Calc moved: the page on the frozen ods-editor-v7 (copy) and the page-only sheets work.  Writer is byte for byte 0.2.58's
# (shell generation 91, e2-editor-v33; nothing under sdk/, editor-shell-v2/ or viewer-shell/ changed), so its nets are not re-run
# (cadence item 5: the gate is bound to the engine package's identity) and the gate reads 0.2.58's generation-91 records.
#   Calc: C, CU, cell, range, autosave, P2 (0.2.58's nets), headers, structure, and the two new features' page criteria on dist:
#   check_calc_sheets.py and check_calc_copy.py.
# Add no file under sdk/, editor-shell-v2/, web/ or spreadsheet-shell/ while it runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/release-0.2.59
LOG=$E/chain-0259.log
echo $$ > $E/chain-0259.pid
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN ${name#$E/}"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END ${name#$E/} exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
C=$E/calc-v7
V7=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/dist/profiles/ods-editor-v7
step $C/calc-sheet-view-v7 python3 tools/check_calc_sheet_view.py --out $C/calc-sheet-view-v7
step $C/cu-v7 python3 tools/check_calc_undo_cu.py --engine $V7 --out $C/cu-v7
step $C/cell-v7 python3 tools/run_calc_editor_browser.py --profile $V7 --repeats 1 --out $C/cell-v7
step $C/range-v7 python3 tools/probe_calc_range_format.py --profile $V7 --repeats 1 --out $C/range-v7
step $C/auto-v7 python3 tools/probe_calc_autosave.py --repeats 1 --out $C/auto-v7
step $C/p2-v7 python3 tools/check_calc_style.py --engine $V7 --out $C/p2-v7
step $C/headers-v7 python3 tools/check_calc_headers.py --engine $V7 --out $C/headers-v7
step $C/structure-v7 python3 tools/check_calc_structure.py --engine $V7 --out $C/structure-v7
cd tools
step $C/sheets-v7 python3 check_calc_sheets.py --engine $V7 --out $C/sheets-v7
step $C/copy-v7 python3 check_calc_copy.py --engine $V7 --out $C/copy-v7
cd ..
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
