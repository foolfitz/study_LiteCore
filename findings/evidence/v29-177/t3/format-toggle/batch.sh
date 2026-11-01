#!/usr/bin/env bash
# The rates behind F3-83's moved cell, one profile and browser at a time, nothing else running.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore
D=findings/evidence/v29-177/t3/format-toggle
run() { local name=$1; shift; echo "$(date +%T) $name" >> $D/batch-log.txt; env "$@" >> $D/batch-log.txt 2>&1; }
run natural-v29-firefox python3 -I $D/repro.py e2-editor-v29 firefox 10 $D/runs/natural-v29-firefox.json
run natural-v28-firefox python3 -I $D/repro.py e2-editor-v28 firefox 10 $D/runs/natural-v28-firefox.json
run natural-v29-chrome  python3 -I $D/repro.py e2-editor-v29 chrome 10 $D/runs/natural-v29-chrome.json
run natural-v28-chrome  python3 -I $D/repro.py e2-editor-v28 chrome 10 $D/runs/natural-v28-chrome.json
run clear1-v29-firefox  CLEAR_MS=1 python3 -I $D/repro.py e2-editor-v29 firefox 10 $D/runs/clear1-v29-firefox.json
run clear1-v28-firefox  CLEAR_MS=1 python3 -I $D/repro.py e2-editor-v28 firefox 10 $D/runs/clear1-v28-firefox.json
echo "$(date +%T) DONE" >> $D/batch-log.txt
