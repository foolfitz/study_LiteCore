#!/usr/bin/env bash
# ods-editor-v8 (dev profile, wasm 61e2a069): the Calc nets of the 0.2.59 release regression (release-0.2.59/chain-0259.sh),
# serial, both browsers, on build/ods/editor-v8/profile instead of dist v7.  The page changed every twips/px conversion for
# zoom (SPEC-P-calc-zoom 3.3), so every Calc net runs, not only sheets/headers/structure.  Copy is not repeated here: it is
# p-copy-03 (P_HOLDS, with P-C1..P-C5).  check_calc_sheet_view.py and probe_calc_autosave.py take no engine: they load the
# page's own engine (frozen v7 / v1 from dist), i.e. the new page on an old engine.
# Add no file under sdk/, editor-shell-v2/, web/ or spreadsheet-shell/ while it runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/calc-v8/regression
LOG=$E/chain-v8.log
echo $$ > $E/chain-v8.pid
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN ${name#$E/}"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END ${name#$E/} exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
V8=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/ods/editor-v8/profile
step $E/calc-sheet-view python3 tools/check_calc_sheet_view.py --out $E/calc-sheet-view
step $E/cu python3 tools/check_calc_undo_cu.py --engine $V8 --out $E/cu
step $E/cell python3 tools/run_calc_editor_browser.py --profile $V8 --repeats 1 --out $E/cell
step $E/range python3 tools/probe_calc_range_format.py --profile $V8 --repeats 1 --out $E/range
step $E/auto python3 tools/probe_calc_autosave.py --repeats 1 --out $E/auto
step $E/p2 python3 tools/check_calc_style.py --engine $V8 --out $E/p2
step $E/headers python3 tools/check_calc_headers.py --engine $V8 --out $E/headers
step $E/structure python3 tools/check_calc_structure.py --engine $V8 --out $E/structure
cd tools
step $E/sheets python3 check_calc_sheets.py --engine $V8 --out $E/sheets
cd ..
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
