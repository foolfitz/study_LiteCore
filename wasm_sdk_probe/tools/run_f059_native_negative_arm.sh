#!/usr/bin/env bash
# Finding 059, the two things owed before the engine's predicate changes: a
# genuine NEGATIVE arm, and whether the state cache is primed when the
# predicate needs it (finding 021's shape).
#
# Nothing here rebuilds core.  The probe is a standalone program compiled
# against the LOK headers and loading the existing native install at runtime.
#
# Usage: tools/run_f059_native_negative_arm.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/build/f059-native-negative-arm}"
mkdir -p "$out"
# Absolute: the profile goes to lok_init_2 as a file:// URL and a relative one
# fails userinstall with a fatal error that reads like a broken build.
out="$(cd "$out" && pwd)"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

# One round is one record.  A rerun that silently replaces the previous round
# makes "it was different last time" unaskable.
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
round="$out/round-$stamp"
if [ -e "$round" ]; then
  echo "round directory already exists: $round" >&2
  exit 1
fi
mkdir -p "$round"

profile_dir="$round/user-profile"
mkdir -p "$profile_dir"

probe="$out/f059-native-negative-arm"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/f059_native_negative_arm.cpp" -ldl -o "$probe"

fixture="$here/test-docs/f059-negative-arm.odt"
if [ ! -f "$fixture" ]; then
  echo "fixture missing: $fixture -- run tools/create_f059_negative_fixture.py" >&2
  exit 1
fi

echo "== running probe =="
echo "   install:  $install_dir"
echo "   fixture:  $fixture"
echo "   round:    $round"

set +e
SAL_USE_VCLPLUGIN=svp \
"$probe" \
  "$install_dir" \
  "file://$profile_dir" \
  "file://$fixture" \
  "file://$round" \
  >"$round/arms.jsonl" 2>"$round/sal.log"
status=$?
set -e

echo "== probe exit: $status =="
cat "$round/arms.jsonl"
echo
echo "round in $round"
exit "$status"
