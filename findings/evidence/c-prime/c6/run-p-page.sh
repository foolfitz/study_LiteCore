#!/usr/bin/env bash
# C6 on the P page: red documents and controls, both browsers, one at a time.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
E=findings/evidence/c-prime/c6
P=wasm_sdk_probe/tools/probe_c6_long_document.py
echo "$(date -u +%FT%TZ) START page $(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-16) probe $(sha256sum $P | cut -c1-16)"
for B in chrome firefox; do
  for spec in "40 2" "24 2" "50 1.5" "33 1.5"; do
    set -- $spec
    out=$E/p-page-$B-$(printf %02d $1)p-dpr$2-1400x1000.json
    timeout 900 python3 $P --browser $B --pages $1 --dpr $2 --window 1400x1000 --out $out > $out.stdout.txt 2>&1
    echo "$(date -u +%FT%TZ) $B $1p dpr$2 exit $? :: $(tail -1 $out.stdout.txt | cut -c1-260)"
  done
done
echo "$(date -u +%FT%TZ) DONE"
