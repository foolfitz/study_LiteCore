#!/usr/bin/env bash
# Build and run the ODS native oracle over the corpus.  W4 of the ODS plan.
#
# The install used is build-native-26-8, which is built FROM libreoffice-26-8.
# native-lok-26-8 is a different commit and would be an oracle for a codebase
# the candidate is not built from; the commit is recorded beside the output so
# a reader can check rather than trust.
#
# Usage: tools/run_ods_native_oracle.sh [CORPUS_DIR] [OUTPUT_DIR]
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
corpus="${1:-$here/test-docs/ods}"
out="${2:-$here/../findings/evidence/m4-ods/01-native-oracle}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"

install_dir="$build/instdir/program"
[ -d "$install_dir" ] || { echo "no install at $install_dir" >&2; exit 1; }

probe="$out/ods-native-oracle"
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/ods_native_oracle.cpp" -ldl -o "$probe"

mapfile -t files < <(find "$corpus" -name '*.ods' | sort)
[ "${#files[@]}" -gt 0 ] || { echo "no .ods under $corpus" >&2; exit 1; }
echo "oracle over ${#files[@]} files"

core_commit="$(git -C "$src" rev-parse HEAD)"
python3 - "$out/context.json" "$core_commit" "$install_dir" "$corpus" <<'PY'
import json, subprocess, sys
out, commit, install, corpus = sys.argv[1:5]
json.dump({
    "release": "m4-ods-native-oracle",
    "coreCommit": commit,
    "install": install,
    "corpus": corpus,
    "why": "the oracle must be the SAME commit the candidate is built from; "
           "native-lok-26-8 is a different one and is deliberately not used",
}, open(out, "w"), indent=2)
print("context ->", out)
PY

"$probe" "$install_dir" "${files[@]}" > "$out/oracle.jsonl" 2> "$out/oracle.err" \
  || echo "oracle exited non-zero; see $out/oracle.err" >&2
echo "-> $out/oracle.jsonl  ($(wc -l < "$out/oracle.jsonl") lines)"
