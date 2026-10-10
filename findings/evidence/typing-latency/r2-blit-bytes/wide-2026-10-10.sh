#!/bin/bash
# R2 at ratio 2 in a 1400x1000 CSS window (not counted).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
D=../findings/evidence/typing-latency/r2-blit-bytes
P=$D/blit_bytes_probe.py
run() { # arm browser gap chars
  flag=""; [ "$1" = skip ] && flag="--skip-stale"
  out=$D/wide-$1-$2-owner-gap$3.json
  echo "== $(date -u +%FT%TZ) wide $1 $2 gap $3"
  timeout 900 python3 $P --page current --dpr 2 --window 1400x1000 $flag --browser $2 --document owner --gap $3 --chars $4 --out $out 2>&1 | tail -2
  echo "exit ${PIPESTATUS[0]}"
}
for b in chrome firefox; do
  run base $b 600 10
  run base $b 80 20
  run skip $b 80 20
done
echo "== done $(date -u +%FT%TZ)"
