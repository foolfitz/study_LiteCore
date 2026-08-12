#!/usr/bin/env bash
# E2-A native paragraph-content HTML readback probe.
#
# Usage: tools/run_e2_a_paragraph_content.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/e2-a-paragraph-content}"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

fixture="$here/test-docs/e1/paragraph-content.odt"
if [ ! -f "$fixture" ]; then
  echo "fixture missing: $fixture" >&2
  exit 1
fi

expected_fixture_sha="920ca5d51ef5e52605af16e8aa98178daee87ec3ab309bcc6ea94ccfd248d28b"
fixture_sha="$(sha256sum "$fixture")"
fixture_sha="${fixture_sha%% *}"
if [ "$fixture_sha" != "$expected_fixture_sha" ]; then
  echo "fixture sha256 mismatch: $fixture" >&2
  echo "expected: $expected_fixture_sha" >&2
  echo "actual:   $fixture_sha" >&2
  exit 1
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/e2-a-native-paragraph-content"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/e2_a_native_paragraph_content.cpp" -ldl -o "$probe"

echo "== running probe =="
echo "   install:  $install_dir"
echo "   fixture:  $fixture"
echo "   sha256:   $fixture_sha"

set +e
SAL_USE_VCLPLUGIN=svp \
"$probe" \
  "$install_dir" \
  "file://$profile_dir" \
  "$out" \
  "file://$fixture" \
  "$fixture_sha" \
  >"$out/results.jsonl" 2>"$out/sal.log"
status=$?
set -e

echo "== probe exit: $status =="
if [ "$status" -ne 0 ]; then
  echo "probe failed; see $out/sal.log" >&2
  exit "$status"
fi

python3 "$here/tools/analyze_readback_nesting.py" \
  --input "$out/results.jsonl" \
  --output "$out/nesting-audit.json"

echo
echo "full output in $out"
