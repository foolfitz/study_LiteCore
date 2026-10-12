#!/usr/bin/env bash
# SPEC-M3-autosave §9.4 「計數」 (host 0.2.13, shell v62): shakedown the six M3 runners and check_m3_autosave.py,
# and only if every one is clean, the counted runs (production UI first, then the six, then autosave), then the
# product-path net.  One runner at a time: each clears the whole oc_files_lock table.
# Same shape as 0.2.12's (findings/evidence/m3-production-ui/runs-0.2.12/chain-2026-10-11b.sh); added: the
# autosave runner (its gate shakedown is three arms in both browsers -- its full shakedown ran the same day on the
# same bytes, findings/evidence/m3-autosave/shakedown/; as5 is in the gate because the review changed its premise
# and the recorder's clock, findings/evidence/m3-autosave/review/DISPOSITION.md -- and its counted run after the
# six), and an identity line at START and at END (the review's item B5: the runners sample their binding once).
set -u
mkdir -p /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/m3-count-2026-10-12
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
LOG=wasm_sdk_probe/build/m3-count-2026-10-12
T=wasm_sdk_probe/tools
SIX="page_honesty locks versions assets host_entry same_second"
say() { echo "$(date -u +%FT%TZ) $*" | tee -a $LOG/chain.txt; }
ident() { echo "host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) dirty[$(git -C ~/Projects/Nextcloud_Apps/litecore status --porcelain | tr '\n' ' ')] version $(grep -o '<version>[^<]*' ~/Projects/Nextcloud_Apps/litecore/appinfo/info.xml | cut -c10-) buildId $(python3 -c 'import json,pathlib;print(json.loads((pathlib.Path.home()/"Projects/Nextcloud_Apps/litecore/engine/MANIFEST.json").read_text())["buildId"])') dist-page $(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-16) web-page $(sha256sum wasm_sdk_probe/web/e2-editor-app.js | cut -c1-16)"; }
say "IDENTITY-START $(ident)"
say "START host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) page $(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-12) tree $(git rev-parse --short HEAD) runner $(sha256sum $T/check_m3_production_ui.py | cut -c1-16) autosave $(sha256sum $T/check_m3_autosave.py | cut -c1-16)"
for r in $SIX; do
  say "shakedown $r begin"
  python3 $T/check_m3_$r.py --label shakedown --repeats 1 > $LOG/shakedown-$r.log 2>&1
  code=$?
  say "shakedown $r exit $code :: $(grep -E '^VERDICT|lands|LANDS' $LOG/shakedown-$r.log | tail -1 | cut -c1-200)"
  if [ $code -ne 0 ]; then say "STOP: shakedown $r not clean; no counted run started"; exit 1; fi
done
say "shakedown autosave begin"
python3 $T/check_m3_autosave.py --label shakedown --arms as2-key,as4a,as5 --repeats 1 > $LOG/shakedown-autosave.log 2>&1
code=$?
say "shakedown autosave exit $code :: $(grep -E '^VERDICT' $LOG/shakedown-autosave.log | tail -1 | cut -c1-200)"
if [ $code -ne 0 ]; then say "STOP: shakedown autosave not clean; no counted run started"; exit 1; fi
E=findings/evidence/m3-production-ui/runs-0.2.13
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
say "counted autosave begin"
python3 $T/check_m3_autosave.py --label counted > $LOG/counted-autosave.log 2>&1
say "counted autosave exit $? :: $(grep -E '^VERDICT|refusing' $LOG/counted-autosave.log | tail -1 | cut -c1-200)"
# The product-path net for this release (findings/evidence/release-0.2.13/product-path/PREDICTION.md), after the
# M3 counts, one run at a time, v8 (candidate, repointed) and v19 (plain dist) interleaved.
PP=findings/evidence/release-0.2.13/product-path
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
say "IDENTITY-END $(ident)"
# The runners leave one Firefox profile (~79 MB) per Firefox session in the snap-visible scratch directory and
# never remove it (167 had piled up by 2026-10-12, 8.1 GB).  Every browser of this chain has exited by now.
SCR=wasm_sdk_probe/build/scratch-m3-production-ui
say "cleanup: $(find $SCR -maxdepth 1 -name 'ff-*' -type d | wc -l) Firefox profiles in $SCR removed"
find $SCR -maxdepth 1 -name 'ff-*' -type d -exec rm -rf {} +
say "DONE"
