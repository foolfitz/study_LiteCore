#!/usr/bin/env bash
# Finding 039 native caret-reset run.
#
# Distinguishes a selection callback that core does not emit from one lost by
# the WASM build by replaying repeated RESET operations against native core.
#
# Usage: tools/run_f039_native.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/f039-native}"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/f039-native-caret-reset"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/f039_native_caret_reset.cpp" -ldl -o "$probe"

fixture="$here/test-docs/e1/list-contexts.odt"
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
echo "-- per-arm callback counts and summary --"
cat "$out/callbacks.jsonl"
echo
echo "full output in $out"
exit "$status"
