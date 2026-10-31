#!/usr/bin/env bash
# Spec v28 append 2: the five cells on generation 82, frame-char-last on generation 81, the positive control, the self-test.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
E=../findings/evidence/v28-083/a-frames
T=tools/check_v82_frame_last_line.py
python3 -I $T --out $E/run-01 > $E/run-01.stdout.txt 2> $E/run-01.stderr.txt; echo $? > $E/run-01.exit.txt
python3 -I $T --product before --cells frame-char-last --out $E/before-frame-char-last > $E/before-frame-char-last.stdout.txt 2> $E/before-frame-char-last.stderr.txt; echo $? > $E/before-frame-char-last.exit.txt
python3 -I $T --mutation swallow-press --out $E/control-swallow-press > $E/control-swallow-press.stdout.txt 2> $E/control-swallow-press.stderr.txt; echo $? > $E/control-swallow-press.exit.txt
python3 -I $T --self-test $E/run-01/report.json > $E/self-test-01.json 2> $E/self-test-01.stderr.txt; echo $? > $E/self-test-01.exit.txt
