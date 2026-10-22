#!/usr/bin/env bash
# RULING-fable-1 section 3 (Option A, owner: run it): one-cell-a1, 20 cycles, record-only, six runs per link,
# alternating v2/v1, then stop whatever they show.  Start only after the full-corpus x3 run is done.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 2
D=../findings/evidence/m4-ods/viewer-v2/fallback-phase-e/e6-repeat/cycles-20
grep -q DONE ../findings/evidence/m4-ods/viewer-v2/fallback-phase-e/full-corpus/runs.txt 2>/dev/null \
  || { echo "STOP: the full-corpus run is not done"; exit 3; }
for i in 1 2 3 4 5 6; do
  for p in ods-viewer-v2 ods-viewer-v1; do
    mkdir -p "$D/$p"
    python3 tools/run_ods_viewer_e6_leak.py --profile "$p" --entries ladder/one-cell-a1.ods --cycles 20 \
      --out "$D/$p" > "$D/$p/run-$i.txt" 2>&1
    echo "$(date -Is) $p run $i exit $?" >> "$D/runs.txt"
  done
done
echo DONE >> "$D/runs.txt"
