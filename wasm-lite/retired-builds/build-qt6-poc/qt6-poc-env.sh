#!/usr/bin/env bash
# 請用 source qt6-poc-env.sh 載入；本檔只設定 Qt6-WASM POC 環境。

export LITECORE_ROOT=/home/jiajun/LibreOffice/study_LiteCore
export EMSDK_ROOT="$LITECORE_ROOT/wasm-lite/tools/emsdk"

export QT6_VERSION=6.10.2
export QT6_HOST_PREFIX=/usr
export QT6_SRC="$LITECORE_ROOT/wasm-lite/tools/qtbase-everywhere-src-6.10.2"
export QT6_BUILD="$LITECORE_ROOT/wasm-lite/tools/qt6-wasm-build-6.10.2-r2"
export QT6_PREFIX="$LITECORE_ROOT/wasm-lite/tools/qt6-wasm-6.10.2"
export QT6DIR="$QT6_PREFIX"

export LO_SRC="$LITECORE_ROOT/libreoffice-26-8"
export LO_BUILD="$LITECORE_ROOT/wasm-lite/build-qt6-poc"
export LO_OUT="$LO_BUILD/instdir/program"
export LO_JOBS=12
export LITE_EXTRA_FONTS_DIR="$LITECORE_ROOT/wasm-lite/tools/extra-fonts"

source "$EMSDK_ROOT/emsdk_env.sh" >/dev/null 2>&1
cd "$LO_BUILD"

printf 'Emscripten: %s\n' "$(em++ --version | head -1)"
printf 'Qt6 source: %s\n' "$QT6_SRC"
printf 'Qt6 prefix: %s\n' "$QT6_PREFIX"
printf 'LO build: %s\n' "$LO_BUILD"
