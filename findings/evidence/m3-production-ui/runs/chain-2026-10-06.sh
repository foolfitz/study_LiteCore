#!/usr/bin/env bash
# SPEC-M3-production-ui §11: shakedown the six M3 runners on host 0.2.7, and only
# if every one is clean, the counted runs (production UI first, then the six).
# One runner at a time: each clears the whole oc_files_lock table.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
LOG=wasm_sdk_probe/build/m3-count-2026-10-06
T=wasm_sdk_probe/tools
SIX="page_honesty locks versions assets host_entry same_second"
say() { echo "$(date -u +%FT%TZ) $*" | tee -a $LOG/chain.txt; }
say "START host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) page $(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-12)"
for r in $SIX; do
  say "shakedown $r begin"
  python3 $T/check_m3_$r.py --label shakedown --repeats 1 > $LOG/shakedown-$r.log 2>&1
  code=$?
  say "shakedown $r exit $code :: $(grep -E '^VERDICT|lands|LANDS' $LOG/shakedown-$r.log | tail -1 | cut -c1-200)"
  if [ $code -ne 0 ]; then say "STOP: shakedown $r not clean; no counted run started"; exit 1; fi
done
E=findings/evidence/m3-production-ui/runs
mkdir -p $E
say "counted production_ui Bdel,Bbs x3 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 3 --arms Bdel,Bbs --out $E/counted-B-x3.json > $E/counted-B-x3.stdout.txt 2>&1; say "counted production_ui B x3 exit $?"
say "counted production_ui Bctl,S,P x1 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 1 --arms Bctl,S,P --out $E/counted-ctl-S-P.json > $E/counted-ctl-S-P.stdout.txt 2>&1; say "counted production_ui ctl/S/P exit $?"
say "counted production_ui B3x x2 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 2 --arms B3x --out $E/counted-B3x-x2.json > $E/counted-B3x-x2.stdout.txt 2>&1; say "counted production_ui B3x x2 exit $?"
for r in $SIX; do
  say "counted $r begin"
  python3 $T/check_m3_$r.py --label counted > $LOG/counted-$r.log 2>&1
  say "counted $r exit $? :: $(grep -E '^VERDICT|lands|LANDS|refusing' $LOG/counted-$r.log | tail -1 | cut -c1-200)"
done
say "DONE"
