#!/usr/bin/env bash
# 20-key ghost, low and high arms, on 0.2.12's and pre-fix 0.2.13's packages; then the fixed package back.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
APP=~/Projects/Nextcloud_Apps/litecore
E=../findings/evidence/131/ghost-20-ab
mkdir -p $E
swap() { rm -rf $APP/engine && cp -r --no-preserve=mode "build/archive/$1" $APP/engine && rm -f $APP/engine/ATTRIBUTION.md; diff -r -x ATTRIBUTION.md $APP/engine "build/archive/$1" && echo "$(date -u +%FT%TZ) swapped in $1 buildId $(python3 -c "import json;print(json.load(open('$APP/engine/MANIFEST.json'))['buildId'])")" >> $E/log.txt; sleep 4; }
for pkg in host-0.2.12-engine-45cdcedfc0fe7e61 host-0.2.13-prefix-engine-0574b1b157ce1e1e; do
  swap $pkg
  mkdir -p $E/$pkg
  python3 tools/probe_hand_test_0212.py --out $E/$pkg --arms high,low --ghost-rapid-keys 20 > $E/$pkg/stdout.txt 2>&1
  echo "$(date -u +%FT%TZ) $pkg probe exit $?" >> $E/log.txt
done
swap host-0.2.13-engine-59e6a9fed026a0ad
python3 ../findings/evidence/release-0.2.13/check_engine_decoded.py > $E/check-engine-decoded-after.txt 2>&1
echo "$(date -u +%FT%TZ) restored, check_engine_decoded exit $?" >> $E/log.txt
echo DONE >> $E/log.txt
