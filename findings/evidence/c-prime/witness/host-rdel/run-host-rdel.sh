#!/usr/bin/env bash
# The page-smoke port's §34.4 witness on a host build (witness/PREDICTION.md, "Not observable on the product path"):
# production UI `Rdel`, both browsers, one round, UNCOUNTED, on host 0.2.12 (C′ page 8909564e…), with the pre-port
# runners at 08d73cff that production UI imports: run_e2_c_page_smoke.py (POINT_AT) and check_m3_page_honesty.py
# (whose ported version needs the ported page smoke).  check_m3_production_ui.py itself was not touched by the port
# (a0925990) and runs at HEAD.  Predicted red in both browsers.  Attempt 1 restored only the page smoke and died at
# import (attempt-1-import-error/).
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" || exit 9
E=findings/evidence/c-prime/witness/host-rdel
T=wasm_sdk_probe/tools
S=$T/run_e2_c_page_smoke.py
H=$T/check_m3_page_honesty.py
[ "$(sha256sum $S | cut -c1-16)" = cc38ee97ca20611d ] || { echo "REFUSED: page smoke at HEAD is $(sha256sum $S | cut -c1-16)" | tee -a $E/log.txt; exit 2; }
[ "$(sha256sum $H | cut -c1-16)" = 6540756e8cf051c6 ] || { echo "REFUSED: page honesty at HEAD is $(sha256sum $H | cut -c1-16)" | tee -a $E/log.txt; exit 2; }
git diff --quiet HEAD -- $S $H || { echo "REFUSED: uncommitted changes in $S or $H would be lost on restore" | tee -a $E/log.txt; exit 2; }
git show 08d73cff:$S > $S
git show 08d73cff:$H > $H
echo "$(date -u +%FT%TZ) START host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) page-smoke $(sha256sum $S | cut -c1-16) page-honesty $(sha256sum $H | cut -c1-16) (both 08d73cff) production_ui $(sha256sum $T/check_m3_production_ui.py | cut -c1-16)" | tee -a $E/log.txt
python3 $T/check_m3_production_ui.py --rounds 1 --arms Rdel --out $PWD/$E/pre-port-rdel.json > $E/pre-port-rdel.stdout.txt 2> $E/pre-port-rdel.stderr.txt
RC=$?
git checkout HEAD -- $S $H
echo "$(date -u +%FT%TZ) END exit $RC; restored page smoke $(sha256sum $S | cut -c1-16) page honesty $(sha256sum $H | cut -c1-16)" | tee -a $E/log.txt
