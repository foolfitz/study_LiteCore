# SPEC R1-A：headless LibreOffice 26.8 WASM 建置

> **日期**：2026-08-01/**狀態**：可執行 spec（v1）/**上層**：[SPEC-R1-000](./SPEC-R1-000-overview.md)

## 1. 目標

從既有 `libreoffice-26-8` worktree 建出 Writer-only、無 GUI 的 Emscripten 產物，
交付核外連結所需的全部檔案（linkdeps、exports、fs image、pre-js）。

## 2. 前置條件與環境

```bash
cd /home/jiajun/LibreOffice/study_LiteCore

# 1) 環境:沿用 Qt6 POC 的環境檔(它匯出 emsdk 4.0.10 與 LITE_EXTRA_FONTS_DIR)
source wasm-lite/build-qt6-poc/qt6-poc-env.sh

# 2) 驗證(兩者都必須通過才能繼續):
emcc --version | head -1        # 必須是 4.0.10;若顯示 3.1.69 表示吃到系統版,停止並回報
echo "$LITE_EXTRA_FONTS_DIR"    # 必須非空且目錄內有 CJK 字型(*.ttc/*.ttf)
ls "$LITE_EXTRA_FONTS_DIR"

# 3) 確認 worktree 狀態未變(全部 OK 才繼續;失敗代表 worktree 有新修改,停止並回報)
cd libreoffice-26-8
for p in ../wasm-lite/patches/libreoffice-26.8-*.patch; do
  git apply --check --reverse "$p" && echo "OK $p"
done
git log -1 --format=%H   # 應為 671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb
```

關於 worktree 內的既有修改（重要，不要「清理」它們）：

- `static/CustomTarget_emscripten_fs_image.mk` 的兩個修改（多語系 registry、`LITE_EXTRA_FONTS_DIR` 字型注入）是本建置**需要的**。
- `solenv/gbuild/platform/unxgcc.mk`（emdwp/T_SYMBOLS）在本組態（無 symbols）不觸發，無害。
- JSPI export 修改在 `ENABLE_EMSCRIPTEN_JSPI` 條件內，本組態不啟用 JSPI，無害。
- `vcl/qt5/QtFrame.cxx` 在 `--disable-gui` 下不編譯，無害。

## 3. 建置目錄與 configure

新建 `wasm-lite/build-headless-probe/`（srcdir≠builddir，與 `build-qt6-poc` 同模式）：

```bash
mkdir -p /home/jiajun/LibreOffice/study_LiteCore/wasm-lite/build-headless-probe
cd /home/jiajun/LibreOffice/study_LiteCore/wasm-lite/build-headless-probe
```

寫入 `autogen.input`（逐行，不要重排）：

```text
--host=wasm32-local-emscripten
--disable-gui
--with-wasm-module=writer
--with-package-format=emscripten
--enable-cairo-rgba
--with-lang=en-US zh-TW
--disable-debug
--enable-sal-log
--disable-crashdump
--disable-lto
```

依據：上游 `static/README.wasm.md`「Building headless LibreOffice as WASM」範例，
加上總覽 §4 的定案（cairo-rgba 開、symbols 不開、scripting 維持預設、無 JSPI 相關旗標）。
不要照抄 `build-qt6-poc/autogen.input`（那是 Qt6+JSPI 組態）。

```bash
/home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-8/autogen.sh
make -j"$(nproc)" 2>&1 | tee build.log
```

註：configure 與 make 都必須在已 source 環境檔的 shell 執行。建置預估數小時；
最終連結吃記憶體，若 OOM 記錄後回報（不要自行改旗標重試超過一次）。

## 4. 驗收清單（全部通過才算完成）

```bash
B=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/build-headless-probe

# 4.1 核外連結交接物齊備
ls -l $B/instdir/program/soffice.js.linkdeps          # 非空
ls -l $B/instdir/program/soffice.data                 # 存在
ls -l $B/instdir/program/soffice.data.js.metadata     # 存在
ls -l $B/workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link
ls -l $B/workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports

# 4.2 exports 內含 LOK 進入點
grep -c "libreofficekit_hook_2\|lok_preinit_2" \
  $B/workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports   # >=2

# 4.3 fs image 內含 zh-TW registry 與 CJK 字型(驗證兩個 fs-image patch 生效)
python3 - <<'EOF'
import json, io
m = json.load(io.open('BUILDDIR/instdir/program/soffice.data.js.metadata'.replace('BUILDDIR', __import__('os').environ.get('B','/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/build-headless-probe'))))
names = [f['filename'] for f in m['files']]
assert any('Langpack-zh-TW' in n for n in names), 'missing zh-TW registry'
assert any(n.endswith(('.ttc',)) or 'CJK' in n for n in names if '/fonts/' in n), 'missing CJK font'
print('fs image OK,', len(names), 'files')
EOF

# 4.4 soffice.wasm 本體可作為對照(不是探針產物,但應存在)
ls -l $B/instdir/program/soffice.js $B/instdir/program/soffice.wasm
```

## 5. 交付：建置清單檔

寫 `$B/PROBE-BASELINE.md`，內容至少包含：

- source commit（`git -C libreoffice-26-8 log -1 --format=%H`）與 worktree patch 驗證結果；
- `emcc --version` 第一行；
- `autogen.input` 全文；
- §4 各交接物的 `stat -c '%n %s'` 與 SHA-256；
- `soffice.wasm`、`soffice.data`、`soffice.js` 的 raw 與 `gzip -9 | wc -c` 體積
  （這是「core 自身產物」對照組；探針產物體積由 R1-C 量）；
- 建置耗時與遇到的異常。

## 6. 失敗處理

- configure 失敗：先確認 emcc 版本與環境檔；仍失敗則開 finding（`findings/`，附 config.log 相關段落），停止。
- 編譯/連結錯誤：開 finding，附 build.log 中第一個 error 前後 50 行。已知風險：headless+cairo-rgba+lang 組合未在本機驗證過，若錯誤指向本地 fs-image 修改與 `--disable-gui` 的互動，記錄後回報，**不要修改 core 檔案**。
- OOM：記錄 `free -h`、失敗目標名稱，回報。
