#!/usr/bin/env bash
# SPEC-P-demo-batch-4 N3.  Compiles the single-file harness (AGENTS.md, native harness rule) and runs every part on the native 26.8.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=$(cd ../findings/evidence/demo-batch-4/native-toggle && pwd)
F=$(cd ../findings/evidence/demo-batch-4/fixture && pwd)
CORE=$(cd ../build-native-26-8/instdir/program && pwd)
{ echo "argv: g++ -std=c++17 -O2 -I../libreoffice-26-8/include tools/n3_native_writer_toggle.cpp -ldl -lpthread -o build/n3-writer/n3"; g++ --version | head -1; sha256sum tools/n3_native_writer_toggle.cpp build/n3-writer/n3; uptime; } > $E/build-receipt.txt
T=$(mktemp -d -p build/n3-writer)
T=$(cd "$T" && pwd)
counter=0
for part in styles undo blank table range caret; do
  mkdir -p "$E/$part"
  P=$(mktemp -d -p "$T")
  start=$(date +%s)
  SAL_USE_VCLPLUGIN=svp timeout 1500 build/n3-writer/n3 "$CORE" "file://$P" "$F" "$E/$part" "$part" > "$E/$part/observations.jsonl" 2> "$E/$part/stderr.txt"
  echo "$part exit=$? seconds=$(( $(date +%s) - start )) rows=$(wc -l < "$E/$part/observations.jsonl")" | tee -a "$E/run.log"
done
echo DONE | tee -a "$E/run.log"
