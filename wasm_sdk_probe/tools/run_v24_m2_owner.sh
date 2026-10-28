#!/usr/bin/env bash
# SPEC-M3-link-batch-v24 6.3 M2, run by the owner (2026-10-28, owner chose B).
# Browser only: no make, no ddev, no host.  About 75 minutes.  Takes no arguments.
#
#   cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/run_v24_m2_owner.sh
#
# Writes only findings/evidence/link-batch-v24/pre-count/m2/run-01/ (refuses if it exists) and two
# files beside it (the runner log and the reader's output).  Prints one line per cell, then the
# reader's summary.  Nothing is retried; a nonpassing cell is recorded and the run goes on.
set -uo pipefail
cd "$(dirname "$0")/.."
EVIDENCE=../findings/evidence/link-batch-v24/pre-count/m2
OUT=$EVIDENCE/run-01
for path in "$OUT" "$OUT.runner.txt" "$OUT.reader.json"; do
  if [ -e "$path" ]; then echo "refusing: $path already exists" >&2; exit 2; fi
done
start=$(date -Iseconds)
python3 tools/run_v24_feature_selection.py --output "$OUT" --population s5-type --keep-going 2>&1 | tee "$OUT.runner.txt"
runner=${PIPESTATUS[0]}
echo "runner exit $runner ($start -> $(date -Iseconds))" | tee -a "$OUT.runner.txt"
python3 -I tools/judge_v24_feature_selection.py "$OUT/report.json" > "$OUT.reader.json"
reader=$?
echo "reader exit $reader" | tee -a "$OUT.runner.txt"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(json.dumps({"verdict": r["verdict"], **r["summary"]}, ensure_ascii=False))' "$OUT.reader.json" | tee -a "$OUT.runner.txt"
