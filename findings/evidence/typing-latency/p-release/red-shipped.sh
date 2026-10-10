#!/bin/bash
# Spec §16.3 red cases for P1 and 123-B on the shipped page (dist/ = 18c8afbe...); not counted.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
D=../findings/evidence/typing-latency/p-release
P=../findings/evidence/typing-latency/r2-blit-bytes/blit_bytes_probe.py
echo "== page $(sha256sum dist/e2-editor-app.js | cut -c1-16) wrapper $(sha256sum $P | cut -c1-16)"
for b in chrome firefox; do
  echo "== $(date -u +%FT%TZ) p1 $b"
  timeout 900 python3 $P --page current --browser $b --document owner --gap 600 --chars 10 --out $D/shipped-$b-p1.json 2>&1 | tail -2
  echo "exit ${PIPESTATUS[0]}"
  echo "== $(date -u +%FT%TZ) 123b $b"
  timeout 900 python3 $P --page current --dpr 2 --window 800x1000 --browser $b --document owner --gap 600 --chars 3 --out $D/shipped-$b-123b.json 2>&1 | tail -2
  echo "exit ${PIPESTATUS[0]}"
done
echo "== done $(date -u +%FT%TZ)"
