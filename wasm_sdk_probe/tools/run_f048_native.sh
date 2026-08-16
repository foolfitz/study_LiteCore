#!/usr/bin/env bash
# Finding 048 native run: why does a click take 22-28 ms to take effect?
#
# Native first, and for the reason finding 016 and finding 045 needed native
# too: a number measured only in the browser cannot separate "core is slow" from
# "our transport is slow".  Nothing this script produces describes the WASM
# artifact.
#
# Predictions were registered before the probe was written, in
# findings/evidence/048/native/PREDICTION.md.  The judging is offline, in
# tools/analyze_f048_native.py, so the run and the criteria stay separable.
#
# The probe compiles to its own output directory.  It never touches a profile's
# build directory -- PLAN-E2-C-relink-v3.md P0 records what happened the one
# time an object-only check was compiled into one.
#
# The anchors are the fallback positioning path, and it is needed on this
# fixture: measured 2026-08-16, `.uno:GoDown` on list-contexts.odt produces no
# LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR at all, while the same walk on
# styled-list.odt produces 23.  Changing the fixture would change the document
# D3's 22-28 ms was measured on, so the fixture stays and the walk gains a
# second measured path.  The anchors come from test-docs/e1/manifest.json.
#
# Usage: tools/run_f048_native.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/../findings/evidence/048/native/run}"
# LO builds its user-installation URL as `file://$profile_dir`, so a relative
# OUTPUT_DIR produces `file://../...` and the kit dies in userinstall with exit
# 77 before a single measurement is taken.  Absolutise it here rather than
# documenting a footgun.
mkdir -p "$out"
out="$(cd "$out" && pwd)"

install_dir="$build/instdir/program"
if [ ! -d "$install_dir" ]; then
  echo "native build not found at $install_dir" >&2
  exit 1
fi

# One round is one record.  The D3 evidence accident (an --output pointing at a
# directory that already held a round) is cheap to prevent here too.
if [ -f "$out/arms.jsonl" ]; then
  echo "refusing to overwrite an existing round: $out/arms.jsonl" >&2
  echo "pass a different OUTPUT_DIR" >&2
  exit 2
fi

mkdir -p "$out"
profile_dir="$out/user-profile"
rm -rf "$profile_dir"
mkdir -p "$profile_dir"

probe="$out/f048-native-click-latency"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/f048_native_click_latency.cpp" -ldl -o "$probe"

fixture="$here/test-docs/e1/list-contexts.odt"
anchors="${2:-E1-LC-ISOLATED,E1-LC-BULLET-ONE,E1-LC-END}"
if [ ! -f "$fixture" ]; then
  echo "fixture missing: $fixture" >&2
  exit 1
fi

# The comparison has one variable only if the native install and the WASM
# profile were built from the same core commit.  Recorded here, checked by the
# analyzer, so a mismatched run is caught rather than interpreted.
core_commit="$(git -C "$src" rev-parse HEAD)"
core_dirty="$(git -C "$src" status --porcelain | wc -l)"
python3 - "$out/context.json" "$core_commit" "$core_dirty" "$fixture" <<'PY'
import hashlib, json, subprocess, sys
out, commit, dirty, fixture = sys.argv[1:5]
json.dump({
    "schemaVersion": 1,
    "finding": "048",
    "arm": "native",
    "coreCommit": commit,
    "coreWorktreeModifiedFiles": int(dirty),
    "fixture": fixture,
    "fixtureSha256": hashlib.sha256(open(fixture, "rb").read()).hexdigest(),
    "note": ("The core worktree carries the build-system patches recorded in "
             "wasm-lite/patches/INVENTORY.md.  Recorded rather than assumed "
             "clean."),
}, open(out, "w"), indent=2)
print(f"   core commit: {commit} ({dirty} modified files)")
PY

echo "== running probe =="
echo "   install:  $install_dir"
echo "   fixture:  $fixture"
echo "   output:   $out"

set +e
SAL_USE_VCLPLUGIN=svp \
"$probe" \
  "$install_dir" \
  "file://$profile_dir" \
  "file://$fixture" \
  "$out" \
  "$anchors" \
  >"$out/arms.jsonl" 2>"$out/sal.log"
status=$?
set -e

echo "== probe exit: $status =="
echo
echo "Judge with: python3 tools/analyze_f048_native.py $out"
