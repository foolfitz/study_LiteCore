#!/bin/bash
# Finding 117 diagnosis (PREDICTION.md): M2-4 then M2-1b on e2-editor-v18-trace117, Chrome, one tool at a time.
# Launched detached (setsid nohup) so it survives the launching session (handoff rule h).  No pgrep/pkill (rule e).
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v18/diag-117
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
ts() { date '+%F %T %z'; }
snap() { ps -eo pid,etime,pcpu,comm --sort=-pcpu | head -12 > "$V/$1"; }
R=tools/run_merge_wasm_shakedown.py
echo "$(ts) CHAIN START runner $(sha256sum $R | cut -c1-16)" >> $LOG
step() { # name, command...
  local name=$1; shift
  snap "$name.ps-before.txt"
  echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt
  echo "$(ts) END   $name exit=$?" >> $LOG
  snap "$name.ps-after.txt"
}
step profile-check python3 tools/build_merge_trace_profile.py --check
step m2-4-chrome python3 $R --browser chrome --mode m2-4 --candidate-profile e2-editor-v18-trace117 --out $V/m2-4-chrome.json
step m2-1b-chrome python3 $R --browser chrome --mode m2-1b --candidate-profile e2-editor-v18-trace117 --out $V/m2-1b-chrome.json
step profile-check-after python3 tools/build_merge_trace_profile.py --check
echo "$(ts) CHAIN DONE runner $(sha256sum $R | cut -c1-16)" >> $LOG
