#!/usr/bin/env bash
# Upstream master WASM build for the 2026-11-10 re-check of findings 001 and 002.
# Stock configuration per static/README.wasm.md plus an explicit --disable-symbols (same as the default).
# No local patches. Separate ccache so the shared cache used by the kept trees is not evicted.
# usage: build.sh <build-dir-name> [<source-dir>]     (e.g. build-nosym; source defaults to $U/src)
set -u
W=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite
U=$W/upstream-master
B=$U/${1:?build dir name}
source "$W/tools/emsdk/emsdk_env.sh" >/dev/null 2>&1
export QT5DIR="$W/tools/qt5-wasm"
export CCACHE_DIR="$U/ccache"
export CCACHE_MAXSIZE=15G
LO_SRC=${2:-$U/src}   # set after emsdk_env.sh, which unsets some short names
cd "$B" || exit 2
echo "=== start $(date -Is) host=$(hostname) nproc=$(nproc)"
echo "=== src $(git -C "$LO_SRC" log -1 --format='%H %cd' --date=iso) dirty=$(git -C "$LO_SRC" status --short --untracked-files=no | wc -l)"
echo "=== emcc $(emcc --version | head -1)"
echo "=== QT5DIR $QT5DIR  CCACHE_DIR $CCACHE_DIR"
echo "=== autogen.input:"; cat autogen.input
if [ ! -f config_host.mk ] || [ autogen.input -nt config_host.mk ]; then
  "$LO_SRC/autogen.sh"; rc=$?
  echo "=== autogen exit=$rc $(date -Is)"
  [ $rc -eq 0 ] || exit $rc
fi
make; rc=$?
echo "=== make exit=$rc $(date -Is)"
exit $rc
