#!/usr/bin/env bash
# V2-160 (SPEC-M4-viewer-v2 4): the full corpus three times on ods-viewer-v2 e96e01ec.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 2
D=../findings/evidence/m4-ods/viewer-v2/fallback-phase-e/full-corpus
for i in 1 2 3; do
  python3 tools/run_ods_viewer_phase_e.py --profile ods-viewer-v2 --out "$D" > "$D/run-$i.txt" 2>&1
  echo "$(date -Is) run $i exit $?" >> "$D/runs.txt"
done
echo DONE >> "$D/runs.txt"
