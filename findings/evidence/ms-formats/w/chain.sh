#!/usr/bin/env bash
# SPEC-P-ms-formats 10.3-10.4: W1-W3 on the development profiles in both browsers, then the red case (--baseline, v32 / v4) in both.
# Serial (the browser lock). Writes only under this directory and wasm_sdk_probe/build/ms-formats-w/.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/ms-formats/w
M0=../findings/evidence/ms-formats/native-m0
H=build/msformat-native-2/msformat-native
LOG=$E/chain.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
for b in chrome firefox; do step $E/$b python3 tools/run_ms_formats_w.py --browser $b --native-m0 $M0 --harness $H --out $E/$b; done
for b in chrome firefox; do step $E/baseline-$b python3 tools/run_ms_formats_w.py --browser $b --native-m0 $M0 --harness $H --out $E/baseline-$b --baseline; done
for r in chrome firefox baseline-chrome baseline-firefox; do step $E/read-$r python3 tools/run_ms_formats_w.py --read $E/$r/report.json; done
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
