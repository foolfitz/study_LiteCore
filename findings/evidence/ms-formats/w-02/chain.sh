#!/usr/bin/env bash
# SPEC-P-ms-formats 11.3 G3: the whole W chain again with the corrected tool (fable's ruling): both browsers, then the red case
# (--baseline, v32 / v4) in both, the reads, then R2's self-test on the two green reports. One tool sha for all of it.
# Serial (the browser lock). Writes only under this directory and wasm_sdk_probe/build/ms-formats-w/.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/ms-formats/w-02
M0=../findings/evidence/ms-formats/native-m0
H=build/msformat-native-2/msformat-native
LOG=$E/chain.log
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END $(basename "$name") exit=$rc"; }
say "START tree $(git rev-parse --short HEAD) tool $(sha256sum tools/run_ms_formats_w.py | cut -c1-16) load $(cut -d' ' -f1-3 /proc/loadavg)"
for b in chrome firefox; do step $E/$b python3 tools/run_ms_formats_w.py --browser $b --native-m0 $M0 --harness $H --out $E/$b; done
for b in chrome firefox; do step $E/baseline-$b python3 tools/run_ms_formats_w.py --browser $b --native-m0 $M0 --harness $H --out $E/baseline-$b --baseline; done
for r in chrome firefox baseline-chrome baseline-firefox; do step $E/read-$r python3 tools/run_ms_formats_w.py --read $E/$r/report.json; done
for b in chrome firefox; do step $E/r2-self-test-$b python3 tools/run_ms_formats_w.py --self-test $E/$b/report.json; done
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
