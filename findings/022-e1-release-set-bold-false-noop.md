# 022 — 已出貨的 e1-editor-v1 會回報假的 `documented-state-noop`，使用者按粗體／斜體卻什麼都沒發生

| | |
|---|---|
| **狀態** | **已修並已進出貨物**（2026-08-06 重新凍結 `e1-editor-v1`，兩瀏覽器驗證三個暴露全部關閉，E1-A/B/C ＋ R6～R8 全回歸通過） |
| **Bugzilla** | — （非上游問題，我方 SDK） |
| **發現日** | 2026-08-06 |
| **嚴重度** | 嚴重（靜默資料遺失類：命令回報成功，文件未變） |
| **可重現** | 100%（兩瀏覽器 × 三種操作，判定全取自存檔 ODT） |
| **是否上游** | **否**（我方 `probe_engine.cpp` 的前置條件捷徑） |
| **影響版本** | `e1-editor-v1` **修正前** WASM `94b38437…`／loader `45c31f32…`；**修正後**（2026-08-06 重新凍結）WASM `97e605ee…`／loader `b9a29749…`；worker `9696c9ce…` 未變（修法在 engine 端） |

## 現象

在已出貨的 narrow editor 裡，以下三步會讓行內格式命令靜默失效：

1. 點擊（click）一段帶有該格式的文字；
2. 選取另一段**沒有**該格式的文字；
3. 按該格式的按鈕。

引擎回 `completion: "documented-state-noop"`、`changed: false`，等於告訴呼叫端
「這段本來就是這個狀態，不需要變更」。實際存檔的 ODT 顯示該段**從未套用**。

使用者看到的是：按了按鈕、沒有錯誤、什麼也沒發生。

**三種操作全部中招**（2026-08-06 補測，Chrome＋Firefox 逐欄相同）：

| 操作 | 前置 click | 目標 | 快取值 | 派送結果 | 存檔 ODT |
|---|---|---|---|---|---|
| 套用粗體 | 粗體字 | 非粗體字 | `bold=true` | `documented-state-noop` | 未變粗體 |
| 套用斜體 | 斜體字 | 非斜體字 | `italic=true` | `documented-state-noop` | 未變斜體 |
| **取消粗體** | 非粗體字 | **粗體字** | `bold=false` | `documented-state-noop` | **仍是粗體** |

取消粗體那一列特別值得注意：它證明這不只是「該套用的沒套用」，**該移除的也沒移除**
——方向無關，任何一次快取與實際不符都會靜默失效。

每一列都配一個**只差前置 click** 的對照組，三個對照組全部正常生效
（`uno-command-result`、存檔確認）。因此差異只可能來自快取值。

## 重現步驟

```bash
cd wasm_sdk_probe
make e1-bold-noop-assets        # 只複製頁面，不重建凍結 artifact（可用 make -n 確認）
python3 tools/run_e1_bold_noop.py --browser chrome    # Firefox 同
```

判定在 `verdict`：`exposed` 列出踩到的配對，`notReached` 列出「快取沒填成功、
這一輪根本沒測到捷徑」的配對——後者**不等於安全**，必須分開看。

harness 跑六個 case（三組配對），每組只差前置的 click：

| case | 前置 click | 目標（search 選取） | 動作 |
|---|---|---|---|
| `control-bold` / `exposure-bold` | 無／`bold anchor` | `E1-STYLED-END` | `set-bold(true)` |
| `control-italic` / `exposure-italic` | 無／`italic anchor` | `E1-STYLED-END` | `set-italic(true)` |
| `control-unbold` / `exposure-unbold` | 無／`E1-STYLED-END` | `bold anchor` | `set-bold(false)` |

Chrome 150.0.7871.128 與 Firefox 153.0.1 六個 case 逐欄相同。

驗證修法（隔離 profile，不動凍結 artifact）：

```bash
make e1-noopfix-assets
python3 tools/run_e1_bold_noop.py --browser chrome --profile e1-editor-v1-noopfix
```

## 證據

- `evidence/022/{chrome,firefox}/`（凍結 profile 的六個 case：`result.json`、
  六份 `after-*.odt`、頁面日誌與截圖）
- `evidence/022/e1-editor-v1-noopfix/{chrome,firefox}/`（修法後同一組 case）
- `evidence/021/e1-release-exposure/`（首輪只測粗體時的紀錄，含 search 定位未踩到的那一版）
- 每個 case 的後置條件都由**存檔 ODT** 判定（解析 `content.xml`／`styles.xml`，解出
  `fo:font-weight="bold"` 的樣式名並沿 `parent-style-name` 繼承鏈解析），與被檢驗的
  callback 無關。

## 分析

### 已觀察

- `probe_engine.cpp` 的 `handleEditorAction` 在 `set-bold`／`set-italic` 上有一條捷徑：
  `boldKnown && bold == 要求值` 時直接回 `documented-state-noop`，**不派送**。
- 該捷徑**不在** `#ifdef OXSDK_E2_FORMAT_BARRIER` 之內，因此**編進所有 profile，包含
  凍結的 `e1-editor-v1`**。
- `e1-editor-v1` 走的是 `updateEditorFormatState` 的 `#else` 分支，該分支**沒有
  `formatStateStale`**——E2 為 finding 021 加的 fail-closed 完全不在這條路上。
- 實測：click 定位會讓快取拿到 `bold=true`；隨後改選別段文字時快取**不更新**
  （[finding 021](021-wasm-format-state-not-refreshed-by-caret-movement.md)），於是捷徑
  用**前一段**的值回答了這一段的前置條件。
- search 定位不會踩到，因為它連快取都填不出來（`bold` 全程 `null`）——同一個缺陷讓
  這條路徑意外地安全。**這不是防護，是巧合。**

### 推論

- 這是 finding 021 的直接後果，但影響面比該 finding 原本記載的大：021 一直被視為
  「E2-A 的閘門問題」，實際上**同一個成因已經在已出貨的 release 上造成靜默 no-op**。
- ~~`set-italic` 與反向操作應同樣暴露，本輪未測~~ → **已補測，兩者皆中**（見「現象」）。

### 待驗證

- 其他 click 序列（例如連續多次 click）是否會讓快取在更多位置被填、擴大暴露面。
- e1-editor-v1 之外的既有 release（R6～R8）是否也連結了這條捷徑——依原始碼位置推論
  應該是，但未逐一驗證。這些 profile 是否真的把 `editorActionV1` 開給呼叫端則另需確認
  （能力表未列 `narrow-editor-v1` 者，即使程式碼在也到不了）。

## 影響與目前決策

- **這是產品缺陷，不是 discovery 缺陷。** 修法有兩個方向，都不需要上游：
  1. **移除捷徑**（與 finding 021 的產品路線 C 一致）：`set-bold`／`set-italic` 一律
     派送，判定只用後置條件。代價是失去「有沒有變」的回報，而該回報本來就不可信。
  2. 為 `#else` 分支補 `formatStateStale` 並在 stale 時 fail closed。代價是使用者會
     看到 typed 拒絕，且 e1-editor-v1 是凍結 artifact，動它要重新走 E1-C 驗收。
- **已採用 (1) 並實作**（2026-08-06）：
  - `src/probe_engine.cpp` 的 `handleEditorAction` 移除該捷徑，`set-bold`／`set-italic`
    一律派送。原處保留說明為什麼移除，以免日後被當成效能優化加回來。
  - `editor-shell/editor-client.js` 同步移除對 `documented-state-noop` 的接受
    （原本 `validNoop` 與 `validChange` 擇一即可）。engine 端不再產生它，client 端也
    不再接受它——否則同一個靜默 no-op 回來時不會有人發現。
- **驗證**：隔離 profile `e1-editor-v1-noopfix`（與 `e1-editor-v1` **完全相同的編譯
  旗標**，只有輸出路徑不同）在 Chrome 與 Firefox 各跑同一組六個 case：
  **`exposed` 為空、`notReached` 為空、六個 case 全部生效並由存檔 ODT 確認**。
  `notReached` 為空很重要——它代表快取仍被填、情境仍然到達，修法不是靠繞過去通過的。
- **凍結的 `e1-editor-v1` 已重建並重新凍結**（2026-08-06，使用者授權）。舊 artifact
  已備份後覆寫；新舊 hash 都記在上表。重建後**直接對出貨物本體**跑同一組六個 case，
  Chrome 與 Firefox 皆 `exposed` 為空、`notReached` 為空、六個 case 全部生效
  ——驗證的是真正會出貨的那份，不是隔離的驗證 profile。
- **暴露面僅限 `e1-editor-v1`**（2026-08-06 確認）：`editorActionV1` 在
  `sdk/sdk-worker.js:37,94` 以 `narrow-editor-v1` 能力開閘，而 dist 內十四個 profile 中
  只有 `e1-editor-v1`（與其驗證變體）宣告該能力。`writer-review`、`writer-review-r6`、
  `writer-reader`、`full-qa` 都沒有，因此雖然共用同一份程式碼，呼叫端到不了。
  discovery profile（`e1-editor-discovery`、`finding-016-*`、`e2-*`）走的是
  `editor-discovery` 那組動作，同樣受此捷徑影響，但不是出貨物。
- **不得把 `documented-state-noop` 當成任何 release 的已驗證能力。**
  [finding 021](021-wasm-format-state-not-refreshed-by-caret-movement.md) 早已寫下這條
  禁令，本 finding 是它成真的實例。

## 環境

- Core commit：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- 受測 profile：`e1-editor-v1`（**未重建**；跑前後 `probe.wasm`／`probe.js`／
  `sdk-worker.js` 的 SHA-256 逐一比對相同：`94b38437…`／`45c31f32…`／`9696c9ce…`）
- 修法驗證 profile：`e1-editor-v1-noopfix`，WASM `e424eec4b42ec3cd…`
  （`make e1-noopfix-assets`；`make -n` 可確認它不觸及 `dist/profiles/e1-editor-v1/`）
- Fixture：`test-docs/e1/styled-list.odt`（`bold anchor` 在 `E1Bold` span 內，
  `E1-STYLED-END` 為無 span 的純段落）
- Chrome：`150.0.7871.128`；Firefox：`153.0.1`

## 還缺什麼才能關閉

- [x] 在已出貨 artifact 上重現，且後置條件由存檔檔案獨立判定。**已重現，兩瀏覽器。**
- [x] 證明差異只來自快取（control 與 exposure 只差前置動作）。**已證明。**
- [x] 測 `set-italic` 與反向操作（取消粗體）。**兩者皆中，兩瀏覽器。**
- [x] 決定修法並實作。**移除捷徑（engine ＋ client），隔離 profile 驗證三個暴露全部關閉。**
- [x] **重建 `e1-editor-v1` 讓修法進到出貨物**，並重跑驗收與回歸。**已完成**：
  `test-e1-{a,b,c}-static`、`test-e2-a-static`、`test-r6-{a,b,c,roundtrip,release}`、
  `test-r7-{a,b,c,d}-static`、`test-r8-{a,b,c,d}-static`、
  `test-finding-016-scheduler-static` 全數通過。
- [x] 確認 R6～R8 是否也把 `editorActionV1` 開給呼叫端。**沒有**——只有
  `e1-editor-v1` 宣告 `narrow-editor-v1`。
- [x] E1-C 瀏覽器驗收對重新凍結的 artifact 重跑。**自動部分兩瀏覽器全過**
  （`automaticPass: true`）。
- [x] **E1-C 的人工 Chewing 輪重跑**（本 finding 造成的連帶工作）。**已完成**，
  2026-08-06 深夜由操作者以 SSH port forward 遠端執行，兩瀏覽器各一輪對
  `97e605ee…` 完成，`manual.pass: true`，裁決回到 `E1_GO_ODT_EDITOR`。
  第一次嘗試因固定字串打錯未過（詳見 DEVLOG），失敗證據保留為 `*-attempt-02`。

## 時間軸

- 2026-08-06：閱讀 finding 021 的修法時注意到 `set-bold` 捷徑不在 E2 的 `#ifdef`
  之內，而 e1-editor-v1 的 `#else` 分支沒有 stale 旗標，推論已出貨 release 可能暴露。
- 2026-08-06：以新 harness（`web/e1-bold-noop-check.html`、`tools/run_e1_bold_noop.py`）
  在**未重建**的凍結 profile 上驗證。第一版用 search 定位，未踩到——查出原因是快取
  根本沒被填（`bold` 全程 `null`），不是防護生效。改用 click 定位（產品 shell 用的
  路徑）後在兩瀏覽器重現。
- 2026-08-06：harness 擴為六個 case（三組配對），補測 `set-italic` 與取消粗體
  ——**三者皆中，兩瀏覽器逐欄相同**。取消粗體證明方向無關。
- 2026-08-06：實作修法（移除 engine 捷徑 ＋ client 不再接受 `documented-state-noop`），
  並建 `e1-editor-v1-noopfix` 隔離 profile 驗證：兩瀏覽器 `exposed` 與 `notReached`
  皆為空，六個 case 全部生效。該階段凍結 artifact 未重建（hash 比對相同）。
- 2026-08-06（使用者授權後）：重建並重新凍結 `e1-editor-v1`。舊 artifact 先備份。
  重建後對出貨物本體重跑六個 case，兩瀏覽器全部關閉。更新三處釘住的 hash
  （`tests/test_e2_profile.py` 的 `FROZEN`、`e1/validation-matrix-v1.json`、
  `e2/discovery-matrix-v1.json` 的 baseline），每處都留了為什麼改的紀錄。
  `editor-shell/tests/editor-client.test.mjs` 原本斷言「接受 typed no-op」，改為
  斷言必然變更，並**新增一項回歸測試：engine 若再送 `documented-state-noop`，client
  必須拒絕**——這個 bug 出過一次，不能讓它悄悄回來。
- 2026-08-06：注意到隔離驗證 profile 與重建後的出貨物 WASM hash 不同
  （`e424eec4…` vs `97e605ee…`）。兩者大小相同、僅 30 個位元組相異，且差異落在
  code section 的 local index，屬連結器在不同輸出路徑下的暫存器配置非決定性。
  未依賴此推論——直接對出貨物本體重跑了完整案例組。
