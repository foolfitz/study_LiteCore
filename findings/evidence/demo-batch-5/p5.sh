#!/usr/bin/env bash
# P5, then its red case on generation 87's page.  The run reads the page from web/, the mirror's assets from dist/.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/demo-batch-5/p5
python3 -I tools/check_writer_enter_range.py --out $E/run-01 > $E/run-01.stdout.txt 2> $E/run-01.stderr.txt; echo "run-01 exit=$?"
python3 -I tools/check_writer_enter_range.py --page-rev 1e4f2b3b7 --only E1,E7 --out $E/red-on-generation-87 > $E/red.stdout.txt 2> $E/red.stderr.txt; echo "red exit=$?"
tail -3 $E/run-01.stderr.txt | cut -c1-700; tail -3 $E/red.stderr.txt | cut -c1-700
