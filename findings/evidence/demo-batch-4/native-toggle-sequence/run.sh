#!/usr/bin/env bash
# SPEC-P-demo-batch-4 N5.  Compiles the harness against the same bridge as N4 and runs it on a copy of the fixtures.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
E=$(cd ../findings/evidence/demo-batch-4/native-toggle-sequence && pwd)
F=$(cd ../findings/evidence/demo-batch-4/fixture && pwd)
CORE=$(cd ../build-native-26-8 && pwd)
LO=$(cd ../libreoffice-26-8 && pwd)
P=$CORE/instdir/program
B=build/n4-writer
INC="-I$LO/include -I$CORE/config_host -I$CORE/workdir/UnoApiHeadersTarget/udkapi/comprehensive -I$CORE/workdir/UnoApiHeadersTarget/offapi/comprehensive -I$CORE/workdir/UnpackedTarball/boost"
c1="g++ -std=c++20 -O2 -fPIC -DLIBO_INTERNAL_ONLY -DCPPU_ENV=gcc3 -DUNX -DLINUX -DX86_64 $INC -c src/writer_caret_bridge.cpp -o $B/bridge-n5.o"
c2="g++ -std=c++17 -O2 -I$LO/include tools/n5_native_writer_toggle_sequence.cpp $B/bridge-n5.o -L$P -lsfxlo -lvcllo -lcomphelper -ltllo $P/libuno_sal.so.3 $P/libuno_cppu.so.3 $P/libuno_cppuhelpergcc3.so.3 -Wl,-rpath,$P -ldl -lpthread -o $B/n5"
{ echo "$c1"; echo "$c2"; g++ --version | head -1; uptime; } > $E/build-receipt.txt
taskset -c 0 $c1 2> $E/compile-bridge.txt || { echo bridge-failed; exit 1; }
taskset -c 0 $c2 2> $E/compile-harness.txt || { echo harness-failed; tail -20 $E/compile-harness.txt; exit 1; }
sha256sum src/writer_caret_bridge.cpp src/writer_caret_bridge.h tools/n5_native_writer_toggle_sequence.cpp $B/n5 >> $E/build-receipt.txt
T=$(mktemp -d -p build/n4-writer); T=$(cd "$T" && pwd)
mkdir "$T/fixture" "$T/profile"; cp "$F"/*.odt "$T/fixture/"
OUT=$E/${1:-run-01}; mkdir -p "$OUT"
s=$(date +%s)
SAL_USE_VCLPLUGIN=svp timeout 900 $B/n5 "$P" "file://$T/profile" "$T/fixture" "$OUT" > "$OUT/observations.jsonl" 2> "$OUT/stderr.txt"
echo "exit=$? seconds=$(( $(date +%s) - s )) rows=$(wc -l < "$OUT/observations.jsonl")" | tee -a "$E/run.log"
