# 007 — Qt 6.10 WASM/JSPI 延遲 pointer-enter 事件以 null DOM 節點終止應用程式

| | |
|---|---|
| **狀態** | 本地修補已驗證；另有獨立的 [008](008-qt6-wasm-inputcontext-invalid-emval-value.md) 待驗證 |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-08-01 |
| **嚴重度** | 阻斷（Start Center 可開啟，但開啟 Writer 後整個應用程式退出） |
| **可重現** | 1/1（目前只有本地 Qt6-WASM POC 的一次完整觀察） |
| **是否上游** | **未確認**（Qt 官方分支仍有相同未防護路徑，但尚無 stock Qt reproducer） |

## 現象

LibreOffice Qt6-WASM 建置與封裝成功，瀏覽器也能載入 Start Center。從 Start Center 開啟
Writer 後，頁面切回 Qt loader 畫面並顯示：

```text
Application exit (Assertion failed: invalid handle: 32)
```

Chrome DevTools Protocol 留下的較早、且帶完整 WASM 符號的例外是：

```text
TypeError: Cannot read properties of null (reading 'getBoundingClientRect')
    at __emval_call_method
    at dom::mapPoint(emscripten::val, emscripten::val, QPointF const&)
    at QWasmWindow::processPointerEnterLeave(PointerEvent const&)
    at QWasmSuspendResumeControl::sendPendingEvents()
```

接著 pthread 回報 `RuntimeError: unreachable`，並出現使用者看到的
`Aborted(Assertion failed: invalid handle: 32)`。修補並重新測試後，null
`getBoundingClientRect` 已不再出現，但 `invalid handle: 32` 仍可由另一條輸入法路徑
獨立重現；後者另記為 finding 008。

## 重現步驟

1. 使用 Emscripten 4.0.10 與啟用 thread、WASM exceptions、WASM JSPI 的 Qt 6.10.2。
2. 以目前 `build-qt6-poc` 組態完成 LibreOffice 26.8 建置。
3. 以具備 COOP/COEP response headers 的本機 HTTP server 開啟
   `instdir/program/qt_soffice.html`。
4. 等待 LibreOffice Start Center 顯示。
5. 選擇 Writer。

**預期**：建立並顯示空白 Writer 文件。

**實際**：應用程式退出，loader 顯示 `invalid handle: 32`。

## 證據

- [`evidence/007/browser-console-qt6-poc.txt`](evidence/007/browser-console-qt6-poc.txt) —
  CDP 取得的 TypeError、具符號 WASM 堆疊、pthread abort 與其他警告
- [`evidence/007/env-qt6-poc.txt`](evidence/007/env-qt6-poc.txt) —
  LibreOffice commit、本地修改、Qt/Emscripten/Chrome 版本及執行產物
- [`../wasm-lite/patches/qtbase-6.10.2-wasm-pointerenter-null-dom-node.patch`](../wasm-lite/patches/qtbase-6.10.2-wasm-pointerenter-null-dom-node.patch) —
  本地 Qt 6.10.2 防護修補

## 分析

### 已觀察並確認的事實

1. `qt_soffice.html`、`soffice.js` 與 `soffice.wasm` 均以 HTTP 200 載入；server 有送出
   `Cross-Origin-Opener-Policy: same-origin` 與
   `Cross-Origin-Embedder-Policy: require-corp`。
2. Start Center 能顯示，因此這不是 WASM 下載、初始實例化或最終連結階段的失敗。
3. 第一個具可操作堆疊的 JavaScript 例外位於 Qt WASM platform plugin：
   `QWasmWindow::processPointerEnterLeave()` 呼叫 `dom::mapPoint()`。
4. Qt 6.10.2 的 `dom::mapPoint()` 對 source 與 target 無條件呼叫
   `getBoundingClientRect()`；沒有 null/undefined 檢查。
5. 呼叫端傳入 `event.target()` 與 `platformScreen()->element()`。這兩個 DOM 值至少有一個
   在處理時已是 `null`。
6. `QWasmSuspendResumeControl` 在 JSPI/Asyncify 啟用時會把原始事件存入
   `pendingEvents`，等下一次 `processEvents()` 才交給 C++ handler。
7. Qt 6.10.3、Qt 6.10 分支與 dev 分支在檢查日仍保留相同的未防護
   `dom::mapPoint(event.target(), platformScreen()->element(), ...)` 呼叫。
8. 套用本 finding 的 null/undefined 防護、重建 Qt 並重新連結 LibreOffice 後，重新開啟
   Writer 時不再出現 null `getBoundingClientRect` 例外，證明本地防護有效。

### 推論（尚待修補後驗證）

- 開啟 Writer 造成 Qt 視窗與 DOM 結構切換；排隊中的 pointer-enter 事件到達 C++ handler
  時，事件目標或 screen element 已失效。最可能是延遲事件的 `event.target()`，但目前
  stack 無法單獨證明兩個參數中究竟是哪一個為 null。
- 原先把 `invalid handle: 32` 視為 null DOM 例外的可能次生 abort；修補後診斷證明這個
  判斷不成立。它可由 `QWasmInputContext::updateInputElement()` 獨立觸發，詳見 finding 008。
- finding 006 移除過期的 `qstdweb::EventListener` export 使程式成功連結並進入 UI；目前
  沒有證據顯示把舊符號換成另一個硬編碼 invoker 能解決本問題。

## 本地修補

在 Qt 6.10.2 的 `QWasmWindow::processPointerEnterLeave()` 中：

1. 先保存 `event.target()` 與 `platformScreen()->element()`。
2. 任一值為 null 或 undefined 時，略過這次 pointer-enter 事件。
3. 只有兩個 DOM 節點都有效時才呼叫 `dom::mapPoint()`。

這是避免整個應用程式退出的最小防護。它尚未證明是適合送往 Qt 上游的完整修法；上游
修法可能需要在 JSPI 事件入列時保存必要的 DOM 狀態。

## 驗證計畫

- [x] 重新建置並安裝 Qt 6.10.2 WASM
- [x] 重新連結 LibreOffice `soffice.js`／`soffice.wasm`
- [x] Start Center 能正常顯示
- [x] 從 Start Center 開啟 Writer，不再出現 null `getBoundingClientRect`
- [ ] finding 008 修補後不再出現 `invalid handle: 32`／pthread `unreachable`
- [ ] 驗證 Writer 視窗的滑鼠進入、離開、點擊與輸入
- [ ] 建立最小 stock Qt6-WASM/JSPI reproducer，以判定是否可回報 Qt 上游

## 手動重新建置

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
source wasm-lite/build-qt6-poc/qt6-poc-env.sh

cmake --build "$QT6_BUILD" -j"$LO_JOBS"
cmake --install "$QT6_BUILD"

make Executable_soffice_bin.clean
set -o pipefail
make -j"$LO_JOBS" 2>&1 | tee "$LITECORE_ROOT/wasm-lite/logs/lo-qt6-poc-pointerenter-fix.log"
```

## 還缺什麼才能送

- [ ] 修補後重現流程通過
- [ ] 在未套 LibreOffice 本地修補的 stock Qt sample 建立最小重現
- [ ] 搜尋 Qt Bug Tracker／Gerrit 是否已有重複或進行中的修正
- [ ] 確認正確上游修法應防守呼叫端，或在 JSPI 入列時保存事件 DOM 狀態
- [ ] 若確認是 Qt 問題，改以 Qt Bug Tracker／Gerrit 回報，不送 LibreOffice Bugzilla

## 時間軸

- 2026-08-01 LibreOffice Qt6-WASM 完成建置與封裝，Start Center 可正常顯示
- 2026-08-01 開啟 Writer 後退出，使用者介面顯示 `invalid handle: 32`
- 2026-08-01 由 CDP 取得具符號堆疊，定位較早的 null `getBoundingClientRect` 例外
- 2026-08-01 對照 Qt 6.10.2 原始碼與 6.10.3／6.10／dev 分支，確認呼叫路徑沒有防護
- 2026-08-01 套用本地 null/undefined 防護並完成重建；瀏覽器驗證確認原 TypeError 消失
- 2026-08-01 `invalid handle: 32` 仍由輸入法路徑獨立重現，拆分為 finding 008
