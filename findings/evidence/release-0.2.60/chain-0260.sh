#!/usr/bin/env bash
# The 0.2.60 hand-test slot's release regression (CLAUDE.md, cadence item 1; the owner named the slot 2026-11-07 23:2x), serial,
# both browsers, on dist.  Only Calc moved: the page on the frozen ods-editor-v8 (copy writes text/html, zoom).  Writer is byte for
# byte 0.2.59's (shell generation 91, e2-editor-v33; nothing under sdk/ or editor-shell-v2/ changed), so its nets are not re-run
# (cadence item 5) and the gate reads 0.2.58's generation-91 records.  viewer-shell/ods-viewer-session.js gained setScale (scale
# stays 1 on the viewer page); the C net (check_calc_sheet_view.py) drives the viewer page too.
#   Calc: C, CU, cell, range, autosave, P2, headers, structure, sheets (0.2.59's nets), then the two features' page criteria on
#   dist: check_calc_copy.py --html (with the native paste harness, P-H4) and check_calc_zoom.py.
# Same steps as release-0.2.59/chain-0259.sh with v7 -> v8, names suffixed -0260 (mirror folders are build/calc-*/<name>).
# Add no file under sdk/, editor-shell-v2/, web/ or spreadsheet-shell/ while it runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/release-0.2.60
LOG=$E/chain-0260.log
echo $$ > $E/chain-0260.pid
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN ${name#$E/}"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END ${name#$E/} exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
C=$E/calc-v8
V8=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/dist/profiles/ods-editor-v8
NATIVE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/calc-v8/native-build-01/v8/calc-undo-native
step $C/calc-sheet-view-0260 python3 tools/check_calc_sheet_view.py --out $C/calc-sheet-view-0260
step $C/cu-0260 python3 tools/check_calc_undo_cu.py --engine $V8 --out $C/cu-0260
step $C/cell-0260 python3 tools/run_calc_editor_browser.py --profile $V8 --repeats 1 --out $C/cell-0260
step $C/range-0260 python3 tools/probe_calc_range_format.py --profile $V8 --repeats 1 --out $C/range-0260
step $C/auto-0260 python3 tools/probe_calc_autosave.py --repeats 1 --out $C/auto-0260
step $C/p2-0260 python3 tools/check_calc_style.py --engine $V8 --out $C/p2-0260
step $C/headers-0260 python3 tools/check_calc_headers.py --engine $V8 --out $C/headers-0260
step $C/structure-0260 python3 tools/check_calc_structure.py --engine $V8 --out $C/structure-0260
cd tools
step $C/sheets-0260 python3 check_calc_sheets.py --engine $V8 --out $C/sheets-0260
step $C/copy-html-0260 python3 check_calc_copy.py --html --engine $V8 --native-harness $NATIVE --out $C/copy-html-0260
step $C/zoom-0260 python3 check_calc_zoom.py --engine $V8 --out $C/zoom-0260
cd ..
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
