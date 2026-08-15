#!/usr/bin/env bash
# A3/A4/A5 re-sweep on the relinked combination artifact (task #49).
#
# SPEC E2-A 10.14 makes this the E2-B entry condition: finding 039 fixed AND
# A3/A4/A5 re-swept after the relink.  The cell layout is P3's, so the two
# sweeps are directly comparable:
#
#   a3 -> browser/<browser>/<fixture>     3 fixtures x 2 browsers x 3 runs
#   a4 -> repeat/<browser>/<fixture>      3 fixtures x 2 browsers x 3 runs
#   a5 -> negative/<browser>/<fixture>    4 fixtures x 2 browsers x 1 run
#
# --profile-override without --evidence-dir is refused by the runner on
# purpose: --evidence-root walks .parent.parent back into the verdict-bound
# trees for keyed modes, which is how P3's first sweep landed in
# browser/chrome/styled-list/attempt-28.
#
# A non-zero exit per run is NORMAL and is why this script does not use `set
# -e`.  The frozen attempt-27 carries `pass: false` too; A3/A4/A5 are judged by
# validate_e2_a.py reading the whole tree, not by a per-run field.  Stopping
# the sweep on the first non-zero exit reports a failure that is not there --
# which is exactly what happened the first time this script was started.
#
# Usage: sweep.sh <output-dir> [profile]

set -uo pipefail

out="${1:?output dir}"
profile="${2:-e2-combination}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"
probe="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [ ! -d "$probe/wasm_sdk_probe" ] && [ "$probe" != "/" ]; do
  probe="$(dirname "$probe")"
done
probe="$probe/wasm_sdk_probe"

run() {   # mode dir browser fixture repeats
  local mode="$1" dir="$2" browser="$3" fixture="$4" repeats="$5" i
  for ((i = 0; i < repeats; i++)); do
    echo "== $mode $browser $fixture ($((i + 1))/$repeats)"
    python3 "$probe/tools/run_e2_discovery.py" \
      --browser "$browser" --mode "$mode" --fixture "$fixture" \
      --profile-override "$profile" \
      --evidence-dir "$out/$dir/$browser/$fixture" \
      >>"$out/sweep.log" 2>&1
    echo "   exit $?"
  done
}

for browser in chrome firefox; do
  for fixture in multi-paragraph plain-grapheme styled-list; do
    run a3 browser "$browser" "$fixture" 3
    run a4 repeat "$browser" "$fixture" 3
  done
  for fixture in multi-paragraph plain-grapheme styled-list table-boundary; do
    run a5 negative "$browser" "$fixture" 1
  done
done

echo "done; log in $out/sweep.log"
