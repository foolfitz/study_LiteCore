#!/usr/bin/env bash
# SPEC-M3-production-ui §13 (§14 R′: findings 119 and 111, host 0.2.9): shakedown the six M3 runners,
# and only if every one is clean, the counted runs (production UI first, then the
# six).  One runner at a time: each clears the whole oc_files_lock table.
# Same shape as 2026-10-06's chain (findings/evidence/m3-production-ui/runs/chain-2026-10-06.sh).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
LOG=wasm_sdk_probe/build/m3-count-2026-10-09b
T=wasm_sdk_probe/tools
SIX="page_honesty locks versions assets host_entry same_second"
say() { echo "$(date -u +%FT%TZ) $*" | tee -a $LOG/chain.txt; }
say "START host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) page $(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-12) tree $(git rev-parse --short HEAD) runner $(sha256sum $T/check_m3_production_ui.py | cut -c1-16)"
for r in $SIX; do
  say "shakedown $r begin"
  python3 $T/check_m3_$r.py --label shakedown --repeats 1 > $LOG/shakedown-$r.log 2>&1
  code=$?
  say "shakedown $r exit $code :: $(grep -E '^VERDICT|lands|LANDS' $LOG/shakedown-$r.log | tail -1 | cut -c1-200)"
  if [ $code -ne 0 ]; then say "STOP: shakedown $r not clean; no counted run started"; exit 1; fi
done
E=findings/evidence/m3-production-ui/runs-0.2.9
mkdir -p $E
say "counted production_ui Kdel,Kbs,Rbs,Rdel x3 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 3 --arms Kdel,Kbs,Rbs,Rdel --out $E/counted-KR-x3.json > $E/counted-KR-x3.stdout.txt 2>&1; say "counted production_ui KR x3 exit $?"
say "counted production_ui Bctl,S,P x1 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 1 --arms Bctl,S,P --out $E/counted-ctl-S-P.json > $E/counted-ctl-S-P.stdout.txt 2>&1; say "counted production_ui ctl/S/P exit $?"
say "counted production_ui B3x x2 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 2 --arms B3x --out $E/counted-B3x-x2.json > $E/counted-B3x-x2.stdout.txt 2>&1; say "counted production_ui B3x x2 exit $?"
for r in $SIX; do
  say "counted $r begin"
  python3 $T/check_m3_$r.py --label counted > $LOG/counted-$r.log 2>&1
  say "counted $r exit $? :: $(grep -E '^VERDICT|lands|LANDS|refusing' $LOG/counted-$r.log | tail -1 | cut -c1-200)"
done
# The product-path net for this release (findings/evidence/release-0.2.9/product-path/PREDICTION.md), after the
# M3 counts, one run at a time, v8 (candidate, repointed) and v19 (plain dist) interleaved.
PP=findings/evidence/release-0.2.9/product-path
ts() { date '+%F %T %z'; }
echo "$(ts) PRODUCT-PATH START tools: $(sha256sum $T/run_e2_c_product_path.py | cut -c1-16)" >> $PP/chain.log
for B in chrome firefox; do
  for N in 1 2 3; do
    for P in v8 v19; do
      OUT=$PWD/$PP/e2-editor-$P-$B-r$N
      if [ "$P" = v8 ]; then CMD="python3 $T/run_e2_c_product_path.py --browser $B --candidate-profile e2-editor-v8 --out $OUT.json"
      else CMD="python3 $T/run_e2_c_product_path.py --browser $B --out $OUT.json"; fi
      echo "$(ts) START $P $B r$N :: $CMD" >> $PP/chain.log
      $CMD > $OUT.stdout.txt 2> $OUT.stderr.txt
      RC=$?
      echo "$(ts) END   $P $B r$N exit=$RC report_exists=$([ -s $OUT.json ] && echo yes || echo no)" >> $PP/chain.log
      say "product-path $P $B r$N exit $RC"
    done
  done
done
echo "$(ts) PRODUCT-PATH DONE" >> $PP/chain.log
say "DONE"
