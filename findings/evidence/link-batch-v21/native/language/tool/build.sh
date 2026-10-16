#!/usr/bin/env bash
# Compiles the two one-file probes against the native 26.8 install (no make, no core build).
# Usage: build.sh <output-dir>
set -eu
OUT=$1
R=/home/jiajun/LibreOffice/study_LiteCore
S=$R/native-lok-26-8/src
B=$R/native-lok-26-8/build
P=$B/instdir/program
T=$(cd "$(dirname "$0")" && pwd)

# This tool: LOK client plus in-process readouts. It links libmergedlo.so (the same file that
# lok_init_2 dlopens, so the loader reuses one copy and the statics are shared) and
# libi18nlangtag.so (MsLangId), with core-internal headers (-DLIBO_INTERNAL_ONLY).
nice -n 10 g++ -std=c++20 -O1 -DLIBO_INTERNAL_ONLY -DLINUX -DUNX -DCPPU_ENV=gcc3 -DOSL_DEBUG_LEVEL=0 \
  -I "$S/include" -I "$B/config_host" \
  -I "$B/workdir/UnoApiHeadersTarget/udkapi/normal" -I "$B/workdir/UnoApiHeadersTarget/offapi/normal" \
  -I "$B/workdir/CustomTarget/officecfg/registry" \
  "$T/lok_language_probe.cpp" \
  -L "$P" -lmergedlo -li18nlangtag -l:libuno_sal.so.3 -l:libuno_cppu.so.3 -ldl -Wl,-rpath,"$P" \
  -o "$OUT/lok_language_probe"

# probe-1's tool, unchanged, with probe-1's recipe (for the replication arms R-orig-*).
nice -n 10 g++ -std=c++17 -O2 -I "$R/libreoffice-26-8/include" \
  "$R/findings/evidence/new-document/probe-1-native-defaults/tool/lok_defaults_probe.cpp" -ldl \
  -o "$OUT/lok_defaults_probe"
