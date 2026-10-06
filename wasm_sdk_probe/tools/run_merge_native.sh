#!/usr/bin/env bash
# Paragraph merge, native: the one-unit selection at every boundary kind, the
# delete of that selection against the user's own key, and one undo.
# See tools/merge_native_boundaries.cpp.
#
# Usage: tools/run_merge_native.sh [OUTPUT_DIR] [ROUNDS]

set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
install_dir="$here/../native-lok-26-8/build/instdir/program"
if [ ! -d "$install_dir" ]; then echo "native build missing: $install_dir" >&2; exit 1; fi
install_dir="$(cd "$install_dir" && pwd)"

out="${1:-$here/../findings/evidence/merge-native}"
rounds="${2:-3}"
mkdir -p "$out"; out="$(cd "$out" && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
round_dir="$out/round-$stamp"; mkdir -p "$round_dir/docs"
profile_dir="$round_dir/user-profile"; mkdir -p "$profile_dir"

probe="$round_dir/merge-native-boundaries"
echo "== compiling =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/merge_native_boundaries.cpp" -ldl -lpthread -o "$probe"

fixture="$here/test-docs/merge/boundaries.fodt"
[ -f "$fixture" ] || { echo "fixture missing: $fixture" >&2; exit 1; }
sha256sum "$fixture" "$here/tools/merge_native_boundaries.cpp" > "$round_dir/inputs.sha256"

echo "== running ($rounds rounds) =="
set +e
SAL_USE_VCLPLUGIN=svp \
  "$probe" "$install_dir" "file://$profile_dir" "file://$fixture" "$round_dir/docs" "$rounds" \
  >"$round_dir/arms.jsonl" 2>"$round_dir/sal.log"
status=$?
set -e
rm -rf "$profile_dir" "$probe"
echo "== exit: $status =="
echo "round: $round_dir"
exit "$status"
