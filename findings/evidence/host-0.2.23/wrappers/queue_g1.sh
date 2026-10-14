#!/bin/bash
cd /home/jiajun/LibreOffice/study_LiteCore
S=/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/30f3fb46-c713-4ab4-a4a4-79969d084998/scratchpad
K=findings/evidence/host-0.2.23
PAGE=ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
$S/health.sh before-G1 || { echo "QUEUE-STOP health rc=$?"; exit 9; }
echo "=== G1 start $(ts)"; echo "$(ts)" > $K/g1-132b/started-utc-G1.txt
python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out $K/g1-132b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3 > $K/g1-132b/probe.out 2>&1
RC=$?; echo "probe exit $RC" >> $K/g1-132b/probe.out
echo "=== G1 end rc=$RC $(ts)"; echo "$(ts)" > $K/g1-132b/ended-utc-G1.txt
python3 -I $S/static_check.py $K/g1-132b/report.json > $K/g1-132b/static-check.txt 2>&1; echo "static-check rc=$?"; cat $K/g1-132b/static-check.txt
python3 findings/evidence/132/judge_132b.py --page $PAGE $K/g1-132b/report.json > $K/g1-132b/judge-output.txt 2>&1; JRC=$?
echo "\$ python3 findings/evidence/132/judge_132b.py --page $PAGE $K/g1-132b/report.json" | cat - $K/g1-132b/judge-output.txt > $K/g1-132b/judge-output.tmp && mv $K/g1-132b/judge-output.tmp $K/g1-132b/judge-output.txt
echo "exit $JRC" >> $K/g1-132b/judge-output.txt
echo "judge exit $JRC"; tail -5 $K/g1-132b/judge-output.txt
python3 findings/evidence/132/read_hold.py $K/g1-132b/report.json > $K/g1-132b/read_hold-output.txt 2>&1; echo "read_hold exit $?"
$S/health.sh after-G1
echo QUEUE-DONE
