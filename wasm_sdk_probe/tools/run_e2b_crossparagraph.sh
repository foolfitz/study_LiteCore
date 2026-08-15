#!/usr/bin/env bash
# SPEC E2-B 9.7: run the three checks that decide B' against A.
#
# Prediction, committed before the probe existed:
# findings/evidence/sdk-e2/discovery/e2b-crossparagraph/PREDICTION.md
#
# Compiles standalone, deliberately: adding a target to the Makefile would
# relink probe.wasm (finding 042) and these checks exist to de-risk that relink,
# not to spend it.  The Makefile entry is owed and is listed in SPEC E2-B 5.2
# with the other deferred one.
#
# Usage: tools/run_e2b_crossparagraph.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/e2b-crossparagraph}"
mkdir -p "$out"
# Absolute: the profile goes to lok_init_2 as a file:// URL and a relative one
# fails userinstall with an error that reads like a broken build.
out="$(cd "$out" && pwd)"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"
saved="$out/saved"
rm -rf "$saved"
mkdir -p "$saved"

probe="$out/e2b-native-crossparagraph"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/e2b_native_crossparagraph.cpp" -ldl -o "$probe"

# Second and third arguments select the misfire-control fixture (SPEC E2-B 9.9
# flip condition 2); with none, this is the multi-paragraph run.
fixture="${2:-$here/test-docs/e1/multi-paragraph.odt}"
first_anchor="${3:-}"
second_anchor="${4:-}"
if [ ! -f "$fixture" ]; then
  echo "fixture missing: $fixture" >&2
  exit 1
fi

echo "== running probe =="
echo "   install: $install_dir"
echo "   fixture: $fixture"
echo "   saved:   $saved"

set +e
SAL_USE_VCLPLUGIN=svp \
"$probe" \
  "$install_dir" \
  "file://$profile_dir" \
  "file://$fixture" \
  "$saved" \
  ${first_anchor:+"$first_anchor" "$second_anchor"} \
  >"$out/arms.jsonl" 2>"$out/sal.log"
status=$?
set -e

echo "== probe exit: $status =="
echo
cat "$out/arms.jsonl"
echo
echo "full output in $out"
exit "$status"
