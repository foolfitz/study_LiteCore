#!/usr/bin/env bash
# Serve a directory with emrun (as on 2026-07-31) and run the unchanged probe wasm-lite/tools/pw/probe.js on one page.
# usage: run_probe.sh <serve-dir> <page.html> <port> <seconds> <out-prefix>
set -u
W=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite
SRV=$1; PAGE=$2; PORT=$3; SECS=$4; OUT=$5
source "$W/tools/emsdk/emsdk_env.sh" >/dev/null 2>&1
mkdir -p "$(dirname "$OUT")"
emrun --no_browser --hostname 127.0.0.1 --port "$PORT" "$SRV" > "$OUT.emrun.log" 2>&1 &
EMRUN=$!
for i in $(seq 1 50); do grep -q 'Now listening' "$OUT.emrun.log" && break; sleep 0.2; done
{
  echo "# probe: $W/tools/pw/probe.js (sha256 $(sha256sum "$W/tools/pw/probe.js" | cut -c1-16))"
  echo "# generated: $(date -Is)"
  echo "# URL: http://127.0.0.1:$PORT/$PAGE   served from $SRV"
  echo "# headers: $(curl -sI "http://127.0.0.1:$PORT/$PAGE" | grep -i -E '^cross-origin' | tr -d '\r' | tr '\n' ' ')"
} > "$OUT.txt"
( cd "$W/tools/pw" && timeout $((SECS + 120)) node probe.js "http://127.0.0.1:$PORT/$PAGE" "$SECS" "$OUT.png" ) >> "$OUT.txt" 2>&1
echo "# probe exit=$?" >> "$OUT.txt"
kill "$EMRUN" 2>/dev/null; wait "$EMRUN" 2>/dev/null
# emrun may be a wrapper; also stop whatever still listens on our port (exact PIDs only)
for p in $(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do kill "$p" 2>/dev/null; done
echo "$OUT.txt"
