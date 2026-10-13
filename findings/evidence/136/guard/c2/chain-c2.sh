#!/usr/bin/env bash
# C2 on the final C′ page (dist 8909564eb2316afa; predictions in spec §17.10, written before any run).
#   ratio 2 wide  (judge_c2.py):       probe_typing_latency_view.py --dpr 2 --window 1400x1000, owner gap 80 / 20 chars,
#                                       owner gap 200 / 10 chars -> c2-candidate-<browser>-<slot>.json
#   ratio 1.5 wide (recorded only):     same wrapper --dpr 1.5, owner gap 80 / 20 -> ratio-1.5/
#   ratio 1 (P2's cells, judge_p2.py --dir ratio-1): probe_typing_latency.py at the default size, owner gap 80 / 20,
#                                       owner gap 200 / 10, boundaries gap 200 / 10 -> ratio-1/p-candidate-<browser>-<slot>.json
# One browser at a time; nothing else CPU-heavy runs beside it (rule vv).  Verdicts are the judges', read afterwards.
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/136/guard/c2
T=wasm_sdk_probe/tools
LOG=$E/chain.txt
PAGE=b24d754a426706bb
mkdir -p $E/ratio-1.5 $E/ratio-1
ts() { date -u '+%FT%TZ'; }
say() { echo "$(ts) $*" >> $LOG; }
h() { sha256sum "$1" | cut -c1-16; }
D=$(h wasm_sdk_probe/dist/e2-editor-app.js)
if [ "$D" != $PAGE ]; then say "REFUSED dist $D (want $PAGE)"; exit 2; fi
say "START tree $(git rev-parse --short HEAD) dist $D view $(h $T/probe_typing_latency_view.py) probe $(h $T/probe_typing_latency.py) chrome-procs $(pgrep -fc '/chrome/chrome( |$)' || true) load $(cut -d' ' -f1-3 /proc/loadavg)"
one() {  # $1 out (no .json), rest = command
  local out=$1; shift
  timeout 600 "$@" --out $out.json > $out.stdout.txt 2>&1
  say "$(basename $out) exit $? :: $(tail -1 $out.stdout.txt | cut -c1-200)"
}
for B in chrome firefox; do
  one $E/c2-candidate-$B-owner-gap80 python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
  one $E/c2-candidate-$B-owner-gap200 python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 200 --chars 10
  one $E/ratio-1.5/c2-ratio1.5-$B-owner-gap80 python3 $T/probe_typing_latency_view.py --dpr 1.5 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
  one $E/ratio-1/p-candidate-$B-owner-gap80 python3 $T/probe_typing_latency.py --browser $B --document owner --gap 80 --chars 20
  one $E/ratio-1/p-candidate-$B-owner-gap200 python3 $T/probe_typing_latency.py --browser $B --document owner --gap 200 --chars 10
  one $E/ratio-1/p-candidate-$B-boundaries-gap200 python3 $T/probe_typing_latency.py --browser $B --document boundaries --gap 200 --chars 10
done
say "DONE"
