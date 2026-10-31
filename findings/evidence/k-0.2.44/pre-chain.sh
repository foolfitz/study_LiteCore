#!/usr/bin/env bash
# Spec K-0.2.44 section 5, on the mirror: the page-gate negative, the Enter replay on v28, a one-round merge smoke through the wrapper.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
E=../findings/evidence/k-0.2.44
python3 $E/probe-legacy-v8-gate.py --out $E/legacy-v8-gate > $E/legacy-v8-gate.stdout.txt 2> $E/legacy-v8-gate.stderr.txt; echo $? > $E/legacy-v8-gate.exit.txt
python3 -I tools/check_v24_shift_enter.py --out $E/enter-replay --repetitions 3 > $E/enter-replay.stdout.txt 2> $E/enter-replay.stderr.txt; echo $? > $E/enter-replay.exit.txt
mkdir -p $E/merge-smoke
python3 tools/run_k_0244_merge.py --browser chrome --candidate-profile e2-editor-v28 --out $E/merge-smoke/shakedown-chrome.json > $E/merge-smoke/stdout.txt 2> $E/merge-smoke/stderr.txt; echo $? > $E/merge-smoke/exit.txt
