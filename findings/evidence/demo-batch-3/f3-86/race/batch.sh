#!/usr/bin/env bash
# The rate behind F3-86's moved cell: finding 178's repro, unchanged, same shell and page on the two engines, one browser at a time.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore
R=findings/evidence/v29-177/t3/format-toggle/repro.py
D=findings/evidence/demo-batch-3/f3-86/race
run() { local name=$1; shift; echo "$(date +%T) $name" >> $D/batch-log.txt; env "$@" >> $D/batch-log.txt 2>&1; }
run natural-v31-firefox python3 -I $R e2-editor-v31 firefox 10 $D/natural-v31-firefox.json
run natural-v30-firefox python3 -I $R e2-editor-v30 firefox 10 $D/natural-v30-firefox.json
run natural-v31-chrome  python3 -I $R e2-editor-v31 chrome 10 $D/natural-v31-chrome.json
echo "$(date +%T) DONE" >> $D/batch-log.txt
