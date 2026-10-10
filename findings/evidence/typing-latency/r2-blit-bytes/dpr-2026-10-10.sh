#!/bin/bash
# R2 at devicePixelRatio 2 (not counted).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
D=../findings/evidence/typing-latency/r2-blit-bytes
P=$D/blit_bytes_probe.py
run() { # dpr arm browser gap chars
  flag=""; [ "$2" = skip ] && flag="--skip-stale"
  out=$D/dpr$1-$2-$3-owner-gap$4.json
  echo "== $(date -u +%FT%TZ) dpr $1 $2 $3 gap $4"
  timeout 900 python3 $P --page current --dpr $1 $flag --browser $3 --document owner --gap $4 --chars $5 --out $out 2>&1 | tail -2
  echo "exit ${PIPESTATUS[0]}"
}
for b in chrome firefox; do
  run 1 base $b 600 10
  run 2 base $b 600 10
  run 2 base $b 80 20
  run 2 skip $b 80 20
done
echo "== done $(date -u +%FT%TZ)"
