#!/usr/bin/env bash
# Finding 045 native run: do the four inline format commands become setters when
# the parameter is sent?
#
# Native first, and for the reason finding 016 needed native too: a negative
# result on the WASM build alone cannot separate "core does not accept this
# argument form" from "our build does not send it properly".  Nothing this
# script produces describes the WASM artifact.
#
# Predictions were registered before the probe was written, in
# findings/evidence/045/native/PREDICTION.md.  The judging is offline, in
# tools/analyze_f045_native.py, so the run and the criteria stay separable.
#
# Usage: tools/run_f045_native.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/../findings/evidence/045/native/run}"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/f045-native"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/f045_native_inline_format_arguments.cpp" -ldl -o "$probe"

fixture="$here/test-docs/e2/d1-anchors.odt"
if [ ! -f "$fixture" ]; then
  echo "fixture missing: $fixture" >&2
  exit 1
fi

echo "== running probe =="
echo "   install:  $install_dir"
echo "   fixture:  $fixture"
echo "   output:   $out"

set +e
SAL_USE_VCLPLUGIN=svp \
"$probe" \
  "$install_dir" \
  "file://$profile_dir" \
  "file://$fixture" \
  "$out" \
  >"$out/arms.jsonl" 2>"$out/sal.log"
status=$?
set -e

echo "== probe exit: $status =="
echo
echo "-- documents saved --"
ls -1 "$out"/after-*.odt 2>/dev/null | sed 's/^/   /' || echo "   (none)"
echo
echo "Judge with: python3 tools/analyze_f045_native.py $out"
