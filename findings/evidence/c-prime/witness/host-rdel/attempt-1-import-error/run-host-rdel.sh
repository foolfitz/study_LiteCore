#!/usr/bin/env bash
# The page-smoke port's §34.4 witness on a host build (witness/PREDICTION.md, "Not observable on the product path"):
# production UI `Rdel`, both browsers, one round, UNCOUNTED, on host 0.2.12 (C′ page 8909564e…), with
# run_e2_c_page_smoke.py temporarily restored to the pre-port commit 08d73cff.  Predicted red in both browsers.
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" || exit 9
E=findings/evidence/c-prime/witness/host-rdel
T=wasm_sdk_probe/tools
F=$T/run_e2_c_page_smoke.py
HEAD_SHA=$(sha256sum $F | cut -c1-16)
[ "$HEAD_SHA" = cc38ee97ca20611d ] || { echo "REFUSED: page smoke at HEAD is $HEAD_SHA" | tee -a $E/log.txt; exit 2; }
git show 08d73cff:$F > $F
echo "$(date -u +%FT%TZ) START host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) page-smoke $(sha256sum $F | cut -c1-16) (08d73cff) production_ui $(sha256sum $T/check_m3_production_ui.py | cut -c1-16)" | tee -a $E/log.txt
python3 $T/check_m3_production_ui.py --rounds 1 --arms Rdel --out $PWD/$E/pre-port-rdel.json > $E/pre-port-rdel.stdout.txt 2> $E/pre-port-rdel.stderr.txt
RC=$?
git checkout HEAD -- $F
echo "$(date -u +%FT%TZ) END exit $RC; page smoke restored $(sha256sum $F | cut -c1-16)" | tee -a $E/log.txt
