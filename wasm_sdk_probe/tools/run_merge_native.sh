#!/usr/bin/env bash
# Paragraph merge, native: the one-unit selection at every boundary kind, the
# delete of that selection against the user's own key, and one undo.
# See tools/merge_native_boundaries.cpp.
#
# Usage: tools/run_merge_native.sh [OUTPUT_DIR] [ROUNDS] [FIXTURE CASES_TSV [PRESSES]]
#
# Without FIXTURE the probe's built-in cases run on test-docs/merge/boundaries.fodt.
# With them, the cases come from CASES_TSV (see the probe's header).  A
# document that must not enter the repository (the owner's) goes with an
# OUTPUT_DIR outside it: every arm's saved copy lands in OUTPUT_DIR.  PRESSES
# makes the key arm press its key that many times, saving after each.

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
# MERGE_UNDO_STEPS (fifth round): the undo limit, so a short run reaches it.
if [ -n "${MERGE_UNDO_STEPS:-}" ]; then
  mkdir -p "$profile_dir/user"
  cat > "$profile_dir/user/registrymodifications.xcu" <<XCU
<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Common/Undo"><prop oor:name="Steps" oor:op="fuse"><value>$MERGE_UNDO_STEPS</value></prop></item>
</oor:items>
XCU
  echo "MERGE_UNDO_STEPS=$MERGE_UNDO_STEPS" > "$round_dir/undo-steps.txt"
fi

# MERGE_RESTORE_PRESSES (sixth round): the probe's arm b may press the
# restore arrow up to that many times; recorded beside the round.
if [ -n "${MERGE_RESTORE_PRESSES:-}" ]; then
  echo "MERGE_RESTORE_PRESSES=$MERGE_RESTORE_PRESSES" > "$round_dir/restore-presses.txt"
fi

# MERGE_FOLLOW_TEXT (R0): text typed after the b and key arms' press, saved
# again as -follow.odt; recorded beside the round.
if [ -n "${MERGE_FOLLOW_TEXT:-}" ]; then
  echo "MERGE_FOLLOW_TEXT=$MERGE_FOLLOW_TEXT" > "$round_dir/follow-text.txt"
fi

probe="$round_dir/merge-native-boundaries"
echo "== compiling =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/merge_native_boundaries.cpp" -ldl -lpthread -o "$probe"

source_fixture="${3:-$here/test-docs/merge/boundaries.fodt}"
cases_file="${4:-}"
presses="${5:-1}"
[ -f "$source_fixture" ] || { echo "fixture missing: $source_fixture" >&2; exit 1; }
if [ -n "$cases_file" ]; then
  [ -f "$cases_file" ] || { echo "cases missing: $cases_file" >&2; exit 1; }
  cases_file="$(cd "$(dirname "$cases_file")" && pwd)/$(basename "$cases_file")"
fi
# A copy per round: LibreOffice writes a lock file next to whatever it loads,
# and a killed run's lock made the next run load the document read-only
# (round-20261006T063803Z-read-only-fault: every save equal to the original).
# An ASCII name, so the file URL needs no escaping whatever the source is called.
fixture="$round_dir/fixture.${source_fixture##*.}"
cp "$source_fixture" "$fixture"
sha256sum "$source_fixture" "$here/tools/merge_native_boundaries.cpp" ${cases_file:+"$cases_file"} \
  > "$round_dir/inputs.sha256"

echo "== running ($rounds rounds) =="
set +e
SAL_USE_VCLPLUGIN=svp \
  "$probe" "$install_dir" "file://$profile_dir" "file://$fixture" "$round_dir/docs" "$rounds" \
  ${cases_file:+"$cases_file"} ${cases_file:+"$presses"} >"$round_dir/arms.jsonl" 2>"$round_dir/sal.log"
status=$?
set -e
rm -rf "$profile_dir" "$probe"; rm -f "$round_dir"/.~lock.*
echo "== exit: $status =="
echo "round: $round_dir"
exit "$status"
