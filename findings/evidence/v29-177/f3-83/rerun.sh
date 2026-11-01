#!/usr/bin/env bash
# F3-83 on the final page (the icon toolbar, HTML only): run-02 both browsers and its readers; Firefox twice more, because the cell that
# moved in run-01 was Firefox's and one run is not a measurement.  Then V0' alone, since it swaps files under dist/.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=../findings/evidence/v29-177
F3=$E/f3-83
LOG=$F3/rerun-log.txt
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; mkdir -p "$(dirname "$name")"; say "BEGIN $(basename "$name")"; "$@" > "$name.stdout.txt" 2> "$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$name.exit.txt"; say "END   $(basename "$name") exit $rc"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
for b in chrome firefox; do step $F3/run-02/$b python3 tools/run_v83_f3_clipboard.py --browser $b --out $F3/run-02/$b; done
step $F3/equal-02 python3 tools/read_v83_f3_equal.py --v83 $F3/run-02
step $F3/equal-02-self-test python3 tools/read_v83_f3_equal.py --v83 $F3/run-02 --self-test
step $F3/read-02 python3 tools/read_v25_f3.py --v25 $F3/run-02
for r in 03 04; do step $F3/run-$r/firefox python3 tools/run_v83_f3_clipboard.py --browser firefox --out $F3/run-$r/firefox; done
mkdir -p $E/v0
step $E/v0/run python3 -I $E/v0/run_v0_prime.py
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
