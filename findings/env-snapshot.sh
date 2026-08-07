#!/usr/bin/env bash
#
# env-snapshot.sh — 產生可以直接貼進 Bugzilla 的環境區塊
#
# 用法:
#   ./env-snapshot.sh                      # 用預設的 build 目錄
#   BUILDDIR=../wasm-lite/build-stock ./env-snapshot.sh
#   ./env-snapshot.sh > evidence/001/env.txt
#
# 為什麼要有這支：Bugzilla 上最常被退回的原因是環境資訊不完整或不精確。
# 手打會漏、會記錯版本號，隔幾天再補更不可靠 —— 發現當下跑一次存檔最省事。
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LO_SRC="${LO_SRC:-$ROOT/libreoffice-26-8}"
BUILDDIR="${BUILDDIR:-$ROOT/wasm-lite/build}"
TOOLS="${TOOLS:-$ROOT/wasm-lite/tools}"

kv() { printf '%-22s %s\n' "$1" "$2"; }

echo "=== LibreOffice ==="
kv "Version"  "$(sed -n 's/^AC_INIT(\[LibreOffice\],\[\([^]]*\)\].*/\1/p' "$LO_SRC/configure.ac" 2>/dev/null | head -1)"
kv "Branch"   "$(git -C "$LO_SRC" rev-parse --abbrev-ref HEAD 2>/dev/null)"
kv "Commit"   "$(git -C "$LO_SRC" rev-parse HEAD 2>/dev/null)"
kv "Commit date" "$(git -C "$LO_SRC" log -1 --format=%cd --date=short 2>/dev/null)"
# 樹是不是乾淨的 —— 有本地修改的話 bug report 必須講清楚
dirty="$(git -C "$LO_SRC" status --porcelain 2>/dev/null | head -20)"
if [ -n "$dirty" ]; then
    echo "Local modifications:   ⚠ 有（下面列出，回報時務必說明）"
    echo "$dirty" | sed 's/^/                       /'
else
    kv "Local modifications" "無（乾淨的上游樹）"
fi

echo
echo "=== 工具鏈 ==="
kv "Emscripten" "$("$TOOLS/emsdk/upstream/emscripten/emcc" --version 2>/dev/null | head -1)"
kv "Qt branch"  "$(git -C "$TOOLS/qt5-src" rev-parse --abbrev-ref HEAD 2>/dev/null)"
kv "Qt commit"  "$(git -C "$TOOLS/qt5-src" rev-parse HEAD 2>/dev/null)"
kv "Qt repo"    "$(git -C "$TOOLS/qt5-src" remote get-url origin 2>/dev/null)"

echo
echo "=== 主機 ==="
kv "OS"     "$(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME")"
kv "Kernel" "$(uname -r)"
kv "Arch"   "$(uname -m)"
kv "Desktop" "${XDG_CURRENT_DESKTOP:-?}"
kv "CPU"    "$(nproc) cores"
kv "RAM"    "$(awk '/MemTotal/{printf "%.1f GB", $2/1048576}' /proc/meminfo)"
kv "Swap"   "$(awk '/SwapTotal/{printf "%.1f GB", $2/1048576}' /proc/meminfo)"

echo
echo "=== 瀏覽器 ==="
# 系統瀏覽器
for b in google-chrome chromium firefox; do
    command -v "$b" >/dev/null 2>&1 && kv "$b" "$("$b" --version 2>/dev/null | head -1)"
done
# probe.js 用的那一份（版本不同會影響 WASM 行為，要分開記）
if [ -d "$TOOLS/pw/node_modules/playwright" ]; then
    kv "Playwright Chromium" "$(cd "$TOOLS/pw" && node -e \
      "const{chromium}=require('playwright');(async()=>{const b=await chromium.launch();console.log(b.version());await b.close();})()" 2>/dev/null)"
fi

echo
echo "=== configure 參數 ($(basename "$BUILDDIR")) ==="
if [ -f "$BUILDDIR/autogen.lastrun" ]; then
    sed 's/^/    /' "$BUILDDIR/autogen.lastrun"
else
    echo "    （找不到 $BUILDDIR/autogen.lastrun）"
fi

echo
echo "=== 產出 ==="
for d in "$BUILDDIR/workdir/installation/LibreOffice/emscripten"; do
    [ -d "$d" ] || continue
    for f in soffice.wasm soffice.data soffice.js; do
        [ -f "$d/$f" ] && kv "$f" "$(du -h "$d/$f" | cut -f1)"
    done
done
