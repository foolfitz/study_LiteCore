#!/bin/bash
# R2/R1 diagnostic chain (not counted).  Sequential; one browser at a time.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
D=../findings/evidence/typing-latency/r2-blit-bytes
P=$D/blit_bytes_probe.py
for gap in 600 80; do
  chars=10; [ "$gap" = 80 ] && chars=20
  for browser in chrome firefox; do
    for page in v58 current; do
      out=$D/r2-$page-$browser-owner-gap$gap.json
      echo "== $(date -u +%FT%TZ) $page $browser gap $gap"
      timeout 900 python3 $P --page $page --browser $browser --document owner --gap $gap --chars $chars --out $out 2>&1 | tail -2
      echo "exit ${PIPESTATUS[0]}"
    done
  done
done
echo "== done $(date -u +%FT%TZ)"
