#!/usr/bin/env bash
# Relink only vcldemo in build-nosym after a change to vcl/Executable_vcldemo.mk.
# gbuild does not track .mk changes, and the new pre-js inputs are older than the
# existing output, so clean the target first (recompiles vcldemo.cxx only).
# Same environment as build.sh. usage: relink_vcldemo.sh
set -u
W=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite
U=$W/upstream-master
source "$W/tools/emsdk/emsdk_env.sh" >/dev/null 2>&1
export QT5DIR="$W/tools/qt5-wasm"
export CCACHE_DIR="$U/ccache"
export CCACHE_MAXSIZE=15G
cd "$U/build-nosym" || exit 2
echo "=== start $(date -Is)"
echo "=== src $(git -C "$U/src" log -1 --format='%H %s') dirty=$(git -C "$U/src" status --short --untracked-files=no | wc -l)"
make Executable_vcldemo.clean; rc=$?
echo "=== clean exit=$rc $(date -Is)"
[ $rc -eq 0 ] || exit $rc
make Executable_vcldemo; rc=$?
echo "=== make exit=$rc $(date -Is)"
exit $rc
