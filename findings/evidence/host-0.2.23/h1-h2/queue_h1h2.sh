#!/bin/bash
# Task 10-15b: H1/H2 on host 0.2.23 -- one browser job at a time, a health check before each (exit 3 wallet locked, 4 ours running, 5 chrome check).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/scroll-page-bubble
H=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.23/h1-h2
LOG=$H/queue-log.txt
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
step() {
  local label=$1 browser=$2 doc=$3 arms=$4
  bash $H/health_h1h2.sh "$label" > /dev/null; rc=$?
  if [ $rc -ne 0 ]; then echo "[$label] $(ts) health STOP rc=$rc" >> $LOG; exit 2; fi
  echo "[$label] $(ts) start" >> $LOG
  timeout 900 python3 -I probe_bubble.py --out $H/$browser --browser $browser --doc $doc --arms $arms --mode host > $H/probe-$browser-$doc.out 2> $H/probe-$browser-$doc.err
  echo "[$label] $(ts) exit $?" >> $LOG
}
step H1-firefox-long60 firefox long60 bubble-wheel,bubble-reduce,bubble-drag,bubble-keys
step H1-firefox-blank firefox blank bubble-short
step H1-chrome-long60 chrome long60 bubble-wheel,bubble-reduce,bubble-drag,bubble-keys
step H1-chrome-blank chrome blank bubble-short
bash $H/health_h1h2.sh after-H1 > /dev/null
echo "[after] $(ts) done rc=$?" >> $LOG
