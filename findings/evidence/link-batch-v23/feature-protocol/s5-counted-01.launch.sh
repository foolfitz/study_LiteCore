#!/bin/bash
# Detached launcher for the first counted S5 run, then its independent aggregate judge.
# Runner output goes to a sibling log first (the runner refuses an existing output directory),
# then is moved into the cohort directory together with the judge output and a receipt.
set -u
SDK=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
REL=../findings/evidence/link-batch-v23/feature-protocol
OUT=$REL/s5-counted-01
LOG=$SDK/$REL/s5-counted-01.runner-log.txt
cd "$SDK" || exit 9
HEAD=$(git rev-parse HEAD)
START=$(date '+%FT%T%:z'); T0=$(date +%s.%N)
{ uptime; date '+%FT%T%:z'; } > "$LOG"
python3 -I tools/run_v23_feature_selection.py --population s5 \
  --pre-red-report ../findings/evidence/link-batch-v23/feature-pre-red/counted-05/report.json \
  --output "$OUT" >> "$LOG" 2>&1
RC=$?
T1=$(date +%s.%N)
echo "exit=$RC $(date '+%FT%T%:z')" >> "$LOG"
if [ -d "$OUT" ]; then
  mv "$LOG" "$OUT/runner.command-output.txt"
  python3 -I tools/judge_v23_feature_selection.py "$OUT/report.json" > "$OUT/aggregate-judge.stdout.json" 2> "$OUT/aggregate-judge.stderr.txt"
  JRC=$?
  python3 -I - "$OUT/commands.json" "$START" "$HEAD" "$RC" "$T0" "$T1" "$JRC" <<'EOF'
import json,sys
path,start,head,rc,t0,t1,jrc=sys.argv[1:]
rel='../findings/evidence/link-batch-v23/feature-protocol/s5-counted-01'
json.dump({'runner':{'argv':['python3','-I','tools/run_v23_feature_selection.py','--population','s5','--pre-red-report',
  '../findings/evidence/link-batch-v23/feature-pre-red/counted-05/report.json','--output',rel],
  'cwd':'/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe','launch':'setsid nohup (detached)','startedAt':start,
  'gitHead':head,'exitCode':int(rc),'wallSeconds':round(float(t1)-float(t0),1)},
  'aggregateJudge':{'argv':['python3','-I','tools/judge_v23_feature_selection.py',rel+'/report.json'],
  'cwd':'/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe','exitCode':int(jrc),'gitHead':head}},open(path,'x'),indent=1)
EOF
fi
