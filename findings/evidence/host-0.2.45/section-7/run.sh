#!/usr/bin/env bash
# Spec v29 section 7 on the installed 0.2.45: the P arm and as5.  Shakedowns; the runners' page pin is 0.2.44's until the next K spec re-pins it, so read cells.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
export PATH="$PWD/wasm_sdk_probe/host-stack/bin:$PATH"
T=wasm_sdk_probe/tools; F=findings/evidence/host-0.2.45/section-7
step() { local name=$1; shift; echo "$(date +%FT%T%z) BEGIN $name" >> $F/log.txt; "$@" > $F/$name.stdout.txt 2> $F/$name.stderr.txt; local rc=$?; echo "exit=$rc" > $F/$name.exit.txt; echo "$(date +%FT%T%z) END $name exit $rc" >> $F/log.txt; }
step production_ui_p python3 $T/check_m3_production_ui.py --rounds 3 --arms P --out "$PWD/$F/production-ui-p.json"
step autosave_as5 python3 $T/check_m3_autosave.py --label shakedown --repeats 3 --arms as5,as5-held
echo DONE >> $F/log.txt
