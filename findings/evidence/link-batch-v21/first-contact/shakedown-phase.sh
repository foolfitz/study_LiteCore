#!/usr/bin/env bash
# First contact (2026-10-17, before the owner's count window): the chain's shakedown phase exactly as
# ../../m3-production-ui/runs-0.2.26/chain-0.2.26.sh runs it (six M3 runners, the autosave gate, new-document), on host
# 0.2.26 / v21, so a red is found before the window and not by the chain's STOP rule.  Not part of any count.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
T=wasm_sdk_probe/tools
O=findings/evidence/link-batch-v21/first-contact
say() { echo "$(date -u +%FT%TZ) $*" | tee -a $O/shakedown-phase.txt; }
say "START tree $(git rev-parse --short HEAD) host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) load $(cut -d' ' -f1-3 /proc/loadavg)"
for r in page_honesty locks versions assets host_entry same_second; do
  python3 $T/check_m3_$r.py --label shakedown --repeats 1 > "$O/shakedown-$r.log" 2>&1
  say "shakedown $r exit $? :: $(grep -E '^VERDICT|lands|LANDS' "$O/shakedown-$r.log" | tail -1 | cut -c1-200)"
done
python3 $T/check_m3_autosave.py --label shakedown --arms as2-key,as4a,as5 --repeats 1 > "$O/shakedown-autosave.log" 2>&1
say "shakedown autosave exit $? :: $(grep -E '^VERDICT' "$O/shakedown-autosave.log" | tail -1 | cut -c1-200)"
python3 $T/check_m3_new_document.py --label shakedown > "$O/shakedown-new_document.log" 2>&1
say "shakedown new_document exit $? :: $(grep -E 'NEW-DOCUMENT|NOT_ESTABLISHED|refusing' "$O/shakedown-new_document.log" | tail -1 | cut -c1-200)"
say "DONE"
