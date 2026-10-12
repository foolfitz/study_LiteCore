#!/usr/bin/env bash
# Finding 129, Part N2: "click at the point, then the key" against Writer's own
# key handling, native LibreOffice 26.8.
# Brief: handoff/tasks/TASK-2026-10-12c-native-page-rectangles-and-129-shapes.md
# Usage: tools/run_f129_native_point_click.sh [OUT_DIR] [ROUNDS]
#        F129_EXTRAS=only tools/run_f129_native_point_click.sh [OUT_DIR] [ROUNDS]
#          runs only the extra shapes (s1e, m1r, m1e; added after the first round)
#          into point-click-extras-round-<stamp>.
#        F129_EXTRAS=drag  likewise for s1d, m1d (selection made with the product's mouse drag)
#          into point-click-extras-drag-round-<stamp>.
#        F129_EXTRAS=dragend  the emuend arms (click aimed at the selection-end rectangle)
#          for s1d, m1d, m1e into point-click-extras-dragend-round-<stamp>.
#
# Each round is its own process with its own profile and its own copies of the
# fixtures (LibreOffice writes a lock file next to whatever it loads); the
# rounds run in parallel.  Arms inside a process run one after the other and
# every arm is a fresh document load.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
install_dir="$here/../native-lok-26-8/build/instdir/program"
if [ ! -d "$install_dir" ]; then echo "native build missing: $install_dir" >&2; exit 1; fi
install_dir="$(cd "$install_dir" && pwd)"

out="${1:-$here/../findings/evidence/129/native}"
rounds="${2:-3}"
mkdir -p "$out"; out="$(cd "$out" && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
extras="${F129_EXTRAS:-}"
case "$extras" in
  only) prefix="point-click-extras-round" ;;
  drag) prefix="point-click-extras-drag-round" ;;
  dragend) prefix="point-click-extras-dragend-round" ;;
  *)    prefix="point-click-round" ;;
esac
round_dir="$out/$prefix-$stamp"; mkdir -p "$round_dir"

old_fx="$here/test-docs/f129/arrow-selection.fodt"
shapes_fx="$here/test-docs/f129/arrow-selection-shapes.fodt"
wrap_fx="$here/test-docs/f129/arrow-selection-wrap.fodt"
tool_src="$here/tools/f129_native_point_click.cpp"
probe="$round_dir/f129-native-point-click"

echo "g++ -std=c++17 -O2 -I<libreoffice-26-8>/include tools/f129_native_point_click.cpp -ldl -lpthread -o f129-native-point-click" > "$round_dir/build-command.txt"
g++ -std=c++17 -O2 -I"$src/include" "$tool_src" -ldl -lpthread -o "$probe"

# The tool hard-codes the S1 paragraph text; refuse to run if it drifted from the fixture.
python3 -I - "$tool_src" "$shapes_fx" <<'PY'
import re, sys
c = open(sys.argv[1]).read()
f = open(sys.argv[2]).read()
fx = re.findall(r'<text:p>(S1 .*?)</text:p>', f)[0]
m = re.search(r'const std::string kS1 =(.*?);', c, re.S)
tool = ''.join(re.findall(r'"([^"]*)"', m.group(1)))
if tool != fx:
    sys.exit("kS1 in the tool differs from the fixture's S1 paragraph")
PY

sha256sum "$old_fx" "$shapes_fx" "$wrap_fx" "$tool_src" "$here/tools/run_f129_native_point_click.sh" > "$round_dir/inputs.sha256"
cp "$tool_src" "$round_dir/tool-source-as-run.cpp"
sha256sum "$here/../findings/evidence/129/native/round-20261012T020528Z/arms.jsonl" >> "$round_dir/inputs.sha256"

pids=()
for r in $(seq 1 "$rounds"); do
  work="$round_dir/work-$r"; mkdir -p "$work/profile"
  cp "$old_fx" "$work/old.fodt"; cp "$shapes_fx" "$work/shapes.fodt"; cp "$wrap_fx" "$work/wrap.fodt"
  (
    cd "$work"
    F129_EXTRAS="$extras" F129_WRAP_FIXTURE_URL="file://$work/wrap.fodt" SAL_USE_VCLPLUGIN=svp "$probe" "$install_dir" "file://$work/profile" "file://$work/old.fodt" \
      "file://$work/shapes.fodt" 1 "" $((r - 1)) >"$round_dir/arms-r$r.jsonl" 2>"$round_dir/arms-r$r.stderr"
    echo "exit $?" > "$round_dir/arms-r$r.exit"
  ) &
  pids+=($!)
done
status=0
for p in "${pids[@]}"; do wait "$p" || status=1; done
for r in $(seq 1 "$rounds"); do cat "$round_dir/arms-r$r.exit"; done
rm -rf "$round_dir"/work-*; rm -f "$probe"
date -u +%Y-%m-%dT%H:%M:%SZ > "$round_dir/ended-utc.txt"
echo "round: $round_dir"
exit "$status"
