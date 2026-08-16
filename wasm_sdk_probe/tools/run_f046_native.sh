#!/usr/bin/env bash
# Finding 046 native run: what is actually in an empty paragraph's readback?
#
# The criterion for 046's remedy (relink queue item 3b) is undecided because the
# shipped product does not project `itemCount`, so "zero blocks" cannot be told
# apart from "only list items".  This captures the raw markup natively and lets
# the ENGINE'S OWN parser classify it -- tools/test_format_readback_parser.py
# slices the scanner out of probe_engine.cpp and compiles it, so no second
# implementation of the rules is involved.
#
# Predictions were registered before the probe was written, in
# findings/evidence/046/native/PREDICTION.md.
#
# Usage: tools/run_f046_native.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/../findings/evidence/046/native/run}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"

install_dir="$build/instdir/program"
[ -d "$install_dir" ] || { echo "native build not found at $install_dir" >&2; exit 1; }

# A round is a record.
if [ -f "$out/captures.jsonl" ]; then
  echo "refusing to overwrite an existing round: $out/captures.jsonl" >&2
  exit 2
fi

profile_dir="$out/user-profile"
rm -rf "$profile_dir"; mkdir -p "$profile_dir"

probe="$out/f046-native-empty-readback"
echo "== compiling probe =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/f046_native_empty_readback.cpp" -ldl -o "$probe"

# Copied out of the corpus: the probe saves next to the document to prove
# the action reached it, and corpus bytes are frozen.
fixture="$out/empty-paragraph.odt"
cp "$here/test-docs/e1/empty-paragraph.odt" "$fixture"
[ -f "$fixture" ] || { echo "fixture missing: $fixture" >&2; exit 1; }

core_commit="$(git -C "$src" rev-parse HEAD)"
python3 - "$out/context.json" "$core_commit" "$fixture" <<'PY'
import hashlib, json, sys
out, commit, fixture = sys.argv[1:4]
json.dump({"schemaVersion": 1, "finding": "046", "arm": "native",
           "coreCommit": commit, "fixture": fixture,
           "fixtureSha256": hashlib.sha256(open(fixture, "rb").read()).hexdigest()},
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
echo "Classify with the engine's own parser:"
echo "  python3 tools/test_format_readback_parser.py --captures $out/captures.jsonl"
