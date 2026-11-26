#!/usr/bin/env bash
# Finding 186: serve one arm's qt_soffice.html with emrun (COOP/COEP, as run_probe.sh does) and run probe_keys.js on it.
# usage: run_keys_probe.sh <arm: M|R|PRE> <port> <out-prefix>
set -u
W=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite
U=$W/upstream-master
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=$1; PORT=$2; OUT=$3
# PRE = the stock build of 2a2335cf0911 from 2026-11-11 (before the regression)
if [ "$ARM" = PRE ]; then B=build-nosym; else B=build-186-$ARM; fi
SRV=$U/$B/workdir/installation/LibreOffice/emscripten
source "$W/tools/emsdk/emsdk_env.sh" >/dev/null 2>&1
mkdir -p "$(dirname "$OUT")"
emrun --no_browser --hostname 127.0.0.1 --port "$PORT" "$SRV" > "$OUT.emrun.log" 2>&1 &
EMRUN=$!
for i in $(seq 1 50); do grep -q 'Now listening' "$OUT.emrun.log" && break; sleep 0.2; done
{
  echo "# probe: probe_keys.js (sha256 $(sha256sum "$HERE/probe_keys.js" | cut -c1-16))"
  echo "# generated: $(date -Is)   load: $(cut -d' ' -f1-3 /proc/loadavg)"
  echo "# URL: http://127.0.0.1:$PORT/qt_soffice.html   served from $SRV"
} > "$OUT.txt"
NODE_PATH="$W/tools/pw/node_modules" timeout 240 node "$HERE/probe_keys.js" "http://127.0.0.1:$PORT/qt_soffice.html" "$OUT" >> "$OUT.txt" 2>&1
echo "# probe exit=$?" >> "$OUT.txt"
kill "$EMRUN" 2>/dev/null; wait "$EMRUN" 2>/dev/null
for p in $(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do kill "$p" 2>/dev/null; done
echo "$OUT.txt"
