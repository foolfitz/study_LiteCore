#!/usr/bin/env bash
# SPEC-P-ms-formats step 4 (W4, Calc): the Calc page switched to the frozen ods-editor-v5, its regression nets, serial, both browsers.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/ms-formats/calc-after-freeze
V5=dist/profiles/ods-editor-v5
LOG=$E/chain.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
step $E/calc-sheet-view-v5 python3 tools/check_calc_sheet_view.py --out $E/calc-sheet-view-v5
step $E/cu-v5 python3 tools/check_calc_undo_cu.py --engine $V5 --out $E/cu-v5
step $E/cell-v5 python3 tools/run_calc_editor_browser.py --profile $V5 --repeats 1 --out $E/cell-v5
step $E/range-v5 python3 tools/probe_calc_range_format.py --profile $V5 --repeats 1 --out $E/range-v5
step $E/auto python3 tools/probe_calc_autosave.py --repeats 1 --out $E/auto
step $E/p2-v5 python3 tools/check_calc_style.py --engine $V5 --out $E/p2-v5
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
