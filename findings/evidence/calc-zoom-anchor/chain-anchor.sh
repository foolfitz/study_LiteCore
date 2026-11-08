#!/usr/bin/env bash
# SPEC-P-calc-zoom append 5 (the zoom anchors on the active cell's top-left, else the view's top-left): the page change's first
# P run on the frozen engine dist/profiles/ods-editor-v8, both browsers, then its two red cases in Chrome (centre-anchor ->
# P-Z5, fallback-centre -> P-Z10).  Page only; no link.  Add no file under web/ or spreadsheet-shell/ while it runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools || exit 9
E=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/calc-zoom-anchor
ENGINE=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/dist/profiles/ods-editor-v8
LOG=$E/chain-anchor.log
echo $$ > $E/chain-anchor.pid
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
run() { local name=$1; shift; say "BEGIN $name"; timeout 2400 python3 "$@" > $E/$name.stdout.txt 2> $E/$name.stderr.txt; local rc=$?; echo $rc > $E/$name.exit.txt; say "END $name exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) dirty $(git status --porcelain -- ../web ../tools | wc -l) load $(cut -d' ' -f1-3 /proc/loadavg)"
run p-anchor-01 check_calc_zoom.py --out $E/p-anchor-01 --engine $ENGINE
for m in centre-anchor fallback-centre; do
  run p-anchor-red-$m check_calc_zoom.py --out $E/p-anchor-red-$m --engine $ENGINE --browsers chrome --mutate $m
done
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
