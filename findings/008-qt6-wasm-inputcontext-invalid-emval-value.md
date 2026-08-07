# 008 — Qt 6.10 WASM input context 使用失效的 DOM emval handle

| | |
|---|---|
| **狀態** | 本地修補已驗證；Bugzilla 草稿已建立；待乾淨 master／26.8 驗證 |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-08-01 |
| **嚴重度** | 阻斷（Start Center 可開啟，但開啟 Writer 後整個應用程式退出） |
| **可重現** | 修補前 5/5；主執行緒代理修補後 0/1 |
| **是否上游** | **未確認**（只在 LibreOffice 自訂 Qt6-WASM/JSPI 組態重現） |

## 現象

finding 007 的 pointer-enter null DOM 防護生效後，從 LibreOffice Start Center 開啟
Writer 仍會退出，loader 顯示：

```text
Application exit (Assertion failed: invalid handle: 32)
```

這次執行過程已不再出現 null `getBoundingClientRect`，因此不是 finding 007 的殘留例外。

## 重現步驟

1. 使用 Emscripten 4.0.10 與啟用 thread、WASM exceptions、WASM JSPI 的 Qt 6.10.2。
2. 套用 finding 007 的 pointer-enter null/undefined 防護。
3. 以目前 `build-qt6-poc` 組態建置 LibreOffice 26.8。
4. 以具備 COOP/COEP response headers 的本機 HTTP server 開啟
   `instdir/program/qt_soffice.html`。
5. 等待 LibreOffice Start Center 顯示，再選擇 Writer。

**預期**：建立並顯示空白 Writer 文件。

**實際**：應用程式退出，loader 顯示 `invalid handle: 32`。

## 證據

- [`evidence/008/browser-stack.txt`](evidence/008/browser-stack.txt) — 暫時區分 handle 類型後取得的
  第一次完整 emval stack
- [`evidence/008/browser-stack-after-ecmastring.txt`](evidence/008/browser-stack-after-ecmastring.txt) —
  `toEcmaString()` 版本仍失敗的第二次完整 stack
- [`evidence/008/env-qt6-poc.txt`](evidence/008/env-qt6-poc.txt) — LibreOffice、Qt、Emscripten、
  瀏覽器與執行產物
- [`evidence/008/env-reentrant-backport.txt`](evidence/008/env-reentrant-backport.txt) — 官方重入
  修正建置完成後、尚未執行瀏覽器驗證的環境快照
- [`evidence/008/build-validation.txt`](evidence/008/build-validation.txt) — Qt 增量建置／安裝、
  `toEcmaString()` 實驗的 LibreOffice 重新連結與產物雜湊
- [`evidence/008/reentrant-backport-validation.txt`](evidence/008/reentrant-backport-validation.txt) —
  Qt 重入修正、增量建置／安裝、LibreOffice 重新連結與產物雜湊
- [`evidence/008/emval32-cross-thread-lifecycle.txt`](evidence/008/emval32-cross-thread-lifecycle.txt) —
  handle 32 在主頁建立、卻由 `em-pthread-7` 使用時未配置的直接生命週期證據
- [`evidence/008/main-thread-proxy-validation.txt`](evidence/008/main-thread-proxy-validation.txt) —
  LibreOffice 主執行緒代理的增量建置、產物雜湊與手動 Writer／中文輸入驗證
- [`../wasm-lite/patches/qtbase-6.10.2-wasm-inputcontext-ecmastring.patch`](../wasm-lite/patches/qtbase-6.10.2-wasm-inputcontext-ecmastring.patch) —
  已被執行期測試反證並還原的字串轉換實驗
- [`../wasm-lite/patches/qtbase-6.10.2-wasm-suspendresume-reentrant.patch`](../wasm-lite/patches/qtbase-6.10.2-wasm-suspendresume-reentrant.patch) —
  Qt 官方重入修正（配合 6.10 的整數事件計數）；已排除前置的 `undefined.index` 例外，
  但沒有修正最終 invalid handle
- [`../wasm-lite/patches/libreoffice-26.8-qt-wasm-inputcontext-main-thread.patch`](../wasm-lite/patches/libreoffice-26.8-qt-wasm-inputcontext-main-thread.patch) —
  將 `QtFrame::SetInputContext()` 的 Qt 呼叫同步代理回瀏覽器主執行緒；已完成建置與一次
  Writer／中文輸入驗證
- [`drafts/008-bugzilla.txt`](drafts/008-bugzilla.txt) — 依目前證據整理的 LibreOffice
  Bugzilla 英文草稿；送出前仍需完成檔尾 TODO

## 分析

### 已確認的事實

1. 暫時把 Emscripten 兩個同名 assertion 分成 `invalid emval handle` 與
   `invalid promise handle` 後，錯誤明確為 `invalid emval handle: 32`。
2. stack 由 `Emval.toValue()` 經 `__emval_set_property()` 回到：

   ```text
   emscripten::val::set<char const (&) [6], std::string const&>()
   QWasmInputContext::updateInputElement()
   QInputMethod::update()
   QWidget::setAttribute()
   QtFrame::SetInputContext()
   vcl::Window::ImplNewInputContext()
   ```

3. `char const (&)[6]` 對應 property 名稱 `"value"`；
   `QWasmInputContext::updateInputElement()` 中唯一相符呼叫為：

   ```cpp
   m_inputElement.set("value",
       queryEvent.value(Qt::ImSurroundingText).toString().toStdString());
   ```

4. 先前把 JavaScript `9683:22` 判成第三個參數是錯誤的；帶 stack 的產物中該行實際是：

   ```js
   handle = Emval.toValue(handle);
   ```

   因此失效的是第一個參數 `m_inputElement`（DOM object handle），不是 property value。
5. 把 value 從 `toStdString()` 改為 `toEcmaString()` 後仍 100% 重現，且仍在
   `QWasmInputContext::updateInputElement()` 的相同 WASM 呼叫位址 `0x53f6476` 退出；字串
   轉換假說已被反證，原始碼已還原為 `toStdString()`。
6. 較早的監控在 invalid handle 之前另捕捉到
   `QWasmSuspendResumeControl::sendPendingEvents()` 對 `undefined` event 讀取 `index`。
   Qt 6.10.2 先快取 `pendingEvents.length`，handler 重入並由內層清空佇列後，外層仍會依舊
   數量繼續 `shift()`。
7. Qt 官方提交 `3a217d259260` 將迴圈改為每輪重新讀取佇列長度；提交
   `66e3fe3f9557` 隨後將回傳型別改成事件數量並標示回補 6.10。此 6.10.2 原始碼只有後者
   的整數計數介面，卻仍是前者修正前的快取迴圈。
8. 回補 suspend/resume 重入修正後，先前的 `sendPendingEvents()` `undefined.index` 例外不再
   出現，但 Writer 仍在相同 input-context 路徑以 `invalid handle: 32` 退出。
9. handle 生命週期追蹤顯示 `QWasmWindow` 在瀏覽器主執行緒（`workerId=0`、
   `pthread=false`、thread `0x0372a98c`）建立 handle 32；值為 `HTMLInputElement`，保存後
   refcount 為 1。
10. `QWasmInputContext::updateInputElement()` 實際在 `em-pthread-7`（thread `0x038c0128`）
    執行。該 worker 的 emval 表沒有 handle 32：`allocated=false`、`value=undefined`；嘗試
    incref 後 refcount 變成 `NaN`。
11. 同一 worker 的 property key/value handles 34、36 都有效，分別是 `"value"` 與空字串；
    只有 object handle 32 缺失。因此這不是 premature decref，也不是字串轉換錯誤，而是把
    主頁 JavaScript context 的 emval handle 帶進另一個 pthread worker 使用。
12. Qt 的 `qwasminputcontext.cpp` 同時以 `-pthread` 與 `-DNDEBUG` 編譯。Emscripten `val.h`
    原本會在 `_REENTRANT` 下以 C `assert(pthread_equal(thread, pthread_self()))` 檢查 val owner，
    但 `-DNDEBUG` 會移除這個檢查，所以錯誤延後到 worker 的 `Emval.toValue()` 才顯現。
13. 診斷修改只套用在產生的 `soffice.js`；生命週期擷取後已還原，SHA-256 回到
   `74b010f544c13212a215d0c468402b1d2bf9ba58ec4f75a160c6dbea86c56f2e`。
14. 主執行緒代理修補後，建置 log 明確包含重新編譯 `vcl/qt6/QtFrame.cxx`、重新連結
    `libvclplug_qt6lo.a` 與 `soffice.js`，並完成 `instsetoo_native` 和頂層模組。
15. 修補後產物能從 Start Center 開啟 Writer，且操作者成功輸入中文；該次流程未再以
    `invalid handle: 32` 退出。
16. 同次測試觀察到英文按鍵一次產生兩個字元。這不是本 finding 的 invalid-handle crash，
    已獨立記錄為 [finding 009](009-qt6-wasm-duplicate-english-key-input.md)。

### 推論（NOT VERIFIED — 待乾淨 master／26.8 驗證）

- 在目前自訂組態中，Qt WASM platform plugin 的 DOM 操作必須留在建立 DOM handle 的
  JavaScript context；LibreOffice Writer focus 流程卻讓 `QWasmInputContext` 從另一個 pthread
  進入。這個執行緒邊界是已觀察的機制，但是否能直接推廣到 current master 仍待驗證。
- `QtFrame::SetInputContext()` 主執行緒代理與 crash 消失有直接的單次 A/B 關係，也符合
  emval owner-thread 證據。LibreOffice 已有同一 helper 修正其他 QtFrame WASM
  `invalid handle` 的先例，因此目前最合理的上游修法是在 LibreOffice 邊界代理；但仍需乾淨
  master／26.8 組態驗證，才能把「是否上游」改成「是」。
- Qt 6.7 沒有 `QWasmSuspendResumeControl`，所以版本差異是合理因素；但 Qt 6.7 原始實驗同時
  搭配 emsdk 3.1.51，尚未建立完整版本矩陣比較，不能只把問題歸因於 Qt 6.10。
- 如果上述邊界代理仍出現其他 invalid handle，再讓 `val.h` 的 wrong-thread 檢查在 Release
  組態輸出 owner/current pthread，以找出下一個未代理的 Qt 入口。

### 上游原始碼檢查邊界

- 本地 `origin/master` 快照 `d9d87d79ced23f8a770eaf94de7e59d59d8eb49e` 的
  `QtFrame::SetInputContext()` 仍直接呼叫 `m_pQWidget->setAttribute(...)`。
- 同檔已有多處 `EmscriptenLightweightRunInMainThread()` 使用方式，包含先前針對另一個
  `invalid handle` 的 `SetScreenNumber()` 修正（LibreOffice commit `46cadd6b0329`）。
- 以上是原始碼檢查，不等於 current master 的執行期重現；送單前仍必須 fetch 並記錄新的
  exact commit。

## 本地修補

- `toEcmaString()`：已建置並重現相同錯誤，**已還原**；patch 僅保留為負面證據。
- suspend/resume 重入：已套用 Qt 官方 `3a217d259260` 的 live-length 迴圈，並保留
  `66e3fe3f9557` 在 6.10 使用的整數事件計數語意；Qt 增量建置、安裝與 LibreOffice
  重新連結均成功。執行期確認它排除了 `undefined.index`，但沒有排除 invalid handle。
- LibreOffice input-context 主執行緒代理：已在 `QtFrame::SetInputContext()` 以
  `EmscriptenLightweightRunInMainThread` 包住 `QWidget::setAttribute()`；已完成增量建置，單次
  手動驗證可開啟 Writer 並輸入中文，不再發生原 invalid-handle crash。

## 驗證計畫

- [x] `toEcmaString()` 執行期反證並還原
- [x] 回補 Qt 官方 suspend/resume 重入修正
- [x] 增量建置並安裝 Qt 6.10.2 WASM
- [x] 重新連結 LibreOffice `soffice.js`／`soffice.wasm`
- [x] 確認暫時產生檔診斷碼不存在，`soffice.js` 回到原始 SHA-256
- [x] 追蹤 handle 32 的配置、引用與使用所在 pthread
- [x] 確認 handle 32 從瀏覽器主執行緒跨到 `em-pthread-7`
- [x] 準備 `QtFrame::SetInputContext()` 主執行緒代理修補
- [x] 增量重建 LibreOffice VCL 與 `soffice`
- [x] 驗證主執行緒代理修補（1 次手動驗證）
- [x] Start Center 能正常顯示
- [x] 從 Start Center 開啟 Writer，不再出現 `invalid handle: 32`
- [x] Writer 文件能接受中文輸入
- [ ] 在相同產物重複驗證至少 3 次
- [ ] 以乾淨 current master 或 `libreoffice-26-8`、只帶必要前置修補重現
- [ ] 在 current master 套用相同最小修補並驗證
- [ ] 若可行，編譯／測試非 WASM Qt6 組態

## 還缺什麼才能送

- [x] 跨 pthread 修補後 Writer 重現流程通過（1 次手動驗證）
- [x] 準備 `drafts/008-bugzilla.txt`，明確揭露自訂組態與其他本地修補
- [ ] fetch current master 並記錄 exact commit
- [ ] 在乾淨 current master 或 `libreoffice-26-8` 重現修補前結果至少 3 次
- [ ] 只套 `SetInputContext()` 最小修補，重現修補後結果至少 3 次
- [ ] 保存修補前後的乾淨 browser console、source SHA 與產物 SHA
- [ ] 搜尋 LibreOffice Bugzilla／Gerrit 是否已有重複或進行中的修正
- [ ] 確認 LibreOffice Bugzilla Component、Hardware 與 OS 欄位
- [ ] 若可行，確認非 WASM Qt6 build／`make check` 不受影響

## 時間軸

- 2026-08-01 finding 007 修補後，null `getBoundingClientRect` 消失，但 Writer 仍以
  `invalid handle: 32` 退出
- 2026-08-01 暫時區分 Emscripten assertion 並加入 stack，確認為 emval handle；當時誤判成
  property value，後續由精確 JavaScript 行號更正為第一個 DOM object 參數
- 2026-08-01 將 Qt `QWasmInputContext` surrounding text 轉換改為 `toEcmaString()`
- 2026-08-01 `toEcmaString()` 版本仍以相同 `invalid emval handle: 32` 退出；確認失效的是
  `__emval_set_property` 第一個參數，還原字串實驗
- 2026-08-01 確認 Qt 6.10.2 具備 `66e3fe3f9557` 的事件計數介面，但缺少
  `3a217d259260` 的重入安全迴圈
- 2026-08-01 回補官方重入修正；Qt 增量建置／安裝與 LibreOffice 重新連結成功，等待
  Writer 執行期驗證
- 2026-08-01 Writer 驗證仍出現 `invalid handle: 32`，但先前的
  `QWasmSuspendResumeControl::sendPendingEvents()` `undefined.index` 例外已消失
- 2026-08-01 暫時追蹤 emval handle 32，確認 `HTMLInputElement` 在瀏覽器主執行緒建立，
  `QWasmInputContext::updateInputElement()` 卻從 `em-pthread-7` 使用相同數值 handle；該 worker
  的 emval 表中 handle 未配置，根因定位為跨 JavaScript context 使用 `emscripten::val`
- 2026-08-01 在 LibreOffice `QtFrame::SetInputContext()` 準備最小主執行緒代理修補；等待
  LibreOffice 增量重建與 Writer 執行期驗證
- 2026-08-01 增量建置重新編譯 `QtFrame.cxx`、重新連結 Qt VCL plugin 與 `soffice`，並完成
  安裝集封裝
- 2026-08-01 手動驗證 Writer 成功開啟且中文可輸入，原 invalid-handle crash 未再出現；
  英文按鍵重複輸入另立 finding 009
- 2026-08-01 依目前證據建立 LibreOffice Bugzilla 草稿；維持「是否上游＝未確認」，等待
  current master／乾淨 26.8 的修補前後驗證
