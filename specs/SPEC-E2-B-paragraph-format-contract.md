# SPEC E2-B：段落格式併入窄版契約

| | |
|---|---|
| **狀態** | **草擬中（v1，2026-08-15）。ABI 未凍結，且不得在第 3 節的閘門通過之前凍結。** |
| **提出日** | 2026-08-15 |
| **前置** | [E2-A](./SPEC-E2-A-paragraph-format-discovery.md) 總判定 `PARTIAL_GO_TO_E2_B`（2026-08-14），**進場條件兩半已於 2026-08-15 滿足**（10.14） |
| **授權依據** | [SPEC-E2-000](./SPEC-E2-000-overview.md) 第 7 節（127–134 行）：順序 E2-A → E2-B → E2-C；「A 未完成前不凍結新 ABI」、「B 與 C 的規格待 A 有結果後另寫，本文件不預先授權」。**A 已有結果，故本規格得以撰寫；第 7 節禁止的是提前凍結，不是提前撰寫。** |
| **外部裁決** | 本規格的形狀（先寫規格、量測當第一個里程碑、凍結閘在其後）由 2026-08-15 的外部裁決訂定，理由記在第 3.1 節 |

## 1. 目的

把 E2-A 已成立的段落層級格式能力，併進出貨 `e1-editor-v1` 的**下一版**窄版契約
（ABI v2），使 `demo-structure` 展示的五個動作能在**產品** artifact 上執行，
而不是只在診斷 artifact 上。

E2-B 完成只代表契約與 shell 可以進入 E2-C；雙瀏覽器 corpus、round-trip、
recovery 與產品驗收仍屬 E2-C（SPEC-E2-000 第 7 節）。

**本規格不擴大 escape hatch**：不新增任意 UNO command、任意 key code、
任意 command string，也不放寬 worker 的 typed 邊界。

## 2. 起點：已經成立與已經不成立的

### 2.1 E2-A 判定為可承諾的

| 動作 | 公開語意 | mutation |
|---|---|---|
| `set-list-none` | 以 explicit closed enum 移除清單，**不是 toggle** | 是 |
| `set-list-unordered` | 同上，設為項目符號 | 是 |
| `set-list-ordered` | 同上，設為編號 | 是 |
| `set-paragraph-heading` | 設為標題，**只承諾第 1 級** | 是 |
| `set-paragraph-body` | 設為「不是 heading」 | 是 |

證據：A3（25 runs／125 次派送）、A4（18／270）、A5（8／42），綁定 `c89f069e…`，
兩瀏覽器；A7 round-trip 406 份 ODT、406/406 桌面重開。

### 2.2 一併繼承的六項縮限（E2-A 10.14）

1. `set-paragraph-body` 的後置條件是「**不是 heading**」，不是「是 Text body」。
2. heading **只承諾第 1 級**（承諾範圍是 H1；量測極限是 level ≥7 不可分，2–6 讀得回 `h2`–`h6`）。
3. readback markup 是序列化器輸出，**不是有文件的契約**。
4. ~~barrier 收尾的選取還原會讓下一次選取請求失敗~~ → **已於 v23 撤除**（任務 #49）。
5. `changed` **永遠不宣稱**（一律 `null`）——路線 C 的直接後果。
6. **不提供前置格式狀態讀取**：產品**無法回答「目前這一段是什麼格式」**。
7. **只驗證過從收合游標派送**——**這一項就是本規格第 3 節閘門要處理的東西**。

### 2.3 一併繼承的 typed 拒絕清單（不得漏接）

- 空段落一律回報失敗（規格層收窄，不是實作缺陷）。
- 帶註腳／尾註的段落設計上拒絕。
- 含 as-char frame 的段落**具名拒絕**（finding 037，**core 端未修**）。
- per-stage 期限只保「stage 不會無限等」，**不保「barrier 一定收場」**。

### 2.4 一併繼承的上游 workaround

引擎的範圍選取是 `RESET`＋`START`＋`END`，而不是 LOK 文件與上游測試示範的
`RESET`＋`END`。這是 [finding 043](../findings/043-fn-select-para-leaves-the-shell-in-selection-mode-and-the-next-lok-range-selection-is-silently-dropped.md)
的版本相容 workaround，**不是產品語意的一部分**。
**移除條件寫在 `probe_engine.cpp` 的註解裡**：上游把 `FN_SELECT_PARA` 的
`SttSelect()` 配上 `EndSelect()` 之後即可拿掉，屆時要重跑第 3 節的閘門。

## 3. 第一道閘門：範圍選取上派送（最便宜的驗證實驗）

> **規則沿用 [E1-D](./SPEC-E1-D-range-selection.md) 第 2 節**：規格的第一道閘門
> 必須是最便宜的驗證實驗，通不過就停止。

### 3.1 為什麼閘門在規格裡，而不是規格之前

「選一段再按按鈕」是 v2 使用者的主手勢，而縮限 7 說這一格**沒有進過驗證矩陣**。
2026-08-15 的外部裁決訂下本規格的形狀，理由有三：

1. **SPEC-E2-000 第 7 節禁的是提前凍結，不是提前撰寫。** 先量再寫，寫的時候已知答案，
   **恰好繞開本專案的核心紀律**——規格先寫、預測先 commit、失敗分支先寫。
   事後寫的規格永遠不會錯，而永遠不會錯的文件在這裡沒有證據價值。
2. **縮限 7 自己就把這筆量測指派給 E2-B**（「E2-B 的產品側掃描矩陣要補的是這一格」）。
   把它拿到規格之前跑，反而違背判定書的安排。
3. **暗格比想像中小**——見下。

### 3.2 暗格的實際大小（v24 更正過的憑據）

解析任務 #49 的 WASM 輪（`940b7723…`，三類 fixture × 兩瀏覽器）：
**每一份 `result.json` 各有 4 筆 `dispatchSelectionCollapsed: false` 的格式派送，
全樹共 24 筆**，全部完成、`failureShape` 為空、`dispatchSelectionRectangles` 為 1。

**那 24 筆不能撤縮限**——它們是附帶觀察，沒有人事先把「在範圍選取上派送」
寫成一個問題去問，所以證明不了任何預先登錄的東西。
**但它們把暗格縮小了**，而這決定閘門要多大。

### 3.3 四臂，約 24 個 run

跑在**組合 artifact**上（產品 select ABI ＋ format barrier）。
每一臂各開一顆引擎（finding 038 的教訓）。判準一律是**回報的狀態與存出來的文件**，
不是「呼叫返回了」。

| 臂 | 問什麼 | 為什麼它是暗的 | 規模 |
|---|---|---|---|
| **G1** `heading-from-range` | 從範圍派送 `set-paragraph-heading` | 24 筆全是 `.uno:DefaultBullet` 一個動作；heading 走 `.uno:StyleApply`，[原生第三輪](../findings/evidence/sdk-e2/discovery/049-selection-after-format/native-round3/README.md)已證明**指令身分會造成差別** | 1 fixture × 2 瀏覽器 × 3 次 |
| **G2** `cross-paragraph-range` | 跨兩段的範圍上派送 | 24 筆的 `dispatchSelectionRectangles` **全是 1**，都是單段 | 1 × 2 × 3 |
| **G3** `reverse-range` | `END` 在 `START` 左邊的範圍上派送 | 端點語意原生量過（#49 的 AJ／AK 臂），**派送當下**沒量過 | 1 × 2 × 3 |
| **G4** `bullet-from-range`（橋接） | 把那 24 筆附帶觀察**升格為預先登錄的可綁定證據** | 附帶觀察不能當憑據 | 1 × 2 × 3 |

**不另設收合對照**：同一棵樹的 click 臂已經印出 `dispatchSelectionCollapsed: true`，
**那個欄位的鑑別力已經展示過**（它印得出兩種值），探針紀律已滿足。

### 3.4 預測與兩個分支——**必須在跑之前 commit**

預測檔放 `findings/evidence/sdk-e2/discovery/e2b-gate/PREDICTION.md`，
沿用任務 #49 的慣例（每一輪的預測在該輪執行之前 commit，commit 本身就是時間戳）。

成本模型直接引那 24 筆：完成、走 callback、約 30 ms、套用到含範圍的段落、
派送之後選取收合。

| 分支 | 判準 | 處置 |
|---|---|---|
| **通過** | G1／G3／G4 完成且後置條件成立；G2 以 **typed** `multiBlock` 拒絕（不是逾時、不是靜默） | 範圍派送**進 ABI**，並把「派送後選取收合」寫成契約的一部分（那 24 筆已觀察到範圍不會被還原，閘門要把它升格為承諾） |
| **不通過** | 任何一臂失敗、逾時、或以未列舉的形狀失敗 | 範圍派送**不進 ABI**：typed 拒絕，或 collapse-first（派送前先收合游標）。**產品範圍縮小，v2 只承諾收合游標派送**，並在 capability 與 UI 明示 |

> **不通過的那一支不是懲罰，是預先寫好的結局。** 它會讓 demo 的手勢維持
> 「點一下段落再按按鈕」——那是**量出來的縮限**，不是為了 demo 好看或難看而做的決定。

### 3.5 閘門與凍結之間還有一步：**產品 build 上重跑**

閘門跑在**組合** artifact 上，而 E2-B 要出貨的是**產品** profile
（不匯出 `oxsdk_editor_discovery_*`、不宣告 diagnostic capability）。
那是一次 relink，**會產生新的 hash**（finding 036：hash 不是原始碼的函數）。

依 finding 027 的規則與 E2-A 進場條件的前例（relink 之後重掃 A3／A4／A5）：

> **凍結 ABI 之前，第 3.3 節的四臂必須在產品 build 上重跑並通過，
> 且 A3／A4／A5 一併重掃通過。** 閘門在組合 artifact 上通過**不構成**凍結條件，
> 它只構成「值得付那次 relink」的條件。

## 4. 候選 ABI（**閘門通過後**才凍結的形狀）

以下是候選，**本規格現階段不凍結它**。

- 版本：`OXSDK_EDITOR_ABI_VERSION == 2`。
- 沿用 v1 的十個 action（1–10），新增五個：

  | 值 | enum |
  |---|---|
  | 11 | `OXSDK_EDITOR_V2_SET_LIST_NONE` |
  | 12 | `OXSDK_EDITOR_V2_SET_LIST_UNORDERED` |
  | 13 | `OXSDK_EDITOR_V2_SET_LIST_ORDERED` |
  | 14 | `OXSDK_EDITOR_V2_SET_PARAGRAPH_HEADING` |
  | 15 | `OXSDK_EDITOR_V2_SET_PARAGRAPH_BODY` |

- capability `narrow-editor-v2`；worker 以 capability **與** `editorContract.version == 2`
  雙重 gating（E1-B 第 4 節的規矩；`sdk-worker.js` 已有先例，
  **只宣告 capability 不夠**——第一顆組合 artifact 就是這樣做出來的）。
- 五個新 action 一律帶 `expected_revision`；stale revision 必須零 mutation。
- 產品 header **不得** include 或暴露 diagnostic enum。

## 5. 不在範圍

沿用 SPEC-E2-000 第 9 節，並補上兩項本規格自己的：

- **H2–H6**：縮限 2，只承諾第 1 級。
- **前置格式狀態讀取**：縮限 6，產品不回答「目前這一段是什麼格式」。
  工具列的按鈕**只反映我們自己上次設了什麼**（路線 C、finding 021）。
- 清單縮排／階層、自訂樣式、字型／字級／顏色、對齊與行距。
- Redo、structural boundary editing、表格／圖片／shape 編輯。

## 6. 驗收與停止條件

沿用 SPEC-E2-000 第 10 節，並具體化為：

**GO_TO_E2_C**：第 3 節閘門通過、產品 build 上重跑通過、A3／A4／A5 重掃通過、
五個動作在兩瀏覽器達門檻次數、completion 可歸屬、revision 每次只前進一格、
且**不需要任何禁止 surface**。

**部分 GO**：清單三態或段落樣式兩態其中一組必須縮限；或範圍派送不進 ABI
（第 3.4 節的不通過分支）。限制以 capability 與 UI 明示。

**停止**：completion 無法歸屬到單一 request；no-op 與遺失不可區分；
清單切換造成 ODT 結構 silent loss；或補齊需要 raw UNO／任意 command string／
sleep／自動 retry。保存失敗 bytes 與 trace 並建立編號 finding。

## 7. Evidence 佈局

`findings/evidence/sdk-e2/discovery/e2b-gate/`：
`PREDICTION.md`（**跑之前 commit**）、`combination-<hash>/`、`product-<hash>/`、
每臂的 `result.json` 與存出來的 ODT。
每個失敗 attempt 獨立保存不覆寫；每筆結果標 `observed`、`inferred` 或 `notValidated`。

**依 `AGENTS.md`（2026-08-15）**，`findings/evidence/**` 底下新寫的一律用英文。

## 8. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-15 | **v1（草擬）。** E2-A 進場條件於同日滿足後撰寫。形狀由外部裁決訂定：**先寫規格、把約 24 run 的最小判別輪當第一個預先登錄的里程碑、ABI 凍結閘在其後**，而不是在規格之前另開一輪 sweep。裁決同時更正了一個實質前提——「在範圍選取上派送從來沒有量過」不成立，#49 的證據樹裡有 24 筆附帶記錄（已由我重新解析驗證），因此暗格縮小為三個子格加一支橋接臂，閘門規模從「五個動作 × 全 fixture × 兩瀏覽器」降到約 24 個 run。撰寫前另完成兩件前置：E2-A v24（縮限 7 憑據句第二次過期，就地更正）與 [finding 044](../findings/044-the-verdict-bound-summary-still-says-there-is-no-verdict.md) 的修復（判定綁定的 `summary.json` 原本仍宣稱 E2-A 沒有總判定；同一支工具、同一棵證據樹重跑，三個 decision 逐位元不變）。 |
