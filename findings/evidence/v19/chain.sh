#!/bin/bash
# The v19 round, spec SPEC-M3-paragraph-merge 31.4 X2-X7, PREDICTION.md (committed before this runs).  One tool at
# a time, in this order: X2 M1-1 (no browser), X3 W3/W5 probes (Chrome), X7 the counted M2 (Chrome, then Firefox),
# X5 product-path net (v8/v19 interleaved, 3 rounds x Chrome/Firefox), X4 counted corpus comparison (v19 vs v18),
# X6 the owner's document (Chrome, diagnostic, last; spec 34.8).  The readers are run afterwards, not here.
# Stop rule: nothing aborts the chain.  Every step's exit code is written to chain.log before anything else, and
# each part is judged from its own reports; a missing or unreadable report means that part was not done.
# No pgrep/pkill anywhere; a `ps` snapshot and a test-browser listing (by command line: rule cc) are kept before
# and after each browser step.  Nothing under tools/ is edited while this runs (spec 34.1).
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v19
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
PPLOG=$V/x5-product-path/chain.log      # the product-path reader parses END lines in this format
ts() { date '+%F %T %z'; }
snap() { ps -eo pid,ppid,etime,pcpu,comm --sort=-pcpu | head -15 > "$V/$1"
  ps -eo pid,etime,args | /usr/bin/grep -E -- '[-]-remote-debugging-port=|[g]eckodriver|[-]marionette' > "$V/$1.test-browsers"; }
identity() { # what every run here is evidence about; equal at start and end, or the round is not about v19
  { echo "$(ts) $1"
    sha256sum dist/profiles/e2-editor-{v19,v8,v18}/{probe.wasm,probe.js,sdk-worker.js,sdk-manifest.json} \
      dist/profiles/resources/cjk-sub-e10.06976180177c8bd2.data dist/profiles/resources/cjk-sub-e10.4144b2b2a44dd797.metadata \
      web/e2-editor-app.js dist/e2-editor-app.js dist/e2-editor.html e2/editor-shell-v2-bundle-v56.json \
      tools/run_merge_wasm_shakedown.py tools/judge_counted_m2.py tools/run_e2_c_product_path.py \
      tools/compare_layout_corpus.py tools/check_merge_key_undo_scope.py tools/check_profile_identity.py
    git -C .. rev-parse HEAD; git -C .. status --short; } > "$V/$2"; }
step() { # name (path under $V, no extension), command...
  local name=$1; shift
  snap "$name.ps-before.txt"
  echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt
  local rc=$?
  echo "$(ts) END   $name exit=$rc" >> $LOG
  snap "$name.ps-after.txt"
}
pp() { # profile browser round
  local P=$1 B=$2 N=$3 OUT=$V/x5-product-path/e2-editor-$1-$2-r$3 CMD
  if [ "$P" = v8 ]; then
    CMD="python3 tools/run_e2_c_product_path.py --browser $B --out $OUT.json"
  else
    CMD="python3 tools/run_e2_c_product_path.py --browser $B --candidate-profile e2-editor-v19 --out $OUT.json"
  fi
  snap "x5-product-path/e2-editor-$P-$B-r$N.ps-before.txt"
  echo "$(ts) START $P $B r$N :: $CMD" | tee -a $LOG >> $PPLOG
  $CMD > $OUT.stdout.txt 2> $OUT.stderr.txt
  local RC=$?
  echo "$(ts) END   $P $B r$N exit=$RC report_exists=$([ -s $OUT.json ] && echo yes || echo no)" | tee -a $LOG >> $PPLOG
}
identity "CHAIN START" identity-at-start.txt
echo "$(ts) CHAIN START head $(git -C .. rev-parse --short HEAD)" >> $LOG

# X2: M1-1 after the link, green and the three red cases (x2-m1-1/run.sh writes its own run.log)
step x2-m1-1/chain bash $V/x2-m1-1/run.sh

# X3: W3/W5 probes on v19 (four cold Chrome sessions; writes x3-w3-w5/sessions.json and the fc logs)
step x3-w3-w5/run python3 $V/x3-w3-w5/run.py

# X7: the counted M2, per browser; file names are the reader's (judge_counted_m2.py FILES)
X=$V/x7-counted-m2
for B in chrome firefox; do
  step x7-counted-m2/counted-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode counted --candidate-profile e2-editor-v19 --out $X/counted-$B.json
  step x7-counted-m2/counted-control-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode counted --control --candidate-profile e2-editor-v19 --out $X/counted-control-$B.json
  step x7-counted-m2/pair-$B python3 tools/run_merge_wasm_shakedown.py --pair $X/counted-$B.json $X/counted-control-$B.json
  step x7-counted-m2/m2-1b-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode m2-1b --candidate-profile e2-editor-v19 --out $X/m2-1b-$B.json
  step x7-counted-m2/m2-4-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode m2-4 --candidate-profile e2-editor-v19 --out $X/m2-4-$B.json
  step x7-counted-m2/red-$B python3 tools/run_merge_wasm_shakedown.py --browser $B --mode m2-1-red --candidate-profile e2-editor-v8 --out $X/red-$B.json
done
echo "$(ts) X7 DONE" >> $LOG

# X5: product-path net, v8 and v19 interleaved
echo "$(ts) PRODUCT-PATH START tools: $(sha256sum tools/run_e2_c_product_path.py | cut -c1-16)" >> $PPLOG
for B in chrome firefox; do
  for N in 1 2 3; do
    pp v8 $B $N
    pp v19 $B $N
  done
done
echo "$(ts) PRODUCT-PATH DONE" | tee -a $LOG >> $PPLOG

# X4: counted corpus comparison, v19 against v18
C=$V/x4-layout-corpus
date -u '+%FT%TZ' > $C/run-started-utc.txt
step x4-layout-corpus/run python3 tools/compare_layout_corpus.py --profiles e2-editor-v19 e2-editor-v18 --out $C
date -u '+%FT%TZ' > $C/run-finished-utc.txt

# X6: the owner's document (diagnostic only; spec 25, 30.1, 34.8)
step x6-v5/shakedown-chrome-v19-v5 python3 tools/run_merge_wasm_shakedown.py --browser chrome --candidate-profile e2-editor-v19 --owner-document --out $V/x6-v5/shakedown-chrome-v19-v5.json

identity "CHAIN DONE" identity-at-end.txt
echo "$(ts) CHAIN DONE" >> $LOG
