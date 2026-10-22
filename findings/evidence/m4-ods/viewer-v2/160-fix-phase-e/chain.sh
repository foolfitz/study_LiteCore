#!/usr/bin/env bash
# Phase E from zero on ods-viewer-v2 aa576ce7 (SPEC-M4-viewer-v2 8.3): the targeted run, E6 (record-only,
# SPEC-M4 addendum 12) with B, the full corpus x3, then V2-160-D over the three.  Every runner gets --out.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 2
D=../findings/evidence/m4-ods/viewer-v2/160-fix-phase-e
log() { echo "$(date -Is) $*" >> "$D/chain.txt"; }
mkdir -p "$D/targeted" "$D/e6" "$D/full-corpus"
log "start; probe.wasm $(sha256sum dist/profiles/ods-viewer-v2/probe.wasm | cut -c1-8)"
python3 tools/run_ods_viewer_phase_e.py --profile ods-viewer-v2 --out "$D/targeted" \
  --only ladder/ --only upstream/fdo67682-2.ods --only upstream/date-time-functions.ods --only upstream/functions.ods \
  --only upstream/move-cell-anchored-shapes.ods --only upstream/tdf106181.ods --only upstream/tdf121963.ods \
  --only upstream/tdf134161.ods --only upstream/tdf154005.ods --only upstream/tdf138507.ods > "$D/targeted/stdout.txt" 2>&1
log "targeted exit $?"
python3 tools/run_ods_viewer_e6_leak.py --profile ods-viewer-v2 --out "$D/e6" > "$D/e6/stdout.txt" 2>&1
log "e6 exit $?"
for i in 1 2 3; do
  python3 tools/run_ods_viewer_phase_e.py --profile ods-viewer-v2 --out "$D/full-corpus" > "$D/full-corpus/run-$i.txt" 2>&1
  log "full corpus run $i exit $?"
done
python3 -I tools/judge_v2_160_d.py "$D"/full-corpus/report-*.json > "$D/full-corpus/v2-160-d.jsonl" 2>&1
log "V2-160-D exit $?"
log DONE
