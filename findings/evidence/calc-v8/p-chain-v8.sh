#!/usr/bin/env bash
# After p-zoom-02 (P_HOLDS): the zoom page red cases (Chrome, as p-red-anchor-only was), copy's P again on the final page
# (the Codex fixes touched the copy path: a copy generation) with its red case, then the Calc regression on v8.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools || exit 9
E=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/calc-v8
ENGINE=../build/ods/editor-v8/profile
NATIVE=$E/native-build-01/v8/calc-undo-native
LOG=$E/p-chain-v8.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
run() { local name=$1; shift; say "BEGIN $name"; timeout 2400 python3 "$@" > $E/$name.stdout.txt 2> $E/$name.stderr.txt; local rc=$?; echo $rc > $E/$name.exit.txt; say "END $name exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
for m in point-15 no-op16 no-centre drag-no-zoom; do
  run p-zoom-red-$m check_calc_zoom.py --out $E/p-zoom-red-$m --engine $ENGINE --browsers chrome --mutate $m
done
run p-copy-04 check_calc_copy.py --html --out $E/p-copy-04 --engine $ENGINE --native-harness $NATIVE
run p-copy-red-plain-only-2 check_calc_copy.py --html --mutate plain-only --browsers chrome --out $E/p-copy-red-plain-only-2 --engine $ENGINE --native-harness $NATIVE
say "BEGIN regression"
bash $E/regression/chain-v8.sh > $E/regression/chain-v8.stdout.txt 2>&1
say "END regression exit=$?"
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
