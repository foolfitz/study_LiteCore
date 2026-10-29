# SPEC-M3-link-batch-v25：修 finding 171／172 的後繼身分

> 狀態：**草案，2026-10-29 釘死前**。釘死之後只准追加（CLAUDE.md 第 10 節）。
> 依據：`findings/evidence/host-0.2.39/k-nine-cells/RULING-v25-fixes.md`（fable 裁決，主 session 已核對）。
> 擁有者 2026-10-29：「好」（照「裁決 → 規格 → 實作 → 連結前檢查 → 連結交擁有者」的順序）。DDEV 另有 session 在用，要用時排隊。

## 1. 為什麼要有

宿主 0.2.39 首次出貨 v24（帶著 v23 的有序指令／unipoll 引擎），同工具同瀏覽器量到 8 格退化（`host-0.2.39/k-nine-cells/`），擁有者當天選擇回退到 0.2.38 的引擎。其中兩個是產品缺陷，而且是同一輪（v23，10-25）加進有序路徑的：

- **finding 171**：有序格式路徑從不推進 barrier 的 `stage`，worker 推成 `dispatched: false` → 空行加項目符號鎖住佇列、進 recoverable-error，還對使用者說「沒送出」。
- **finding 172**：`inlineFormatArgumentResolved` 加了「本次 flush 要收到該狀態項」→ 要求目前已經是的格式狀態（no-op）判 `LOK_COMMAND_FAILED` → 清除格式在第一個 no-op 就中斷，斜體留著，再按斜體反而關掉。

v25 只修這兩件，其餘行為等於 v24。

## 2. 範圍

**做**：171、172 的引擎修正（新 define）、v25 worker（v24 衍生，差異是封閉清單）、頁面改指 v25、殼層 generation 78、Makefile 區塊、連結機械、紅案與連結後判準。

**不做**（各自是後續項）：
- 頁面「清除格式遇錯繼續」（裁決 Q1 (c)：可以是另一項，但不是修法）。
- finding 038 在有序引擎上不再重現的調查（finding 候選）。
- `induce_worker_failure` 的後繼 runner（I-worker-inducer-single-shot 的修理）。
- L-noop-trusts-last-state-item 的原生 N=5 臂（欠著，不擋）。
- K 本身（照 `k-protocol-ruling/RULING.md`，另需 8–10 小時不開站時段）。

## 3. 決定紀錄

| 題 | 決定 | 出處 |
|---|---|---|
| 172 的修法 | (a′)：照常派送；poll 時 `success:false` 且本次 flush 沒有 `.uno:X` 狀態項時，若 `<x>Known && cache == requested`，判「已驗證的 no-op」，**回覆與真的改變相同**（`changed:true`、`uno-command-result`、revision+1），多一個欄位 `witness` | 裁決 Q1 |
| 為什麼不回 `changed:false` | 被 E1-C 凍結的 `editor-shell/editor-client.js:84-90` 要求每個 mutation 都 `changed === true`，否則 `EDITOR_RESULT_INVALID`（在 `RECOVERY_ERRORS`），佇列會像 171 一樣鎖住 | 裁決 Q1，已核對 |
| 171 的修法 | 有序路徑在 `postUnoCommand` 之前設 `barrier.stage = AwaitingResult`（舊路徑 `probe_engine.cpp:6215` 的做法），**並且**在 barrier 紀錄裡明確序列化 `dispatched` | 裁決 Q2 |
| 契約的主人 | 引擎的 barrier 紀錄；worker 只是投影，不再從引擎內部欄位推斷契約 | 裁決 Q2 |
| 提早設 stage 安不安全 | 安全：v23 define 下還編進來的程式碼沒有任何一處讀 `stage`（2235、2256、5981–6081 都在 `#ifndef OXSDK_E2_V23_LINK_BATCH` 裡）；期限計時器只看 `stageDeadlineArmed`，有序路徑從不設 | 主 session 讀碼，2026-10-29 |

## 4. 設計

### 4.1 引擎（全部在 `#ifdef OXSDK_E2_V25_FORMAT_PROOF` 之下）

- 新 define `OXSDK_E2_V25_FORMAT_PROOF`，要求 `OXSDK_E2_V24_TYPED_INSERT`（沒有就 `#error`，比照 `editor_api.h` 的寫法）。編輯器 ABI 留 6；**沒有新 export**。
- **171**：
  1. `ordered_format.inc` `startOrderedFormatAction`：在 `gFormatBarrier = barrier;` 之前設 `barrier.stage = FormatBarrierStage::AwaitingResult;`。路由拒絕（派送前就回）的分支不設，維持 `idle`。
  2. `FormatStateBarrier` 加 `bool dispatchRecorded = false; bool dispatched = false;`；`deferOrderedFormatReply` 在 lambda 裡把參數 `dispatched` 寫進 `gFormatBarrier`（`dispatchRecorded = true`）。
  3. `appendFormatBarrierDetails`：`dispatchRecorded` 為真時輸出 `"dispatched":true|false`（前例 `:3864`、`:6621`）。
- **172**：`ordered_engine_reply.inc` `composeOrderedUno` 的 `editor-action-completed` 分支：
  - `witness` 的決定：`commandResultSucceeded(payload)` → `"uno-success"`；否則本次 flush 有該狀態項且狀態等於要求 → `"on-time-item"`；否則**沒有**該狀態項、該項在準時讀取表上、`<x>Known` 且快取等於要求 → `"state-noop"`；都不是 → 照舊 `LOK_COMMAND_FAILED`。
  - 「在準時讀取表上」用引擎既有的表（`probe::replystate::kReads`，由 `tests/test_reply_state_reads.py` 對 `out-n1b/on-time-list.json` 守著），不另寫清單。
  - 成功回覆照舊（`changed:true`、`completion:"uno-command-result"`、revision+1），在 `completion` 之後加 `"witness":"<值>"`。非四種行內格式的指令，`witness` 只會是 `"uno-success"`，其餘照舊失敗。
  - `inlineFormatArgumentResolved` 本身**不改**（舊路徑與 v23／v24 的前置處理輸出不變）；v25 用一個新的輔助函式表達 no-op 條件。
- **前置處理不變的證明（V0-v25）**：以 v23、v24 的 define 前置處理 `probe_engine.cpp`、`sdk_api.cpp`、`editor_api.cpp`，輸出必須與改動前的 HEAD 逐位元組相同。

### 4.2 worker（`sdk/v25-feature-worker.js`）

由封存的 v24 worker（`build/archive/e2-editor-v24-27615808-worker-41041fe7/sdk-worker.js`）衍生，差異是封閉清單：

1. `productFormatBarrier`：`dispatched: typeof value.dispatched === "boolean" ? value.dispatched : (stage 推算，照舊)`；註解改寫：stage 推算只是舊引擎的退路。
2. `editor-action-completed` 的投影加 `witness`：值在 `{"uno-success","on-time-item","state-noop"}` 之內原樣帶出，其他（含缺）→ `null`（R4）。
3. profile 條件 `e2-editor-v24` → `e2-editor-v25`；ABI 條件照舊 6。
4. 檔頭註解說明衍生來源與本節。

### 4.3 SDK

`sdk/document-sdk.js` **不改**。`witness` 只是證據欄位，頁面不依它決定任何事。

### 4.4 頁面與殼層

- `web/e2-editor-app.js`：`workerUrl` 改成 `./profiles/e2-editor-v25/sdk-worker.js`；`PINNED_WASM_SHA256` 改成 v25 實際 wasm 的前 16 位（連結後才知道）；`typedInsert` 宣告的要求照舊。
- **殼層 generation 78**：頁面在 generation 77 的綁定集合裡，要凍新的 generation；**等本批殼層改動全部做完才凍**。v77 原樣保留。E1-C `intact: true`。

### 4.5 manifest 與身分

profile `e2-editor-v25`；`editorContract` 的每一個葉（含 `typedInsert`）等於 v24；`wasmSha256`、`loaderSha256`、`workerSha256` 換成 v25 的；匯出表等於 v24 的（沒有新增）。

## 5. 身分與連結的機械

比照 v24 規格 §5，只換名字：

- Makefile 的 v25 區塊接在 v24 之後：`E2_V25_BUILD := build/e2/editor-v25`、`E2_V25_DIST := dist/profiles/e2-editor-v25`；編譯規則逐字照抄 v24，defines 多 `-DOXSDK_E2_V25_FORMAT_PROOF`；匯出表取 v24 封存的 `exports.txt`；worker `cp sdk/v25-feature-worker.js`，前置檢查驗衍生來源是封存的 v24 worker（`41041fe7…`）；連結從第一次就受守衛（`refuse_unasked_relink`），用 `link_product_stack_1m`。
- 新檔：`tools/build_e2_v25_feature_profile.py`、`tools/check_v25_feature_contract.py`、`tools/link_v25_feature_owner.sh`、只跑測試的 `test-v25-feature-static`。v24 的工具位元組不動（它們被 v24 的計數綁著）。
- `test-e2-c-static` 的 M1-1 載體行加 `--carrier E2_V25=probe_engine,sdk_api,editor_api`，**先紅**（證人 commit）再綠。
- `tools/what_the_link_ships.py` 加 variant `link-batch-v25`。
- v24 的封存 `build/archive/e2-editor-v24-27615808-worker-41041fe7/` 直接沿用（連結前驗 `SHA256SUMS`）。
- 連結前的凍結集合：`findings/evidence/link-batch-v25/pre-link/frozen-set-before.sha256`。

## 6. 判準

### 6.1 連結前（原始碼與單元測試，agent 自己跑）

| 編號 | 判準 | 紅案（先紅） |
|---|---|---|
| R1 | 有序路徑、普通文字、`set-bold false` → `editor-action-completed`、`witness:"state-noop"`；正向對照 `set-bold true`（有狀態項）→ `"on-time-item"` | 不帶 v25 define（＝v24 的條件）時，同一案回 `LOK_COMMAND_FAILED`——**這是會在出貨前抓到 172 的那一案** |
| R2 | 快取不等於要求、沒有狀態項 → `LOK_COMMAND_FAILED`（059 的保護區段臂） | 把 no-op 條件改成「不看快取」的突變時要紅 |
| D1 | 空段落 → `multi-block-readback` 的錯誤帶 `"dispatched":true`、`stage` 不是 `idle` | 不帶 v25 define 時 `dispatched` 缺、`stage` 是 `idle` |
| D2 | `gesture-not-permitted`（派送前拒絕）→ `"dispatched":false`、`stage` 是 `idle` | — |
| W1 | worker 差異是封閉清單（對封存 v24 worker 的 diff 只有 §4.2 的四項） | 多改一行要紅 |
| W2 | worker：`dispatched` 布林優先、缺時退回 stage 推算；`witness` 未知值→`null` | 兩種形狀各一個反例 |
| V0-v25 | v23、v24 define 的前置處理輸出與改動前 HEAD 逐位元組相同 | 故意在共用段落改一個字要紅 |
| S | em++ `-fsyntax-only`（v25 define）乾淨，附正向對照（故意的錯在帶 define 時被抓到） | 正向對照本身 |
| M1-1 | 載體行先紅後綠 | 證人 commit |
| L | `what_the_link_ships` 的 `link-batch-v25` | — |

### 6.2 連結之後（靜態，連結當天）

五個 artifact 的雜湊、`check_v25_feature_contract.py`（葉等於 v24、只換三個雜湊）、匯出表等於 v24、封存 `e2-editor-v25-<wasm8>-worker-<worker8>`。

### 6.3 連結之後（瀏覽器，任何計數之前；鏡像，不用 DDEV）

- **F1**：`diag_format.py`（加 v25 為第三個產品）：v25 的 bullet 情境 `ready` 且 `dispatched:true`；format 情境的存檔 `MKAFTERCLEAR` **不是**斜體、`MKITALAGAIN` 是斜體，與 v22 相同。
- **F2（R3）**：新工具 `tools/check_v25_clear_format_noop.py`：普通文字上按清除格式 → 四個 `ok`、toast「已清除…」、狀態 `ready`；**紅案：同一工具對 v24 必須紅**（v24 是天然的反例，不必重連結一顆突變引擎）。
- **F3**：product-path 一般臂（T4 的作法，v78 重綁），兩瀏覽器各 1 回；DISPOSITIONS 第 1–6 列在 v25 上要 PASS，其餘 40 格與 v24 的 T4 相同。
- **F4**：A4 四臂（`run_v24_four_arms.py` 的衍生包裝），兩瀏覽器。

### 6.4 計數與 K

見 §9。K 照 `k-protocol-ruling/RULING.md`（含修正一）與 `k-nine-cells/DISPOSITIONS.md` 的釘死判準。

## 7. 連結（擁有者的步驟）

`bash tools/link_v25_feature_owner.sh`（會編譯，交擁有者；比照 v24）。

## 8. 順序

1. 本規格釘死（commit）。
2. 引擎改動 → R1、R2、D1、D2、V0-v25、S、M1-1、L 全綠（紅案先紅）。
3. worker → W1、W2。
4. Makefile／工具／連結腳本 → `test-v25-feature-static` 綠。
5. 交擁有者連結。
6. §6.2 → 頁面改指 v25、generation 78 凍結 → §6.3。
7. 依 §9 的決定做計數；K 另排時段。

## 9. 重驗範圍（**提案，待擁有者確認**）

v25 只動格式回覆路徑，而且全部在新 define 之下。提案：
- **不重跑** S5（1,176）、R1（144）、S1–S4（234）：條件是 V0-v25 之外，再加一支工具封閉的比對，證明 v25 的前置處理輸出相對於 v24，只差 §4.1 宣告的那幾段（形式二）。比對不成立就全部重跑。
- **要重跑**：F3、F4（便宜，而且直接覆蓋被改的那一族）。

這是判斷，不由起草方自己宣告（CLAUDE.md 第 8 節）。擁有者不確認的話，預設是全部重跑。

## 10. 具名限制

- **L-noop-trusts-last-state-item**（新）：快取過期，而且派送被拒（保護區段）時，no-op 會被誤判成立；v22 有完全相同的洞。原生 N=5 臂可以移除或確認它（欠著）。
- **I-worker-inducer-single-shot**、**I-ink-trigger-race**、**I-enter-raw-substring**：K 的判讀，見 DISPOSITIONS。

## 11. §34.4

本輪：因執行而修 1（`capture-after.py` 的 buildId 欄位）；因審核而修 2（K 裁決修正一的錨點、DISPOSITIONS 第 7 列的成因）。

## 13. 實作逼出的更正（2026-10-29，只追加；連結之前）

1. **S 的守衛對照選錯編譯單元。**`editor_api.h` 只有 `editor_api.cpp` 會 include（v24 的守衛也一樣），所以「只帶 v25、不帶 v24」的對照要用 `editor_api.cpp` 的編譯行。第一次拿 `probe_engine.cpp` 跑，它照樣綠——錯的是對照，不是守衛（`s-v25-run01-wrong-control-tu.json` 保留）。因執行而修 1。
2. **v24 的 E1 改讀 v24 連結時的原始碼。**`tests/test_v24_typed_insert_engine.py` 主張「v24 區塊以外，從 `ceaa2770` 起什麼都沒改」，這是 v24 的連結前閘門，說的是 v24 連結時的原始碼（`1f95a9fca`）。v25 在 v24 區塊以外加了自己的區塊，所以在活的樹上依構造是紅的（`v24-static-live-tree-red-by-construction.txt`）。比照 v24 規格 §14 的 V0′：測試檔一個字都不改，`test-v24-feature-static` 用它內建的 `V24_E1_SRC` 指向 `git archive 1f95a9fca` 抽出的 src，結果綠（在 `cd60b7d61` 上也綠）。活的樹上，v23／v24 物件的位元組由 V0-v25 守著。
3. **`what_the_link_ships`（`--since 1f95a9fca`）**：四個單元裡只有 `probe_engine` 的前置處理輸出有變，變的段落正好是 §4.1 宣告的四處（barrier 欄位、`dispatched` 序列化、stage、witness）；其餘三個單元相同。這可以當 §9 的材料，但 §9 仍然等擁有者確認。
4. **原生測試沒有涵蓋的部分**：`dispatched` 與 `witness` 的 JSON 序列化寫在 `probe_engine.cpp`／`ordered_engine_reply.inc` 的輸出串流裡，原生 harness 測的是決定邏輯。序列化由連結後的 F1、F2 量到。

## 14. 連結完成與 §9 的決定（2026-10-29，只追加；連結之後、任何 v25 瀏覽器執行之前）

擁有者 14:14–14:17 連結：wasm `44cb15ea…`、loader `ed1d9a55…`、worker `75557b22…`、manifest `e7780061…`、匯出表等於 v24（`f5b21630…`）。§6.2 全過（`findings/evidence/link-batch-v25/post-link/`）：兩道契約檢查、X1 對 v24 只宣告 worker 而 `VERDICT PASS`、三個紅案各只紅自己那一條、凍結集合 2,453 個檔不變而且只多 v25 的四個檔、`ScDocShell` 0 次（有正向對照）、E1-C intact，已封存 `e2-editor-v25-44cb15ea-worker-75557b22`。

**§9：擁有者選「沿用」**（2026-10-29 原話：「沿用」）。S5、R1、S1–S4 的計數不在 v25 上重跑；F3、F4 照跑。依據是 §9 寫的條件：`pre-link/ships.stdout.txt` 顯示相對於 v24 連結時的原始碼，只有 `probe_engine` 的前置處理輸出有變。**欠著**：把「每一段變動都落在 `#ifdef OXSDK_E2_V25_FORMAT_PROOF` 之內」寫成一支讀 `ships` 輸出與原始碼的小工具（形式二），在任何 K 之前補上；補上之前，「只差宣告段落」這件事是讀出來的，還不是工具判的。

## 15. 切換、generation 78、§9 讀取器與 §6.3 的 F1／F2（2026-10-29，只追加；F3、F4 之前）

1. **切換**（`e06d10a1b`，`findings/evidence/link-batch-v25/cutover/`）：`build_cutover_page.py` 只改兩行（釘選 `44cb15ea8d36f0e0`、worker URL），頁面 `b15a6d8e…` → `6e66c930…`；`make -n e2-c-assets` 只印一行 `cp`（SDK 沒改，§4.3）。**V0′ 補做**：本規格沒有列，但 §9 沿用 v24 的計數，而 v24 的兩支讀取器（`read_v24_remaining_cohort.py`、`judge_v24_product_four_arms.py`）都綁活的殼層摘要——切換後在活的樹上**依構造**是 NE（`shell digest differs: 550b68bf…`）。只把頁面（原始碼與 `dist/`）換回 `b15a6d8e` 時，兩支都逐位元組重現已 commit 的結果；放回後雜湊核對無誤；E1-C intact。
2. **generation 78**（`9450e5340`，`freeze-78/`）：照 §8 的順序在 §6.3 之前凍（§4.4 宣告的殼層改動只有頁面，已完成；v24 是在 6.3 準備之後才凍，順序不同）。第八個排除 `sdk/v25-feature-worker.js`：本規格沒有列，比照 v24 規格 4.4 對 `sdk/v24-feature-worker.js` 的前例與理由。與 v77 只差頁面。Makefile 的 bundle 行改指 v78（改前紅、改後綠、指回 v77 或工具預設 v76 都紅）。`test-e2-c-reachability` 整體仍紅在既有的覆蓋稽核那一行，在切換前的樹（`b241c83a4`）上量到完全相同的問題清單。凍結後再做一次 V0′，同樣成立。若 6.3 逼出殼層改動，那是 generation 79，不覆寫 78。
3. **§13 第 3 點讀過頭了。**`what_the_link_ships.py` 的舊一側只抽 `.cpp`，同目錄的 `.inc`／`.h` 經 `-Isrc` 解析到**活的樹**，兩側讀的是同一份新的引入檔。v25 的 `ships` 只有 `probe_engine.cpp` 的兩段（barrier 欄位、`dispatched` 序列化）；stage（`ordered_format.inc`）與 witness（`ordered_engine_reply.inc`）不在裡面。§13 第 3 點寫「正好是宣告的四處」，§14 擁有者決定所引的也是同一份報告。這個盲點在工具本身（任何同目錄引入檔都看不到），不只在 v25；哪些舊批次的宣稱靠過它，另列工作項。
4. **§14 欠的讀取器已補**（`dfa9ba6bd`，`tools/check_v25_ships_confined.py`，`findings/evidence/link-batch-v25/section-9-reader/`）：用 Makefile 的實際編譯行；(A) v25 的行與「去掉 v25 define 的同一行」前置處理（保留行號標記），每一個不同的行對回檔:行，必須在條件含 `OXSDK_E2_V25_FORMAT_PROOF` 的分支裡；(B) v24 的行在樹上與 `git archive 1f95a9fca`（引入檔各取自己的 commit）正規化後相同；(C) v24 的行＝v25 的行去掉 define。活的樹：`CONFINED_V25_HOLDS`，39 行、0 行在外（32 行在兩個 `.inc`，正是 `ships` 看不到的），內容正是 §4.1 宣告的各段。四個紅案（衍生巨集洩漏到區塊外、區塊外的無條件改動、零行、`ships` 零段）各自只紅自己那一條。**所以 §9「只差宣告段落」現在是工具判的**；結論與擁有者當時依據的讀法相同，只是當時的證據少看了兩處。
5. **§13 第 4 點：頁面層量不到序列化。**v25 同時把 stage 提前，worker 的退路推算也會給 `dispatched: true`；v22 的引擎根本不送 `dispatched`，頁面照樣顯示 `true`（F1 實測）。所以 F1 在 Chrome 的 worker 裡經 `Target.setAutoAttach` 包一層 `JSON.parse` 觀察器，直接讀引擎紀錄是否**帶有** `dispatched`／`witness`（不改任何送出的位元組）。
6. **F1**（`findings/evidence/link-batch-v25/f1/`，`diag_format.py` 以路徑匯入、位元組不動，衍生工具 `diag_format_v25.py`；v24 從自己的位元組送——切換後 `dist/` 是 v25，`diag_format.py` 的「v24＝`dist/` 原樣」會量到 v25）：run-01 Chrome 3 回 **`F1_HOLDS`**（`read_f1.py`，八個變異全紅）。v25：項目符號後 `ready`、引擎紀錄 `dispatched: true`／`stage: awaiting-result`、存檔 `MKAFTERCLEAR` 非斜體、`MKITALAGAIN` 斜體、每個 set-* 引擎回覆帶已知 `witness`，3/3。v24 這幾條 0/3；v22 參考值 3/3。
7. **F2 的處方更正（因執行而修 1，在任何證據執行之前）。**照字面「普通文字上按清除格式」試跑（`f2-shake-01`，scratch），v24 是**綠的**：剛放好游標後的第一次清除格式，LOK 在 flush 裡廣播了四個狀態項（v25 的 witness 全是 `on-time-item`）。172 要的是「本次 flush 沒有該狀態項」，而 LOK 只在狀態有變時才重播。處方改成：同樣在普通文字上連按兩次，**判第二次**；第一次是暖身，必須以「已清除」與 `ready` 結束，否則算工具自己的設定問題。判準（四個 ok、toast、`ready`、對 v24 必須紅）不變，另加一條：第二次的 `set-bold` witness 必須是 `state-noop`（證明走到修法的路徑，而不是剛好有廣播）。v24 只有「為 172 而紅」（暖身成立、第二次第一個回覆是 `LOK_COMMAND_FAILED`）才算反例。
8. **F2**（`findings/evidence/link-batch-v25/f2/`，新工具 `tools/check_v25_clear_format_noop.py`，產品同 F1 由 `tools/v25_f_products.py` 建構並逐檔核對身分）：run-01 Chrome 與 Firefox 各 3 回 **`F2_HOLDS`**。v25 6/6 PASS，第二次按的四個回覆都是 ok、witness 都是 `state-noop`、toast「已清除…」、`ready`；v24 6/6「為 172 而紅」（`set-bold` 就 `LOK_COMMAND_FAILED`，後面三個沒送）。十二回的暖身全部成立。
9. **F3 的判準在跑之前要先釘清楚**（待擁有者決定；決定後另追加一節）：§6.3 寫「其餘 40 格與 v24 的 T4 相同」，但每個瀏覽器 46 個檢查、第 1–6 列共 6 格，數字對不上任何切法；而且 172 的修法會讓九格之外的同族格子變好（v24 T4 run-02 的 Firefox `clear-format-removes-every-inline-format` NE、`an-inline-format-reaches-a-selection` FAIL），照字面「相同」會讓修法本身判 F3 紅。
10. §34.4（本節）：因執行而修 1（F2 的處方）；因審核而修 0。

## 16. F3 的判準（2026-10-29，只追加；任何 F3 執行之前釘死）

擁有者 2026-10-29 選 A（「不准退化」）。取代 §6.3 F3 的「其餘 40 格與 v24 的 T4 相同」；原文留著。被逼出來的原因見 §15 第 9 點（數字對不上母數；172 的修法會讓九格以外的同族格子變好）。

- **執行**：`tools/run_v25_f3.py`（由 `run_v24_t4.py` 衍生，差異是封閉清單：載入 runner 之前把 `build_e2_c_shell_bundle.MANIFEST` 改綁到 generation 78，並寫下改綁紀錄），Chrome、Firefox 各 1 回，頁面是 `dist/` 送的 v25（`6e66c930`）。
- **基準**：v24 T4 的判定執行 run-02（`findings/evidence/link-batch-v24/pre-count/t4/run-02/{chrome,firefox}/report.json`，T4 的判定讀取 `read-02.json` 所讀的那一次）。v24 是上一個計數過、出貨過的產品（0.2.39）。
- **母數（形式二）**：由判讀工具從基準報告逐瀏覽器產生，每個檢查 id 一格。
  - **P 組**：`k-nine-cells/DISPOSITIONS.md` 表中處置以 **product** 開頭的列（由工具解析；目前是第 1–6 列，Chrome 4 格、Firefox 2 格）：v25 必須 PASS。
  - **排除**：id 以 `v23-product-` 開頭的四臂，由 F4 判。
  - **其餘每一格**：v24 是 PASS 的，v25 必須 PASS；v24 不是 PASS 的，v25 必須與 v24 相同或是 PASS。轉成 PASS 的逐格點名列出，不默默放過。
  - 兩邊報告的 id 集合必須相同（多一格或少一格都點名判紅）；基準或 v25 報告沒有任何檢查、或 P 組解析出零列，判紅（非空洞性）。
- **記錄、不是判準**：Chrome 的 wire（每個 `insertText` 的 route 與回覆 method），以及 T4 的第 1 條規則在 v25 上的結果。
- **預設**：沒跑或 NE，F3 不成立；第 1–6 列對 K 的處置不解除。
- 判讀工具 `tools/read_v25_f3.py`，紅案先做（v24 PASS 的格子改成 FAIL、P 組一格 NE、少一格、多一格、空報告、DISPOSITIONS 沒有 product 列），每個都要紅。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-29 | 初版（裁決之後、任何 v25 實作之前） |
| 2026-10-29 | §13 追加：實作逼出的四點更正（連結之前） |
| 2026-10-29 | §14 追加：連結完成、§6.2 結果、§9 擁有者選沿用 |
| 2026-10-29 | §15 追加：切換、generation 78、§9 讀取器、§13 第 3／4 點的更正、F1／F2 結果、F2 處方更正、F3 判準待定 |
| 2026-10-29 | §16 追加：F3 判準（擁有者選 A，不准退化），F3 執行之前 |
