#!/usr/bin/env bash
# Finding 096, arm U: run the native dedup probe with SAL lok logging.
# Criteria pinned first in
#   handoff/tasks/TASK-2026-09-10-096-why-the-core-is-silent-at-a-boundary.md
# Usage: tools/run_f096_native_dedup.sh [OUT_DIR]
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
install_dir="$here/../native-lok-26-8/build/instdir/program"
if [ ! -d "$install_dir" ]; then echo "native build missing: $install_dir" >&2; exit 1; fi
install_dir="$(cd "$install_dir" && pwd)"

out="${1:-$here/../findings/evidence/096/native}"
mkdir -p "$out"; out="$(cd "$out" && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
round="$out/round-$stamp"; mkdir -p "$round"
profile_dir="$round/user-profile"; mkdir -p "$profile_dir"

probe="$round/f096-native-dedup"
echo "== compiling =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/f096_native_dedup.cpp" -ldl -o "$probe"

fixture="$here/test-docs/e1/a11y-audible.odt"
[ -f "$fixture" ] || { echo "fixture missing: $fixture" >&2; exit 1; }

echo "== running (SAL_LOG=+INFO.lok) =="
set +e
SAL_USE_VCLPLUGIN=svp SAL_LOG="+INFO.lok" \
  "$probe" "$install_dir" "file://$profile_dir" "file://$fixture" \
  >"$round/presses.jsonl" 2>"$round/sal.log"
status=$?
set -e
echo "== exit: $status =="
echo "--- presses.jsonl ---"; cat "$round/presses.jsonl"
echo "--- Skipping-duplicate lines, with the marker above each ---"
grep -nE ">>>MARK|Skipping duplicate" "$round/sal.log" || true
echo "round: $round"
exit "$status"
