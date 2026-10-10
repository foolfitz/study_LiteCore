#!/usr/bin/env bash
# SPEC-M3-production-ui §17.4 C5 (i) / §17.11: the ported harness on the P page (host 0.2.11, page 36c2b18b…),
# the same shape as 0.2.11's count (findings/evidence/m3-production-ui/runs-0.2.11/chain-2026-10-10b.sh):
# six shakedowns (any non-clean = STOP), production UI's three counted-shape reports, the six M3 runners
# counted-shape, the product-path net's twelve runs.  NOT a release count: a comparison, read with
# findings/evidence/c-prime/c5/compare.py against 0.2.11's committed reports.  Each M3 runner writes into its
# own runs/ directory; the new report is moved here right after the run and the move is logged.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
E=findings/evidence/c-prime/c5/runs-p-page
LOG=$E/chain.txt
T=wasm_sdk_probe/tools
SIX="page_honesty locks versions assets host_entry same_second"
say() { echo "$(date -u +%FT%TZ) $*" | tee -a $LOG; }
P=$(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-12); W=$(sha256sum wasm_sdk_probe/web/e2-editor-app.js | cut -c1-12)
say "START host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) dist $P web $W tree $(git rev-parse --short HEAD) smoke $(sha256sum $T/run_e2_c_page_smoke.py | cut -c1-16) pp $(sha256sum $T/run_e2_c_product_path.py | cut -c1-16) honesty $(sha256sum $T/check_m3_page_honesty.py | cut -c1-16)"
if [ "$P" != 36c2b18baa83 ] || [ "$W" != 36c2b18baa83 ]; then say "STOP: dist/web is not the P page"; exit 1; fi
mkdir -p $E/shakedown $E/m3
for r in $SIX; do
  say "shakedown $r begin"
  python3 $T/check_m3_$r.py --label shakedown --repeats 1 > $E/shakedown/$r.log 2>&1
  code=$?
  say "shakedown $r exit $code :: $(grep -E '^VERDICT|lands|LANDS' $E/shakedown/$r.log | tail -1 | cut -c1-200)"
  if [ $code -ne 0 ]; then say "STOP: shakedown $r not clean; no counted-shape run started"; exit 1; fi
done
mkdir -p $E/production-ui
say "production_ui Kdel,Kbs,Rbs,Rdel x3 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 3 --arms Kdel,Kbs,Rbs,Rdel --out $E/production-ui/counted-KR-x3.json > $E/production-ui/counted-KR-x3.stdout.txt 2>&1; say "production_ui KR x3 exit $?"
say "production_ui Bctl,S,P x1 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 1 --arms Bctl,S,P --out $E/production-ui/counted-ctl-S-P.json > $E/production-ui/counted-ctl-S-P.stdout.txt 2>&1; say "production_ui ctl/S/P exit $?"
say "production_ui B3x x2 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 2 --arms B3x --out $E/production-ui/counted-B3x-x2.json > $E/production-ui/counted-B3x-x2.stdout.txt 2>&1; say "production_ui B3x x2 exit $?"
for r in $SIX; do
  d=findings/evidence/m3-$(echo $r | tr _ -)/runs
  before=$(ls $d 2>/dev/null | sort)
  say "counted-shape $r begin"
  python3 $T/check_m3_$r.py --label counted > $E/m3/$r.log 2>&1
  code=$?
  new=$(comm -13 <(echo "$before") <(ls $d 2>/dev/null | sort) | grep '\.json$')
  for f in $new; do mv "$d/$f" "$E/m3/$r-$f"; say "moved $d/$f -> $E/m3/$r-$f"; done
  say "counted-shape $r exit $code :: $(grep -E '^VERDICT|lands|LANDS|refusing' $E/m3/$r.log | tail -1 | cut -c1-200)"
done
PP=$E/product-path
mkdir -p $PP
ts() { date '+%F %T %z'; }
echo "$(ts) PRODUCT-PATH START tools: $(sha256sum $T/run_e2_c_product_path.py | cut -c1-16)" >> $PP/chain.log
for B in chrome firefox; do
  for N in 1 2 3; do
    for V in v8 v19; do
      OUT=$PWD/$PP/e2-editor-$V-$B-r$N
      if [ "$V" = v8 ]; then CMD="python3 $T/run_e2_c_product_path.py --browser $B --candidate-profile e2-editor-v8 --out $OUT.json"
      else CMD="python3 $T/run_e2_c_product_path.py --browser $B --out $OUT.json"; fi
      echo "$(ts) START $V $B r$N :: $CMD" >> $PP/chain.log
      $CMD > $OUT.stdout.txt 2> $OUT.stderr.txt
      RC=$?
      echo "$(ts) END   $V $B r$N exit=$RC report_exists=$([ -s $OUT.json ] && echo yes || echo no)" >> $PP/chain.log
      say "product-path $V $B r$N exit $RC"
    done
  done
done
echo "$(ts) PRODUCT-PATH DONE" >> $PP/chain.log
say "DONE"
