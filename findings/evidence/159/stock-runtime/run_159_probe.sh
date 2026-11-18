#!/usr/bin/env bash
# Finding 159: serve a build's qt_soffice.html with emrun (COOP/COEP, as finding 186's run_keys_probe.sh does) and run
# probe_159.js on it.
# usage: run_159_probe.sh <build dir under wasm-lite/upstream-master, e.g. build-186-R> <port> <out-prefix> [<locale>]
set -u
W=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite
U=$W/upstream-master
HERE=$(cd "$(dirname "$0")" && pwd)
B=$1; PORT=$2; OUT=$3; LOC=${4:-}
SRV=$U/$B/workdir/installation/LibreOffice/emscripten
source "$W/tools/emsdk/emsdk_env.sh" >/dev/null 2>&1
mkdir -p "$(dirname "$OUT")"
emrun --no_browser --hostname 127.0.0.1 --port "$PORT" "$SRV" > "$OUT.emrun.log" 2>&1 &
EMRUN=$!
for i in $(seq 1 50); do grep -q 'Now listening' "$OUT.emrun.log" && break; sleep 0.2; done
{
  echo "# probe: probe_159.js (sha256 $(sha256sum "$HERE/probe_159.js" | cut -c1-16))  cases.json (sha256 $(sha256sum "$HERE/cases.json" | cut -c1-16))"
  echo "# generated: $(date -Is)   load: $(cut -d' ' -f1-3 /proc/loadavg)"
  echo "# URL: http://127.0.0.1:$PORT/qt_soffice.html   served from $SRV   locale: ${LOC:-browser default (LANG=${LANG:-unset})}"
  echo "# soffice.wasm sha256 $(sha256sum "$SRV/soffice.wasm" | cut -c1-16)  soffice.data sha256 $(sha256sum "$SRV/soffice.data" | cut -c1-16)"
} > "$OUT.txt"
NODE_PATH="$W/tools/pw/node_modules" timeout 300 node "$HERE/probe_159.js" "http://127.0.0.1:$PORT/qt_soffice.html" "$OUT" "$HERE/cases.json" $LOC >> "$OUT.txt" 2>&1
echo "# probe exit=$?" >> "$OUT.txt"
kill "$EMRUN" 2>/dev/null; wait "$EMRUN" 2>/dev/null
for p in $(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do kill "$p" 2>/dev/null; done
echo "$OUT.txt"
