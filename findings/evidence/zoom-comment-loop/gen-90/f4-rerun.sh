#!/usr/bin/env bash
# F4 of chain-90.sh again (cadence item 4: only that arm): both browsers refused at 15:03 on foreign CPU (another session's
# `make -j 2 ... CppunitTest_editeng_core ...` at 99 percent; f4-90/*/wrapper.json). Same commands, output under f4-90-r2/.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/zoom-comment-loop/gen-90
LOG=$E/chain-90.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START f4-rerun tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
F4=$E/f4-90-r2
for b in chrome firefox; do step $F4/$b-run python3 tools/run_four_arms.py --generation 90 --browser $b --out $F4/$b; done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_product_four_arms.py --generation 90 $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
say "DONE f4-rerun load $(cut -d' ' -f1-3 /proc/loadavg)"
