#!/usr/bin/env bash
# P1's mixed-page fixture on native LibreOffice: what does getPartPageRectangles()
# return for 8 pages of mixed sizes and orientations?
# Brief: handoff/tasks/TASK-2026-10-13m-mixed-page-fixture-native.md
# Usage: SCRATCH_DIR=<dir outside the repository> tools/run_native_mixed_page_rectangles.sh [OUT_DIR] [ROUNDS]
#
# Reuses tools/native_page_rectangles.cpp UNCHANGED (its sha256 is recorded and
# compared with the one in the earlier 60-page round).  The fixture is generated
# into SCRATCH_DIR (never into the repository) by
# tools/create_mixed_page_document.py, generated twice 3 s apart and compared,
# then verified against the spec by the generator's own --verify.  ROUNDS
# (default 3) fresh processes, each with its own fresh profile and its own copy
# of the fixture (byte-compared with cmp).
#
# Environment:
#   SCRATCH_DIR  required; must not be inside the repository
#   NATIVE_ROOT  directory holding native-lok-26-8/ and libreoffice-26-8/
#                (default /home/jiajun/LibreOffice/study_LiteCore; the
#                 worktrees do not contain them)
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # wasm_sdk_probe
repo="$(cd "$here/.." && pwd)"
native_root="${NATIVE_ROOT:-/home/jiajun/LibreOffice/study_LiteCore}"
install_dir="$native_root/native-lok-26-8/build/instdir/program"
src="$native_root/libreoffice-26-8"
if [ ! -d "$install_dir" ]; then echo "native build missing: $install_dir" >&2; exit 1; fi
if [ ! -d "$src/include/LibreOfficeKit" ]; then echo "core headers missing: $src/include" >&2; exit 1; fi
install_dir="$(cd "$install_dir" && pwd)"

scratch="${SCRATCH_DIR:?set SCRATCH_DIR to a directory outside the repository}"
mkdir -p "$scratch"; scratch="$(cd "$scratch" && pwd)"
case "$scratch/" in
  "$repo"/*) echo "SCRATCH_DIR must be outside the repository ($repo)" >&2; exit 1 ;;
esac

out="${1:-$repo/findings/evidence/link-batch/page-rectangles}"
rounds="${2:-3}"
mkdir -p "$out"; out="$(cd "$out" && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
round_dir="$out/mixed-round-$stamp"; mkdir -p "$round_dir"

probe="$round_dir/native-page-rectangles"
build_cmd="g++ -std=c++17 -O2 -I<libreoffice-26-8>/include tools/native_page_rectangles.cpp -ldl -lpthread -o native-page-rectangles"
echo "$build_cmd" > "$round_dir/build-command.txt"
g++ -std=c++17 -O2 -I"$src/include" "$here/tools/native_page_rectangles.cpp" -ldl -lpthread -o "$probe"

# ---- the fixture: generated twice, 3 s apart, compared ----------------------
fixture="$scratch/mixed8.odt"; fixture_b="$scratch/mixed8-second-run.odt"
{
  echo "python3 tools/create_mixed_page_document.py --out <scratch>/mixed8.odt"
  python3 "$here/tools/create_mixed_page_document.py" --out "$fixture"
  sleep 3
  echo "python3 tools/create_mixed_page_document.py --out <scratch>/mixed8-second-run.odt   (3 s later)"
  python3 "$here/tools/create_mixed_page_document.py" --out "$fixture_b"
  if cmp -s "$fixture" "$fixture_b"; then echo "second run byte-identical to the first: yes"; else echo "second run byte-identical to the first: NO"; fi
  echo "python3 tools/create_mixed_page_document.py --verify <scratch>/mixed8.odt"
  python3 "$here/tools/create_mixed_page_document.py" --verify "$fixture"
} 2>&1 | tee "$round_dir/create-fixture-command.txt"
rm -f "$fixture_b"

{
  sha256sum "$here/tools/native_page_rectangles.cpp" "$here/tools/run_native_mixed_page_rectangles.sh" \
    "$here/tools/create_mixed_page_document.py" "$here/tools/analyze_native_mixed_page_rectangles.py"
  echo "$(sha256sum "$fixture" | cut -d' ' -f1)  <generated mixed8.odt, not in the tree>"
} | sed "s#$here/##" > "$round_dir/inputs.sha256"
{
  echo "native build: $install_dir"
  grep -h -E "^(buildid|Version|version)" "$install_dir/versionrc" 2>/dev/null || true
  echo "SAL_USE_VCLPLUGIN=svp"
  echo "rounds: $rounds"
} > "$round_dir/environment.txt"

status=0
for r in $(seq 1 "$rounds"); do
  work="$scratch/work-mixed-$r"; rm -rf "$work"; mkdir -p "$work/profile"
  cp "$fixture" "$work/doc.odt"
  cmp "$work/doc.odt" "$fixture"
  echo "== mixed round $r =="
  set +e
  SAL_USE_VCLPLUGIN=svp "$probe" "$install_dir" "file://$work/profile" "file://$work/doc.odt" \
    mixed "$r" >"$round_dir/mixed-r$r.jsonl" 2>"$round_dir/mixed-r$r.stderr"
  s=$?
  set -e
  echo "exit $s" | tee "$round_dir/mixed-r$r.exit"
  [ "$s" -eq 0 ] || status=1
  rm -rf "$work"
done
rm -f "$probe"
date -u +%Y-%m-%dT%H:%M:%SZ > "$round_dir/ended-utc.txt"

python3 "$here/tools/analyze_native_mixed_page_rectangles.py" "$round_dir" || status=1
echo "round: $round_dir"
exit "$status"
