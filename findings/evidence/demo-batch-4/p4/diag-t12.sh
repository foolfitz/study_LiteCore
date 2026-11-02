#!/usr/bin/env bash
# The arms of diag_t12.py after the first: one process per arm, the page differs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
D=../findings/evidence/demo-batch-4/p4
run() { name=$1; shift; echo "$(date +%T) BEGIN $name"; python3 -I $D/diag_t12.py --out $D/diag-t12/$name "$@" > $D/diag-t12-$name.log 2>&1; echo "$(date +%T) END $name exit=$?"; }
run v32-valid-chrome --fixture image-valid-fixture.odt
run v31-corrupt-chrome --profile e2-editor-v31
