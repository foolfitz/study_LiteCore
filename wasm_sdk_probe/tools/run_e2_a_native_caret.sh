#!/usr/bin/env bash
# Finding 021 decisive experiment, native side.
#
# A2-native and A2-wasm disagreed about whether paragraph format state follows
# the caret.  They also moved the caret differently -- native with .uno:GoDown,
# WASM with search + setTextSelection and with mouse clicks -- so the two runs
# never tested the same thing.  This runs all three movement methods against the
# same document on the same core commit, leaving the movement method as the only
# variable.
#
# Usage: tools/run_e2_a_native_caret.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/e2-a-native-caret}"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/e2-a-native-caret-tracking"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/e2_a_native_caret_tracking.cpp" -ldl -o "$probe"

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

# The verdict comes from the analyzer, not from a grep in this script.  The
# previous native runner printed a headline that a prefix mismatch had made
# wrong; summary lines here stay descriptive and the judgement lives in one
# place that can be re-run against the retained stream.
python3 "$here/tools/analyze_e2_a_native_caret.py" "$out/callbacks.jsonl" \
  --output "$out/analysis.json"

echo
echo "full output in $out"
