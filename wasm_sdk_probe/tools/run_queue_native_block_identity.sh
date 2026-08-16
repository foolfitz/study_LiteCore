#!/usr/bin/env bash
# queue-verify-caret-by-block-identity, native run: is the datum there, and does
# it settle what the queue item claims it settles?
#
# The item says the three ambiguities "all reduce to the same missing datum".
# Nobody has checked that.  Reading core 26.8 already establishes that no
# paragraph index exists in any LOK payload; what is left to measure is whether
# the one per-block datum that DOES exist -- the focused paragraph's own text --
# separates the three cases.  Two of the four predictions say it does not, so
# this round can cost the queue item its wording.
#
# Predictions were registered before the probe was written, in
# findings/evidence/queue-block-identity/native/PREDICTION.md.
# Judging is offline, in tools/analyze_queue_block_identity.py, so the run and
# the criteria stay separable.
#
# The probe compiles to its own output directory.  It never touches a profile's
# build directory -- PLAN-E2-C-relink-v3.md P0 records what happened the one
# time an object-only check was compiled into one.
#
# Usage: tools/run_queue_native_block_identity.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/../findings/evidence/queue-block-identity/native/run}"
# LO builds its user-installation URL as `file://$profile_dir`, so a relative
# OUTPUT_DIR produces `file://../...` and the kit dies in userinstall before a
# single measurement is taken.
mkdir -p "$out"
out="$(cd "$out" && pwd)"

install_dir="$build/instdir/program"
[ -d "$install_dir" ] || { echo "native build not found at $install_dir" >&2; exit 1; }

# One round is one record.
if [ -f "$out/captures.jsonl" ]; then
  echo "refusing to overwrite an existing round: $out/captures.jsonl" >&2
  echo "pass a different OUTPUT_DIR" >&2
  exit 2
fi

profile_dir="$out/user-profile"
rm -rf "$profile_dir"; mkdir -p "$profile_dir"

probe="$out/queue-native-block-identity"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/queue_native_block_identity.cpp" -ldl -o "$probe"

# The fixture is generated into the run, not taken from the frozen corpus: this
# measurement needs four shapes in one document and the corpus is hash-bound.
fixture="$out/block-identity.odt"
fixture_sha="$(python3 "$here/tools/create_block_identity_fixture.py" "$fixture")"

core_commit="$(git -C "$src" rev-parse HEAD)"
python3 - "$out/context.json" "$core_commit" "$fixture" "$fixture_sha" <<'PY'
import json, sys
out, commit, fixture, sha = sys.argv[1:5]
json.dump({"schemaVersion": 1, "queueItem": "queue-verify-caret-by-block-identity",
           "arm": "native", "coreCommit": commit, "fixture": fixture,
           "fixtureSha256": sha},
          open(out, "w"), indent=2)
PY

echo "== running probe =="
set +e
SAL_USE_VCLPLUGIN=svp "$probe" "$install_dir" "file://$profile_dir" \
  "file://$fixture" >"$out/captures.jsonl" 2>"$out/sal.log"
status=$?
set -e
echo "== probe exit: $status =="
echo
echo "Judge with:"
echo "  python3 tools/analyze_queue_block_identity.py $out"
