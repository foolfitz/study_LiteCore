#!/bin/sh
# SPEC-P-calc-structure 4.2: P on the relinked dev profile, the three page reds (Chrome), and P-S8 (the headers P).
cd "$(dirname "$0")/../../../wasm_sdk_probe/tools" || exit 2
E=../../findings/evidence/calc-structure
ENGINE=../build/ods/editor-v6/profile
run() { name=$1; shift; python3 "$@" > $E/$name.stdout.txt 2> $E/$name.stderr.txt; echo $? > $E/$name.exit.txt; }
run p-01 check_calc_structure.py --out $E/p-01 --engine $ENGINE
for m in above-index-plus-1 count-one no-reason-title; do
  run p-red-$m check_calc_structure.py --out $E/p-red-$m --engine $ENGINE --browsers chrome --mutate $m
done
run p-s8-headers check_calc_headers.py --out $E/p-s8-headers --engine $ENGINE
