# 156 — LibreOfficeKit unipoll: lo_runLoop no longer runs the application (it returns at once) since ImplSVMain returns early when VCL is initialised

| | |
|---|---|
| **狀態** | **已確認**（原生最小重現，2026-10-20；原始碼讀過）；未送 |
| **Bugzilla** | 無（上游送出擱置，2026-08-15 起；只登錄） |
| **發現日** | 2026-10-20（v23 有序指令的原生 unipoll harness，裁決 1 §2.6） |
| **嚴重度** | 一般（對上游）。對本專案：**不擋**——WASM 上 `soffice_main` 刻意洩漏 Desktop，引擎的 mainloop profile 本來就自己呼叫 `Application::Execute`（finding 021）；原生 harness 有繞法 |
| **可重現** | 原生 harness 冒煙 1 次＋最小重現 2 次（不帶 load、帶 load），每次 `runLoop` 都在 0.02–0.03 ms 返回、0 次 poll |
| **是否上游** | **未確認**（強烈指向上游）。原生安裝是從**沒有本地修改**的上游樹（`native-lok-26-8/src`，671c848b）建的；origin/master（2026-10-11，`016fd5d04925`）的 `svmain.cxx` 最後一次改動仍是 `caa4036188ed`、早退還在。缺：上游預設組態的 build、Bugzilla 查重複 |

## 現象

在 unipoll 模式下（`SAL_LOK_OPTIONS=unipoll`），LOK 用戶端呼叫 `pClass->runLoop(kit, poll, wake, data)` 預期會阻塞、由 poll 回呼驅動主迴圈（Collabora 的 kit 就是這樣用：`cool-26-04/kit/Kit.cpp:3561`，`runLoop` 返回時記「Kit unipoll loop run terminated」）。在 26.8（671c848b）上，**`runLoop` 立刻返回、一次 poll 都沒呼叫**。原生之後再呼叫 `documentLoad` 會在 `vcl::Window::ImplUpdateGlobalSettings` 當掉。

## 重現步驟

1. 原生 26.8 安裝（svp）。`SAL_LOK_OPTIONS=unipoll SAL_USE_VCLPLUGIN=svp`。
2. `lok_init_2(install, profile)`。
3. `runLoop(kit, poll, wake, &state)`，poll 回呼計數、第 50 次回 -1（要求結束）。

**預期**：`runLoop` 在第 50 次 poll 之後返回。
**實際**（harness 冒煙 1）：`runLoop` 0.018 ms 返回，poll 0 次。

最小重現：`evidence/156/runloop_returns.cpp`，輸出 `evidence/156/runloop-returns-output.txt`〔已觀察〕：

```
## unipoll, noload
{"rec":"runLoop-returned","ms":0.027,"polls":0}
# exit 0
## unipoll, load
{"rec":"runLoop-returned","ms":0.020,"polls":0}
# exit 139          <- SIGSEGV in documentLoad
## threaded, load   (no unipoll: runLoop is not this mode's API; recorded, not a control)
{"rec":"runLoop-returned","ms":0.217,"polls":0}
{"rec":"documentLoad-returned","doc":true}
```

沒有正向對照：手上沒有 `caa4036188ed` 之前的原生 build，「runLoop 會阻塞」那一側沒量過，只讀過舊版原始碼與 COOL core。

## 證據

- `evidence/156/harness-smoke-1/unipoll-r1.jsonl`：`{"rec":"init","runLoopReturnedMs":0.017773,"pollsDuringRunLoop":0,…}`〔已觀察〕
- 之後的 SIGSEGV 堆疊（harness 自己接著呼叫 `Application::Execute`、在 poll 裡 `documentLoad`）：`ImplUpdateGlobalSettings` ← `WorkWindow::WorkWindow` ← `TaskCreator::createTask` ← `lo_documentLoadWithOptions`。gdb 的輸出抄在 `evidence/link-batch-v23/native/ordered-commands/smoke/NOTES.md`〔已觀察〕
- 環境：`evidence/156/env-native-src.txt`（建原生安裝的樹，乾淨）、`env-libreoffice-26-8.txt`（標頭用的樹，有 5 個本地修改，都與 vcl／desktop 的這段無關）

## 分析（讀原始碼，commit 671c848b）

1. unipoll 的 `lo_initialize` 不建 `lo_startmain`，直接在呼叫端執行緒 `InitVCL()`（`desktop/source/lib/init.cxx:8378-8387`）。`InitVCL` 在沒有 Application 物件時建一個 bare `Application`（`vcl/source/app/svmain.cxx:294-296`），之後 `IsVCLInit()` 為真。
2. `lo_runLoop` 註冊 poll 回呼後呼叫 `soffice_main()`（`init.cxx:7722-7743`）。`soffice_main` 在堆疊上建 `desktop::Desktop aDesktop`（`desktop/source/app/sofficemain.cxx:94`）後呼叫 `SVMain()` → `ImplSVMain()`。
3. **`caa4036188ed`（2026-02-27，"vcl: osx: clean up macOS nested ImplSVMain() hacks"）**之後，`ImplSVMain` 開頭是 `if ( IsVCLInit() ) return EXIT_SUCCESS;`（`svmain.cxx:196-197`）。之前的版本在 VCL 已初始化時照樣執行 `pSVData->mpApp->Main()`（`bInit = bWasInitVCL || InitVCL()` 然後 `if( bInit ) … mpApp->Main()`）——這正是 unipoll 下 `Desktop::Main` 跑起主迴圈的路。Collabora co-26.04 的 core 仍是舊版（`cool-26-04/engine/vcl/source/app/svmain.cxx`，`bWasInitVCL` 那段）。
4. 所以 `Desktop::Main` 從不執行，`runLoop` 立刻返回。原生時 `soffice_main` 返回會解構 `aDesktop`，`~Application` 執行 `ImplDeInitSVData()` 並清 `mpApp`（`vcl/source/app/svapp.cxx:165-168`）——之後的 VCL 使用當掉。Emscripten（無 JSPI）時 `soffice_main` 改用 `new desktop::Desktop()` 刻意洩漏（`sofficemain.cxx:78-92`），所以 WASM 不會當，但同樣**沒有** `Desktop::Main`。

**未驗證（當假說看）**：該 commit 的作者是否預期 LOK unipoll 走這條路；master 在 2026-02-27 之後是否已修。commit 訊息只談 macOS 的巢狀 `ImplSVMain`。

## 對本專案的意義

- 有序指令（v23）的候選 C：引擎的 mainloop profile 本來就自己呼叫 `Application::Execute`（finding 021：`runLoop` 早退，「補呼 `Application::Execute()`」）。021 把早退寫成平台性質；**實際上是這個上游改動**。WASM 上 Desktop 被洩漏所以不當，但 `Desktop::Main` 的初始化不會發生——之後的 v23 規格要列出這件事（哪些初始化由誰做）。
- 原生 harness 的繞法：不呼叫 `runLoop`，自己做它的三個註冊（`registerPollCallbacks`、`registerViewCallbacks`、`UpdateMainThread`），再補 `SfxApplication::GetOrCreate()`（iOS 的 LOK 初始化也自己補這一行，`init.cxx:8294`）。

## 環境

`evidence/156/env-native-src.txt`、`evidence/156/env-libreoffice-26-8.txt`。

## 還缺什麼才能送

- [x] 跑 `evidence/156/runloop_returns.cpp`（不帶 load、帶 load 各一次）：`runloop-returns-output.txt`
- [x] 查 master：origin/master 2026-10-11 的早退還在，`svmain.cxx` 之後沒有改動
- [ ] 正向對照：在 `caa4036188ed^` 的 build 上 `runLoop` 會阻塞並呼叫 poll（需要另一份原生 build，擁有者的 make）
- [ ] 搜尋 Bugzilla／gerrit 有沒有重複（關鍵字 `runLoop` `unipoll` `ImplSVMain` `caa4036188ed`）
- [ ] 確認 Component（大概是 LibreOffice Kit）
- [ ] 上游送出目前擱置（記憶 `upstream-submissions-on-hold`）；重啟時先重查重複

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | LibreOfficeKit（送出前查證） |
| Version | 26.8.0.0 alpha / master（送出前查證） |
| Hardware / OS | x86-64 / Linux |
| Summary | （同標題） |

## 時間軸

- 2026-10-20：原生 unipoll harness 冒煙 1 當掉，讀原始碼找到 `caa4036188ed`；對照 COOL core；登錄。
- 2026-10-20：最小重現在有序指令的正式量測跑完之後跑（不重疊）：unipoll 下 `runLoop` 0 次 poll 立刻返回、之後 `documentLoad` SIGSEGV；origin/master 未修。
