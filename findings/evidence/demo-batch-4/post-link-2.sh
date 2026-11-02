#!/usr/bin/env bash
# After post-link.sh: swap-levels with the reply put back, so the red is the reader's and not the client's check; the read's cost with a save before each new document.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/demo-batch-4
LOG=$E/post-link.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
step $E/p4/red-swap-levels-02-log python3 -I tools/check_writer_toggle.py --profile e2-editor-v32 --mutate swap-levels --only T2 --out $E/p4/red-swap-levels-02
step $E/p4/read-cost-02-log python3 -I $E/p4/read_cost.py --out $E/p4/read-cost-02
say "DONE2 load $(cut -d' ' -f1-3 /proc/loadavg)"
