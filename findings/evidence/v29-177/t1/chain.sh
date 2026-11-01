#!/usr/bin/env bash
# T1 (SPEC-M3-v29-tick-pacing section 6, append 2): C2, all 12 cells, 3 rounds, in the shape of the K chain's c2_run, on a clean
# desk (desk_gate before each round: a dirty desk stops the chain, it does not wait).  The judges are unedited; judge_on_83.py
# moves the page pin in process.  Nothing else may run meanwhile, the session included.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
T=wasm_sdk_probe/tools
F=findings/evidence/v29-177/t1
LOG=$F/log.txt
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
c2_one() { local out=$1; shift; timeout 600 "$@" --out "$out.json" > "$out.stdout.txt" 2>&1; say "c2 $(basename "$out") exit $?"; }
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
for R in 1 2 3; do
  D=$F/r$R
  python3 -I findings/evidence/link-batch-v22/shakedown/desk_gate.py > "$F/desk-gate-r$R.txt" 2>&1
  rc=$?
  say "desk gate r$R exit $rc :: $(tail -1 "$F/desk-gate-r$R.txt" | cut -c1-160)"
  if [ $rc -ne 0 ]; then say "STOP dirty desk before r$R"; exit 3; fi
  mkdir -p "$D/ratio-1.5" "$D/ratio-1"
  for B in chrome firefox; do
    c2_one "$D/c2-candidate-$B-owner-gap80"              python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
    c2_one "$D/c2-candidate-$B-owner-gap200"             python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 200 --chars 10
    c2_one "$D/ratio-1.5/c2-ratio1.5-$B-owner-gap80"     python3 $T/probe_typing_latency_view.py --dpr 1.5 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
    c2_one "$D/ratio-1/p-candidate-$B-owner-gap80"       python3 $T/probe_typing_latency.py --browser $B --document owner --gap 80 --chars 20
    c2_one "$D/ratio-1/p-candidate-$B-owner-gap200"      python3 $T/probe_typing_latency.py --browser $B --document owner --gap 200 --chars 10
    c2_one "$D/ratio-1/p-candidate-$B-boundaries-gap200" python3 $T/probe_typing_latency.py --browser $B --document boundaries --gap 200 --chars 10
  done
  python3 -I $F/judge_on_83.py c2 --dir "$D" > "$F/judge-c2-r$R.txt" 2>&1; say "judge_c2 r$R exit $?"
  python3 -I $F/judge_on_83.py p2 --dir "$D/ratio-1" > "$F/judge-p2-r$R.txt" 2>&1; say "judge_p2 r$R exit $?"
done
say "DONE load $(cut -d' ' -f1-3 /proc/loadavg)"
