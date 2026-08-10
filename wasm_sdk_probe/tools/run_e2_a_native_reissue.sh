#!/usr/bin/env bash
# E2-A native re-issue run.
#
# Answers the one question product route C created and never checked: with the
# precondition read removed, pressing the same closed action twice dispatches
# twice.  Are the five paragraph-level commands setters (safe) or toggles (the
# second press undoes the first)?
#
# The verdict lives in analyze_e2_a_native_reissue.py, not in a summary line
# here.  Last time this script computed its own headline it got it wrong with a
# prefix match, and the wrong headline is harder to notice than a wrong number.
#
# Usage: tools/run_e2_a_native_reissue.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/e2-a-native-reissue}"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/e2-a-native-reissue"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/e2_a_native_reissue.cpp" -ldl -o "$probe"

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

python3 "$here/tools/analyze_e2_a_native_reissue.py" \
  --run "$out" --fixture "$fixture" --output "$out/analysis.json"

echo
echo "full output in $out"
