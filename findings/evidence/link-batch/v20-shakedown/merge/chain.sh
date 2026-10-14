#!/bin/bash
# Part B of task 2026-10-14e: the merge shakedown on e2-editor-v20, one browser per invocation (arg: chrome|firefox).
# Detached; every step's rc is logged first; no pkill; our own pgrep-style check is a ps listing with the bracket trick.
B=$1
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch/v20-shakedown/merge
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
ts() { date '+%F %T %z'; }
ours() { ps -eo pid,etime,args | /usr/bin/grep -E -- '[p]robe_|[c]heck_m3|[r]un_e2_c|[r]un_merge|[r]un_v20' | /usr/bin/grep -v -- "chain.sh"; }
snap() { ps -eo pid,ppid,etime,pcpu,comm --sort=-pcpu | head -15 > "$V/$1"
  ps -eo pid,etime,args | /usr/bin/grep -E -- '[-]-remote-debugging-port=|[g]eckodriver|[-]marionette' > "$V/$1.test-browsers"; }
identity() { { echo "$(ts) $1"
  sha256sum dist/profiles/e2-editor-v20/{probe.wasm,probe.js,sdk-worker.js,sdk-manifest.json} web/e2-editor-app.js dist/e2-editor-app.js \
    dist/e2-editor.html tools/run_merge_wasm_shakedown.py tools/run_e2_c_product_path.py e2/editor-shell-v2-bundle-v67.json
  git -C .. rev-parse HEAD; git -C .. status --short; } > "$V/$2"; }
precheck() { # before each step: wallet, chrome count, ours; wait while something of ours runs
  local n=0
  { echo "$(ts) precheck $1"
    echo "kdewallet Locked: $(busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked 2>&1)"
    echo "pgrep -c chrome: $(pgrep -c chrome)"; } >> $V/prechecks.txt
  while [ -n "$(ours)" ]; do
    echo "$(ts) WAIT $1: ours still running: $(ours | head -3)" >> $LOG; sleep 150; n=$((n+1)); [ $n -gt 40 ] && break; done
  echo "ours (ps listing of probe_|check_m3|run_e2_c|run_merge|run_v20): [$(ours)]" >> $V/prechecks.txt
}
step() { local name=$1; shift
  precheck "$name"; snap "$name.ps-before.txt"; echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt; local rc=$?
  echo "$(ts) END   $name exit=$rc report_exists=$([ -s $V/$name.json ] && echo yes || echo no)" >> $LOG; snap "$name.ps-after.txt"; }
identity "START $B" identity-at-start-$B.txt
echo "$(ts) CHAIN START $B head $(git -C .. rev-parse --short HEAD)" >> $LOG
P=e2-editor-v20
step shakedown-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --candidate-profile $P --frame-cell --rounds 2 --out $V/shakedown-$B.json
if [ ! -s $V/shakedown-$B.json ]; then echo "$(ts) CHAIN ABORT: no shakedown report for $B" >> $LOG; identity "ABORT $B" identity-at-end-$B.txt; exit 2; fi
step control-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --candidate-profile $P --frame-cell --rounds 2 --control --out $V/control-$B.json
if [ -s $V/control-$B.json ]; then
  echo "$(ts) START pair-$B" >> $LOG
  python3 tools/run_merge_wasm_shakedown.py --pair $V/shakedown-$B.json $V/control-$B.json > $V/pair-$B.stdout.txt 2> $V/pair-$B.stderr.txt
  echo "$(ts) END   pair-$B exit=$?" >> $LOG
fi
step m2-1b-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode m2-1b --candidate-profile $P --out $V/m2-1b-$B.json
step m2-4-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode m2-4 --candidate-profile $P --out $V/m2-4-$B.json
identity "DONE $B" identity-at-end-$B.txt
echo "$(ts) CHAIN DONE $B" >> $LOG
