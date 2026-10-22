#!/usr/bin/env bash
# W0 (SPEC-M3-production-ui 17.27): does a headless Chrome with the launcher's flags reach a local http page
# in the machine's current wallet state, with and without --password-store=basic?  One fresh profile per
# arm; `--dump-dom` of a page served on 127.0.0.1; 90 s cap.  The wallet's D-Bus state is read before and
# after each arm (whether the secrets service / kwalletd6 is running, and Locked).
#   bash w0-dump-dom.sh OUTDIR
set -u
out=${1:?outdir}; mkdir -p "$out"
site=$(mktemp -d); printf '<!doctype html><title>w0</title><p id=x>w0-page-reached</p>\n' > "$site/index.html"
port=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
python3 -m http.server "$port" --bind 127.0.0.1 --directory "$site" >/dev/null 2>&1 & srv=$!
sleep 1
state() {
  echo "  running: $(busctl --user list 2>/dev/null | awk '$2 != "-" && /kwallet|secret|ksecretd/ {print $1"("$3")"}' | tr '\n' ' ')"
  echo "  Locked: $(busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked 2>&1)"
}
for arm in default basic; do
  prof=$(mktemp -d)
  extra=(); [ "$arm" = basic ] && extra=(--password-store=basic)
  { echo "== arm $arm $(date -Is)"; echo "before:"; state; } >> "$out/w0.txt"
  start=$(date +%s.%N)
  timeout 90 google-chrome --headless=new --user-data-dir="$prof" --no-first-run --no-default-browser-check \
    "${extra[@]}" --dump-dom "http://127.0.0.1:$port/" > "$out/w0-$arm.dom" 2> "$out/w0-$arm.stderr"
  rc=$?
  end=$(date +%s.%N)
  { echo "exit $rc after $(python3 -c "print(round($end-$start,2))") s; page reached: $(grep -c w0-page-reached "$out/w0-$arm.dom")"; echo "after:"; state; } >> "$out/w0.txt"
  pkill -f "user-data-dir=$prof" 2>/dev/null; rm -rf "$prof"
done
kill $srv; rm -rf "$site"
google-chrome --version >> "$out/w0.txt"
