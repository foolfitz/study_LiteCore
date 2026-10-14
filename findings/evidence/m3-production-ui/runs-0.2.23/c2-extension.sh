#!/usr/bin/env bash
# C2 extension r4-r6 (ruling handoff/RULING-2026-10-15-pre-binding.md J-b.2, row "1 x PASS, 2 x FAIL both attributable
# to 135 -> one extension, once: three more runs, the same way").  NOT part of chain-0.2.23.sh: the main session runs
# this only after reading r1-r3's judge lines and finding exactly that row (the reading table is applied by the reader,
# W-b2 is not built).  Same shape as the chain's c2_run (findings/evidence/136/guard-r2/c2/chain-c2.sh), with an identity
# check first: the bytes must still be the bound ones, or the six verdicts would not be about one page.
#   bash findings/evidence/m3-production-ui/runs-0.2.23/c2-extension.sh
set -u
REPO=/home/jiajun/LibreOffice/study_LiteCore
cd "$REPO" || exit 9
T=wasm_sdk_probe/tools
C2=findings/evidence/release-0.2.23/c2
PAGE=ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e
VIEW_PIN=1412e4c863de6fcb      # judge_c2.py RUNNER: "probe_typing_latency_view.py 1412e4c863de6fcb over probe dbad93c0dcf27fbf"
PROBE_PIN=dbad93c0dcf27fbf     # judge_p2.py RUNNER
OURS='probe_|judge_|check_m3|run_e2_c|run_merge|run_v20'
h() { sha256sum "$1" | cut -c1-16; }
ts() { date -u +%FT%TZ; }

# ---- identity: the bytes are still the bound ones (dist = web = the pinned page; the probes are the judges' pins;
# the judges' PAGE lines still name the page); r1-r3 exist and r4-r6 do not.
bad=0
dist=$(h wasm_sdk_probe/dist/e2-editor-app.js); web=$(h wasm_sdk_probe/web/e2-editor-app.js)
view=$(h $T/probe_typing_latency_view.py); probe=$(h $T/probe_typing_latency.py)
echo "$(ts) identity: dist $dist web $web (want ${PAGE:0:16}); view $view (pin $VIEW_PIN); probe $probe (pin $PROBE_PIN)"
[ "$dist" = "${PAGE:0:16}" ] && [ "$web" = "$dist" ] || { echo "REFUSED: the page moved"; bad=1; }
[ "$view" = "$VIEW_PIN" ] && [ "$probe" = "$PROBE_PIN" ] || { echo "REFUSED: a probe moved under the judges' RUNNER pins"; bad=1; }
grep -q "^PAGE = \"$PAGE\"" findings/evidence/c-prime/c2/judge_c2.py && grep -q "^PAGE = \"$PAGE\"" findings/evidence/typing-latency/judge_p2.py \
  || { echo "REFUSED: a judge's PAGE pin is not $PAGE"; bad=1; }
for K in 1 2 3; do [ -s "$C2/r$K/chain.txt" ] || { echo "REFUSED: $C2/r$K has no chain.txt (r1-r3 must exist first)"; bad=1; }; done
for K in 4 5 6; do [ -e "$C2/r$K" ] && { echo "REFUSED: $C2/r$K already exists (the extension runs once)"; bad=1; }; done
n=$(pgrep -af "$OURS" | grep -v -F -- "$0" | grep -c . || true)
[ "$n" -eq 0 ] || { echo "REFUSED: $n of our process(es) running"; pgrep -af "$OURS" | grep -v -F -- "$0"; bad=1; }
w=$(busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked 2>&1)
[ "$w" = "b false" ] || { echo "REFUSED: kdewallet Locked = [$w]"; bad=1; }
[ $bad -eq 0 ] || exit 3

c2_one() {  # dir out-stem, command...
  local d=$1 out=$2; shift 2
  timeout 600 "$@" --out "$out.json" > "$out.stdout.txt" 2>&1
  echo "$(ts) $(basename "$out") exit $? :: $(tail -1 "$out.stdout.txt" | cut -c1-200)" >> "$d/chain.txt"
}
for K in 4 5 6; do
  D=$C2/r$K
  mkdir -p "$D/ratio-1.5" "$D/ratio-1"
  { echo "$(ts) pgrep -c chrome: $(pgrep -c chrome || true)"; echo "Chrome browsers (pgrep -fc '/opt/google/chrome/chrome( |$)'): $(pgrep -fc '/opt/google/chrome/chrome( |$)' || true)"
    echo "/proc/loadavg: $(cat /proc/loadavg)"; echo "pgrep -af '$OURS' (ours): $(pgrep -af "$OURS" | grep -v -F -- "$0" | tr '\n' ' ')"; echo "firefox processes at start: $(pgrep -c firefox || true)"
    echo "note: extension run r$K (J-b.2 row 3), started by hand after reading r1-r3"; } > "$D/desk-at-start.txt"
  echo "$(ts) START tree $(git rev-parse --short HEAD) dist $dist view $view probe $probe chrome-procs $(pgrep -fc '/chrome/chrome( |$)' || true) load $(cut -d' ' -f1-3 /proc/loadavg)" >> "$D/chain.txt"
  echo "$(ts) c2 r$K begin"
  for B in chrome firefox; do
    c2_one "$D" "$D/c2-candidate-$B-owner-gap80"              python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
    c2_one "$D" "$D/c2-candidate-$B-owner-gap200"             python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 200 --chars 10
    c2_one "$D" "$D/ratio-1.5/c2-ratio1.5-$B-owner-gap80"     python3 $T/probe_typing_latency_view.py --dpr 1.5 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
    c2_one "$D" "$D/ratio-1/p-candidate-$B-owner-gap80"       python3 $T/probe_typing_latency.py --browser $B --document owner --gap 80 --chars 20
    c2_one "$D" "$D/ratio-1/p-candidate-$B-owner-gap200"      python3 $T/probe_typing_latency.py --browser $B --document owner --gap 200 --chars 10
    c2_one "$D" "$D/ratio-1/p-candidate-$B-boundaries-gap200" python3 $T/probe_typing_latency.py --browser $B --document boundaries --gap 200 --chars 10
  done
  echo "$(ts) DONE" >> "$D/chain.txt"
  echo "$(ts) c2 r$K done :: $(grep -c ' exit 0 ' "$D/chain.txt") of 12 cells exit 0"
done
echo "$(ts) extension DONE; judge each: python3 -I findings/evidence/c-prime/c2/judge_c2.py --dir $C2/rK ; python3 -I findings/evidence/typing-latency/judge_p2.py --dir $C2/rK/ratio-1"
