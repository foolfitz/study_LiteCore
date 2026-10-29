# 171：有序格式路徑的 barrier 從不離開 `idle`，已送出的項目符號被投影成「沒送出」，空行加項目符號因此進入 recoverable-error

| | |
|---|---|
| **狀態** | 已確認（直接量到錯誤 payload）／**v25 已修並量過**（F1，2026-10-29）；尚未出貨——宿主仍是回退後的 0.2.38 引擎 |
| **Bugzilla** | —（本樹缺陷，不是上游） |
| **發現日** | 2026-10-29（K 裁決修正一要求的 9 格處置；同工具對三個出貨產品定位） |
| **嚴重度** | 中——使用者可見：空行按項目符號，編輯器鎖住佇列、要求回到檢查點；而且對使用者說錯話（實際已送出，卻被分類成「什麼都沒送出」） |
| **可重現** | v24：H3 兩瀏覽器、T4 run-01/02/03、four-arms-counted-01、diag run-01/02；v23：10-27 integration 全部報告。v21、v22：0 次 |
| **首次出貨** | 宿主 0.2.39（v24）。v23 從未出貨；0.2.27–0.2.38 是 v22，沒有這個缺陷 |

## 現象

`bulleting-a-blank-line-does-not-demand-a-rollback`：在空段落按項目符號。

| | v22（0.2.27–0.2.38） | v24（0.2.39） |
|---|---|---|
| 錯誤碼 | `MUTATION_OUTCOME_UNKNOWN` | `MUTATION_OUTCOME_UNKNOWN` |
| `formatBarrier.failureShape` | `multi-block-readback` | `multi-block-readback` |
| `formatBarrier.route` | `collapsed` | `collapsed` |
| **`formatBarrier.dispatched`** | **`true`** | **`false`** |
| 頁面處置 | `review`：佇列開著、說明「這是檢查的極限，不是文件壞了」 | `none` 的說明（空字串）＋佇列鎖住 → **recoverable-error** |

（`findings/evidence/host-0.2.39/k-nine-cells/diag-format/run-02/report.json`，v22／v24 各一次，同一個配方。）

## 機制（讀碼＋上面的量測）

1. v23 新增的有序格式路徑 `startOrderedFormatAction`（`wasm_sdk_probe/src/ordered_format.inc`，`3120a15dc`，2026-10-25）整段同步完成，**從來不設定 `barrier.stage`**，所以錯誤裡的 stage 一直是預設的 `idle`。舊（threaded）路徑在 `postUnoCommand` 之前會把 stage 設成 `AwaitingResult`。
2. worker 的投影 `productFormatBarrier`（`sdk/v24-feature-worker.js:353`，`sdk/v23-feature-worker.js:324` 相同）用 `dispatched: stage !== "idle"` 推算，註解寫明它依賴第 1 點的前提（「probe_engine.cpp sets AwaitingResult immediately before postUnoCommand」）。前提在有序路徑上不成立 → `dispatched: false`。
3. 頁面的 `formatFailureDisposition`（`editor-shell-v2/paragraph-editor-client.js`）：`dispatched === false` → `refused-no-mutation` → `recoveryFor` 回 `none`，不是 `review`。只有 `review` 會被 `narrow-editor-v2-session.js:1121` 包成不擋佇列的結果。
4. 錯誤碼仍是 `MUTATION_OUTCOME_UNKNOWN`，在 base session 的 `RECOVERY_ERRORS` 裡（`editor-shell/editor-session.js:15-21`）→ `_blockQueue(..., "recoverable-error")`。

所以「空行加項目符號」不是 v23 讓 readback 變差，readback 的結果兩版相同；是**處置的輸入被投影錯了**。同一條路上任何以 `MUTATION_OUTCOME_UNKNOWN` 結束的有序格式動作，都會被說成「沒送出」，同時鎖住佇列。

## 修法方向（2026-10-29 已由裁決 Q2 決定，見下一節；以下為當時的原文）

- 引擎：有序路徑在 `postUnoCommand` 之前把 barrier 推進到「已送出」的 stage（照舊路徑的 `AwaitingResult`），或明確帶出 `dispatched`。這會改引擎，屬於新後繼身分（v25）的連結。
- 不建議只改 worker 或頁面的推算：根因是引擎送出的紀錄跟 worker 依賴的契約不一致，在下游補只會讓兩邊再分岔一次。
- 回歸網：在有序路徑上要有一個紅案，斷言 worker 對 `multi-block-readback` 的投影是 `dispatched: true`。這次是靠 K 的跨版本比對才抓到的。

## 修法與量測（2026-10-29，v25）

- 修法（裁決 Q2，規格 `SPEC-M3-link-batch-v25` §4.1，全部在 `OXSDK_E2_V25_FORMAT_PROOF` 之下）：有序路徑在 `postUnoCommand` 之前把 `stage` 設成 `AwaitingResult`，**並且**引擎在 barrier 紀錄裡明確序列化 `dispatched`；worker 改成「引擎有給布林值就用它，沒有才退回 stage 推算」。
- 量測（`findings/evidence/link-batch-v25/f1/`，本機鏡像，Chrome 3 回）：v25 的空行項目符號仍是 `MUTATION_OUTCOME_UNKNOWN`（與 v22 相同），但頁面留在 `ready`，不再要求回到檢查點；**引擎原始紀錄**有 `dispatched: true`、`stage: awaiting-result`（3/3）。同一工具上 v24 是 `recoverable-error`、引擎紀錄沒有 `dispatched`、`stage: idle`（3/3）。〔實測〕
- 引擎紀錄是在 worker 裡包一層 `JSON.parse` 讀到的（不改任何送出的位元組）：頁面層看到的 `dispatched: true` 分不出是引擎序列化的還是 worker 從 stage 推算的——v22 的引擎根本不送 `dispatched`，頁面照樣顯示 `true`。〔實測〕
- 仍待：F3（product-path 一般臂）上兩個瀏覽器的 `bulleting-a-blank-line-does-not-demand-a-rollback` 要 PASS，才算對 K 的處置解除；出貨要等宿主新版本（0.2.40 候選）與 DDEV 時段。

## 對 K 的處置（裁決修正一）

Chrome、Firefox 的 `bulleting-a-blank-line-does-not-demand-a-rollback`：**產品缺陷**。修好之前，這兩格對 0.2.26 的錨點判紅，K 不成立。

## 證據

- 定位：`findings/evidence/host-0.2.39/k-nine-cells/`（README 的判讀表先寫後跑；H2 v21、H4 v22、H3 v24，同工具 `7ba30235`、同瀏覽器、連續執行）。
- 錯誤 payload：`k-nine-cells/diag-format/run-02/report.json`（run-01 的 barrier 欄位是 null，因為解析器讀錯位置；已在 README 說明）。
