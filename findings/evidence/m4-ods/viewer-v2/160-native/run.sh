#!/usr/bin/env bash
# Finding 160 natively (README.md).  Build the probe like the native oracle (one g++), then ROUNDS passes
# over the ODS corpus on build-native-26-8 (built from libreoffice-26-8, the candidate's commit).
#   bash run.sh [ROUNDS] [OUTDIR]
set -euo pipefail
here=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
src=/home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-8
install=/home/jiajun/LibreOffice/study_LiteCore/build-native-26-8/instdir/program
rounds=${1:-5}
out=${2:-/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/m4-ods/viewer-v2/160-native}
mkdir -p "$out"
probe="$out/probe-160-native"
g++ -std=c++17 -O2 -pthread -I"$src/include" "$here/tools/probe_160_native.cpp" -ldl -o "$probe"
mapfile -t files < <(find "$here/test-docs/ods" -name '*.ods' | sort)
echo "$(date -Is) start: ${#files[@]} files x $rounds rounds, core $(git -C "$src" rev-parse --short HEAD)" >> "$out/runs.txt"
"$probe" "$install" "$rounds" "${files[@]}" > "$out/reads.jsonl" 2> "$out/probe.err" || echo "probe exit $?" >> "$out/runs.txt"
echo "$(date -Is) done: $(wc -l < "$out/reads.jsonl") document lines" >> "$out/runs.txt"
