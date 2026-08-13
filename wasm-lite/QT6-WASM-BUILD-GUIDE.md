# LibreOffice 26.8 Qt6-WASM 可行性建置指引

本指引的目標不是產出最終精簡版，而是回答一個前置問題：

> LibreOffice 26.8 能否透過 Qt6 + JSPI 在瀏覽器啟動，並正常使用繁中輸入法？

這是一輪 **POC（proof of concept）建置**。在它通過前，先不要同時做 LTO、字型精簡、檔案開啟或其他產品功能。

相關背景見：

- [`../DEVLOG-2026-07-31-wasm.md`](../devlog/DEVLOG-2026-07-31-wasm.md)
- [`../findings/001-wasm-configmgrwriter-crash.md`](../findings/001-wasm-configmgrwriter-crash.md)
- [`../findings/004-emscripten-install-partial-symbols.md`](../findings/004-emscripten-install-partial-symbols.md)
- [`../findings/005-qt5-wasm-no-input-context.md`](../findings/005-qt5-wasm-no-input-context.md)
- [Qt 6.10 官方 WebAssembly 文件](https://doc.qt.io/qt-6.10/wasm.html)

## 0. 先知道的結論

這輪固定使用以下版本與模式：

| 項目 | 固定值 | 理由 |
|---|---|---|
| LibreOffice | 26.8，commit `671c848b1bb8` | 與 Qt5 已知正常的 t3 基準相同 |
| Qt | 6.10.2，只建 QtBase | 本機 host Qt 是 6.10.2；Qt-WASM 要求同版本 host Qt |
| Emscripten | 4.0.10 | LibreOffice 26.8 的 WASM 文件指定版本；Qt 與 LO 必須使用同一套 SDK |
| Qt 模式 | threads + Wasm exceptions + JSPI | LibreOffice 的 Qt6 非 proxy 路徑所需 |
| LO 模式 | Qt6 + JSPI + 關閉 proxy-to-pthread | 26.8 目前唯一已知可嘗試的 Qt6 組合 |
| symbols | 只開 `Executable_soffice_bin` | `--disable-symbols` 已證實會讓 WASM 啟動即崩潰 |
| LTO | 關閉 | 尚未驗證，不能和 Qt5 → Qt6 同輪測試 |

Qt 6.10.2 官方主要搭配 Emscripten 4.0.7，但從原始碼建置時允許使用較新版本。這裡刻意採用 4.0.10，原因是 LibreOffice 端已固定並實測該版本；不要用兩套 Emscripten 分別編 Qt 與 LO。

### 不要做的事

- 不要執行 `build-wasm-lite.sh all`；目前腳本仍以 Qt5 為主，而且 configure 參數含已過時的 `--disable-symbols`。
- 不要修改或重新 configure `build-t3/`；它是已知正常的固定參考點。
- 不要裸打 `emcc`、`em++` 或 `emrun`；系統另有 Emscripten 3.1.69，必須先載入專案的 emsdk。
- 不要在這輪加入 `--enable-lto` 或 `--without-fonts`。
- 不要把 `workdir/installation/` 當唯一產出；部分 symbols 建置會在複製 `.dwp` 時失敗，應以 `instdir/program/` 為準。

## 1. 實驗配置

依照 [`../Skills/build-variable-bisect/SKILL.md`](../Skills/build-variable-bisect/SKILL.md) 的原則，保留已知正常 t3，另開 Qt6 POC 目錄：

```text
wasm-lite/build-t3/                 Qt5、可啟動、中文輸入失敗；固定參考點
wasm-lite/build-qt6-poc/            Qt6 + JSPI；本指引的新建置
wasm-lite/tools/qt6-wasm-build-6.10.2/
wasm-lite/tools/qt6-wasm-6.10.2/
```

Qt5 → Qt6 並不是一個單獨旗標，而是最小的有效變因組：

```text
Qt5 + proxy-to-pthread
          ↓
Qt6 + JSPI + no proxy-to-pthread
```

其餘會影響結果的設定，特別是 release、symbols、Writer-only、語言、字型及 LTO，應與 t3 保持一致。

## 2. 設定本次 shell 環境

以下變數只對目前的 shell 有效。開新終端機時要重新執行：

```bash
export LITECORE_ROOT=/home/jiajun/LibreOffice/study_LiteCore
export EMSDK_ROOT="$LITECORE_ROOT/wasm-lite/tools/emsdk"

export QT6_VERSION=6.10.2
export QT6_HOST_PREFIX=/usr
export QT6_TARBALL="$LITECORE_ROOT/wasm-lite/tools/qtbase-everywhere-src-6.10.2.tar.xz"
export QT6_SRC="$LITECORE_ROOT/wasm-lite/tools/qtbase-everywhere-src-6.10.2"
export QT6_BUILD="$LITECORE_ROOT/wasm-lite/tools/qt6-wasm-build-6.10.2"
export QT6_PREFIX="$LITECORE_ROOT/wasm-lite/tools/qt6-wasm-6.10.2"

export LO_SRC="$LITECORE_ROOT/libreoffice-26-8"
export LO_BUILD="$LITECORE_ROOT/wasm-lite/build-qt6-poc"
export LO_OUT="$LO_BUILD/instdir/program"
export LO_JOBS=12

set -o pipefail
```

## 3. Host 前置套件

本機已經有 CMake、Ninja、Qt 6.10.2 runtime 與 Qt build tools，但目前缺少 `qt6-base-dev` 與 `qmake6`。Qt-WASM cross build 需要同版本的 host Qt headers 與工具。

以下是本指引唯一需要 root 權限的系統修改，請由使用者手動執行；其原因是補齊編譯器工具、LibreOffice host 工具依賴與 Qt 6.10.2 host development files：

```bash
sudo apt install build-essential git ccache autoconf automake libtool \
  pkg-config flex bison gperf gettext python3 python3-dev zip unzip \
  nasm libxml2-utils xsltproc perl cmake ninja-build qt6-base-dev qmake6
```

安裝後做唯讀確認：

```bash
qtpaths6 --qt-version
qmake6 -v
cmake --version | head -1
ninja --version
```

預期 host Qt 為 `6.10.2`。若不是相同 patch 版本，先停止，不要混用不同版本的 host Qt 與 Qt-WASM source。

## 4. 載入並確認 Emscripten 4.0.10

```bash
source "$EMSDK_ROOT/emsdk_env.sh"
command -v em++
em++ --version | head -1
command -v emrun
```

預期：

- `em++` 與 `emrun` 都位於 `wasm-lite/tools/emsdk/` 下。
- `em++` 顯示 `4.0.10`。

若路徑是 `/usr/bin/em++` 或版本是 3.1.69，代表載入錯誤，不能繼續。

## 5. 取得 QtBase 6.10.2 原始碼

只需要 QtCore、QtGui、QtWidgets 與 WASM platform plugin，所以下載 48 MB 左右的 QtBase submodule tarball，不需要 1.2 GB 的完整 Qt source bundle。

```bash
mkdir -p "$LITECORE_ROOT/wasm-lite/tools"
cd "$LITECORE_ROOT/wasm-lite/tools"

test -f "$QT6_TARBALL" || \
  curl -fL -O \
    https://download.qt.io/official_releases/qt/6.10/6.10.2/submodules/qtbase-everywhere-src-6.10.2.tar.xz

printf '%s  %s\n' \
  aeb78d29291a2b5fd53cb55950f8f5065b4978c25fb1d77f627d695ab9adf21e \
  "$(basename "$QT6_TARBALL")" | sha256sum -c -

test -d "$QT6_SRC" || tar -xf "$QT6_TARBALL"
```

Checksum 必須顯示 `OK`。來源與雜湊可由 [Qt 官方 mirror metadata](https://download.qt.io/archive/qt/6.10/6.10.2/submodules/qtbase-everywhere-src-6.10.2.tar.xz.mirrorlist)交叉確認。

## 6. 編譯並安裝 Qt6-WASM

先再確認這個 shell 使用正確 emsdk：

```bash
source "$EMSDK_ROOT/emsdk_env.sh"
em++ --version | head -1
```

建立獨立 build 與 install prefix：

```bash
mkdir -p "$QT6_BUILD" "$QT6_PREFIX" "$LITECORE_ROOT/wasm-lite/logs"
cd "$QT6_BUILD"
```

Configure：

```bash
"$QT6_SRC/configure" \
  -prefix "$QT6_PREFIX" \
  -qt-host-path "$QT6_HOST_PREFIX" \
  -platform wasm-emscripten \
  -release \
  -opensource -confirm-license \
  -feature-thread \
  -feature-wasm-exceptions \
  -feature-wasm-jspi \
  -nomake tests \
  -nomake examples \
  -ccache \
  2>&1 | tee "$LITECORE_ROOT/wasm-lite/logs/qt6-wasm-configure.log"
```

三個 feature 都是必要條件：

- `thread`：LibreOffice 使用 pthread。
- `wasm-exceptions`：JSPI 不相容於舊的 Emscripten JavaScript exceptions。
- `wasm-jspi`：讓 Qt 的巢狀事件流程使用 JS Promise Integration。

若 configure 說 `wasm-jspi` 是未知 feature，應停止並保存 log；不要靜默改成 Asyncify，因為那會變成另一條尚未設計的實驗路線。

檢查 resolved Qt 設定；輸出中三項都應為啟用：

```bash
rg -n 'FEATURE_(thread|wasm_exceptions|wasm_jspi)|QT_FEATURE_(thread|wasm_exceptions|wasm_jspi)' \
  "$QT6_BUILD/CMakeCache.txt"
```

接著建置並安裝：

```bash
cmake --build "$QT6_BUILD" --parallel "$LO_JOBS" \
  2>&1 | tee "$LITECORE_ROOT/wasm-lite/logs/qt6-wasm-build.log"

cmake --install "$QT6_BUILD" \
  2>&1 | tee "$LITECORE_ROOT/wasm-lite/logs/qt6-wasm-install.log"
```

若要重試不同 Qt configure 參數，使用新的 build 目錄後綴，例如 `qt6-wasm-build-6.10.2-r2`，不要覆蓋第一輪紀錄。

## 7. 驗證 Qt6-WASM 安裝內容

先確認 target qmake 查到的是 Qt-WASM prefix，而不是 host Qt：

```bash
test -x "$QT6_PREFIX/bin/qmake"
"$QT6_PREFIX/bin/qmake" -v

export QT6_PLUGIN_ROOT="$("$QT6_PREFIX/bin/qmake" -query QT_INSTALL_PLUGINS)"
printf 'QT6_PLUGIN_ROOT=%s\n' "$QT6_PLUGIN_ROOT"
```

預期 `Using Qt version` 為 6.10.2，library path 指向 `$QT6_PREFIX`。

LibreOffice configure 與產生 HTML 時需要下列檔案：

```bash
test -f "$QT6_PREFIX/lib/libQt6Core.a"
test -f "$QT6_PREFIX/lib/libQt6Gui.a"
test -f "$QT6_PREFIX/lib/libQt6Widgets.a"
test -f "$QT6_PLUGIN_ROOT/platforms/libqwasm.a"
test -f "$QT6_PLUGIN_ROOT/platforms/wasm_shell.html"
test -f "$QT6_PLUGIN_ROOT/platforms/qtloader.js"
test -f "$QT6_PLUGIN_ROOT/platforms/qtlogo.svg"
```

LibreOffice 26.8 的 HTML 產生規則會以 `sed` 替換 Qt 樣板。先確認三個預期 placeholder 都存在：

```bash
rg -n '@APPNAME@|@APPEXPORTNAME@|@PRELOAD@' \
  "$QT6_PLUGIN_ROOT/platforms/wasm_shell.html"
```

應同時看到 `@APPNAME@`、`@APPEXPORTNAME@`、`@PRELOAD@`。若任一不存在，先停止；否則 LibreOffice 可能完成 link，卻靜默產生不能啟動的 HTML。

## 8. 準備 LibreOffice 26.8 原始碼

先記錄固定點並確認沒有非預期變更：

```bash
git -C "$LO_SRC" rev-parse HEAD
git -C "$LO_SRC" status --short
```

預期 commit：

```text
671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb
```

確認繁中翻譯 submodule 已初始化：

```bash
git -C "$LO_SRC" submodule status translations
```

若輸出最前面是 `-`，才執行：

```bash
git -C "$LO_SRC" submodule update --init --depth 1 translations
```

確認 CJK 字型已存在：

```bash
ls -lh "$LITECORE_ROOT/wasm-lite/tools/extra-fonts/"
```

目前預期已有 `NotoSansCJK-Regular.ttc`。

為了讓 `zh-TW` 語言包及 CJK 字型進入 `soffice.data`，套用現有腳本的單一步驟：

```bash
cd "$LITECORE_ROOT/wasm-lite"
LO_SRC="$LO_SRC" ./build-wasm-lite.sh patch

git -C "$LO_SRC" diff --check
git -C "$LO_SRC" diff -- static/CustomTarget_emscripten_fs_image.mk
```

這一步只應修改 `static/CustomTarget_emscripten_fs_image.mk`。若出現其他檔案，先停止檢查。

## 9. 建立 Qt6 POC 的 `autogen.input`

建立新 build 目錄，並預先避開 findings/003 的全新目錄 parallel-build race：

```bash
mkdir -p "$LO_BUILD/workdir/UnpackedTarball"
mkdir -p "$LO_BUILD/workdir_for_build/UnpackedTarball"
```

用編輯器建立 `$LO_BUILD/autogen.input`：

```bash
$EDITOR "$LO_BUILD/autogen.input"
```

內容如下。特別注意 `--with-lang=en-US zh-TW` 必須維持在同一行，而且執行 `autogen.sh` 時不要用 command substitution 展開：

```text
--host=wasm32-local-emscripten
--disable-gen
--disable-scripting
--with-package-format=emscripten
--with-wasm-module=writer
--with-lang=en-US zh-TW
--with-fonts
--enable-release-build
--disable-debug
--disable-dbgutil
--enable-symbols=Executable_soffice_bin
--disable-sal-log
--disable-assert-always-abort
--disable-crashdump
--disable-breakpad
--disable-pch
--disable-lto
--without-help
--without-helppack-integration
--without-myspell-dicts
--without-java
--without-doxygen
--without-export-validation
--disable-python
--disable-cve-tests
--disable-odk
--disable-online-update
--disable-firebird-sdbc
--disable-postgresql-sdbc
--with-theme=colibre
--enable-ccache
--with-build-platform-configure-options=--enable-ccache
--disable-qt5
--enable-qt6
--enable-emscripten-jspi
--disable-emscripten-proxy-to-pthread
```

本檔刻意保留 t3 的冗長 no-op 旗標，讓第一次 Qt6 POC 盡量只改變 Qt 路線。Qt6 確認可行後，再另開一輪清理旗標。

## 10. Configure LibreOffice

同一個 shell 先設定完整環境：

```bash
source "$EMSDK_ROOT/emsdk_env.sh"
export QT6DIR="$QT6_PREFIX"
export LITE_EXTRA_FONTS_DIR="$LITECORE_ROOT/wasm-lite/tools/extra-fonts"

command -v em++
"$QT6DIR/bin/qmake" -v
```

從 build 目錄執行 `autogen.sh`，不帶任何參數，讓它直接讀取 `autogen.input`：

```bash
cd "$LO_BUILD"
"$LO_SRC/autogen.sh" \
  2>&1 | tee "$LITECORE_ROOT/wasm-lite/logs/lo-qt6-poc-configure.log"
```

不要執行下列形式：

```text
autogen.sh $(cat autogen.input)
```

那會把 `--with-lang=en-US zh-TW` 拆成兩個 argv，並把 `zh-TW` 誤判成 build system type。

## 11. Configure 後先檢查 resolved configuration

在付出數小時編譯成本前，確認真正生效的設定：

```bash
rg -n '^export (ENABLE_QT5|ENABLE_QT6|ENABLE_EMSCRIPTEN_JSPI|ENABLE_EMSCRIPTEN_PROXY_TO_PTHREAD|ENABLE_LTO|ENABLE_RELEASE_BUILD|ENABLE_SYMBOLS_FOR|QT6_PLATFORMS_SRCDIR)=' \
  "$LO_BUILD/config_host.mk"
```

預期關鍵值：

```text
ENABLE_QT5=
ENABLE_QT6=TRUE
ENABLE_EMSCRIPTEN_JSPI=TRUE
ENABLE_EMSCRIPTEN_PROXY_TO_PTHREAD=
ENABLE_LTO=
ENABLE_RELEASE_BUILD=TRUE
ENABLE_SYMBOLS_FOR=Executable_soffice_bin
QT6_PLATFORMS_SRCDIR=<Qt6-WASM 的 platforms 路徑>
```

再和已知正常 t3 比較完整 resolved configuration：

```bash
diff -u \
  <(rg '^export ' "$LITECORE_ROOT/wasm-lite/build-t3/config_host.mk" | sort) \
  <(rg '^export ' "$LO_BUILD/config_host.mk" | sort) \
  | rg '^[+-]export ' \
  | rg -v 'SRCDIR|BUILDDIR|WORKDIR|PATH='
```

這個 diff 本來就會有差異。合理差異應集中在：

- Qt5／Qt6 enable 狀態。
- JSPI／proxy-to-pthread 狀態。
- Qt include、library、qmake、moc 與 platform plugin 路徑。

`ENABLE_LTO`、`ENABLE_RELEASE_BUILD`、`ENABLE_SYMBOLS_FOR` 與 Writer-only 狀態若意外不同，先修正 configure，不要開始 make。

## 12. 編譯 LibreOffice Qt6-WASM

```bash
source "$EMSDK_ROOT/emsdk_env.sh"
export QT6DIR="$QT6_PREFIX"
export LITE_EXTRA_FONTS_DIR="$LITECORE_ROOT/wasm-lite/tools/extra-fonts"

cd "$LO_BUILD"
make -j"$LO_JOBS" \
  2>&1 | tee "$LITECORE_ROOT/wasm-lite/logs/lo-qt6-poc-build.log"
```

預期耗時數小時；最後 link `soffice.wasm` 為單執行緒，且會大量使用記憶體。現有 31 GB RAM + 64 GB swap 足以進行這輪非 LTO 建置。

### 關於最後的 `.dwp`／install 失敗

如果 make 最後只因 `emscripten-install` 找不到或複製 `.dwp` 失敗，先對照 [`../findings/004-emscripten-install-partial-symbols.md`](../findings/004-emscripten-install-partial-symbols.md)。只要下節的 `instdir/program/` 產物齊全，就可以繼續做啟動驗證；不要改用不安全的 `--disable-symbols` 迴避。

其他 compile 或 link error 則不屬於這個已知問題，應保存完整 log，停在原錯誤上分析。

## 13. 靜態檢查輸出物

```bash
test -f "$LO_OUT/qt_soffice.html"
test -f "$LO_OUT/soffice.js"
test -f "$LO_OUT/soffice.wasm"
test -f "$LO_OUT/soffice.data"
test -f "$LO_OUT/soffice.data.js.metadata"
test -f "$LO_OUT/qtloader.js"

ls -lh "$LO_OUT"/qt_soffice.html \
  "$LO_OUT"/soffice.js \
  "$LO_OUT"/soffice.wasm \
  "$LO_OUT"/soffice.data \
  "$LO_OUT"/soffice.data.js.metadata
```

確認 Qt template 的 placeholder 已全部替換：

```bash
if rg -n '@APPNAME@|@APPEXPORTNAME@|@PRELOAD@' "$LO_OUT/qt_soffice.html"; then
  printf 'ERROR: Qt template placeholder 尚未替換完成\n'
else
  printf 'OK: 沒有殘留 placeholder\n'
fi

rg -n 'soffice_entry|soffice\.js|window\.Module = instance' \
  "$LO_OUT/qt_soffice.html"
```

確認繁中語言與字型進入虛擬檔案系統：

```bash
rg -n 'Langpack-zh-TW\.xcd|NotoSansCJK-Regular\.ttc' \
  "$LO_OUT/soffice.data.js.metadata"
```

若上述內容缺少，這是 fs image／打包問題，不是 Qt6 輸入法結論；應先修正後再測 IME。

## 14. 啟動本機伺服器

使用 `emrun`，因為 threaded WASM 需要 COOP／COEP headers。不要用單純的 `python -m http.server`。

終端機 A：

```bash
source "$EMSDK_ROOT/emsdk_env.sh"
emrun --no_browser --hostname 127.0.0.1 --port 6940 \
  "$LO_OUT/qt_soffice.html"
```

測試網址：

```text
http://127.0.0.1:6940/qt_soffice.html
```

每次測試請開新分頁；重新整理可能命中舊的 WASM cache。

## 15. 先跑 20 秒自動探針

依照 [`../Skills/emscripten-app-debug/SKILL.md`](../Skills/emscripten-app-debug/SKILL.md)，先用短探針同步收集 console、network、worker、page error、page state 與截圖。

終端機 B：

```bash
cd "$LITECORE_ROOT/wasm-lite/tools/pw"
node probe.js \
  http://127.0.0.1:6940/qt_soffice.html \
  20 \
  /tmp/qt6-wasm-poc.png \
  | tee "$LITECORE_ROOT/wasm-lite/logs/lo-qt6-poc-probe.log"
```

至少確認：

- `soffice.js`、`soffice.wasm`、`soffice.data`、metadata 與 worker 請求都有出現且成功。
- 沒有 `PAGEERROR`、`REQFAIL` 或 `CRASH`。
- page state 的 `crossOriginIsolated` 是 `true`。
- page state 的 `hasSAB` 是 `true`。
- canvas 已顯示並具有合理尺寸。

啟動型錯誤通常在數秒內發生；除非網路下載本身很慢，不要先把探針延長到 90 秒。

## 16. 人工繁中輸入法驗證

自動探針通過後，分別用 Chrome 與 Firefox 開新分頁測試：

1. 等待 Writer 空白文件完全顯示。
2. 先輸入一行英文，確認鍵盤焦點與一般 key event 正常。
3. 切換到 fcitx 繁中輸入法。
4. 輸入「測試中文輸入法」。
5. 確認組字視窗、候選字選擇與文字 commit 都正常。
6. 測試 Backspace、左右方向鍵、候選字切換及第二次連續組字。
7. 保持程式操作至少五分鐘，開啟數個 Qt 對話框，觀察 hang 或 crash。

不要只以「畫面上出現中文字」判定成功；至少要確認 composition 過程沒有漏字、重複 commit、游標錯位或候選視窗失效。

## 17. 成功與失敗判準

| 階段 | 通過條件 |
|---|---|
| Qt build | 三個 feature 開啟；QtBase static libraries、`libqwasm.a` 與 loader template 齊全 |
| LO configure | Qt6、JSPI 開；proxy、Qt5、LTO 關；symbols 只開 soffice target |
| LO link | `instdir/program/` 的 HTML、JS、WASM、data 與 metadata 齊全 |
| 自動啟動 | 20 秒無 crash；所有資源成功請求；cross-origin isolation 與 SAB 正常 |
| 核心目標 | Chrome 與 Firefox 都能完成繁中 composition、候選選字與 commit |
| 初步穩定性 | 一般輸入及數個 Qt 對話框操作五分鐘，沒有可重現的 hang／crash |

若只有 `.dwp` 打包失敗，但 `instdir/program/` 可正常啟動，不算 Qt6 路線失敗。

若 Qt6 能啟動但繁中輸入仍完全無反應，才算這輪核心假設失敗；保存 browser、輸入法、console 與 network 證據後，再決定要修 Qt input context 還是重新評估架構。

## 18. 常見問題定位

### `Qmake not found`

- `QT6DIR` 必須指向 Qt6-WASM install prefix。
- 不要拿 `/usr/bin/qmake` 代替；目前它是 Qt5。
- `$QT6DIR/bin/qmake -v` 必須顯示 Qt 6.10.2 並指向 target prefix。

### `No Qt6 WASM QPA plugin found`

檢查：

```bash
"$QT6DIR/bin/qmake" -query QT_INSTALL_PLUGINS
```

該路徑下的 `platforms/` 必須同時有 `libqwasm.a` 與 `wasm_shell.html`。

### Link 時出現 JSPI 或 exception undefined symbol

先確認：

- Qt 與 LibreOffice 都由同一個 Emscripten 4.0.10 編譯。
- Qt configure 同時開啟 `wasm-jspi` 與 `wasm-exceptions`。
- LO resolved config 的 `ENABLE_EMSCRIPTEN_JSPI=TRUE`。
- 沒有意外使用 Qt host libraries 取代 Qt-WASM static libraries。

### `qt_soffice.html` 存在但 loader 不動

先查 placeholder 與 `window.Module = instance`，再看探針 network timeline。Qt 樣板若已改版，LibreOffice `solenv/gbuild/platform/unxgcc.mk` 的 `sed` 可能靜默失效。

### Worker 或 SharedArrayBuffer 錯誤

- 必須由 `emrun` 或其他會送 COOP／COEP headers 的 server 提供檔案。
- 確認網址是 `127.0.0.1`／`localhost` 或 HTTPS。
- 探針中的 `crossOriginIsolated` 與 `hasSAB` 都必須為 `true`。

### 白畫面但 console 線索很少

不要先猜。確認 network timeline 是否真的請求 `.wasm`、`.data`、metadata 與 worker；缺少的 request 通常比 stack trace 更能定位 loader 問題。

## 19. 記錄實驗結果

完成後更新一張最小矩陣：

```text
build dir       Qt / 執行模式                    啟動    繁中 IME    穩定性
--------------  --------------------------------  ------  ----------  --------
build-t3        Qt5 + proxy-to-pthread            OK      FAIL        baseline
build-qt6-poc   Qt6 + JSPI + no proxy-to-pthread  ?       ?           ?
```

環境快照：

```bash
cd "$LITECORE_ROOT/findings"
BUILDDIR=../wasm-lite/build-qt6-poc ./env-snapshot.sh \
  | tee "$LITECORE_ROOT/wasm-lite/logs/lo-qt6-poc-environment.txt"
```

請分開記錄：

- **已驗證事實**：特定組態是否能編、啟動、輸入中文。
- **機制推論**：為什麼會 hang、crash 或無法輸入。

這輪完成後，才決定是否把 Qt6 支援正式整合進 `build-wasm-lite.sh`，並另開後續的字型精簡與 LTO 實驗。
