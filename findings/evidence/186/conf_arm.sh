#!/usr/bin/env bash
# Configure-only arm for finding 186 (no make). Same environment as wasm-lite/upstream-master/build.sh.
# usage: [LO_SRC=<source tree>] conf_arm.sh <arm-dir> <extra autogen flags...>   (LO_SRC defaults to wasm-lite/upstream-master/submit)
# The five stock flags are the ones the 2026-11-11 failing run and build-nosym used.
set -u
SRC_OVERRIDE=${LO_SRC:-}   # read before emsdk_env.sh, which unsets some short names
W=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite
U=$W/upstream-master
ARM=${1:?arm dir}; shift
source "$W/tools/emsdk/emsdk_env.sh" >/dev/null 2>&1
export QT5DIR="$W/tools/qt5-wasm"
export CCACHE_DIR="$U/ccache"
LO_SRC=${SRC_OVERRIDE:-$U/submit}
mkdir -p "$ARM" && cd "$ARM" || exit 2
{
  printf '%s\n' --with-distro=LibreOfficeWASM32 --disable-symbols --enable-ccache \
    --with-build-platform-configure-options=--enable-ccache --with-parallelism=10 "$@"
} > autogen.input
{
  echo "=== start $(date -Is) host=$(hostname)"
  echo "=== src $(git -C "$LO_SRC" log -1 --format='%H %cd' --date=iso) branch=$(git -C "$LO_SRC" branch --show-current)"
  echo "=== src dirty files: $(git -C "$LO_SRC" status --short --untracked-files=no | tr '\n' ' ')"
  echo "=== configure.ac sha256 $(sha256sum "$LO_SRC/configure.ac" | cut -d' ' -f1)"
  echo "=== emcc $(emcc --version | head -1)"
  echo "=== QT5DIR $QT5DIR"
  echo "=== autogen.input:"; cat autogen.input
  SECONDS=0
  "$LO_SRC/autogen.sh"; rc=$?
  echo "=== autogen exit=$rc seconds=$SECONDS $(date -Is)"
} > arm.log 2>&1
grep -E '^=== autogen exit|VCLplugs to be built|^configure: error' arm.log
