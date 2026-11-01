#!/usr/bin/env bash
# Spec K-0.2.45 section 6, on the mirror: the page-gate negative, the Enter replay on v29, a one-round merge smoke through the wrapper,
# and one round of the K product-path runner per browser (the two replacements have never run together, spec section 4).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/k-0.2.45
L=$E/pre-chain-log.txt
step() { local name=$1; shift; echo "$(date +%FT%T%z) BEGIN $name" >> $L; "$@" > $E/$name.stdout.txt 2> $E/$name.stderr.txt; local rc=$?; echo $rc > $E/$name.exit.txt; echo "$(date +%FT%T%z) END $name exit $rc" >> $L; }
mkdir -p $E/merge-smoke $E/path-smoke
step legacy-v8-gate python3 $E/probe-legacy-v8-gate.py --out $E/legacy-v8-gate
step enter-replay python3 -I tools/check_v83_shift_enter.py --out $E/enter-replay --repetitions 3
step merge-smoke-run python3 tools/run_k_0245_merge.py --browser chrome --candidate-profile e2-editor-v29 --out $E/merge-smoke/shakedown-chrome.json
step path-smoke-firefox python3 tools/run_k_0245_path.py --browser firefox --out $E/path-smoke/firefox
step path-smoke-chrome python3 tools/run_k_0245_path.py --browser chrome --out $E/path-smoke/chrome
echo "$(date +%FT%T%z) DONE" >> $L
