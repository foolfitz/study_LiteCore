# 開發筆記 2026-08-01 — LibreOffice Qt6-WASM

本篇接續 [`DEVLOG-2026-07-31-wasm.md`](DEVLOG-2026-07-31-wasm.md)，記錄從
Qt6-WASM 環境準備、LibreOffice 完整建置，到 Writer 首次成功啟動及輸入中文的過程。

> 最重要的狀態：**Qt6-WASM Writer 已能開啟且可輸入中文。**
> 原本會使應用程式退出的 `invalid handle: 32` 已由 LibreOffice 本地修補排除；目前的新阻斷是
> 英文按鍵一次輸入兩個字元，另記為
> [`finding 009`](../findings/009-qt6-wasm-duplicate-english-key-input.md)。

---

## 一分鐘版

這一輪完成：

1. 以 Qt 6.10.2、Emscripten 4.0.10 與 JSPI 建出 LibreOffice 26.8 WASM。
2. 排除最終連結仍匯出舊 Qt `qstdweb::EventListener` 符號的問題。
3. 修正部分 symbols 建置未執行 `emdwp`、導致安裝封裝找不到 `.dwp` 的問題。
4. 在瀏覽器顯示 Start Center，並排除開啟 Writer 時的兩個獨立執行期錯誤：
   - Qt 延遲 pointer-enter 事件使用 null DOM node。
   - LibreOffice 從 event-handler pthread 進入 Qt input context，跨 JavaScript context
     使用主執行緒建立的 DOM emval handle。
5. 將 `QtFrame::SetInputContext()` 的 Qt 呼叫同步代理回瀏覽器主執行緒後，Writer 成功開啟，
   中文輸入成功。
6. 同次測試發現英文按鍵重複輸入，尚未診斷。

目前不能宣稱「上游已確認」：成功與失敗都是在帶多個必要本地修補的自訂 Qt6-WASM/JSPI
組態上觀察，且 crash 修補後只有一次手動執行期驗證。

---

## 目前環境

```text
Workspace       /home/jiajun/LibreOffice/study_LiteCore
LibreOffice     libreoffice-26-8 @ 671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb
Build dir       wasm-lite/build-qt6-poc
Qt              6.10.2 WASM
Emscripten      4.0.10
Qt features     thread=ON, wasm_exceptions=ON, wasm_jspi=ON
LO JSPI mode    --enable-emscripten-jspi --disable-emscripten-proxy-to-pthread
Browser         Chrome 150.0.7871.128（已驗證的手動工作階段）
Host            Ubuntu 26.04 LTS / x86-64
```

LibreOffice 的完整 configure 參數保存在
[`wasm-lite/build-qt6-poc/autogen.input`](../wasm-lite/build-qt6-poc/autogen.input)。關鍵部分是：

```text
--enable-qt6
--disable-qt5
--enable-emscripten-jspi
--disable-emscripten-proxy-to-pthread
--with-wasm-module=writer
--with-lang=en-US zh-TW
--enable-symbols=Executable_soffice_bin
--disable-lto
```

### 已驗證產物

```text
soffice.js
SHA-256  90a11899092e7af9004190822c6a24b7885ec126aad174ecd56638477f2debe5

soffice.wasm
SHA-256  601c9ab1de3a6798f1f1fe3be2ba76001fe66312e18b9136d822d9e7726898c9

soffice.wasm.debug.wasm.dwp
SHA-256  7e281e46d6867399d470e84f7152e441647ac027dca99e46f5e9904439bce6d9
```

完整建置與執行期驗證紀錄見
[`findings/evidence/008/main-thread-proxy-validation.txt`](../findings/evidence/008/main-thread-proxy-validation.txt)。

---

## 建置過程

### 1. Qt 6.10.2 WASM

Qt 已完成：

```text
cmake --build
cmake --install
```

安裝位置與環境變數由 `wasm-lite/build-qt6-poc/qt6-poc-env.sh` 管理。開始任何 Qt 或
LibreOffice 增量建置前都要先 source 該檔，避免誤用系統的 Emscripten 3.1.69。

### 2. LibreOffice configure 與 make

LibreOffice configure 完成後，完整 `make` 依序遇到兩個建置問題：

#### finding 006：過期 EventListener export

最終連結 `soffice.js` 時，LibreOffice 要求匯出 Qt 6.10.2 已不存在的
`qstdweb::EventListener` method invoker：

```text
wasm-ld: error: symbol exported via --export not found:
_ZN10emscripten8internal13MethodInvoker...qstdweb13EventListener...
```

LibreOffice 原始碼中兩處硬編碼該 Qt 內部符號。移除舊匯出後，`soffice.js` 與
`uri-encode.js` 完成連結。詳見
[`finding 006`](../findings/006-qt6-wasm-stale-eventlistener-export.md)。

#### finding 004：部分 symbols 未產生 `.dwp`

所有非 instset 模組完成後，封裝階段因 `.dwp` 不存在而失敗：

```text
cp: cannot stat '.../soffice.wasm.debug.wasm.dwp': No such file or directory
```

根因是 Emscripten linker recipe 用實際輸出路徑重新呼叫
`gb_target_symbols_enabled`，而非使用已由 gbuild 正確算出的 target-local `T_SYMBOLS`。
改用非空的 `$(T_SYMBOLS)` 後，最終產生 `.dwp`，`instsetoo_native` 與頂層模組完成：

```text
[build BIN] instsetoo_native
[build MOD] instsetoo_native
[build MOD] libreoffice
[build BIN] top level modules: libreoffice
[build ALL] top level modules: build-non-l10n-only build-l10n-only
```

詳見 [`finding 004`](../findings/004-emscripten-install-partial-symbols.md)。該 finding 的狀態欄與
核取清單尚需另行依最終成功結果整理，這不是本次 008 Bugzilla 草稿的一部分。

---

## 執行期診斷

### 1. Start Center 可啟動

建置與封裝完成後，瀏覽器可以載入 Qt loader、WASM 與資料映像，LibreOffice Start Center
能正常顯示。因此下載、WASM 實例化與基本 Qt 初始化均已通過。

### 2. finding 007：延遲 pointer-enter 使用 null DOM node

開啟 Writer 時，第一個可操作的符號化例外是：

```text
TypeError: Cannot read properties of null (reading 'getBoundingClientRect')
    at dom::mapPoint(...)
    at QWasmWindow::processPointerEnterLeave(...)
    at QWasmSuspendResumeControl::sendPendingEvents()
```

Qt 在 JSPI 模式延後處理 pointer event；處理時 event target 或 screen element 已失效。
本地加入 null/undefined 防護後，這個 TypeError 消失，但 `invalid handle: 32` 仍由另一條路徑
獨立重現。詳見
[`finding 007`](../findings/007-qt6-wasm-pointerenter-null-dom-node.md)。

### 3. finding 008：input context 跨 pthread 使用 DOM emval

完整堆疊定位到：

```text
Emval.toValue()
__emval_set_property()
emscripten::val::set("value", ...)
QWasmInputContext::updateInputElement()
QInputMethod::update()
QWidget::setAttribute(Qt::WA_InputMethodEnabled)
QtFrame::SetInputContext()
vcl::Window::ImplNewInputContext()
```

#### 已確認事實

- handle 32 是 `HTMLInputElement`。
- 它在瀏覽器主執行緒建立：`workerId=0`、`pthread=false`、thread `0x0372a98c`。
- `QWasmInputContext::updateInputElement()` 在 `em-pthread-7`、thread `0x038c0128` 執行。
- worker 的 emval table 中 handle 32 未配置：`allocated=false`、`value=undefined`。
- 同次呼叫的 property key/value handles 有效，只有 DOM object handle 失效。
- 因此不是字串轉換、premature decref 或 finding 007 的殘留錯誤。

原始生命週期證據見
[`findings/evidence/008/emval32-cross-thread-lifecycle.txt`](../findings/evidence/008/emval32-cross-thread-lifecycle.txt)。

Emscripten 的 `emscripten::val` 代表特定 JavaScript context 中的值，必須在擁有它的執行緒
使用。相關上游說明：<https://github.com/emscripten-core/emscripten/issues/20610>。

#### LibreOffice 最小修補

檔案：`libreoffice-26-8/vcl/qt5/QtFrame.cxx`

```diff
-    m_pQWidget->setAttribute(Qt::WA_InputMethodEnabled);
+    GetQtInstance().EmscriptenLightweightRunInMainThread(
+        [this] { m_pQWidget->setAttribute(Qt::WA_InputMethodEnabled); });
```

雖然路徑是 `vcl/qt5`，該程式碼同時供 Qt6 VCL plugin 使用。既有 helper 只在以下組態從
非瀏覽器主執行緒做同步代理：

```text
__EMSCRIPTEN__ && ENABLE_QT6 && HAVE_EMSCRIPTEN_JSPI
    && !HAVE_EMSCRIPTEN_PROXY_TO_PTHREAD
```

其他組態直接執行 lambda。helper 也會在同步代理前釋放 SolarMutex、在目標執行緒重新取得，
因此不應改用裸的 Emscripten proxy 呼叫。

LibreOffice 已有相近先例：commit `46cadd6b0329` 以同一 helper 修正另一個 QtFrame WASM
`invalid handle`：<https://github.com/LibreOffice/core/commit/46cadd6b0329>。

本地 patch：
[`wasm-lite/patches/libreoffice-26.8-qt-wasm-inputcontext-main-thread.patch`](../wasm-lite/patches/libreoffice-26.8-qt-wasm-inputcontext-main-thread.patch)

### 4. 修補後結果

建置確認重新編譯 `vcl/qt6/QtFrame.cxx`、重新連結 Qt6 VCL plugin、`soffice.js` 與
`soffice.wasm`，並完成安裝封裝。

單次手動驗證結果：

- Start Center 正常。
- Writer 成功開啟。
- 不再發生 `invalid handle: 32`。
- 中文輸入成功。
- 英文按一次會出現兩個字元。

最後一項已拆成 [`finding 009`](../findings/009-qt6-wasm-duplicate-english-key-input.md)，不可混進
008 crash 的 Bugzilla ticket。

---

## 上游判定

### 目前能說的

- 在目前自訂組態中，跨 pthread 使用 DOM emval 是直接觀察到的事實。
- `QtFrame::SetInputContext()` 的單行主執行緒代理與 crash 消失有 A/B 關係。
- 本地 `origin/master` 快照 `d9d87d79ced23f8a770eaf94de7e59d59d8eb49e` 仍直接呼叫
  `m_pQWidget->setAttribute(...)`；但這只代表本地 remote-tracking ref 的原始碼檢查，不是
  master 執行期重現。
- LibreOffice 已為相同 WASM 執行緒邊界提供專用 helper，也已有同類修補先例。

### 目前不能說的

- 尚不能把「是否上游」改成「是」。
- 尚未以剛 fetch 的 current master、乾淨 26.8 或只有必要前置修補的組態重現。
- 尚未證明所有 Qt6-WASM／瀏覽器組合都受影響。
- 尚未證明這個修補不會暴露其他 input event 問題；英文按鍵重複仍待診斷。

因此 008 維持「本地修補已驗證／是否上游未確認」，Bugzilla 內容先保存為 draft。

---

## 送上游前的驗證計畫

1. 更新 `origin/master`，建立乾淨、獨立的 master worktree。
2. 確認 current master 的 `QtFrame::SetInputContext()` 仍是直接 Qt 呼叫。
3. 在 current master 或乾淨 `libreoffice-26-8` 上只套必要的 Qt 6.10 建置／啟動前置修補，
   不先套 008 修補，重新取得 crash。
4. 修補前至少重現 3 次，記錄瀏覽器 console、source SHA、產物 SHA 與瀏覽器版本。
5. 只套 008 最小修補，再重建並重跑至少 3 次。
6. 驗證 Start Center、Writer 開啟、中文 composition、英文輸入與基本滑鼠操作。
7. 若可行，對非 WASM Qt6 組態執行編譯與 `make check`，確認 helper 的直接執行路徑無回歸。
8. 搜尋 LibreOffice Bugzilla／Gerrit 是否已有重複。
9. 確認 Bugzilla Component、Hardware／OS 欄位。
10. 補齊 [`findings/drafts/008-bugzilla.txt`](../findings/drafts/008-bugzilla.txt)，再送出。

送出程式修補時應先進 `master`；master 合併後再以 `git cherry-pick -x` 提議回移
`libreoffice-26-8`。2026-08-01 已在 26.8 hard code freeze 時段，是否能進
`libreoffice-26-8-0` 應交由 release engineer 判定，不能自行假設。

---

## 工作樹注意事項

目前 `libreoffice-26-8` 不是乾淨工作樹，包含多個互相獨立的本地修改：

```text
M desktop/CustomTarget_soffice_bin-emscripten-exports.mk
M solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk
M solenv/gbuild/platform/unxgcc.mk
M static/CustomTarget_emscripten_fs_image.mk
M vcl/qt5/QtFrame.cxx
?? LibreOffice_VCL_Qt6_研究報告.md
```

這些既有修改必須保留，不可 reset 或混成一個上游 commit。008 上游提交只能包含
`vcl/qt5/QtFrame.cxx` 的最小變更；其他問題應各自驗證、各自提交。

Workspace 根目錄本身不是 Git repository，因此本篇、findings 與 drafts 不會自動出現在
LibreOffice source tree 的 commit 中。

