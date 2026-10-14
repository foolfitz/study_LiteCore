#!/bin/bash
# usage: health.sh LABEL   (appends to the evidence health-checks.txt; exit 3 = KWallet locked, 4 = something of ours running, 5 = chrome check failed)
LABEL="$1"
OUT=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.23/h1-h2/health-checks.txt
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
W=$(busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked 2>&1)
echo "[$LABEL] $(ts) wallet: $W" | tee -a $OUT
if [ "$W" = "b true" ]; then echo "[$LABEL] STOP: KWallet locked" | tee -a $OUT; exit 3; fi
TMPD=$(mktemp -d /tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/30f3fb46-c713-4ab4-a4a4-79969d084998/scratchpad/chk-XXXXXX)
N=$(timeout 30 google-chrome --headless=new --user-data-dir=$TMPD --dump-dom https://litecore.ddev.site:8443/login 2>/dev/null | grep -o Nextcloud | wc -l); RC=$?
rm -rf $TMPD
echo "[$LABEL] $(ts) chrome --dump-dom Nextcloud x$N" | tee -a $OUT
if [ "$N" -lt 10 ]; then echo "[$LABEL] STOP: chrome check failed" | tee -a $OUT; exit 5; fi
OURS=$(pgrep -af 'probe_|judge_|check_m3|run_e2_c|run_merge|run_v20' | grep -v pgrep | grep -v "health" | grep -v queue | grep -v admin_root | wc -l)
echo "[$LABEL] pgrep -c chrome=$(pgrep -c chrome) chromeBrowsers=$(pgrep -fc '/opt/google/chrome/chrome( |$)') pgrep -c firefox=$(pgrep -c firefox) load=$(cut -d' ' -f1-3 /proc/loadavg) ours-running=$OURS" | tee -a $OUT
if [ "$OURS" != "0" ]; then echo "[$LABEL] STOP: ours running" | tee -a $OUT; pgrep -af 'probe_|judge_|check_m3|run_e2_c|run_merge|run_v20' | grep -v pgrep | tee -a $OUT; exit 4; fi
exit 0
