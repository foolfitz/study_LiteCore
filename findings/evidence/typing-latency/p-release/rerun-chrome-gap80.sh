#!/bin/bash
# P2's Chrome owner-gap80, re-run alone (the first run overlapped a static-test compile; README).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
T=../findings/evidence/typing-latency
echo "== page $(sha256sum dist/e2-editor-app.js | cut -c1-16) probe $(sha256sum tools/probe_typing_latency.py | cut -c1-16)"
echo "== $(date -u +%FT%TZ) probe chrome owner-gap80 (re-run)"
timeout 900 python3 tools/probe_typing_latency.py --browser chrome --document owner --gap 80 --chars 20 --out $T/p-candidate-chrome-owner-gap80.json 2>&1 | tail -1 | cut -c1-400
echo "exit ${PIPESTATUS[0]}"
echo "== done $(date -u +%FT%TZ)"
