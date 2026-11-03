#!/usr/bin/env bash
# Re-run of chain-89.sh's Writer steps that refused on 2026-11-03 (KWallet unreadable): P5, P4, shift-lines, zoom, P1, F4.
# Same commands, output under gen-89/rerun-01/; Calc sheet view, F3, W and V0prime ran that night and are not repeated.
# The tree has f8865e28b: pre_run_checks() records the wallet and no longer refuses.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/ms-formats/gen-89/rerun-01
LOG=$E/rerun-01.log
mkdir -p $E
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg) wallet $(busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked 2>&1)"
step $E/p5/final-89-log python3 -I tools/check_writer_enter_range.py --profile e2-editor-v33 --out $E/p5/final-89
step $E/p4/final-89-log python3 -I tools/check_writer_toggle.py --out $E/p4/final-89
step $E/shift-lines/live-page-89-log python3 -I tools/check_writer_shift_lines.py --out $E/shift-lines/live-page-89
step $E/writer-zoom/run-89-log python3 -I tools/check_writer_zoom.py --out $E/writer-zoom/run-89
step $E/p1/final-89-log python3 -I tools/check_writer_align.py --out $E/p1/final-89
F4=$E/f4-89
for b in chrome firefox; do step $F4/$b-run python3 tools/run_v89_four_arms.py --browser $b --out $F4/$b; done
A=$(cd $F4 && pwd)
step $F4/aggregate python3 tools/judge_v89_product_four_arms.py $A/chrome/report.v23-four-arms $A/firefox/report.v23-four-arms --out $F4/aggregate-judge.json
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
