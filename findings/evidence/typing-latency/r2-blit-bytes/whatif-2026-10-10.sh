#!/bin/bash
# R2 what-if chain (not counted).  Pairs: baseline, then --skip-stale, same session conditions.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
D=../findings/evidence/typing-latency/r2-blit-bytes
P=$D/blit_bytes_probe.py
for gap in 600 80; do
  chars=10; [ "$gap" = 80 ] && chars=20
  for browser in chrome firefox; do
    for arm in base skip; do
      flag=""; [ "$arm" = skip ] && flag="--skip-stale"
      out=$D/whatif-$arm-$browser-owner-gap$gap.json
      echo "== $(date -u +%FT%TZ) $arm $browser gap $gap"
      timeout 900 python3 $P --page current $flag --browser $browser --document owner --gap $gap --chars $chars --out $out 2>&1 | tail -2
      echo "exit ${PIPESTATUS[0]}"
    done
  done
done
echo "== done $(date -u +%FT%TZ)"
