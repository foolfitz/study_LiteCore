#!/usr/bin/env bash
# source this file; it only sets the environment for the a11y gate 0 core build.
#
# Same environment as the product's core build (`build-headless-probe`): emsdk
# 4.0.10 out of this tree, and LITE_EXTRA_FONTS_DIR for the CJK font the
# fs-image patch injects.  It does NOT cd anywhere, unlike qt6-poc-env.sh.

export LITECORE_ROOT=/home/jiajun/LibreOffice/study_LiteCore
export EMSDK_ROOT="$LITECORE_ROOT/wasm-lite/tools/emsdk"
export LO_SRC="$LITECORE_ROOT/libreoffice-26-8"
export LO_BUILD="$LITECORE_ROOT/wasm-lite/build-a11y-gate0"
export LITE_EXTRA_FONTS_DIR="$LITECORE_ROOT/wasm-lite/tools/extra-fonts"

set +u
# shellcheck disable=SC1091
source "$EMSDK_ROOT/emsdk_env.sh" >/dev/null 2>&1
set -u

printf 'emcc:                  %s\n' "$(emcc --version 2>/dev/null | head -1)"
printf 'LITE_EXTRA_FONTS_DIR:  %s (%s)\n' "$LITE_EXTRA_FONTS_DIR" \
       "$(ls "$LITE_EXTRA_FONTS_DIR" 2>/dev/null | tr '\n' ' ')"
printf 'build dir:             %s\n' "$LO_BUILD"
