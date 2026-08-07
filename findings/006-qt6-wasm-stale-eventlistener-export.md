# 006 — Qt 6.10 WASM/JSPI 最終連結仍匯出已移除的 EventListener 符號

| | |
|---|---|
| **狀態** | 待驗證（最終連結已通過；瀏覽器執行期仍待驗證） |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-08-01 |
| **嚴重度** | 阻斷（`soffice.js` 無法完成最終連結） |
| **可重現** | 1/1（linker 的確定性錯誤） |
| **是否上游** | **未確認**（目前只在自訂 Qt 6.10.2／lite 組態重現） |

## 現象

LibreOffice 的 Qt6-WASM/JSPI 建置已完成大部分 C/C++ 編譯與靜態函式庫連結，最後產生
`instdir/program/soffice.js` 時，`wasm-ld` 因匯出清單包含 Qt 6.10.2 已不存在的
`qstdweb::EventListener::handleEvent` Embind method invoker 而失敗。

`-sASYNCIFY=2 (JSPI) is still experimental` 是 warning；真正使命令回傳非零的是下一行的
`symbol exported via --export not found`。

## 重現步驟

1. 以 Emscripten 4.0.10 建置 Qt 6.10.2，啟用 thread、WASM exceptions 與 WASM JSPI。
2. 設定 LibreOffice 26.8，至少帶入：
   `--enable-qt6 --enable-emscripten-jspi --disable-emscripten-proxy-to-pthread`。
3. 執行 `make`，直到最終連結 `Executable/soffice.js`。

**預期**：產生 `instdir/program/soffice.js` 與對應 WASM 產物。

**實際**：`wasm-ld` 找不到以下被要求匯出的符號，`make` 以 Error 2 結束：

```text
_ZN10emscripten8internal13MethodInvokerINS0_3rvp11default_tagEMN7qstdweb13EventListenerEFvNS_3valEEvPS5_JS6_EE6invokeERKS8_S9_PNS_7_EM_VALE
```

## 證據

- [`evidence/006/make-error.txt`](evidence/006/make-error.txt) — 最終連結錯誤與前後文
- [`evidence/006/env.txt`](evidence/006/env.txt) — 發現當下環境快照；尾端註明快照工具的 Qt5 欄位限制及本次實際 Qt6 環境
- [`evidence/006/symbol-audit.txt`](evidence/006/symbol-audit.txt) — LibreOffice 符號來源及 Qt 6.10.2 archive 符號查核
- [`evidence/006/link-success-qt6-poc.txt`](evidence/006/link-success-qt6-poc.txt) — 移除舊匯出後的最終連結成功證據與產物

關鍵錯誤：

```text
wasm-ld: error: symbol exported via --export not found: _ZN10emscripten8internal13MethodInvokerINS0_3rvp11default_tagEMN7qstdweb13EventListenerEFvNS_3valEEvPS5_JS6_EE6invokeERKS8_S9_PNS_7_EM_VALE
em++: error: '.../wasm-ld @/tmp/emscripten_udu5j62x.rsp.utf-8' failed (returned 1)
```

## 分析

### 已觀察並確認的事實

LibreOffice commit `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb` 在兩處硬編碼同一個
Qt 內部符號：

1. `solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk:36` 的 `-sJSPI_EXPORTS`
2. `desktop/CustomTarget_soffice_bin-emscripten-exports.mk:24-26` 產生的 `EXPORTED_FUNCTIONS` 清單

這段 workaround 來自 LibreOffice commit `5c357a4c66990e2ffd4d46d627ee836e7c30fa25`
（2025-02-12，`Fix plain LOWA build`）。該提交當時所用 Qt 內部實作確實有
`qstdweb::EventListener::handleEvent(emscripten::val)`。

本次安裝的 Qt 6.10.2 中：

- 原始碼與 `libQt6Core.a` 都沒有 `qstdweb::EventListener` 或舊 `MethodInvoker`。
- 事件處理由 `QWasmEventHandler`／`QWasmSuspendResumeControl` 負責。
- `libQt6Core.a` 內存在新的自由函式 invoker：
  `emscripten::internal::Invoker<..., void>::invoke(void (*)())`。
- `qwasmsuspendresumecontrol.cpp` 以 `emscripten::async()` 註冊 `qtSendPendingEvents`；
  Emscripten 4.0.10 的 Embind JS 支援會對 async function-table entry 使用
  `WebAssembly.promising()`。

因此舊符號不是「漏連某個 Qt archive」，而是 LibreOffice 匯出規則和 Qt 6.10.2
內部 ABI 不一致。

### 已排除項目

| 假設 | 結果 | 證據 |
|---|---|---|
| JSPI experimental warning 直接使建置失敗 | 排除 | warning 後仍繼續；真正錯誤來自 `wasm-ld --export` |
| Qt 6.10.2 安裝不完整 | 排除 | QtCore/Gui/Widgets/qwasm archive 均存在，且 `llvm-nm` 可讀出新事件處理符號 |
| 單純是 build cache 留下的舊字串 | 排除 | 目前 LibreOffice 原始碼的兩條規則仍會主動產生該字串 |

### 本地修補

針對本專案固定使用的 Qt 6.10.2：

1. `JSPI_EXPORTS` 僅保留 `_emscripten_check_mailbox`。
2. 不再把舊 `qstdweb::EventListener` method invoker 加入 `EXPORTED_FUNCTIONS`。
3. 同步移除現有 build artifact 匯出清單的舊行，讓下一次 `make` 可直接重新連結。

**已驗證**：移除舊匯出後，`Executable/soffice.js` 與 `Executable/uri-encode.js` 均完成
最終連結，建置進入 `[build ALL] All modules but instset`；`soffice.js` 與 `soffice.wasm`
也已落地。後續失敗是 finding 004 記錄的 `.dwp` 安裝封裝問題，不是舊 Qt 符號再次失敗。

**尚未驗證**：瀏覽器執行期行為。Qt 6.10.2 新事件路徑是否完全涵蓋 LibreOffice 原
workaround 想保護的 Extension Manager／檔案選擇事件，必須實際啟動後測試。

## 環境

```text
LibreOffice   26.8.0.1.0+ @ 671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb
Emscripten    4.0.10 (b7dc6e5747465580df5984e723b9d1f10d8e804b)
Qt            6.10.2，官方 qtbase source tarball
Qt features   thread=ON, wasm_exceptions=ON, wasm_jspi=ON
Host          Ubuntu 26.04 LTS / x86_64
Build dir     wasm-lite/build-qt6-poc
Configure     --enable-qt6 --enable-emscripten-jspi --disable-emscripten-proxy-to-pthread
              --with-wasm-module=writer --with-lang=en-US zh-TW
Local patch   static/CustomTarget_emscripten_fs_image.mk（語系與 CJK 字型；與 linker export 無關）
```

完整快照見 [`evidence/006/env.txt`](evidence/006/env.txt)。

## 還缺什麼才能送

- [x] 套用修補後重新執行 `make`，確認 `soffice.js` 最終連結成功
- [ ] 在瀏覽器啟動，測試基本 UI、中文輸入、檔案選擇與 Extension Manager 事件路徑
- [ ] 用較接近上游預設的 Qt6-WASM 組態重現，排除 lite flags 與本地 fs-image patch
- [ ] 搜尋 LibreOffice Bugzilla／Gerrit 是否已有重複或進行中的 Qt 6.10 修正
- [ ] 確認 Component 與修補是否需保留舊 Qt6 相容性

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | Build tooling（送出前確認） |
| Version | 26.8.0.1 rc |
| Hardware / OS | All / All |
| Summary | WASM/Qt6: stale qstdweb::EventListener export breaks linking with Qt 6.10 |

## 時間軸

- 2026-08-01 Qt 6.10.2／Emscripten 4.0.10 建置到 `soffice.js` 最終連結時失敗
- 2026-08-01 確認舊符號由 LibreOffice 兩處規則加入，Qt 6.10.2 archive 中不存在
- 2026-08-01 確認 LibreOffice GitHub master 仍保留 2025 年 workaround；建立本地相容性修補
- 2026-08-01 手動重跑 `make` 後通過 `soffice.js` 最終連結並到達 `[build ALL]`；瀏覽器執行期仍待驗證
