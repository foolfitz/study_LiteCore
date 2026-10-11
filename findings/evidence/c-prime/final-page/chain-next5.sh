#!/usr/bin/env bash
# Next 5 on the final C′ page (dist 8909564eb2316afa), the parts that are not latency measurements:
#   A. ruling-1 condition 3: C3 / C4 on the two red pages (c34/red-pages/, made from this page) -- both must go
#      red (never-stale-outside: C4, typing arm; label-at-reply: the bold arm, typing recorded); if either is
#      not red in a browser, STOP: nothing after it runs.
#   B. C3 / C4 on the real page: three arms, both browsers, --c4.
#   C. C6 on the C′ page: 40 p ratio 2 wide, 50 p ratio 1.5 wide, controls 24 p / 33 p, both browsers; judged
#      by the DRAWN criterion pinned in review/DISPOSITION-tools.md (not judged here).
#   D. 124-B / 125-B: 40 presses, 5 letters, 1400x1000, both browsers.
# One browser at a time.  Exit codes are recorded; verdicts are read from the reports afterwards.
set -u
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
E=findings/evidence/c-prime/final-page
T=wasm_sdk_probe/tools
RED=findings/evidence/c-prime/c34/red-pages
LOG=$E/chain.txt
PAGE=8909564eb2316afa
mkdir -p $E/c34-red $E/c34 $E/c6 $E/arrows
ts() { date -u '+%FT%TZ'; }
say() { echo "$(ts) $*" >> $LOG; }
h() { sha256sum "$1" | cut -c1-16; }
D=$(h wasm_sdk_probe/dist/e2-editor-app.js)
if [ "$D" != $PAGE ]; then say "REFUSED dist $D (want $PAGE)"; exit 2; fi
say "START tree $(git rev-parse --short HEAD) dist $D window-probe $(h $T/probe_c_prime_window.py) c6 $(h $T/probe_c6_long_document.py) arrows $(h $T/probe_124_125_arrows.py) pp $(h $T/run_e2_c_product_path.py) red never-stale-outside $(h $RED/never-stale-outside.js) label-at-reply $(h $RED/label-at-reply.js)"

win() {  # $1 out-name, then probe args
  local out=$1; shift
  timeout 900 python3 $T/probe_c_prime_window.py "$@" --out $out.json > $out.stdout.txt 2>&1
  local rc=$?
  say "window $(basename $out) exit $rc :: $(tail -1 $out.stdout.txt | cut -c1-220)"
  return $rc
}

# A. red cases
red_ok=1
for B in chrome firefox; do
  win $E/c34-red/never-stale-outside-$B-typing-c4 --browser $B --arm typing --c4 --page $RED/never-stale-outside.js
  [ $? -eq 1 ] || { red_ok=0; say "RED CASE NOT RED: never-stale-outside $B"; }
  win $E/c34-red/label-at-reply-$B-bold --browser $B --arm bold --page $RED/label-at-reply.js
  [ $? -eq 1 ] || { red_ok=0; say "RED CASE NOT RED: label-at-reply bold $B"; }
  win $E/c34-red/label-at-reply-$B-typing --browser $B --arm typing --page $RED/label-at-reply.js
done
if [ $red_ok -ne 1 ]; then say "STOP: a condition-3 red case was not red; B, C, D not run"; exit 1; fi
say "condition 3: both red cases red in both browsers"

# B. the real page
for B in chrome firefox; do
  for A in typing backspace bold; do
    win $E/c34/real-$B-$A-c4 --browser $B --arm $A --c4
  done
done

# C. C6
for B in chrome firefox; do
  for spec in "40 2" "24 2" "50 1.5" "33 1.5"; do
    set -- $spec
    out=$E/c6/cprime-$B-$(printf %02d $1)p-dpr$2-1400x1000
    timeout 900 python3 $T/probe_c6_long_document.py --browser $B --pages $1 --dpr $2 --window 1400x1000 --out $out.json > $out.stdout.txt 2>&1
    say "c6 $B $1p dpr$2 exit $? :: $(tail -1 $out.stdout.txt | cut -c1-220)"
  done
done

# D. 124-B / 125-B
for B in chrome firefox; do
  out=$E/arrows/arrows-$B-40-5-1400x1000
  timeout 900 python3 $T/probe_124_125_arrows.py --browser $B --presses 40 --letters 5 --window 1400x1000 --out $out.json > $out.stdout.txt 2>&1
  say "arrows $B exit $? :: $(tail -1 $out.stdout.txt | cut -c1-220)"
done
say "DONE"
