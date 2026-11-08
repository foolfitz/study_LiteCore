#!/usr/bin/env bash
# The 0.2.61 hand-test slot's release regression (CLAUDE.md, cadence item 1; the owner chose A on 2026-11-08 11:5x: release now),
# serial, both browsers, on dist.  Only the Calc page moved: zoomTo anchors on the active cell's top-left, else the view's top-left
# (SPEC-P-calc-zoom append 5).  The engine is 0.2.60's frozen ods-editor-v8; Writer is byte for byte 0.2.60's (generation 91).
# The same nets as release-0.2.60/chain-0260.sh, names suffixed -0261 (mirror folders are build/calc-*/<name>); the zoom step runs
# check_calc_zoom.py with append 5's P-Z5 and P-Z10.
# Add no file under sdk/, editor-shell-v2/, web/ or spreadsheet-shell/ while it runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/release-0.2.61
LOG=$E/chain-0261.log
echo $$ > $E/chain-0261.pid
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN ${name#$E/}"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END ${name#$E/} exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
C=$E/calc-v8
V8=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/dist/profiles/ods-editor-v8
NATIVE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/calc-v8/native-build-01/v8/calc-undo-native
step $C/calc-sheet-view-0261 python3 tools/check_calc_sheet_view.py --out $C/calc-sheet-view-0261
step $C/cu-0261 python3 tools/check_calc_undo_cu.py --engine $V8 --out $C/cu-0261
step $C/cell-0261 python3 tools/run_calc_editor_browser.py --profile $V8 --repeats 1 --out $C/cell-0261
step $C/range-0261 python3 tools/probe_calc_range_format.py --profile $V8 --repeats 1 --out $C/range-0261
step $C/auto-0261 python3 tools/probe_calc_autosave.py --repeats 1 --out $C/auto-0261
step $C/p2-0261 python3 tools/check_calc_style.py --engine $V8 --out $C/p2-0261
step $C/headers-0261 python3 tools/check_calc_headers.py --engine $V8 --out $C/headers-0261
step $C/structure-0261 python3 tools/check_calc_structure.py --engine $V8 --out $C/structure-0261
cd tools
step $C/sheets-0261 python3 check_calc_sheets.py --engine $V8 --out $C/sheets-0261
step $C/copy-html-0261 python3 check_calc_copy.py --html --engine $V8 --native-harness $NATIVE --out $C/copy-html-0261
step $C/zoom-0261 python3 check_calc_zoom.py --engine $V8 --out $C/zoom-0261
cd ..
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
