#!/bin/bash
# Spec §16.8: Firefox's 123-B red case at 797x1000 on the shipped page (dist/ = 18c8afbe...); not counted.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
D=../findings/evidence/typing-latency/p-release
P=../findings/evidence/typing-latency/r2-blit-bytes/blit_bytes_probe.py
echo "== page $(sha256sum dist/e2-editor-app.js | cut -c1-16) wrapper $(sha256sum $P | cut -c1-16)"
echo "== $(date -u +%FT%TZ) 123b firefox 797x1000"
timeout 900 python3 $P --page current --dpr 2 --window 797x1000 --browser firefox --document owner --gap 600 --chars 3 --out $D/shipped-firefox-123b.json 2>&1 | tail -2
echo "exit ${PIPESTATUS[0]}"
echo "== done $(date -u +%FT%TZ)"
