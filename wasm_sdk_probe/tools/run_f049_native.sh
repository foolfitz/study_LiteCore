#!/usr/bin/env bash
# Task #49 native run: which part of the format barrier breaks the next range
# selection?
#
# Prediction is in
# findings/evidence/sdk-e2/discovery/049-selection-after-format/PREDICTION.md
# and was committed before this script ever ran.
#
# Usage: tools/run_f049_native.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/f049-native}"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/f049-native-select-after-format"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/f049_native_select_after_format.cpp" -ldl -o "$probe"

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
  >"$out/arms.jsonl" 2>"$out/sal.log"
status=$?
set -e

echo "== probe exit: $status =="
echo
echo "-- per-arm result --"
cat "$out/arms.jsonl"
echo
echo "full output in $out"
exit "$status"
