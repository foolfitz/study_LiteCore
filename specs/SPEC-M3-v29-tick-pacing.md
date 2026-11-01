# SPEC-M3-v29-tick-pacing：有工作時不等主迴圈節拍（引擎 `e2-editor-v29`、殼層 generation 83、宿主 0.2.45）

> 狀態：**釘死**（2026-11-01，連結之前）。審核一輪（opus，`findings/evidence/v29-177/review-opus-1.md`），會改變行為或判準的項目已併入；不再開第二輪。之後只准追加（CLAUDE.md 第 10 節）。
> 依據：finding 177；擁有者 2026-11-01 選 B「停下，先修延遲」。

## 1. 為什麼要有

finding 177：v23 起打字每字 commit 從 4 ms 變 85 ms，上螢幕 13 ms 變 67 ms。原因是 core 的主迴圈 100 fps、每拍只派一個使用者事件，而有序引擎在 poll 回覆。鏡像實驗證實：只改節奏，commit 就回到 9.8 ms。這也讓 K6 不可能成立，所以 K 停在這裡。

## 2. 範圍

**做**：

1. 引擎：`src/main_loop_pacing.hpp` 的純規則，掛在 `mainLoopPollCallback`：有工作時 `EM_TIMING_SETIMMEDIATE`（搭引擎 worker 內的 `MessageChannel`），閒置滿 300 ms 回 `EM_TIMING_SETTIMEOUT, 10`（等於 core 的 fps=100）。
2. profile `e2-editor-v29`（v28 的後繼，**要重新連結**，擁有者跑）。
3. 殼層 generation 83（頁面釘新的 wasm 與 worker 路徑）；宿主 0.2.45。

**不做**：

- 不動 core（`svpinst.cxx` 的 fps 與一拍一事件都不改）。
- 不動有序引擎的規則：一次 poll 一個回覆或一個指令、回覆優先、poll 不阻塞。
- worker 不變：`sdk/v28-last-block-worker.js` 逐位元組沿用。ABI 6、export、manifest 葉都不變。
- 頁面暫存佇列的上限不改（AS-5 先看 v29 重跑的結果，§7 第 5 項）。

## 3. 決定紀錄

| 題 | 決定 | 理由 |
|---|---|---|
| 為什麼不用常駐 immediate | 不採用 | 閒置文件會讓一顆核心空轉 |
| 為什麼不用 `setTimeout(0)` | 不採用 | 瀏覽器夾到約 4 ms，實測 44.8 ms，過不了 C2 |
| immediate 的機制 | 預先裝 `MainLoop.setImmediate`（`MessageChannel`），不用 emscripten 的模擬 | 模擬在 pthread 裡有無界洩漏（`Module["setImmediates"]` 沒有消費者），且每拍經 `sdk-worker` 轉發；實測延遲同級（finding 177） |
| 為什麼不改 core | 不採用 | core 重建是小時級；引擎一個呼叫就夠 |
| 切換在哪裡 | 只在 poll | 引擎執行緒、迴圈內；事件 tick 不到 poll，所以事件排空中途不會切換 |
| 「有工作」的定義 | 本次 poll 處理過東西，或有指令排隊，或有回覆待送 | 與 `anyInput` 同源 |
| 寬限時間 | 300 ms | 大於 C2 最慢間隔 200 ms，連續打字不會回到節拍；閒置只多空轉不到 0.3 秒 |
| 回到節拍的值 | `EM_TIMING_SETTIMEOUT, 10` | `emscripten_set_main_loop_arg(..., 100, 1)` 換算的值，閒置行為與 v28 相同 |
| define | `OXSDK_E2_V29_TICK_PACING`，沒有 `OXSDK_E2_V28_LAST_BLOCK` 就 `#error` | 比照 v28 |
| 回歸基準 | v28／generation 82／0.2.44 | 上一個出貨版 |

## 4. 身分與連結的機械

- Makefile v29 區塊是 v28 的文字換名字，多 `-DOXSDK_E2_V29_TICK_PACING` 與 `src/main_loop_pacing.hpp` 依賴；匯出表、worker 基底取 `build/archive/e2-editor-v28-13f674e4-worker-a5df83db`；連結受守衛（`refuse_unasked_relink`）。
- 新檔：`tools/check_v29_tick_pacing_contract.py`、`tools/build_e2_v29_tick_pacing_profile.py`、`tools/link_v29_tick_pacing_owner.sh`、只跑測試的 `test-v29-tick-pacing-static`。v28 的工具位元組不動。
- `test-e2-c-static` 的 M1-1 載體行加 `--carrier E2_V29=probe_engine,sdk_api,editor_api`。
- **連結是擁有者的**：`bash tools/link_v29_tick_pacing_owner.sh`（agent 只跑 `bash -n`）。

## 5. 連結前的判準（agent 跑，證據 `findings/evidence/v29-177/pre-link/`）

| 代號 | 判準 |
|---|---|
| U | `tests/main_loop_pacing_test.cpp` 綠；四個變異都紅（`pacing-mutations.txt`） |
| S | `-fsyntax-only` exit 0；三個正向對照都在預期處報錯（少 v28 define 的 `#error`、掛鉤呼叫與 switch 各改壞一處） |
| M | `make -i test-e2-c-static` 紅集合恰好等於 `p6-named-reds.txt`；M1-1 帶 E2_V29 成立 |
| D | `make -n` 只有 `build/e2/editor-v29` 的編譯行加一次受守衛的連結 |

## 6. 連結後的判準（agent 跑，鏡像）

| 代號 | 判準 | 沒做的預設 |
|---|---|---|
| P | contract 工具 `--manifest` 成立、`withheld: []`、封存 | 不切頁 |
| T1 | 桌面乾淨、單獨跑：C2 全部 12 格 3 輪，兩支 judge 照 J-b.2 的表 | 不出 0.2.45 |
| T2 | 閒置 CPU：瀏覽器整棵行程樹的 CPU 秒數（`/proc` 的 utime＋stime），靜置 10 秒，**v29 ≤ v28 × 1.5 ＋ 0.5 秒**。四種情況都量：`boundaries` 與長文件，各在「開好」與「打 10 字後等 2 秒」；兩瀏覽器。紅案：常駐 immediate（`diag_tick.py channel`）必須不過 | 不出 0.2.45 |
| T3 | 順序：第 83 代 F3、F4、V0′ 比照第 82 代；S4 活的工具在 v29 重跑；merge 走 K 包裝器，含 `--control`＋`--pair`；打字探針 `--gap 290` 與 `--gap 310` 跨在寬限兩側，每字 commit、順序正確。v23–v28 的證據都是在 85 ms 下取得的：回覆早了約 75 ms，計時器類回呼相對回覆的先後可能變 | 不出 0.2.45 |
| T4 | 洩漏：Chrome 打字 60 秒，引擎 worker 的 JS heap 沒有隨打字線性成長（CDP `Runtime.getHeapUsage`），`diag_tick.py immediate` 當紅案 | 不出 0.2.45 |

**T1 的 `boundaries` commit 中位數**：常駐全速下三次重複落在 8.4–10.9 ms，門檻是 ≤ 10 ms（v20 時代定的，v21 實測 4.3）。**v29 上不改門檻、不調寬限去湊。** 超線時不算 v29 失敗，但 K6 會紅，所以門檻要不要為有序引擎重定，要在下一份 K 規格之前由擁有者／裁決決定（上螢幕的門檻不動，v29 上螢幕比 v21 快）。

## 7. 宿主與 K 之前（要 ddev 時段）

1. 宿主 0.2.45 裝上、Files 實流程。
2. 擁有者手測打字。
3. `as5` 重跑：還紅就是 finding 177 以外的問題，開新 finding。
4. production UI 的 P 臂重跑（清單 K 追加 3 已修、沒驗）。
5. same-second R3：`FOREIGN_PHASE` 依 v29 的存檔速度重定。
6. 新 K 規格：抄 `SPEC-M3-K-0.2.44` 協定與追加 1–3，鏈前先普查計數才走的路徑。

## 8. 具名限制

- **L-v29-first-key-wakes-on-a-tick**：閒置後的第一個字最多多等一拍（10 ms）才進 immediate。
- **L-v29-spins-during-typing**：連續打字期間引擎 worker 全速空轉，打字停 300 ms 後才停。T2 只量閒置，不量打字中的耗電。
- **L-v29-idle-chain-outlives-the-grace**：長文件上計時器觸發而沒有輸入時 tick 不到 poll（`svpinst.cxx:447-455`），全速會延續到閒置鏈結束，不只 300 ms。T2 的長文件格量的就是這個上限。
- **L-v29-small-client-contention**：T1 在 12 核桌面上量，看不到雙核機器上的競爭。

## 9. 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-11-01 | 初版。 |
| 2026-11-01 | 審核一輪：immediate 改 `MessageChannel`；§6 T1 改 3 輪、T2 單一公式＋四情況＋紅案、T3 指名活的工具與寬限兩側、T4 改洩漏；限制兩條；釘死。 |
