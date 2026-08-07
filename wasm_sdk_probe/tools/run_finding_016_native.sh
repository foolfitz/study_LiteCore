#!/usr/bin/env bash
# Finding 016 native comparison run.
#
# Asks a native stock-configured LibreOffice 26.8 the same question the
# e1-editor-discovery WASM profile answered with silence: does a forward delete
# that leaves caret geometry unchanged emit any documented LOK callback?
#
# Run with SAL_USE_VCLPLUGIN=svp so the comparison matches how Collabora Online
# actually runs LibreOfficeKit (headless backend, normal build) rather than a
# --disable-gui build, which would leave a negative result ambiguous.
#
# Usage: tools/run_finding_016_native.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/finding-016-native}"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir -- has 'make' finished?" >&2
  exit 1
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/finding-016-native-lok"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/finding_016_native_lok.cpp" -ldl -o "$probe"

fixture="$here/test-docs/e1/plain-grapheme.odt"
if [ ! -f "$fixture" ]; then
  echo "fixture missing: $fixture" >&2
  exit 1
fi

echo "== running probe =="
echo "   install:  $install_dir"
echo "   fixture:  $fixture"

# SAL_LOG surfaces whether the accessibility focus listener actually attaches.
# Finding 016 could not distinguish "listener never attached" from "focused
# paragraph is genuinely empty", because getA11yFocusedParagraph() only ever
# serialises cached members. The lok.a11y log answers it directly.
set +e
SAL_USE_VCLPLUGIN=svp \
SAL_LOG="+INFO.lok.a11y+WARN" \
"$probe" \
  "$install_dir" \
  "file://$profile_dir" \
  "file://$fixture" \
  >"$out/callbacks.jsonl" 2>"$out/sal.log"
status=$?
set -e

echo "== probe exit: $status =="
echo
echo "-- callback stream --"
cat "$out/callbacks.jsonl"
echo
echo "-- verdict line --"
grep '"verdict"' "$out/callbacks.jsonl" || echo "(no verdict emitted -- probe died early)"
echo
echo "-- did INVALIDATE_TILES (id 0) appear? --"
if grep -q '"callback":0,' "$out/callbacks.jsonl"; then
  echo "yes"
else
  echo "no (open question -- native did not emit it either)"
fi
echo
# Tile invalidation alone is the wrong headline: the decisive comparison is
# whether core emits *any* content-derived signal that the WASM profile misses.
# .uno:StateWordCount carries a character count, so it changes exactly when the
# document text does.
echo "-- deferred STATE_CHANGED stream (id 8) --"
echo "   count: $(grep -c '"callback":8,' "$out/callbacks.jsonl")"
echo "   content-derived signal across the mutation:"
grep -o 'StateWordCount=[^"]*' "$out/callbacks.jsonl" | sed 's/^/     /'
echo
echo "-- a11y listener attach evidence --"
grep -i "attach\|LOKDocumentFocusListener\|accessib" "$out/sal.log" | head -20 \
  || echo "(no lok.a11y lines)"
echo
echo "full output in $out"
