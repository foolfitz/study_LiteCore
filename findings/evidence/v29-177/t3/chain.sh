#!/usr/bin/env bash
# T3 then T4 (SPEC-M3-v29-tick-pacing section 6, append 2), mirror only, no ddev.  Not timing: the desk need not be clean.  Every
# step runs even if an earlier one is red: the point is the whole list of reds, once.  V0' runs separately afterwards.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/v29-177
LOG=$E/t3/chain-log.txt
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() {  # name-with-path, command...
  local name=$1; shift
  mkdir -p "$(dirname "$name")"
  say "BEGIN $(basename "$name") :: $*"
  "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"
  local rc=$?
  echo "exit=$rc" > "$name.exit.txt"
  say "END   $(basename "$name") exit $rc"
}
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"

# 1. Either side of the 300 ms grace: the change's own risk first.
G=$E/t3/typing-gap
for rep in 1 2 3; do for gap in 290 310; do for b in chrome firefox; do for d in boundaries owner; do
  r=$G/runs/$b-$d-gap$gap-r$rep
  step "$r" python3 -I $G/gap_order.py run $b $d $gap 20 "$r.json"
done; done; done; done

# 2. Merge through the K wrapper.
M=$E/t3/merge
P=e2-editor-v29
step $M/full-chrome-run  python3 tools/run_v83_merge.py --browser chrome  --candidate-profile $P --out $M/full-chrome.json
step $M/full-firefox-run python3 tools/run_v83_merge.py --browser firefox --candidate-profile $P --out $M/full-firefox.json
step $M/instrumented-run python3 tools/run_v83_merge.py --browser chrome --candidate-profile $P --cases C01,C15,C29 --out $M/instrumented.json
step $M/control-run      python3 tools/run_v83_merge.py --browser chrome --candidate-profile $P --cases C01,C15,C29 --control --out $M/control.json
step $M/pair             python3 tools/run_v83_merge.py --pair $M/instrumented.json $M/control.json
step $M/m2-4-run         python3 tools/run_v83_merge.py --browser chrome  --candidate-profile $P --mode m2-4 --out $M/m2-4.json
step $M/m2-1b-run        python3 tools/run_v83_merge.py --browser firefox --candidate-profile $P --mode m2-1b --out $M/m2-1b.json

# 3. T4, three pairs.
H=$E/t4
for r in 1 2 3; do
  step $H/run-0$r/subject-run python3 -I $H/heap_during_typing.py run subject $H/run-0$r/subject.json
  step $H/run-0$r/red-run     python3 -I $H/heap_during_typing.py run red     $H/run-0$r/red.json
done

# 4. F4-83 and F3-83.
F4=$E/f4-83; F3=$E/f3-83
mkdir -p $F3/run-01
for b in chrome firefox; do
  step $F4/$b-run python3 tools/run_v83_four_arms.py --browser $b --out $F4/$b
done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_v83_product_four_arms.py $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
for b in chrome firefox; do
  step $F3/run-01/$b python3 tools/run_v83_f3_clipboard.py --browser $b --out $F3/run-01/$b
done
step $F3/equal-01 python3 tools/read_v83_f3_equal.py --v83 $F3/run-01
step $F3/equal-01-self-test python3 tools/read_v83_f3_equal.py --v83 $F3/run-01 --self-test
step $F3/read-01 python3 tools/read_v25_f3.py --v25 $F3/run-01

# 5. S4 on v29.
S=$E/s4
C=tools/check_v83_last_line_bullet.py
mkdir -p $S
step $S/run-01-run python3 -I $C --out $S/run-01
for m in press-list-none cosmetic-review wrong-button-b-number wrong-button-b-none wrong-button-b-heading wrong-button-b-body; do
  step $S/mutation-$m-run python3 -I $C --mutation $m --out $S/mutation-$m
done
step $S/self-test-01 python3 -I $C --self-test $S/run-01/report.json
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
