#!/bin/bash
DIR=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v16-shakedown/product-path-b003534c
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$DIR/chain.log
ts() { date '+%F %T %z'; }
# overlap sampler: records any other tools/run_* process (not the product-path runner) every 10 s
( while true; do
    o=$(pgrep -af 'tools/run_' | grep -v 'run_e2_c_product_path' | cut -c1-200)
    if [ -n "$o" ]; then echo "$(ts) $o" >> $DIR/overlap-sampler.log; fi
    sleep 10
  done ) &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null' EXIT
echo "$(ts) CHAIN START runner_sha256=$(sha256sum tools/run_e2_c_product_path.py | cut -d' ' -f1)" >> $LOG
run() { # profile browser round
  P=$1; B=$2; N=$3
  while pgrep -f 'run_e2_c_product_path|run_merge|geckodriver|chromedriver' >/dev/null; do
    echo "$(ts) WAIT other process present: $(pgrep -af 'run_e2_c_product_path|run_merge|geckodriver|chromedriver' | cut -c1-120 | tr '\n' '|')" >> $LOG
    sleep 20
  done
  OUT=$DIR/e2-editor-$P-$B-r$N
  if [ "$P" = v8 ]; then
    CMD="python3 tools/run_e2_c_product_path.py --browser $B --out $OUT.json"
  else
    CMD="python3 tools/run_e2_c_product_path.py --browser $B --candidate-profile e2-editor-v16 --out $OUT.json"
  fi
  echo "$(ts) START $P $B r$N :: $CMD > $OUT.stdout.txt 2> $OUT.stderr.txt" >> $LOG
  $CMD > $OUT.stdout.txt 2> $OUT.stderr.txt
  RC=$?
  echo "$(ts) END   $P $B r$N exit=$RC report_exists=$([ -s $OUT.json ] && echo yes || echo no)" >> $LOG
  if [ ! -s $OUT.json ]; then
    echo "$(ts) CHAIN ABORT: no report written for $P $B r$N" >> $LOG
    exit 2
  fi
}
for B in chrome firefox; do
  for N in 1 2 3; do
    run v8 $B $N
    run v16 $B $N
  done
done
echo "$(ts) CHAIN DONE runner_sha256=$(sha256sum tools/run_e2_c_product_path.py | cut -d' ' -f1)" >> $LOG
