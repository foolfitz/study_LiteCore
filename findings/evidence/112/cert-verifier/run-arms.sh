#!/usr/bin/env bash
# PREDICTION.md's arms, one launch at a time: E1 (runner flags) x3, E2 (+ --disable-component-update) x2.
set -u
cd "$(dirname "$0")" || exit 9
for L in e1-1 e1-2 e1-3; do
  python3 -I probe_cert_verifier.py --label $L --out $L.json >> runs.log 2>&1; echo "$(date -u +%FT%TZ) $L exit $?" >> runs.log
done
for L in e2-1 e2-2; do
  python3 -I probe_cert_verifier.py --label $L --disable-component-update --out $L.json >> runs.log 2>&1; echo "$(date -u +%FT%TZ) $L exit $?" >> runs.log
done
echo "$(date -u +%FT%TZ) DONE" >> runs.log
