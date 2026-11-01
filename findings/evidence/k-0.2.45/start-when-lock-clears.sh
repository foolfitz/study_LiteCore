#!/usr/bin/env bash
# The owner said go at 01:35 with the hand-test editor still open in Firefox (a LOCK heartbeat every 60 s).  The chain's runners clear the whole
# lock table, so it must not start over a live session, and the owner's desktop is not ours to touch.  So: wait for the table to empty, the X on
# the editor releases at once, a closed tab expires in 5 minutes; then start the chain, then stay until it exits.  Gives up after two hours.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
export PATH="$PWD/wasm_sdk_probe/host-stack/bin:$PATH"
K=findings/evidence/k-0.2.45
L=$K/start-when-lock-clears.log
WINDOW='the run to DONE, about 8-10 hours, agreed by the owner at 2026-11-02 01:35 +0800: 手測完成，都符合預期／請繼續跑'
say() { echo "$(date +%FT%T%z) $*" >> "$L"; }
deadline=$(( $(date +%s) + 7200 ))
say "waiting for an empty lock table"
while :; do
  n=$(cd "$HOME/Projects/Nextcloud_Apps/litecore" && ddev mysql -B -N -e "SELECT COUNT(*) FROM oc_files_lock;" 2>&1 | tail -1)
  [ "$n" = "0" ] && break
  python3 -I $K/clear_expired_read.py >> "$L" 2>&1
  if [ "$(date +%s)" -gt "$deadline" ]; then say "GAVE UP: $n row(s) after two hours; the chain did not start"; exit 3; fi
  sleep 20
done
say "lock table empty, starting the chain"
setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.45/chain-0.2.45.sh --owner-window "$WINDOW" > "$K/chain-launch.out" 2>&1 < /dev/null &
sleep 3
pid=$(pgrep -f 'chain-0.2.45.sh --owner-window' | head -1)
[ -n "$pid" ] || { say "NO CHAIN PROCESS"; tail -3 "$K/chain-launch.out" >> "$L"; exit 4; }
say "chain pid $pid"
tail --pid="$pid" -f /dev/null
say "chain exited"
tail -3 "$K/chain-launch.out" >> "$L"
