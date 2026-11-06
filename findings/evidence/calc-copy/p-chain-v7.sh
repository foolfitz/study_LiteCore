#!/bin/sh
# SPEC-P-calc-copy 4.2: the page red case (Chrome), then the Calc page criteria already held on v6, rerun on the new link
# (ods-editor-v7, wasm 36d0e1b8) as its regression: sheets (SPEC-P-calc-sheets), headers, structure.
cd "$(dirname "$0")/../../../wasm_sdk_probe/tools" || exit 2
E=../../findings/evidence/calc-copy
ENGINE=../build/ods/editor-v7/profile
mkdir -p $E/v7-regression
run() { name=$1; shift; python3 "$@" > $E/$name.stdout.txt 2> $E/$name.stderr.txt; echo $? > $E/$name.exit.txt; }
run p-red-anchor-only check_calc_copy.py --out $E/p-red-anchor-only --engine $ENGINE --browsers chrome --mutate anchor-only
run v7-regression/sheets check_calc_sheets.py --out $E/v7-regression/sheets --engine $ENGINE
run v7-regression/headers check_calc_headers.py --out $E/v7-regression/headers --engine $ENGINE
run v7-regression/structure check_calc_structure.py --out $E/v7-regression/structure --engine $ENGINE
echo done
