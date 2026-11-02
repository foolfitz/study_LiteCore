#!/usr/bin/env bash
# SPEC-P-demo-batch-4 N4.  Compiles src/writer_caret_bridge.cpp and the harness with the g++ lines tools/run_calc_cell_native.py uses
# (AGENTS.md, native harness rule) and runs every part on the native 26.8.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=$(cd ../findings/evidence/demo-batch-4/native-caret-read && pwd)
F=$(cd ../findings/evidence/demo-batch-4/fixture && pwd)
CORE=$(cd ../build-native-26-8 && pwd)
LO=$(cd ../libreoffice-26-8 && pwd)
P=$CORE/instdir/program
B=build/n4-writer
INC="-I$LO/include -I$CORE/config_host -I$CORE/workdir/UnoApiHeadersTarget/udkapi/comprehensive -I$CORE/workdir/UnoApiHeadersTarget/offapi/comprehensive -I$CORE/workdir/UnpackedTarball/boost"
if [[ ${1:-} != norun-build ]]; then
c1="g++ -std=c++20 -O2 -fPIC -DLIBO_INTERNAL_ONLY -DCPPU_ENV=gcc3 -DUNX -DLINUX -DX86_64 $INC -c src/writer_caret_bridge.cpp -o $B/bridge.o"
c2="g++ -std=c++17 -O2 -I$LO/include -I$CORE/workdir/UnpackedTarball/boost tools/n4_native_writer_caret_read.cpp $B/bridge.o -L$P -lsfxlo -lvcllo -lcomphelper -ltllo $P/libuno_sal.so.3 $P/libuno_cppu.so.3 $P/libuno_cppuhelpergcc3.so.3 -Wl,-rpath,$P -ldl -lpthread -o $B/n4"
{ echo "$c1"; echo "$c2"; g++ --version | head -1; uptime; } > $E/build-receipt.txt
taskset -c 0 $c1 2> $E/compile-bridge.txt || { echo bridge-failed; tail -30 $E/compile-bridge.txt; exit 1; }
taskset -c 0 $c2 2> $E/compile-harness.txt || { echo harness-failed; tail -30 $E/compile-harness.txt; exit 1; }
sha256sum src/writer_caret_bridge.cpp src/writer_caret_bridge.h tools/n4_native_writer_caret_read.cpp $B/n4 >> $E/build-receipt.txt
fi
T=$(mktemp -d -p build/n4-writer); T=$(cd "$T" && pwd)
# A copy per run: a run stopped partway leaves a .~lock file beside the document, and the next run opens it read-only and every command
# silently does nothing (the first range run, 84 arms, all unchanged, every read agreeing with the file).
mkdir "$T/fixture"; cp "$F"/*.odt "$T/fixture/"; F=$T/fixture
for part in ${PARTS:-blank range table widen caret}; do
  mkdir -p "$E/$part"; X=$(mktemp -d -p "$T"); s=$(date +%s)
  SAL_USE_VCLPLUGIN=svp timeout 1500 $B/n4 "$P" "file://$X" "$F" "$E/$part" "$part" > "$E/$part/observations.jsonl" 2> "$E/$part/stderr.txt"
  echo "$part exit=$? seconds=$(( $(date +%s) - s )) rows=$(wc -l < "$E/$part/observations.jsonl")" | tee -a "$E/run.log"
done
echo DONE | tee -a "$E/run.log"
