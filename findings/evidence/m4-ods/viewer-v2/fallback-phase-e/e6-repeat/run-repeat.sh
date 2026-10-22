#!/usr/bin/env bash
# Five E6 runs per profile, alternating (diagnostic; README.md).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 2
D=../findings/evidence/m4-ods/viewer-v2/fallback-phase-e/e6-repeat
for i in 1 2 3 4 5; do
  for p in ods-viewer-v2 ods-viewer-v1; do
    mkdir -p "$D/$p"
    python3 tools/run_ods_viewer_e6_leak.py --profile "$p" --bound 0 --out "$D/$p" > "$D/$p/run-$i.txt" 2>&1
    echo "$(date -Is) $p run $i exit $?" >> "$D/runs.txt"
  done
done
echo DONE >> "$D/runs.txt"
