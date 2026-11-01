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

## 10. 追加（2026-11-01，連結之後）

**連結**：擁有者「幫我跑」，agent 代跑，2 分 49 秒；wasm `e61e5890…`、loader `0ca2665c…`、worker `a5df83db…`（與 v28 相同）、manifest `a0352c83…`，`withheld: []`，contract 兩次成立。封存 `build/archive/e2-editor-v29-e61e5890-worker-a5df83db`。

**T1 的先行量測**（頁面未切，鏡像改指向，`findings/evidence/v29-177/post-link/typing_on_v29.py`；不是 T1 本身，T1 要在切頁之後 12 格 3 輪）：`boundaries` commit 中位數 Chrome 10.2／9.0／9.1、Firefox 9.2／9.4／9.4 ms；長文件間隔 80 ms，Chrome 16.1（最大 57.9）、Firefox 14.3（最大 40.4）ms，v28 是 575.8、588.3 ms。

**T2 成立，判讀方式追加**：§6 的公式沒有寫一次還是多次。第一輪（`idle-run-01-sum-of-live-processes/`）量出負值，是我的讀法缺陷（加總活著的行程，行程在窗口內結束時總數下降），不算數。改成逐行程取差值後，同一情況單次離群值兩個版本都有（v28 最高 13.72 秒、v29 最高 4.22 秒），所以**每個情況各 3 次、比中位數**：8 種情況全部 v29 ≤ v28 × 1.5 ＋ 0.5 秒。紅案（常駐全速）10.16–13.22 秒。

**還沒做**：P 之後的切頁、generation 83、T1、T3、T4。

## 11. 追加 2（2026-11-01，切頁之後、T1／T3／T4 的任何執行之前）

**切頁與凍結**：頁面 `022d0cd0…`（`3b0a2ebb…` 改兩行），第 83 代 `607b280d…`、檔案 `98371d7f…`，只差頁面，第 82 代的 11 項排除逐字沿用（`findings/evidence/v29-177/cutover/`、`freeze-83/`）。

**§6 沒寫死的部分，這裡釘死（都是把「比照」寫成可判的條件，不改任何既有判準）**：

| 項 | 工具 | 成立 |
|---|---|---|
| F3-83 | `run_v83_f3_clipboard.py`（衍生） | `read_v83_f3_equal.py` 對 F3-82 `F3_83_EQUAL`，**宣告的移動：無**；讀法一恰好是 F3-82 的四個問題。v29 只動時間，不動行為，任何一格移動（含變綠）都停下查清 |
| F4-83 | `run_v83_four_arms.py`、`judge_v83_product_four_arms.py`（衍生） | 兩瀏覽器 24/24 |
| S4 | `check_v83_last_line_bullet.py`（薄包裝，`check_v82_last_line_bullet.py` 不改，行程內把 `after` 換成 v29；`before` 仍是第 81 代／v27） | `S4_HOLDS`、六個突變都 `S4_MUTATION_CAUGHT`、self-test 全紅 |
| merge | `run_v83_merge.py`（`run_k_0244_merge.py` 的衍生，K 的 pin 不改；綁定 `t3/merge/binding.json`，只有 wasm 與頁面兩鍵移動） | Chrome、Firefox 全表各一輪，**逐格讀 `pass`**（不數 `outcome`）全過；`--cases C01,C15,C29` 的 instrumented／`--control`／`--pair` 無差異；`m2-1b`（Firefox）、`m2-4`（Chrome）的逐格 `pass` 全過 |
| 寬限兩側打字 | `t3/typing-gap/gap_order.py`（`probe_typing_latency.py` 不改，行程內加一次存檔） | `--gap 290`、`310` × 兩瀏覽器 × `boundaries`、`owner` × 20 字 × 3 次，共 24 次，每次：`keysSeen` = 20、每字有 commit、存檔裡 `a…t` 依序連續且只出現一次；self-test 全紅。一次跑不算（CLAUDE.md：間歇缺陷次數就是量測） |
| V0′-83 | `v29-177/v0/run_v0_prime.py`（衍生，加第六階段 v82，git `69c5583a9`） | `V0_PRIME_HOLDS`；在所有用到 `dist/` 的量測之後單獨跑 |

**T4 的判準**（§6 只寫「沒有隨打字線性成長」，這裡定成數字）：`t4/heap_during_typing.py`，Chrome、`boundaries`、間隔 80 ms、700 字（約 60 秒），打字前與每 70 字後各取一次樣本，共 11 個：對每個 worker 先 `HeapProfiler.collectGarbage` 再 `Runtime.getHeapUsage`。**`grows`＝末減首 ≥ 1 MiB 且 10 段裡至少 8 段上升。** 成立＝受測臂（v29）沒有 worker `grows`、紅案臂（v28＋stock immediate，`diag_tick.py` 的 `immediate`，鏡像內改指）至少一個 worker `grows`、兩臂都至少有一個 worker 回答全部 11 次。停在 `Atomics.wait` 的 pthread 不回 CDP，記 `noAnswer`：它沒有事件迴圈可以洩漏。紅案不成立＝儀器看不到洩漏，T4 不成立（不是 v29 過關）。

**T1**：`link-batch-v22/shakedown/desk_gate.py` 每輪前要 clean（量時間的格子，閘門適用）。`judge_c2.py`、`judge_p2.py` 不改，`t1/judge_on_83.py` 在行程內把頁面 pin 換成 `022d0cd0…`（pin 屬於 K 0.2.44 規格）。`boundaries` commit 超過 10 ms 依 §6 記錄、不算 v29 失敗，交擁有者在下一份 K 規格之前決定。

**順序**：T3（F3、F4、S4、merge、寬限兩側）→ T4 → V0′-83；T1 等桌面乾淨。T3／T4 不判時間，桌面不必乾淨。

## 12. 追加 3（2026-11-01，T4 跑完之後）：更正第 11 節 T4 的 `grows`

**取代**第 11 節「`grows`＝末減首 ≥ 1 MiB 且 10 段裡至少 8 段上升」。**新的 `grows`＝末減首 ≥ 1 MiB。** 第 11 節原文保留。

**逼出來的量測**：紅案三輪長了 21.9、23.0、23.8 MiB，但 V8 的陣列是倍增的，heap 呈階梯（例：11.1、15.3、15.3、19.1、24.6、24.6、24.6、33.0、33.0、33.0、33.0 MiB），10 段只有 6–8 段上升，所以照原判準 run-01、02 是 `T4_RED`（`reading-pinned-run-0N.json` 留著）。這是我寫錯，子句描述的是一條平滑直線，真正的洩漏畫不出那條線。

**為什麼不是放寬**：拿掉這個子句只會讓受測臂**更容易**轉紅，不會更容易過。受測臂三輪最多長 0.070 MiB，離 1 MiB 還有約 14 倍。子句只影響紅案，而紅案本來就看得到洩漏。

## 13. 追加 4（2026-11-01）：F3-83 的讀法、頁面 HTML、T3／T4 的結果

**F3-83**：照第 11 節的工具，`F3_83_MOVED`，Firefox 一格 4/4 移動。成因是 finding 178（runner 每臂按兩次），不是產品。**第 11 節的 F3-83 工具換成 `f3-83/diag_single_press.py`**：`run_v83_f3_clipboard.py` 在記憶體裡拿掉第一按，其餘不變。判讀工具與「宣告的移動：無」都不動。結果：Firefox 3 次、Chrome 1 次，46/46 等於 F3-82，`F3_83_EQUAL`，讀法一恰好是 F3-82 的四個問題，self-test `ALL_RED`。

**為什麼不是放寬**：拿掉的是一個使用者不會做的動作，判準一個字沒改。預測先 commit（`7aca664aa`）。紅案就是同一批位元組上的原工具（4/4 紅）。

**工具列 HTML**：擁有者 2026-11-01 指示換成圖示（`findings/evidence/toolbar-icons/`）。只改 `web/e2-editor.html`（`ca58f40f…`），`e2-editor-app.js` 與第 83 代的 digest 不變。四臂判讀綁 HTML，所以 F4 在新頁重跑（`f4-83/final-page/`，24/24），V0′ 的階段多還原 HTML。merge 的 `htmlSha256` 下一份 K 規格要重算。

**結果**：

| 項 | 結果 | 跑在哪個 HTML |
|---|---|---|
| 寬限兩側打字 | 24/24 | 舊 |
| merge | 全表 26/26×2、control／pair 無差異、m2-1b 20/20、m2-4 過 | 舊 |
| S4 | `S4_HOLDS`，六個突變都抓到 | 舊 |
| T4 | 三輪成立（追加 3） | 舊 |
| F4-83 | 24/24 | 新 |
| F3-83 | `F3_83_EQUAL`（單按） | 新 |
| V0′-83 | `V0_PRIME_HOLDS` | 新 |
| 工具列 | 雙瀏覽器真實指標成立 | 新 |

標「舊」的四項沒有在新 HTML 重跑：HTML 的差異只有工具列的樣式與標記，按鈕文字、順序、動作、無障礙名稱逐一相同（`check_toolbar.py`）。計數時全部都會在最終位元組上重跑。

**T1 還沒跑**：要乾淨桌面，閘門目前擋在擁有者的桌面 Chrome 與 zen。

## 14. 追加 5（2026-11-01）：T1 的結果

C2 三輪 PASS。`judge_p2` 第 1 輪 PASS，第 2、3 輪唯一的 FAIL 是 Chrome `boundaries` commit 中位數 11.3、12.3 ms（門檻 ≤ 10）；Firefox 三輪 9、9.7、8.7。依 §6 不算 v29 失敗。**門檻要不要為有序引擎重定，等擁有者決定**，在那之前 K6 依 J-b.2 會紅。數字：`findings/evidence/v29-177/t1/`。
