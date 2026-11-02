#!/usr/bin/env bash
# Spec append 1: everything that reads the HTML, again on the final HTML.  Serial; V0' last, alone, because it swaps files under dist/.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/demo-batch-1
LOG=$E/chain-84b.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
Z=$E/writer-zoom
step $Z/run-02-log python3 -I tools/check_writer_zoom.py --out $Z/run-02
for m in no-side-follow no-centre no-flex-none stretched; do step $Z/mutation-02-$m-log python3 -I tools/check_writer_zoom.py --out $Z/mutation-02-$m --browsers chrome --mutation $m; done
F4=$E/f4-84-final
for b in chrome firefox; do step $F4/$b-run python3 tools/run_v84_four_arms.py --browser $b --out $F4/$b; done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_v84_product_four_arms.py $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
F3=$E/f3-84-final
mkdir -p $F3/baseline-f3-83
ln -sfn ../../../v29-177/f3-83/diag-single-press/chrome-1 $F3/baseline-f3-83/chrome
ln -sfn ../../../v29-177/f3-83/diag-single-press/firefox-1 $F3/baseline-f3-83/firefox
for b in chrome firefox; do step $F3/run-01/$b python3 tools/run_v84_f3_clipboard.py --browser $b --out $F3/run-01/$b; done
step $F3/equal python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83
step $F3/equal-self-test python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --baseline $F3/baseline-f3-83 --self-test
step $E/v0-02/run python3 -I $E/v0-02/run_v0_prime.py
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
