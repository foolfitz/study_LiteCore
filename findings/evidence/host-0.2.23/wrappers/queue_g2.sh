#!/bin/bash
cd /home/jiajun/LibreOffice/study_LiteCore
S=/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/30f3fb46-c713-4ab4-a4a4-79969d084998/scratchpad
K=findings/evidence/host-0.2.23
D=$K/g2-burst1s
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
for B in firefox chrome; do
  $S/health.sh before-G2-$B || { echo "QUEUE-STOP health rc=$?"; exit 9; }
  echo "=== G2 $B start $(ts)"; echo "$(ts)" > $D/started-utc-G2-$B.txt
  python3 findings/evidence/host-0.2.21/probe_10_14o.py --out $D --browser $B --doc long60 --arms burst-1s,page-number --mode host > $D/probe-$B.out 2>&1
  RC=$?; echo "probe exit $RC" >> $D/probe-$B.out
  echo "=== G2 $B end rc=$RC $(ts)"; echo "$(ts)" > $D/ended-utc-G2-$B.txt
done
python3 -I $S/static_check.py $D/report-host-firefox-long60.json $D/report-host-chrome-long60.json > $D/static-check.txt 2>&1; echo "static-check rc=$?"; cat $D/static-check.txt
echo "\$ python3 -I findings/evidence/host-0.2.21/judge_k.py --k2 $D --k4 $D" > $D/judge-k-output.txt
python3 -I findings/evidence/host-0.2.21/judge_k.py --k2 $D --k4 $D >> $D/judge-k-output.txt 2>&1; JRC=$?; echo "exit $JRC" >> $D/judge-k-output.txt
echo "judge_k exit $JRC"; cat $D/judge-k-output.txt
echo "\$ python3 -I findings/evidence/host-0.2.21/judge_k.py --red-check" > $D/judge-k-red-check-output.txt
python3 -I findings/evidence/host-0.2.21/judge_k.py --red-check >> $D/judge-k-red-check-output.txt 2>&1; echo "exit $?" >> $D/judge-k-red-check-output.txt
tail -3 $D/judge-k-red-check-output.txt
$S/health.sh after-G2
echo QUEUE-DONE
