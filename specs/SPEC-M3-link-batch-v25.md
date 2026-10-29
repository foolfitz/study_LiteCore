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

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-29 | 初版（裁決之後、任何 v25 實作之前） |
| 2026-10-29 | §13 追加：實作逼出的四點更正（連結之前） |
