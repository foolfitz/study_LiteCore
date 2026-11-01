#!/usr/bin/env bash
# Spec K-0.2.45 section 6: the counted branches a shakedown cannot reach, by the real runners in counted mode, the four quickest and most
# different bindings.  Not K: the reader takes only reports newer than the chain's START.  The reports are moved to counted-dry-run/ after.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
export PATH="$PWD/wasm_sdk_probe/host-stack/bin:$PATH"
T=wasm_sdk_probe/tools; D=findings/evidence/k-0.2.45/counted-dry-run; mkdir -p $D
step() { local name=$1; shift; echo "$(date +%FT%T%z) BEGIN $name" >> $D/log.txt; "$@" > $D/$name.stdout.txt 2> $D/$name.stderr.txt; local rc=$?; echo "exit=$rc" > $D/$name.exit.txt; echo "$(date +%FT%T%z) END $name exit $rc" >> $D/log.txt; }
step production_ui python3 $T/check_m3_production_ui.py --counted --rounds 1 --arms P --out "$PWD/$D/production-ui-p.json"
step versions python3 $T/check_m3_versions.py --label counted
step assets python3 $T/check_m3_assets.py --label counted
step new_document python3 $T/check_m3_new_document.py --label counted
echo DONE >> $D/log.txt
