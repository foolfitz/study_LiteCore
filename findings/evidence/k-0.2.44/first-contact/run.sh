#!/usr/bin/env bash
# First contact before the K 0.2.44 restart (SPEC-M3-K-0.2.44 append 1).  Not a count: every report here is a shakedown,
# and nothing here is read by read-0.2.44.sh.  It exercises what the stopped chain never reached (host_entry, same_second,
# new_document, the autosave gate) and what the chain gives no shakedown at all (production UI, C2), after H1-H4, plus the
# read side (--red-cases, the C2 judges) on the reports it lands.  Every step runs even if an earlier one is red: the point
# is the whole list of reds, once.  The merge modes are not here: their reading waits for a ruling.
#   setsid nohup bash findings/evidence/k-0.2.44/first-contact/run.sh > /dev/null 2>&1 &
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
T=wasm_sdk_probe/tools
F=findings/evidence/k-0.2.44/first-contact
LOG=$F/log.txt
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
step() {  # name, command...
  local name=$1; shift
  say "BEGIN $name :: $*"
  "$@" > "$F/$name.stdout.txt" 2> "$F/$name.stderr.txt"
  local rc=$?
  say "END   $name exit $rc :: $(grep -E '^VERDICT|lands|LANDS|^red|^clean|DELIVERED|NEW-DOCUMENT|NOT_ESTABLISHED|refusing' "$F/$name.stdout.txt" "$F/$name.stderr.txt" | tail -1 | cut -c1-230)"
}
say "START tree $(git rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
step assets      python3 $T/check_m3_assets.py --label shakedown --repeats 1
step host_entry  python3 $T/check_m3_host_entry.py --label shakedown --repeats 1
step same_second python3 $T/check_m3_same_second.py --label shakedown --repeats 1
step new_document python3 $T/check_m3_new_document.py --label shakedown
step production_ui python3 $T/check_m3_production_ui.py --rounds 1 --arms Kdel,Kbs,Rbs,Rdel,Bctl,S,P --out "$PWD/$F/production-ui.json"

# C2, one full run as the chain's c2_run, then its two judges.
D=$F/c2/r1
mkdir -p "$D/ratio-1.5" "$D/ratio-1"
c2_one() { local out=$1; shift; timeout 600 "$@" --out "$out.json" > "$out.stdout.txt" 2>&1; say "c2 $(basename "$out") exit $?"; }
for B in chrome firefox; do
  c2_one "$D/c2-candidate-$B-owner-gap80"            python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
  c2_one "$D/c2-candidate-$B-owner-gap200"           python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 200 --chars 10
  c2_one "$D/ratio-1.5/c2-ratio1.5-$B-owner-gap80"   python3 $T/probe_typing_latency_view.py --dpr 1.5 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
  c2_one "$D/ratio-1/p-candidate-$B-owner-gap80"     python3 $T/probe_typing_latency.py --browser $B --document owner --gap 80 --chars 20
  c2_one "$D/ratio-1/p-candidate-$B-owner-gap200"    python3 $T/probe_typing_latency.py --browser $B --document owner --gap 200 --chars 10
  c2_one "$D/ratio-1/p-candidate-$B-boundaries-gap200" python3 $T/probe_typing_latency.py --browser $B --document boundaries --gap 200 --chars 10
done
step judge_c2 python3 -I findings/evidence/c-prime/c2/judge_c2.py --dir "$D"
step judge_p2 python3 -I findings/evidence/typing-latency/judge_p2.py --dir "$D/ratio-1"

step autosave python3 $T/check_m3_autosave.py --label shakedown --repeats 1

# The read side the chain's read-0.2.44.sh will use, on the newest shakedown report of each runner.
for r in page_honesty locks versions assets host_entry same_second; do
  rep=$(ls -t findings/evidence/m3-$(echo $r | tr _ -)/shakedown/*.json 2>/dev/null | head -1)
  step red-$r python3 $T/check_m3_$r.py --red-cases "$rep"
done
rep=$(ls -t findings/evidence/m3-autosave/shakedown/*.json | head -1); step red-autosave python3 $T/check_m3_autosave.py --red-cases "$rep"
rep=$(ls -t findings/evidence/new-document/shakedown/*.json 2>/dev/null | head -1); step red-new_document python3 $T/check_m3_new_document.py --red-cases "$rep"
step red-production_ui python3 $T/check_m3_production_ui.py --red-cases "$F/production-ui.json"
say "DONE"
