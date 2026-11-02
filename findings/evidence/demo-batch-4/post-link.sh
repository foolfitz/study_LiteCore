#!/usr/bin/env bash
# The runbook's steps 3 to 6, serial.  Each step's stdout, stderr and exit are kept beside its result.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/demo-batch-4
LOG=$E/post-link.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
step $E/p4/run-02-log python3 -I tools/check_writer_toggle.py --profile e2-editor-v32 --out $E/p4/run-02
step $E/p4/red-swap-levels-log python3 -I tools/check_writer_toggle.py --profile e2-editor-v32 --mutate swap-levels --only T2 --out $E/p4/red-swap-levels
step $E/p4/red-no-undo-log python3 -I tools/check_writer_toggle.py --profile e2-editor-v32 --mutate no-undo --only T8 --out $E/p4/red-no-undo
step $E/p4/red-no-second-press-log python3 -I tools/check_writer_toggle.py --profile e2-editor-v32 --mutate no-second-press --only T1 --out $E/p4/red-no-second-press
step $E/p1/run-01-log python3 -I tools/check_writer_align.py --profile e2-editor-v32 --out $E/p1/run-01
step $E/p4/read-cost-log python3 -I $E/p4/read_cost.py --out $E/p4/read-cost
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
