#!/bin/bash
# Spec §16.2 P1, 123-B (wrapper), P2 (counted probe dbad93c0, as is), P3 (wrapper, recorded) on the candidate
# page in dist/ (web/e2-editor-app.js after the 123 and P commits).  Predictions: spec §16.4 and §16.8.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
D=../findings/evidence/typing-latency/p-release
T=../findings/evidence/typing-latency
W=../findings/evidence/typing-latency/r2-blit-bytes/blit_bytes_probe.py
echo "== page $(sha256sum dist/e2-editor-app.js | cut -c1-16) wrapper $(sha256sum $W | cut -c1-16) probe $(sha256sum tools/probe_typing_latency.py | cut -c1-16)"
wrap() { # out browser args...
  out=$1; b=$2; shift 2
  echo "== $(date -u +%FT%TZ) wrapper $out $b $*"
  timeout 900 python3 $W --page current "$@" --browser $b --document owner --out $D/$out 2>&1 | tail -2 | cut -c1-400
  echo "exit ${PIPESTATUS[0]}"
}
probe() { # browser document gap chars slot
  echo "== $(date -u +%FT%TZ) probe $1 $5"
  timeout 900 python3 tools/probe_typing_latency.py --browser $1 --document $2 --gap $3 --chars $4 --out $T/p-candidate-$1-$5.json 2>&1 | tail -1 | cut -c1-400
  echo "exit ${PIPESTATUS[0]}"
}
for b in chrome firefox; do
  wrap candidate-$b-p1.json $b --gap 600 --chars 10
  win=800x1000; [ $b = firefox ] && win=797x1000
  wrap candidate-$b-123b.json $b --dpr 2 --window $win --gap 600 --chars 3
done
for b in chrome firefox; do
  probe $b owner 80 20 owner-gap80
  probe $b owner 200 10 owner-gap200
  probe $b boundaries 200 10 boundaries-gap200
done
for b in chrome firefox; do
  wrap p3-dpr15wide-$b-owner-gap80.json $b --dpr 1.5 --window 1400x1000 --gap 80 --chars 20
  wrap p3-dpr2narrow-$b-owner-gap80.json $b --dpr 2 --gap 80 --chars 20
  wrap p3-dpr2wide-$b-owner-gap80.json $b --dpr 2 --window 1400x1000 --gap 80 --chars 20
done
echo "== done $(date -u +%FT%TZ)"
