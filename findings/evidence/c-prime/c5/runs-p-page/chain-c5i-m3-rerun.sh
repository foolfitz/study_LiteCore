#!/usr/bin/env bash
# fable ruling 2 (findings/evidence/c-prime/ruling/fable-ruling-2.md), conditions 3 and 4: re-run ONLY the five
# static-gated M3 runners counted-shape, same invocation as chain-c5i.sh, on the P page and host 6b53c2e; their
# reports go to m3-rerun/ (the five witness reports in m3/ and chain.txt stay untouched); then re-compare with the
# ORIGINAL product-path dir, production UI and host entry reports and the five NEW M3 reports.  No shakedowns
# (ruling condition 3).  Any nonzero comparison = STOP and hand back (condition 4).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
E=findings/evidence
R=$E/c-prime/c5/runs-p-page
O=$R/m3-rerun
LOG=$O/chain.txt
T=wasm_sdk_probe/tools
mkdir -p $O
say() { echo "$(date -u +%FT%TZ) $*" | tee -a $LOG; }
P=$(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-12); W=$(sha256sum wasm_sdk_probe/web/e2-editor-app.js | cut -c1-12)
H=$(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD)
say "START host $H dist $P web $W tree $(git rev-parse --short HEAD) $(for f in check_m3_page_honesty check_m3_locks check_m3_versions check_m3_assets check_m3_same_second run_e2_c_page_smoke; do printf '%s=%s ' $f $(sha256sum $T/$f.py | cut -c1-8); done)"
if [ "$P" != 36c2b18baa83 ] || [ "$W" != 36c2b18baa83 ] || [ "$H" != 6b53c2e ]; then say "STOP: not the P page on host 6b53c2e"; exit 1; fi
for r in page_honesty locks versions assets same_second; do
  d=$E/m3-$(echo $r | tr _ -)/runs
  before=$(ls $d 2>/dev/null | sort)
  say "counted-shape $r begin"
  python3 $T/check_m3_$r.py --label counted > $O/$r.log 2>&1
  code=$?
  new=$(comm -13 <(echo "$before") <(ls $d 2>/dev/null | sort) | grep '\.json$')
  for f in $new; do mv "$d/$f" "$O/$r-$f"; say "moved $d/$f -> $O/$r-$f"; done
  say "counted-shape $r exit $code :: $(grep -E '^VERDICT|LAND|CORRECT|DELIVERED|KEPT|refusing' $O/$r.log | tail -1 | cut -c1-200)"
done
cand() { ls $O/$1-*.json | head -1; }
python3 $E/c-prime/c5/compare.py --product-path $E/release-0.2.11/product-path $R/product-path --cand-runner aa9a22806d10ed71 \
 --m3 production_ui-KR $E/m3-production-ui/runs-0.2.11/counted-KR-x3.json $R/production-ui/counted-KR-x3.json \
 --m3 production_ui-ctl $E/m3-production-ui/runs-0.2.11/counted-ctl-S-P.json $R/production-ui/counted-ctl-S-P.json \
 --m3 production_ui-B3x $E/m3-production-ui/runs-0.2.11/counted-B3x-x2.json $R/production-ui/counted-B3x-x2.json \
 --m3 page_honesty $E/m3-page-honesty/runs/2026-10-10T031815+0000.json $(cand page_honesty) \
 --m3 locks $E/m3-locks/runs/2026-10-10T041853+0000.json $(cand locks) \
 --m3 versions $E/m3-versions/runs/2026-10-10T050528+0000.json $(cand versions) \
 --m3 assets $E/m3-assets/runs/2026-10-10T050926+0000.json $(cand assets) \
 --m3 host_entry $E/m3-host-entry/runs/2026-10-10T051336Z.json $(ls $R/m3/host_entry-*.json) \
 --m3 same_second $E/m3-same-second/runs/2026-10-10T051850+0000.json $(cand same_second) > $R/compare-output-rerun.txt 2>&1
say "compare exit $? :: $(grep SUMMARY $R/compare-output-rerun.txt)"
say "DONE"
