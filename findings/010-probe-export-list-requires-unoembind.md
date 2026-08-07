# 010 — Core Emscripten exports 清單與「不連 unoembind」的外部 probe 規格衝突

| | |
|---|---|
| **狀態** | 已解決（專案規格問題，已在 probe 層避開並完成雙瀏覽器驗證） |
| **Bugzilla** | 不適用 |
| **發現日** | 2026-08-01 |
| **嚴重度** | 阻斷（外部 probe 無法連結） |
| **可重現** | 1/1 |
| **是否上游** | 否（core 的清單與 core 自身連結方式一致；是外部 probe 規格組合不一致） |

## 現象

R1-B 依規格複製 core 的完整 `soffice_bin-emscripten-exports/exports`，同時依規格不連
`libunoembind.a`。第一層，`wasm-ld` 因 export 清單中的 247 個 UNO 例外 RTTI 沒有定義而
停止；排除這批 RTTI 後，第二層是 `libsofficeapp.a(initjsunoscripting.o)` 仍直接引用
`init_unoembind_uno()`。兩者處理後雖可連結，第一次瀏覽器開檔又發現不能排除所有 RTTI：
`documentLoad` 所拋的 `InteractiveAugmentedIOException` 會越過既有的 UNO exception catch，
造成 uncaught WebAssembly exception。

## 重現步驟

1. 完成 R1-A headless core build。
2. 依 `SPEC-R1-B-probe-app.md` §6 複製完整 core exports 並連結外部 probe。
3. 保持 §6 的限制，不加入 `libunoembind.a` 或 `bindings_uno.js`。

**預期**：外部 probe 成功連結，且不攜帶 UNO embind API。

**實際**：`wasm-ld` 回報大量 `symbol exported via --export not found`，exit 1。

## 證據

- [`evidence/010/link-error.txt`](evidence/010/link-error.txt) — 最先出現的 linker 錯誤與資源摘要。
- Core exports 共 254 行：前 7 行是固定 C exports，後 247 行來自
  `workdir/CustomTarget/bridges/gcc3_wasm/exports`。
- `llvm-nm` 確認失敗範例 `_ZTIN3com3sun4star10deployment16InstallExceptionE` 的 provider 是
  `workdir/LinkTarget/StaticLibrary/libunoembind.a:bindings_uno.o`。
- 同一 archive 也是 `init_unoembind_uno()` 的唯一 provider；第二次連結只剩此一 undefined
  symbol。
- `soffice.js.linkdeps` 不含 `unoembind`。
- A/B 測試確認：只補回
  `__ZTIN3com3sun4star3ucb31InteractiveAugmentedIOExceptionE` 即可讓相同 runtime 正常
  `documentLoad`；額外開除錯符號並非必要條件。
- 最終 `metrics.json` 的 24 份瀏覽器輸出與 round-trip 全數通過，證明處置不是只讓 linker
  靜默通過。

## 分析

Core 自身的 `desktop/Executable_soffice_bin.mk` 同時使用完整 exports，並以
`--whole-archive libunoembind.a` 供應橋接 RTTI，因此 core 組合沒有問題。外部 probe 規格則要求
使用同一份完整 exports，卻明確禁止加入該 archive，兩項要求無法同時滿足。

Probe 只需要固定 C exports（特別是 `libreofficekit_hook_2`）、Emscripten 配置需要的
`main`/allocation exports，以及九個 `_probe_*` ABI。處置是在 probe 的 exports 生成階段排除
`^__ZTI` 橋接清單，再補回實測證明為檔案載入 catch 必需的單一 UCB exception RTTI；另外以
精準的 `--wrap=_Z18initJsUnoScriptingv` 將整個 JavaScript UNO scripting 初始化替換為 probe
端 no-op。這比只補一個 `init_unoembind_uno()` stub 更完整，因為原函式後續還假設 `uno.js`
已建立 `Module.uno_init$resolve` 與 `Module.uno_main$resolve`，而本 probe 按規格不載入
`uno.js`。

「排除全部 RTTI」會開檔失敗的原因可由 A/B 結果定位到該 UCB RTTI 的可見性／唯一性，但
本次沒有再把它推廣成上游工具鏈結論；現階段只採最小、已由兩個瀏覽器驗證的修正。本次沒有
修改 core，亦沒有關閉 undefined-symbol 檢查，最終產物仍未連結 `libunoembind.a`。

## 環境

```text
LibreOffice   26.8.0.1.0+ @ 671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb
Emscripten    4.0.10 (b7dc6e5747465580df5984e723b9d1f10d8e804b)
Build dir     wasm-lite/build-headless-probe
Probe         wasm_sdk_probe
```

## 後續

- [x] 在外部 probe Makefile 排除由 bridge 追加的 `__ZTI*` exports。
- [x] 補回 `documentLoad` 例外處理實際需要的單一 UCB RTTI，完成有／無該 export 的 A/B。
- [x] 在 probe link 精準 wrap 未使用的 `initJsUnoScripting()`，不載入 UNO JS bridge。
- [x] 以嚴格 undefined-symbol 檢查完成連結，並在 Chrome／Firefox 跑過完整垂直切片。
- [x] 將 exports 生成方式回寫研究報告與 DEVLOG。

## 時間軸

- 2026-08-01 首次外部連結於 1.64 秒後穩定失敗。
- 2026-08-01 確認缺失符號由規格禁止的 `libunoembind.a:bindings_uno.o` 提供。
- 2026-08-01 排除橋接 RTTI 後，確認 core startup 還直接呼叫 `init_unoembind_uno()`。
- 2026-08-01 將 exports 收斂為 C ABI，並精準 wrap 不適用的 JS UNO scripting 初始化。
- 2026-08-01 瀏覽器 A/B 定位到 UCB exception RTTI 不可一併排除；只補回該符號後，正式
  `-s` 產物在 Chrome 150／Firefox 152 完成 open、paint、insert、save 與桌面 round-trip。
