# SPEC E1-D — 窄版契約加入範圍選取

| | |
|---|---|
| **狀態** | **已實作並重建**（2026-08-07）；E1-C 人工輪待操作者重跑 |
| **提出日** | 2026-08-07 |
| **起因** | demo 需要滑鼠拖曳反白；`narrow-editor-v1` 目前只有字元移動與 Shift 擴張 |
| **前置** | E1 已達 `E1_GO_ODT_EDITOR`（artifact `97e605ee…`） |

## 1. 要解決的問題

窄版編輯器可以用 Shift+←／→ 逐字元擴張選取，但無法用滑鼠拉出一段。引擎其實已經實作
了範圍選取，只是掛在 `editorDiscoverySelect` 之下、由 `editor-discovery-closed-actions`
把關，而出貨的 `e1-editor-v1` 不宣告該能力。

## 2. 第一道閘門（最便宜的驗證實驗）

**規則**：規格的第一道閘門必須是最便宜的驗證實驗，通不過就停止。這裡的最便宜作法是在
**已經建好**的 `e1-editor-discovery` 上驗證兩個候選方法，完全不重建。

harness：`wasm_sdk_probe/web/e1-drag-select-gate.html` ＋ `-app.js`
（`make e1-drag-select-gate-assets`，刻意不相依任何 profile）。
證據：`findings/evidence/e1-drag-select-gate/gate-metrics.json`。Firefox 153.0.1，
12 個案例，全部**由選取讀回判定後置條件**，不採信請求 resolve 這件事本身。

### 2.1 已觀察：`mouse-drag` 不通過

`mouse-drag` 送 MOUSEBUTTONDOWN → MOUSEMOVE → MOUSEBUTTONUP，等
`LOK_CALLBACK_TEXT_SELECTION`。

| 案例 | 完成訊號 | 選取讀回 |
| --- | --- | --- |
| 全新 worker 第一次拖過整行文字 | `completed`／`documented-callback-text-selection` | **`none`、空字串** |
| 同上，之後輪詢 1 秒（40 次） | 同上 | **始終 `none`** |
| 同一 worker 連續三次 | 三次皆 `completed` | 讀到的是較早那次的範圍 |
| 零長度（起點＝終點） | `completed` | `none`，worker 仍可用 |
| 空白區 | `completed` | `none`，worker 仍可用 |

**這正是 [finding 022](../findings/022-e1-release-set-bold-false-noop.md) 的缺陷類別**：
回報成功而什麼都沒發生。差別只在 022 是快取造成，這裡是完成訊號打在 mouse-down 清除
選取所觸發的那個 callback 上。輪詢一秒仍為空，證明不是單純落後。

**結論：`mouse-drag` 不得升格。**

### 2.2 已觀察：`text-handles-unstable` 通過

同一支 harness、同一個 profile，改走 `setTextSelection(RESET, 起點)` ＋
`setTextSelection(END, 終點)`：

| 案例 | 結果 |
| --- | --- |
| 全新 worker 第一次選取 | `"ASCII abc XY"`，**第一次讀回就正確**，2 ms（另一輪 3 ms） |
| 零長度 | `completed`，選取 `none`，worker 仍可用 |
| 空白區後再選有效範圍 | 前者 `completed`，後者正確選到 `"ASCII abc XY"` |
| 四個遞增範圍（200／400／600／800 twips） | `"A"`／`"ASC"`／`"ASCII"`／`"ASCII a"`，逐次單調成長，各自由讀回驗證，`sourceSequence` 推進到 21 |

選到的字數比我用「行寬 ÷ 字數」估的少，那是**我的估算錯**（錨點矩形寬度不等於可見字形
寬度），不是引擎的問題；重要的性質成立：**選取是所請求範圍的確定性函數，且可由讀回驗證**。

沒有任何一個案例卡住 `gEditorPending`。這一點很重要——findings 018 與 022 都是栽在
「沒事可做時沒有 callback」，而這裡即使選不到東西也乾淨完成。

### 2.3 兩次 harness 失敗，保留不掩蓋

`handles-then-poll-1` 與 `handles-empty-area` 以 `search timed out after 30000 ms`
中止。那是 harness 連開第 10 個引擎時的主機負載偶發（與 E1-C lifecycle 的
`init timed out` 同類），**不是選取結果**。兩筆保留在證據裡。它們使
「`text-handles-unstable` 第一次呼叫」的樣本數降為 1，見 §5 待驗證。

### 2.4 閘門裁決

**通過，但只對 `text-handles-unstable`。** 升格範圍選取是可行的；要升格的是 API 路徑，
不是合成滑鼠事件那條。前端把滑鼠拖曳手勢對應成一次範圍請求——這本來就比較誠實，因為
起訖點前端自己就有，不需要引擎去合成滑鼠事件再猜。

## 2.5 契約形狀（2026-08-07 補測，Chrome 150 ＋ Firefox 153.0.1）

規格 §5 原列的三項待驗證會影響契約怎麼寫，因此在動引擎之前先補完。全部零重建，
證據 `findings/evidence/e1-drag-select-gate/shape-{firefox,chrome}.json`
與兩份存檔 ODT。

| 選取範圍之後 | 結果 | 判定依據 |
| --- | --- | --- |
| **跨行／跨段落範圍** | ✓ 選到 48 字元橫跨三段：`E1-PLAIN-START\nASCII abc XYZ 0123456789\n臺灣中文游標測試` | 選取讀回 |
| **`set-bold`** | ✓ `uno-command-result` | 存檔 `content.xml` 出現 `T1` 帶 `fo:font-weight="bold"`，套在**正好那 12 個選取字元** |
| **`replaceSelection`（打字取代）** | ✓ revision 0→1 | 存檔 ODT：原選取字串出現 0 次、`E1D-REPLACED` 出現 1 次 |
| **`delete-backward`** | ✗ **typed 拒絕** `EDITOR_STATE_UNAVAILABLE`：`selection barrier requires a callback-confirmed collapsed caret` | 拒絕後搜尋仍找得到原字串——fail-closed，文件無損 |

前三項兩瀏覽器逐項相同；取代目前只跑過 Firefox。

**刪除那一項是設計輸入，不是缺陷。** `startSelectionBarrierDelete` 明確要求
`initial.type == LOK_SELTYPE_NONE` 且選取矩形為空——那是
[finding 016](../findings/016-lok-forward-delete-completion-gap.md) 的修法：它自己造一個
單字元選取再驗證，所以必須從收合游標出發。範圍刪除是**另一種交易形狀**（選取已存在、
後置條件是「被選取的文字從存檔中消失」），不是把 barrier 放寬就好。

因此本規格**只做選取，不做範圍刪除**：

- 拖曳選取 → 粗體／斜體 ✓、打字取代 ✓，這兩條已由存檔檔案證實。
- 範圍上按 Backspace／Delete 維持既有的 typed 拒絕，前端明示不支援，不做任何補償動作。
- 範圍刪除若要做，另立里程碑並自帶閘門，不夾帶進本次。

## 3. 打算怎麼做

1. 引擎：在 `narrow-editor-v1` 下新增一個封閉的範圍選取操作，只接受 API 路徑。
   完成條件用 **verified-selection 後置條件**（讀回選取），不單靠 callback——
   即使 §2.2 顯示 callback 在此路徑上表現良好，契約也不該建立在它上面。
   選不到東西時回報「無選取」，不是失敗，也不是假成功。
2. `editor-shell/editor-client.js`：typed wrapper ＋ 後置條件檢查。
3. 重建 `e1-editor-v1`，更新三處釘住的 hash、跑全回歸。
4. demo 前端接上滑鼠拖曳。
5. **E1-C 人工輪作廢，需要操作者重跑一輪**（使用者 2026-08-07 已同意）。

## 3.1 實作結果（2026-08-07）

**ABI**：`oxsdk_editor_select_range(requestId, handle, startX, startY, endX, endY)`。
方法在此邊界**寫死**成 `setTextSelection` 路徑——不是預設值，是 `mouse-drag` 根本傳不
進來。worker 的 `editorSelectRangeV1` 由 `narrow-editor-v1` 把關並**拒收 `method` 欄位**。

**第一版建置有缺陷，已在留下 artifact 前修掉。** 範圍選取只在選取真的改變時才拿得到
`LOK_CALLBACK_TEXT_SELECTION`；在空白處拉範圍而游標本來就是收合的，什麼都沒變、沒有
callback，操作**逾時 60 秒**並讓 session 進入 recovery。成因由對照確認：從文字選取出發
9 ms 完成，從收合游標出發逾時。**這正是 finding 018 的形狀，也正是 §2.3 那格
`handles-empty-area` 因 harness 逾時而從未真正跑過的那一項**——閘門有測它，我卻沒有
重跑就往下走。

**修法：有界的選取讀回。** `EditorSelectReadbackDeadlineMs = 250`。派送後若期限內沒有
callback，引擎在自己的迴圈醒來、**讀回選取**並以 `verified-selection-readback` 完成，
回報實際存在的東西（通常是「沒選到」）。**期限不宣告成功，它只是去看**。只有產品的
range-select 會 arm 這個期限；診斷 profile 維持原本的純 callback 語意，findings 當初的
量測基準不受影響。

修後實測（session 層）：正常範圍 19 ms、零長度 2 ms 收合、**空白區 252 ms 回報「沒選到」
且不卡死**、其後範圍選取 8 ms 正常、打字 revision 前進。

**新 artifact**：wasm `69d4333d…`、loader `ff9c9b43…`、worker `053adcf1…`。

**demo 已接上拖曳**（mousedown 定位、mousemove 合併為單一在途請求、mouseup 收尾；
零長度拖曳視為點擊、不送範圍）。實測：單行一塊反白、跨三段**四塊**、空白區不卡死、
之後仍可打字。

## 4. 不可退讓

- 不得接受「回報成功但選取讀回為空」當作成功——那就是 finding 022。
- 不得用固定 delay 湊出選取；等待必須綁在可觀察訊號上並有界。
- 不得升格 `mouse-drag`。
- 既有八個 `EDITOR_V1_ACTIONS` 的語意不變；這是新增操作，不是改既有動作。

## 5. 待驗證

- ~~`text-handles-unstable` 在全新 worker 的第一次呼叫只有 1 個成功樣本~~ ——
  **2026-08-07 已補齊**：8 次獨立重複（每次全新 engine ＋ 全新文件），
  **8／8 第一次讀回就正確**、文字每次相同、零 harness 失敗。證據
  `findings/evidence/e1-drag-select-gate/gate-handles-first.json`。這正是 `mouse-drag`
  陣亡的位置，現在兩者的差異已有足夠樣本支撐。
- ~~Chrome 未跑~~ —— §2.5 已在 Chrome 150 補跑（§2.1／2.2 的方法比較仍只有 Firefox）。
- ~~跨段落、跨行的範圍未測~~ —— §2.5 已測，跨三段成立。
- ~~選取後接既有 mutation 是否如常~~ —— §2.5 已測：`set-bold` 與 `replaceSelection`
  成立且由存檔判定，`delete-backward` typed 拒絕（見 §2.5 的設計結論）。
- 選取取代只跑過 Firefox，Chrome 未跑。
- 範圍選取後接 `undo` 未測。
- 方法名帶的 `unstable` 來自 E1-A；升格前要決定改名或說明為何不再適用。
