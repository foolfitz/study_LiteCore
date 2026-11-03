#!/usr/bin/env bash
# SPEC-P-demo-batch-5 on the installed 0.2.53, serial.  Run with host-stack/bin first on PATH.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.53 || exit 9
export PATH=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/host-stack/bin:$PATH
T=../../../wasm_sdk_probe/tools
say() { echo "$(date +%T) $*" >> h5-log.txt; }
step() { local name=$1; shift; say "BEGIN $name"; "$@" > $name.stdout.txt 2> $name.stderr.txt; local rc=$?; echo "exit=$rc" > $name.exit.txt; say "END $name exit=$rc"; }
step host-features python3 -I host_batch5.py --out host-features
step host-calc-theme python3 -I ../host-0.2.51/host_calc_theme.py --out host-calc-theme
step files-workflow-01 python3 $T/run_calc_editor_host.py --out files-workflow-01
step host-batch python3 -I ../host-0.2.46/host_batch.py --out host-batch
step host-layout python3 -I ../demo-batch-2/host_layout.py --out host-layout
step capture-after python3 -I capture-after.py "$(ls -d install-2* | tail -1)" files-workflow-01
say DONE
