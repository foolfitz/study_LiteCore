#!/bin/bash
# Fable's fifth ruling, Part 5 items 1 and 3 (not counted).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
D=../findings/evidence/typing-latency/r2-blit-bytes
for b in chrome firefox; do
  echo "== $(date -u +%FT%TZ) small bench $b"
  timeout 900 python3 $D/canvas-bench/run_bench.py --small --browser $b --out $D/canvas-bench/bench-small-$b.json > /dev/null 2>&1
  echo "exit $?"
done
for b in chrome firefox; do
  for arm in base skip; do
    flag=""; [ "$arm" = skip ] && flag="--skip-stale"
    echo "== $(date -u +%FT%TZ) dpr 1.5 wide $arm $b gap 80"
    timeout 900 python3 $D/blit_bytes_probe.py --page current --dpr 1.5 --window 1400x1000 $flag --browser $b --document owner --gap 80 --chars 20 --out $D/dpr15-$arm-$b-owner-gap80.json 2>&1 | tail -2
    echo "exit ${PIPESTATUS[0]}"
  done
done
echo "== done $(date -u +%FT%TZ)"
