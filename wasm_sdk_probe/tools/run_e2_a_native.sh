#!/usr/bin/env bash
# E2-A A2 native state-readback run.
#
# Answers the precondition the whole E2-A barrier design rests on: do
# .uno:DefaultBullet, .uno:DefaultNumbering and .uno:StyleApply actually reach a
# LibreOfficeKit client, and what exact strings does StyleApply carry?
#
# Native first, for the same reason Finding 016 ended up needing it: a negative
# result from the WASM profile alone cannot tell "core never sends this" apart
# from "our build does not receive it". Running native first also yields the
# StyleApply strings, which the barrier has to match exactly and which cannot be
# guessed safely.
#
# Usage: tools/run_e2_a_native.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/e2-a-native}"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/e2-a-native-state-readback"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/e2_a_native_state_readback.cpp" -ldl -o "$probe"

fixture="$here/test-docs/e1/styled-list.odt"
if [ ! -f "$fixture" ]; then
  echo "fixture missing: $fixture" >&2
  exit 1
fi

echo "== running probe =="
echo "   install:  $install_dir"
echo "   fixture:  $fixture"

set +e
SAL_USE_VCLPLUGIN=svp \
"$probe" \
  "$install_dir" \
  "file://$profile_dir" \
  "file://$fixture" \
  "$out" \
  >"$out/callbacks.jsonl" 2>"$out/sal.log"
status=$?
set -e

echo "== probe exit: $status =="
echo
echo "-- STATE_CHANGED payloads for the three watched commands --"
grep -o '\.uno:\(DefaultBullet\|DefaultNumbering\|StyleApply\)=[^"]*' \
  "$out/callbacks.jsonl" | sort | uniq -c | sed 's/^/   /' \
  || echo "   (none -- A2 fails, barrier design cannot proceed)"
echo
echo "-- distinct StyleApply values (barrier must match these exactly) --"
grep -o '\.uno:StyleApply=[^"]*' "$out/callbacks.jsonl" | sort -u | sed 's/^/   /' \
  || echo "   (none)"
echo
echo "-- did UNO_COMMAND_RESULT arrive for any dispatched command? --"
# The callback name in the stream is the full LOK_CALLBACK_ prefixed form.
# Matching the short name here silently reports zero for every run, which is
# how the first pass of this script produced a wrong headline.
echo "   count: $(grep -c 'LOK_CALLBACK_UNO_COMMAND_RESULT' "$out/callbacks.jsonl" || true)"
grep -o '"commandName": "[^"]*", "success": [a-z]*' "$out/callbacks.jsonl" \
  | sed 's/^/   /' || echo "   (none)"
echo
echo "-- saved postcondition documents --"
ls -1 "$out"/after-*.odt 2>/dev/null | sed 's/^/   /' || echo "   (none saved)"
echo
echo "full output in $out"
