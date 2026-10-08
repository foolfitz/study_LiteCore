#!/bin/bash
# Finding 117 diagnosis: M2-1b again (the first attempt lost its CDP connection at its 5th record, 12:11:33,
# the same second the KDE screen locker started; attempt1/).  Same runner, same profile, same command.
V=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v18/diag-117
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 99
LOG=$V/chain.log
ts() { date '+%F %T %z'; }
snap() { ps -eo pid,etime,pcpu,comm --sort=-pcpu | head -12 > "$V/$1"; }
R=tools/run_merge_wasm_shakedown.py
echo "$(ts) RERUN START runner $(sha256sum $R | cut -c1-16)" >> $LOG
step() { local name=$1; shift; snap "$name.ps-before.txt"; echo "$(ts) START $name :: $*" >> $LOG
  "$@" > $V/$name.stdout.txt 2> $V/$name.stderr.txt; echo "$(ts) END   $name exit=$?" >> $LOG; snap "$name.ps-after.txt"; }
step profile-check-rerun python3 tools/build_merge_trace_profile.py --check
step m2-1b-chrome python3 $R --browser chrome --mode m2-1b --candidate-profile e2-editor-v18-trace117 --out $V/m2-1b-chrome.json
echo "$(ts) RERUN DONE runner $(sha256sum $R | cut -c1-16)" >> $LOG
