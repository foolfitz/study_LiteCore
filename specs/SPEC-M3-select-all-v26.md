# SPEC-M3-select-all-v26：Ctrl+A 全選與 finding 174（manifest 後繼 profile `e2-editor-v26`、殼層 generation 80、宿主 0.2.42，不重新連結）

> 狀態：**釘死**（2026-10-30，任何實作與瀏覽器執行之前）。釘死之後只准追加（CLAUDE.md 第 10 節）。
> 依據：工單 `handoff/WORKORDER-v26-select-all.md`；研究筆記 `research/2026-10-29-select-all-route-on-v25.md`（第一部分讀碼、第二部分量測）；證據 `findings/evidence/select-all-v25/`（`b5d3b9834`）；finding 174（`2c05017b0`）。
> 擁有者 2026-10-29：全選「A：放進下一個引擎批次」；2026-10-30 看過量測後改選「B：不重新連結，先出」。2026-10-30：174「B：三種都改」，「A：跟全選一起進 0.2.42」。
> 草稿經一次對抗性審核（opus，2026-10-30），12 項中 10 項經讀碼確認後併入；見 §8。

## 1. 為什麼要有

**全選。**擁有者在宿主 0.2.40 上按 Ctrl+A，沒有全選。不是退化：全選（wire id 21）從 v4 起就在引擎裡，manifest 一直扣住它（`gestures: []`），頁面刻意不綁 Ctrl+A——2026-08-19 用幾何範圍模擬全選，回報成功、什麼都沒選。2026-10-30 的量測（v25、scratch manifest、harness 直送 worker、Chrome 54 格）〔實測〕：

- 游標在本文按全選，選到整份文件（兩端＝文件頭尾、複製含每個本文段落與格子、頁面畫出底色），修訂號不變、`changed: false`；回覆在選取 callback 之後的同一次 poll 組成（59/59）。
- 之後的打字、Backspace、刪除、粗體、復原，在表格、frame、附註、空白文件上都正常。08-19 的失敗在有序引擎上不重現。
- 限制：含 as-char frame 的範圍複製回 `complex`、沒有文字；三個 gesture 都要給；附註本文不在複製內容裡但會隨錨點刪掉。

引擎不用改。

**Finding 174。**擁有者在 0.2.41 手測 173：新文件空白處按清單，清單套上了，但跳出紅色錯誤框，前面是 `MUTATION_OUTCOME_UNKNOWN` 與引擎的英文訊息，最後才是 083 那句中文〔實測，擁有者畫面〕。成因〔讀碼〕：`run()` 對處置為 `review`（已送出、佇列開著、請使用者看一下）的三種情況——046、059、083／173——一律用 `toast(\`${label}：${describeError(error)}\`＋說明, true)`，錯誤樣式加錯誤碼加英文。

## 2. 範圍

**做**（不重新連結；wasm、loader、exports 與 v25 archive 逐位元組相同，頁面釘選 `44cb15ea8d36f0e0` 不變）：

1. **profile `e2-editor-v26`**：v25 的後繼身分（`e2-editor-v7` 的前例：沿用引擎位元組、只改 manifest）；和 v7 不同，worker 要改一行（§4.2）。
2. **殼層 client** `editor-shell-v2/narrow-editor-v2-client.js`：接受 `select-all`，postcondition 類別 "move"；匯出 client 接受的動作的聯集。
3. **殼層 session** `editor-shell-v2/narrow-editor-v2-session.js`：它自己的動作允許清單改讀那個聯集；`select-all` 以非變更（`mutation: false`）入佇列。
4. **頁面** `web/e2-editor-app.js`：worker URL 改指 v26；Ctrl+A／Cmd+A；用回覆更新頁面的選取形狀；174 的提示呈現。
5. 殼層 **generation 80**（三個檔）；**宿主 0.2.42**。

**不做**：

- 含 frame 的範圍無法複製（`complex`）：不修（§6 L-complex-copy），只要求失敗照實說。
- `delete-selection` 的限制字串不改。
- 工具列的全選按鈕、右鍵選單。
- Ctrl+A 之後按 Enter（`insert-paragraph-break` 只給 collapsed，引擎拒絕）、Ctrl+V 蓋過整份範圍：不改行為；前者量、後者具名限制（§5.4、§6）。
- 頁面的形狀信念在「範圍→打字／刪除」之後沒有回到 collapsed：拖曳選取之後本來就這樣（`e2-editor-app.js` 約 2810 行的註解），本規格只量、不修（§6 L-stale-shape）。
- 游標在 frame、腳註、尾註裡面；文件以表格開頭或結尾：具名限制。
- 下一個改引擎的批次改稱 **v27**（工單檔名不改）。K、`what_the_link_ships.py` 的盲點不在範圍內。

## 3. 決定紀錄

| 題 | 決定 | 出處 |
|---|---|---|
| 全選出貨方式 | 不連結、manifest 後繼＋殼層＋頁面 | 擁有者 2026-10-30 選 B |
| 174 範圍 | 三種 `review` 都改；錯誤碼與英文訊息改記主控台 | 擁有者 2026-10-30 選 B |
| 174 與全選同一版 | 同一個 generation 80、同一次安裝；規格裡是兩組獨立判準 | 擁有者 2026-10-30 選 A |
| profile 名稱 | `e2-editor-v26` | 「版本是身分」；v7 前例 |
| gesture | 三個都給 | 研究筆記第二部分第 3 題（只給 collapsed 時第二次按被拒，實測） |
| worker | 只改 `featureExtendPermitted` 的 profile 名稱 | §4.2 |
| wasm 放哪 | `profiles/e2-editor-v26/` 放逐位元組相同的副本，不跨目錄引用 | 一個 profile 目錄自成一體、以目錄封存。沒有額外的下載代價：宿主的網址本來就帶 buildId（所有檔案的雜湊），每次發佈都會換 |
| client／session 的清單 | client 匯出 `EDITOR_SELECT_ALL_ACTIONS = ["select-all"]` 與聯集 `EDITOR_ACCEPTED_ACTIONS`（＝V4＋全選）；session 的 `ACTIONS` 改讀聯集；V3／V4 清單不改 | 審核第 1、3 項：session 的第二份清單會落後（ABI 4 時發生過一次） |
| 全選算不算變更 | 不算：加進 session 的 `BOUNDARY_CAPABLE_MOVES`（它的定義是「以 posted key 到達引擎的動作」，全選正是 `Key::A|Mod1`、`mutation = false`）；不加進 `CHECKPOINTED_MOVES` | 審核第 2 項：否則沒改過的文件按 Ctrl+A 就變「未存檔」（098 的形狀），唯讀文件會拒絕全選 |
| postcondition | 沿用 "move" | 量到的回覆正是它接受的兩種 completion |
| 頁面怎麼送 | 走 `editorAction("select-all", { onResult })`，`ACTION_LABELS["select-all"] = "全選"` | 審核第 12 項：與其他快捷鍵同一套 `SESSION_ACCEPTS`、`engineActionsOut`（128）規則 |
| 按住不放 | `event.repeat` 只 `preventDefault`、不送（Ctrl+S 的 106 規則） | 審核第 8 項 |
| 成功時說什麼 | 不另外跳提示（底色就是回饋）；延遲欄照 `run()` 顯示「全選」 | 格子裡第一次按只選到格子，說「已選取整份」會是假的 |
| 沒選到時說什麼 | 回覆 ok、`state.selection.collapsed === true` → 「全選沒有選到任何內容」；選取讀不到 → 照 079 的規則保留舊形狀、舉旗、不說話 | 審核第 5 項 |
| 文件還沒有任何選取回報時 | 全選被拒（`EDITOR_FORMAT_GESTURE_UNSUPPORTED`；三個 gesture 都給了之後，這是全選唯一會被這個碼拒的情況）→ 「請先點一下文件，再按 Ctrl+A」 | 審核第 7 項；引擎 `probe_engine.cpp:6340-6346` |
| 174 的呈現 | `review` 的三種：`${label}：${那句中文}`、一般樣式（`toast(..., false)`），錯誤碼與英文以 `console.warn` 記錄；其他處置（rollback、restart、none）不變 | 擁有者選 B |

## 4. 設計

### 4.1 manifest

`profiles/e2-editor-v26/sdk-manifest.json`＝v25 archive 的 manifest，**恰好四個值**不同：

| 欄位 | v25 | v26 |
|---|---|---|
| `profile` | `e2-editor-v25` | `e2-editor-v26` |
| `sdkVersion` | `0.6.0-r6-worker+e2-editor-v25` | `0.6.0-r6-worker+e2-editor-v26` |
| `editorContract.workerSha256` | `75557b22…` | v26 worker 的 sha256 |
| `editorContract.actions["select-all"]` | `{"id":21,"gestures":[],"limits":["withheld-pending-characterisation"]}` | `{"id":21,"gestures":["collapsed","range-single","range-cross"],"limits":["characterised-2026-10-30-select-all-v25","copy-of-a-range-holding-a-frame-is-complex","caret-in-frame-or-note-not-characterised"]}` |

組裝工具 `tools/build_e2_v26_select_all_profile.py`：輸入 v25 archive（先逐檔核對 `SHA256SUMS`）與 `sdk/v26-select-all-worker.js`，輸出 `dist/profiles/e2-editor-v26/` 四個檔。不讀 `build/e2/editor-v25/`、不依賴任何物件檔，不可能觸發連結。Makefile 加一個只依賴 archive 與 worker 原始碼的規則（`cp`＋python，無編譯）。

### 4.2 worker

`sdk/v26-select-all-worker.js`＝`sdk/v25-feature-worker.js` 只改 `featureExtendPermitted` 裡的 `"e2-editor-v25"` → `"e2-editor-v26"`（＋一行註解指向本規格）。v25 的 worker 原始碼不改。

為什麼非改不可：`featureExtendPermitted` 用 profile 名稱放行 ABI6 的**行移動延伸**（Shift＋↑↓、Shift＋Home／End；字元移動走 `EDITOR_V1_MOVE_ACTIONS`，不經它）。不改而 manifest 改名，行延伸會被判不允許——靜默失效。

### 4.3 殼層 client 與 session

- client：新匯出 `EDITOR_SELECT_ALL_ACTIONS`、`EDITOR_ACCEPTED_ACTIONS`；`APPENDED` 併入全選；`postconditionClassOf("select-all") === "move"`（與 `DOCUMENT_MOVE_ACTIONS` 並列，不放進 `MOVE_ACTIONS`，那個集合決定 `extendSelection` 是否合法）。
- session：`const ACTIONS = new Set(EDITOR_ACCEPTED_ACTIONS)`；`BOUNDARY_CAPABLE_MOVES` 加 `"select-all"`（註解寫明理由與本規格）；`CHECKPOINTED_MOVES` 不變。
- `closed-lists.test.mjs`：D13 的普查改讀 `EDITOR_ACCEPTED_ACTIONS`；`moves.length` 的斷言明寫改成 9（「六個按鍵路徑的移動、142 的兩個、全選」）；`move-document-middle`、`paste-markdown` 仍在送出前被拒。

### 4.4 頁面

1. `workerUrl` → `./profiles/e2-editor-v26/sdk-worker.js`；`PINNED_WASM_SHA256` 不變。
2. sink keydown：`accel`＋`a`、無 Shift、無 Alt、`!event.isComposing && !session.input?.state?.composing`、`session.offers("select-all")` → `preventDefault`；`event.repeat` 時到此為止；否則 `editorAction("select-all", { onResult })`。條件不成立 → 什麼都不做（今天的行為）。
3. `onResult`：`selectionShapeOf(result)` 讀得到 → `lastSelectionShape` 設為它並 `updateGestureAffordance()`；讀不到 → 照 `pumpDrag` 的 079 規則保留舊值、舉旗。`state.selection.collapsed === true` → 提示「全選沒有選到任何內容」。
4. 全選被拒、碼是 `EDITOR_FORMAT_GESTURE_UNSUPPORTED` → 提示「請先點一下文件，再按 Ctrl+A」（取代 `run()` 的通用錯誤提示）。
5. 174：`run()` 的 `review` 分支改為 `toast(\`${label}：${sentence}\`, false)`，三句中文（059、083／173、046）一字不改，去掉外層括號；`console.warn` 記錄 `label`、`error.code`、`error.message`、`failureShape`。其他分支不動。
6. 08-19 那段「Ctrl+A is deliberately NOT bound」的註解改寫：保留 08-19 的量測，加上 10-30 的量測與本規格。

### 4.5 身分

- profile `e2-editor-v26`；archive `build/archive/e2-editor-v26-44cb15ea-worker-<v26 worker 前 8 碼>`（四個檔＋`exports.txt`＋`SHA256SUMS`＋`ATTRIBUTION.md`）。
- 殼層 generation 80＝generation 79 只差三個檔（頁面、client、session）；排除清單＝v79 的八筆＋`sdk/v26-select-all-worker.js`。Makefile bundle 行改指 v80（改前紅、改後綠、指回 v79 紅）。凍結之後若還要改，是 generation 81。

## 5. 判準

證據目錄 `findings/evidence/select-all-v26/`（宿主另放 `findings/evidence/host-0.2.42/`）。每條都有「沒做的話」的預設結論。

### 5.1 P1：profile 身分（形式二，工具封閉）

`tools/check_v26_profile.py`：

1. `probe.wasm`、`probe.js` 與 v25 archive 逐位元組相同；`exports.txt` 相同。
2. worker 與 v25 archive 的 worker 的差異恰好是 §4.2 那一處（工具算 diff、與寫在工具裡的期望 hunk 比）。
3. manifest 兩份 JSON 的逐路徑差異恰好是 §4.1 的四個路徑；`workerSha256` 等於第 2 條那份 worker 的實際 sha256；`select-all` 整筆等於 §4.1 表中的值（含 `limits`）。
4. 母數由工具從 worker 原始碼的 `EDITOR_V4_ACTION_IDS` 讀出：每個名字在 v26 manifest 裡都**存在**，扣住的寫成 `gestures: []`（不能省略——引擎對省略的動作預設全開）。

**紅案**（先做，`p1/red/`）：`select-all` 刪掉（省略而非扣住）、只給 `collapsed`、`limits` 少一筆、多改一個欄位、worker 多一個位元組、`workerSha256` 不符、wasm 換檔——各自必須紅。
**預設**：沒跑或紅案沒做，P1 不成立，後面一律不跑。

### 5.2 U1：client 與 session（單元，先紅）

`editor-shell-v2/tests/narrow-editor-v2-select-all.test.mjs`：

- `postconditionClassOf("select-all") === "move"`。
- 假引擎授權 `select-all`：真的 `NarrowEditorV2Session` 的 `action("select-all")` 送出 `editorActionV2`，payload `extendSelection: false`、`enabled: false`、帶 `expectedRevision`；入佇列時 `mutation: false`；`actionMutates("select-all") === false`；回覆之後 `hasUnsavedEdits() === false`。
- 唯讀 session：`action("select-all")` 被接受（不是 `EDITOR_VIEW_ONLY`）。
- 回覆用 10-30 run-01 的實際形狀（`documented-callback-visible-cursor` 與 `verified-move-readback` 各一）→ 接受；修訂號前進、`changed: true`、completion `uno-command-result` → 各自 `EDITOR_RESULT_INVALID`。
- manifest 扣住或省略 → `offers("select-all") === false`。
- `closed-lists.test.mjs` 依 §4.3 改寫後全綠。

**紅案**：未修改的 client／session 上新測試紅在第一條（client）與 session 那條（`EDITOR_ACTION_UNSUPPORTED`）；見證 `u1/red-before.txt`。另做一個變異：session 的 `ACTIONS` 改回 `EDITOR_V4_ACTIONS`，必須紅（「第二份清單落後」要被抓到）。修好後 `node --test editor-shell-v2/tests/*.test.mjs` 全綠，`u1/green-after.txt`。
**預設**：沒有紅的見證，U1 不成立。

### 5.3 U2：頁面的綁定（單元，先紅）

`editor-shell-v2/tests/page-select-all.test.mjs`，照 `page-boundary-noop.test.mjs` 從頁面原始碼切出 sink keydown 與全選的 `onResult`／拒絕處理，協作者換成替身：

- offers 為真：Ctrl+A、Cmd+A 各 → `preventDefault` 一次、送一次 `select-all`；`repeat: true` → `preventDefault`、不送。
- offers 為假：Ctrl+A → 沒有 `preventDefault`、不送。
- Shift+Ctrl+A、Alt+Ctrl+A、`isComposing`、`session.input.state.composing` → 都不送。
- 回覆 `collapsed: false` → `lastSelectionShape` 為 `selectionShapeOf` 的值、無「沒有選到」提示；`collapsed: true` → 提示含「沒有選到任何內容」；選取讀不到 → 形狀不變、舉旗、無提示。
- 拒絕 `EDITOR_FORMAT_GESTURE_UNSUPPORTED` → 提示含「請先點一下文件」。

**紅案**：未修改的頁面上第一條紅；測試檔自帶變異——拿掉 offers 判斷，第二條必須紅（不提供的 profile 上綁了 Ctrl+A 要紅，工單的紅案）；拿掉 repeat 判斷，repeat 那條必須紅。見證 `u2/red-before.txt`。
**預設**：沒有紅的見證，U2 不成立。

### 5.4 S1：全選，使用者那條路（瀏覽器，鏡像，真的輸入，形式二）

`tools/check_v26_select_all.py`，由 `findings/evidence/select-all-v25/measure_select_all.py` 衍生（後者不改）。全選由**頁面**送出：真的 Ctrl+A（Chrome CDP、Firefox WebDriver actions）。harness 只讀（`getSelection`、`editorGetStateV2`、存檔），不驅動。參考游標用真的 Ctrl+Home／Ctrl+End 取得，再真的點回第一行。

- **產品**（mirror 逐檔核對身分，不過不跑）：**after**＝`dist/`（generation 80、v26）；**before**＝generation 79 的三個檔（從 git，profile v25）；**unoffered**＝after，但 v26 manifest 換成 `select-all` 扣住的 scratch；**fake**＝after，HTML 加改寫器把頁面收到的 `select-all` 回覆的 `state.selection` 換成 collapsed（08-19 的形狀，在頁面那一側構造）；**v25-worker**＝after，但 `profiles/e2-editor-v26/sdk-worker.js` 換成 v25 的 worker（manifest 的 `workerSha256` 一併換回，只給延伸臂用）。
- **文件**：10-30 的六份（list-contexts、table-boundary、frame-contexts、endnote-frame、frame-no-image、宿主空白範本 `7e6221b6…`）＋一份多頁文件（`pp.open_long_document`，至少 3 頁）。
- **觀察器**：頁面的 Worker 包裝（request／reply）、底色的 `fillRect`、一個 document 層的 keydown 監聽（冒泡階段，記錄 Ctrl+A 的 `defaultPrevented`）、`hasUnsavedEdits` 不可讀時以頁面的未存檔標記代替（實作時寫明讀哪個）。
- **after 的臂**（每回先真的點進第一行；每一條 PASS 子句有 id）：
  1. `select`：Ctrl+A。恰好一個 `select-all` 請求、回覆 ok；有文字的文件：選取不是 collapsed、兩端等於參考游標、`getSelection` 依序含每個本文錨點（frame 的兩份改判 `complex`）、`data-selection-shape` 不是 `collapsed`、畫了底色、`ready`、無 notice、無「沒有選到」提示、**未存檔標記沒有出現**；空白文件：ok、collapsed、提示含「沒有選到任何內容」、`ready`；多頁文件：兩端是第一頁第一行與最後一頁最後一行。
  2. `type`：Ctrl+A、真的按鍵打標記。每個 `insertText` ok；存檔後本文只剩一段＝標記。另記錄（不判）之後的 `data-selection-shape` 與 ⌫／⌦／分段／換行按鈕是否 disabled（L-stale-shape）。
  3. `backspace`：Ctrl+A、Backspace。送出 `delete-selection` ok；存檔後本文是一個空段落（空白文件：`delete-backward`、文件不變）。
  4. `bold`：Ctrl+A、Ctrl+B。存檔後每個本文段落與格子是粗體（10-30 run-02 的讀法）。
  5. `undo`：Ctrl+A、打標記、Ctrl+Z 至多 2 次 → 文字等於原文（空白文件 1 次）。
  6. `copy`（只 Chrome）：Ctrl+A、Ctrl+C。純文字四份：提示「已複製」、剪貼簿依序含每個錨點；frame 兩份：錯誤提示（不含「已複製」）、文件不變。
  7. `enter`（list-contexts）：Ctrl+A、Enter。文件不變（存檔逐段相等）、`ready`、無 notice；提示文字記錄（L-enter-over-range）。
  8. `mac`（list-contexts）：Cmd+A。同 `select`。
  9. `table-cell`（table-boundary、frame-contexts）：真的 ArrowDown 進第一列、Ctrl+A 三次。三次都 ok；`getSelection` 長度嚴格遞增（frame-contexts 的複製是 `complex`，改用回覆的矩形數不遞減且第三次之後刪除條件成立）；每次之後形狀不是 `collapsed`。
  10. `unobserved`（list-contexts）：開檔後不點，以 JS 把焦點交給 sink（harness 代替頁面在重開之後自己給焦點，`e2-editor-app.js` 約 2008 行），真的 Ctrl+A。兩種結果之一算 PASS：ok 且同 `select` 的整份條件；或被拒、提示含「請先點一下文件」。兩者都要文件不變、`ready`。
  11. `extend`（list-contexts）：真的 Shift+↓ 一次。回覆 ok、選取不是 collapsed。
- **反例必須為對的原因而紅**：**before**／`select`：沒有送出任何 `select-all`、選取 collapsed；**unoffered**／`select`：同上，且 `defaultPrevented` 為 false；**fake**／`select`（list-contexts）：提示含「沒有選到任何內容」、形狀 `collapsed`；**v25-worker**／`extend`：延伸被拒。紅在別的原因上＝工具設定問題，判讀不成立。
- **次數**：`select` 在 list-contexts、table-boundary 上 N＝3，其餘 N＝1；Chrome、Firefox（`copy` 只 Chrome）。反例各瀏覽器 1 回。
- **判定 `S1_HOLDS`**：五個身分都過；after 每回 PASS；四種反例每回為對的原因而紅；`--self-test REPORT`：工具對每一個 PASS 子句 id 各做一個變異（母數是工具自己的子句表，形式二），每個都必須讓判定轉紅，沒有變異的子句 id 本身就是紅。
- 不是計時量測，不需要桌面閘門。
- **預設**：沒跑、或任何一回 NE，S1 不成立。Firefox 的 `copy` 沒跑＝Firefox 上的全選複製未建立（L-firefox-copy）。

### 5.5 U3／S2：finding 174（先紅）

- **U3**（單元）：`editor-shell-v2/tests/page-review-presentation.test.mjs`，切出 `run()` 的錯誤處理：三種 `review`（`LOK_COMMAND_FAILED`；`select-text-returned-none`；`multi-block-readback`）→ `toast` 的第二個參數為 false、文字＝`${label}：`＋該句中文、**不含** `error.code`、**不含** `error.message`；`console.warn` 收到 code 與 message。`rollback`、`restart`、無處置三種 → 與今天相同（`true`、含 code）。各句的鑑別片語沿用 v79 U2（059「核心的回覆」、083「這一段是空的」、046「不只一個段落」）。**紅案**：未修改的頁面上第一條紅；見證 `u3/red-before.txt`。
- **S2**（瀏覽器）：`tools/check_v80_blank_bullet.py`，由 `check_v79_blank_bullet.py` 衍生（後者不改），B1 的程序、產品（before＝generation 79、after＝80）、次數（兩瀏覽器 × 兩臂 × N＝3）照舊。after 的 PASS＝B1 的四條，再加：`#toast` 沒有 `bad` class、文字不含 `MUTATION_OUTCOME_UNKNOWN` 也不含引擎訊息的英文片段 `selection read`。before 為 174 而紅＝B1 的四條成立而 `#toast` 有 `bad` 且含 `MUTATION_OUTCOME_UNKNOWN`。
- **059 的檢查被解除武裝**（L-174-disarms-059）：F3 的 `a-format-that-worked-is-not-reported-as-failed`（`run_e2_c_product_path.py`，被綁、不改）判的是「提示裡沒有 `LOK_COMMAND_FAILED`」。174 之後錯誤碼不再出現在提示裡，那一格不論 059 有沒有回來都會過。它的位置由 U3 的 059 那條（提示含「核心的回覆」時就是 059 的情況）與本條的聲明承接；F3-80 那一格的 PASS 不得被引用為 059 沒回來的證據。
- **預設**：沒有紅的見證或 S2 沒跑，174 未修。

### 5.6 回歸：F3、F4

- **F3-80**：`tools/run_v80_f3.py`（由 `run_v79_f3.py` 衍生）。兩條讀法：`read_v25_f3.py --v25 <dir>` → `F3_HOLDS`；`read_v80_f3_equal.py`（由 `read_v79_f3_equal.py` 衍生）每一格與 F3-79 相同。格子移動就停下查清，不重跑洗掉；174 會讓讀提示的格子移動的話，先在本規格追加點名那一格與理由，再判。
- **F4-80**：由 v79 的三支衍生，兩瀏覽器四臂 24/24。
- **衍生時要換的釘選**（封閉清單；審核第 9 項）：`tools/v79_four_arms_identity.py` 的 `PROFILE`、`ARTIFACT_PINS`（`sdk-worker.js`、`sdk-manifest.json`）、`ARCHIVED_PROFILE`、`PAGE_SHA256`、殼層摘要與 bundle；`tools/v79_f_products.py` 的 `PROFILE`、`ARCHIVE`、`DECLARED`（三個檔）；`run_v79_f3.py`／`read_v79_f3_equal.py` 的 generation 與基準目錄；宿主的 `prepare-release.py` 裡的 `'e2-editor-v25'`。衍生工具第一次跑之前，對每個衍生檔做「舊值還在不在」的掃描（字串 `e2-editor-v25`、`75557b22`、`e7780061`、`9cb6ea1f`、`bundle-v79`），有剩就停。
- **預設**：沒跑、NE、或有格子移動而沒查清，回歸不成立。

### 5.7 E1-C 與沿用的讀取器

- `check_e1_c_bundle_intact.py`：`intact: true`、`187706b2dcb07d2b`。
- generation 79 的讀取器（B1、F3-79、F4-79）凍結 80 之後在活的樹上依構造 NE；照 v79 的 V0′ 作法換回三個宣告的檔重讀，輸出與已 commit 的逐位元組相同，放回之後核對雜湊。
- **預設**：沒做，沿用的結果視為讀不出來，0.2.42 不送裝。

### 5.8 generation 80

- 凍結前：P1、U1、U2、U3、S1、S2 全過。
- 凍結：與 79 只差三個檔（工具算出的差異＝封閉清單）。`make -n e2-c-assets` 只印三行 `cp`。
- **預設**：沒凍，F3-80／F4-80 不跑。

### 5.9 宿主 0.2.42

- 由 `findings/evidence/host-0.2.41/` 衍生（不改那些檔）：父＝`main` **2bb5718**；前身 archive `host-0.2.41-engine-829a988e199ebc43`。
- 套件判準：對 0.2.41 恰好改 3 筆（頁面、client、session）、新增 4 筆（`profiles/e2-editor-v26/` 四個檔）、移除 4 筆（`profiles/e2-editor-v25/` 四個檔；工具先確認套件裡沒有別的頁面用 v25）；新增的 `probe.wasm`／`probe.js` 與移除的逐位元組相同。紅案：多一筆、少一筆、v26 的 wasm 與 v25 不同，各自要紅。
- 安裝要擁有者的新時段，`slot.json` 有明確的「不開站」回答；fgp-nc、nc-bridge 照擁有者的選擇維持關閉。
- 裝完：Files 實流程、`capture-after.py`（具名限制照舊）、請擁有者手測：(a) 新文件按清單 → 提示不是紅框、沒有英文；(b) 開一份既有文件，**先點一下文件**，Ctrl+A → 底色蓋住整份 → 打字取代 → Ctrl+Z 兩次回原文；(c) 新文件點一下、Ctrl+A → 「全選沒有選到任何內容」。
- **預設**：沒有時段就不裝；0.2.41 仍是日常未計數候選。

## 6. 具名限制

- **L-complex-copy**：含 as-char frame 的範圍，複製／剪下拿不到文字（LOK 回 COMPLEX，引擎只對 TEXT 取文字）；照實報錯，剪下先複製、失敗就不刪。
- **L-notes-not-copied**：附註本文不在複製內容裡；打字或刪除會連附註一起刪（復原可回）。
- **L-enter-over-range**：範圍上按 Enter 被引擎拒絕（`insert-paragraph-break` 只給 collapsed），文件不變；提示是通用錯誤提示（S1 `enter` 記錄的文字）。拖曳選取之後本來就這樣。
- **L-paste-over-range**：Ctrl+V 蓋過整份範圍沒有量。
- **L-stale-shape**：範圍→打字／刪除之後，頁面的形狀信念仍是範圍，collapsed-only 的工具列按鈕變灰直到下一次點擊；拖曳選取之後本來就這樣。S1 記錄、不判。
- **L-caret-in-apparatus**：游標在 frame、腳註、尾註裡面時的全選沒有量。
- **L-table-edges**：文件以表格開頭或結尾沒有量。
- **L-first-paragraph-style**：打字取代整份時沿用第一段的段落樣式（實測）；與桌面 Writer 一致是推論。
- **L-174-disarms-059**：見 §5.5。
- **L-firefox-copy**：Firefox 的全選→複製沒有量。
- **L-no-native**：沒有跑原生 LibreOffice 對照。

## 7. 順序

1. 本規格釘死（commit）。
2. P1 工具與紅案 → worker、組裝工具、Makefile 規則 → 組出 `dist/profiles/e2-editor-v26/` → P1 綠 → archive。
3. U1、U2、U3 先紅（見證）→ 實作 client、session、頁面 → 全綠。
4. `make -n e2-c-assets` 只印三行 `cp` → `make e2-c-assets` → 逐檔 `cmp`。
5. S1、S2 工具 → 反例先跑 → S1 → `S1_HOLDS`；S2；兩支的 `--self-test` 全紅。
6. 凍 generation 80、Makefile 改指 80。
7. F3-80、F4-80 → V0′、E1-C。
8. 宿主 0.2.42 套件 → 擁有者時段 → 安裝 → Files 實流程 → 事後讀取 → 擁有者手測。

沒有任何一步要編譯：profile 組裝只有 `cp` 與 python；`make e2-c-assets` 只有 `cp`。

## 8. §34.4 與審核

本規格釘死之前：因執行而修 0；**因審核而修 10**（opus 對抗性審核，12 項；主 session 讀碼確認後採用）：

| 審核項 | 處置 |
|---|---|
| 1 session 的第二份動作清單會拒絕全選 | 採用（§2 第 3 項、§4.3、U1 的變異） |
| 2 全選會以 `mutation: true` 入佇列（未存檔標記、唯讀被拒） | 採用（§3、§4.3、U1、S1 `select`） |
| 3 D13 普查看不到平行清單 | 採用（聯集匯出、`moves.length` 改 9） |
| 4 延伸臂用 Shift+→ 不會紅 | 採用（改 Shift+↓；§4.2 改寫理由） |
| 5 `collapsed !== false` 與 079 規則矛盾 | 採用（`=== true`） |
| 6 形狀信念在打字／刪除後過時 | 改列具名限制 L-stale-shape 並記錄（拖曳之後本來就這樣，頁面約 2810 行） |
| 7 Enter、Ctrl+V、未有選取回報 | Enter 量＋具名限制；Ctrl+V 具名限制；未有選取回報加提示與 `unobserved` 臂 |
| 8 按住 Ctrl+A | 採用 |
| 9 衍生工具的釘選清單不全 | 採用（§5.6 的封閉清單＋舊值掃描） |
| 10 L-cold-wasm 的成因錯 | 採用（宿主網址本來就帶 buildId；刪除該限制） |
| 11 判準形式的細項 | 採用（參考游標改真按鍵、`--self-test` 依子句普查、P1 母數讀 worker、P1 釘 `limits`、Firefox copy 的預設、`defaultPrevented` 的觀察法） |
| 12 走 `editorAction()`、組字判斷 | 採用 |

審核另確認無誤：只有 worker 的 `featureExtendPermitted` 綁 profile 名稱；頁面只釘 wasm 前綴與 `typedInsert`；宿主由 `workerUrl` 推出 profile；E1-C bundle 不含 editor-shell-v2；finding 111 的佇列順序讓 Ctrl+A 不會插到打字之前；`selectionShapeOf` 讀回覆的 `state.selection`；move 類接受量到的兩種 completion；payload 過得了 worker 的驗證。

主 session 另外找到一項（不在審核內）：L-174-disarms-059（§5.5）。

## 9. 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-10-30 | 草稿。 |
| 2026-10-30 | 草稿第二版：併入 finding 174（擁有者 B／A）與對抗性審核（§8）。 |
| 2026-10-30 | 釘死。 |

## 追加一（2026-10-30，finding 175；fable 代擁有者裁決 A）

> 本節只追加，不改上面任何一字。依據：S1 試跑（`--plan shake`）第 4 回 after／list-contexts／copy／chrome 的複製提示是「已複製 U+0045,U+0031,…（175 個編碼）… 字」（記錄 `findings/evidence/175/shake-run4-copy.json`）；finding 175；裁決原文 `findings/evidence/175/RULING-fable-2026-10-30.md`。

**§2「做」追加第 6 項**：頁面的複製與剪下成功提示，用複製到的字數（`codePoints` 陣列的長度），不再把每個字的編碼串進句子。只改頁面；`input/input-adapter.js` 的 `summarizeUnicode` 不改（r7 的頁面與既有證據的形狀都讀它）。

**§5.4 追加子句 `C.count`**（S1 的 `copy` 臂，Chrome，非 frame 的文件）：提示符合 `已複製 (\d+) 字`，而且那個數字等於剪貼簿文字的 code point 數。`--self-test` 對它的變異是把數字加一，判定必須轉紅。

**§5.10 U4（單元，先紅）**：`editor-shell-v2/tests/page-copy-toast-count.test.mjs`，從頁面原始碼切出複製與剪下的提示：兩者都符合 `已(複製|剪下) (\d+) 字`，數字＝code point 數，不含 `U+`。紅案：未修改的頁面上第一條紅，見證 `u4/red-before.txt`。U2 既有的見證不動。
**預設**：沒有紅的見證，175 未修。

**順序**（取代 §7 第 3–5 步之後的部分，前面已做的不重做，除非下面點名）：本追加 commit → U4 紅 → 修頁面 → U4 綠 → `make -n e2-c-assets`（三行 `cp`）→ `make e2-c-assets`＋`cmp` → 整套 `node --test`（U1／U2／U3 一併重跑）→ **S2 整個重跑**（頁面位元組在它跑過之後變了；判準不變；之前的 S2 run-01 不算數）→ 完整 S1（含 `C.count`）→ 凍 generation 80。**S1 試跑的 11 回只是 finding 175 的證據，不得當作閘門的執行引用。**

**§6 追加具名限制**：
- **L-cut-toast-browser-unmeasured**：剪下的提示沒有瀏覽器臂；由 U4 涵蓋。
- **L-copy-lies-pattern-stale**：`run_e2_c_product_path.py`（被綁、不改）的 `copy-lies` 變異內嵌舊的複製提示那一行（約 2489 行）；本修法之後，下一次 `--mutate copy-lies` 會以「tree moved」中止。F3-80／F4-80 不帶 `--mutate`，不受影響；下一次變異普查要知道這筆債。

**§9 的四個條件**：(1) 先於滿足——完整 S1 還沒跑、generation 80 未凍；(2) 被逼出來且指名——上述試跑第 4 回與 finding 175；(3) 形式——逐實例性質（每一次複製），在工具的子句表裡有變異（形式二）；(4) 截止——`S1_HOLDS` 落地即封閉，之後對提示的顧慮變成 finding。計數：S2、S1 因位元組改變而歸零；S2 的判準不變。

**§8 追加**：因執行而修 1（S1 試跑，finding 175）。

| 日期 | 修改 |
|---|---|
| 2026-10-30 | 追加一：finding 175（fable 代擁有者裁決 A）。 |


## 追加二（2026-10-30，F3-80 的三格移動；fable 代擁有者裁決「B 修改版」）

> 本節只追加，不改上面任何一字。依據：F3-80 的兩條讀法（`findings/evidence/select-all-v26/f3/read-01.json` `F3_RED`、`equal-01.json` `F3_80_MOVED`）；§5.6 要求的查清（`f3/MOVED-CELLS.md`）；裁決原文 `f3/RULING-fable-2026-10-30.md`。

**移動的三格**（Chrome；Firefox 46/46 不動）：

| 格 | F3-79 | F3-80 |
|---|---|---|
| `an-aborted-gesture-stops-selecting` | PASS | NOT_ESTABLISHED |
| `an-inline-format-reaches-a-selection`（`read_v25_f3.py` 的 [P]） | PASS | FAIL |
| `the-page-agrees-with-the-engine-about-the-selection` | PASS | NOT_ESTABLISHED |

**機制**（讀原始碼）：被綁、不改的 `tools/run_e2_c_product_path.py` 在三處（約 7515、8408、8504 行）用 `re.findall(r"U\+…")` 從複製提示解析引擎選到的文字；finding 175 把提示從編碼清單改成字數，三處都解析出空字串／零。F4-80 的 runner 在 generation 80 上把同一套檢查又跑了一次，移動的是同樣三格、其他格不動。Firefox 不動，是因為它的複製在 F3-79 就被拒（`CLIPBOARD_DENIED`）。

**§5.6 那句延伸**：「174 **或 175**（任何改提示文字的修法）會讓讀提示的格子移動的話，先在本規格追加點名那一格與理由，再判。」

**更正追加一**：追加一的具名限制 L-copy-lies-pattern-stale 寫「F3-80／F4-80 不帶 `--mutate`，不受影響」——**這句作廢**。它來自 fable 對 175 的裁決第 6 條，寫的時候沒有追 runner 不帶變異的路徑，主 session 照抄。實際上有三支一般檢查讀同一個提示。

**不宣稱**：generation 80 的 F3 **不**宣稱 `F3_HOLDS` 也**不**宣稱 `F3_80_EQUAL`。紀錄就是 `F3_RED`／`F3_80_MOVED`，各自恰好是上面三格；接受與否由下面的讀取工具判。

**讀過差異**：generation 79→80 的三個檔（`git diff 9f084bf06 HEAD`），逐 hunk：頁面＝`run()` 的 review 提示（174）、`ACTION_LABELS` 加「全選」、複製與剪下提示（175）、keydown 的註解與 `takeSelectAllKey` 一行、新增 `selectAllKey`／`selectAllResult`／`takeSelectAllKey`、`workerUrl` 改 v26；narrow client＝select-all 的清單與 move 類；narrow session＝允許清單改讀聯集、`BOUNDARY_CAPABLE_MOVES` 加 select-all。profile 的 worker 只改 profile 名稱一處，manifest 只改名稱、版本字串、select-all 的 gestures 與 limits、`workerSha256`。**沒有一處碰到拖曳結束、`pointercancel`、`blur` 的處理，也沒有碰到粗體的派送。**若有，B 不成立，要先做下面的工作項再打包。

**讀取工具**：`tools/read_v80_f3_append2.py`（新檔；不改 `read_v25_f3.py`、`read_v80_f3_equal.py`、被綁的 runner，也不重產 `read-01.json`／`equal-01.json`）。只讀已 commit 的報告：基準＝`shell-v79-173/f3/run-01/chrome/report.json`；generation 80＝`select-all-v26/f3/run-01/chrome/report.json` 與 `select-all-v26/f4/chrome/report.json`；加上 `f3/read-01.json`、`f3/equal-01.json`。輸出 `f3/append2-read-01.json`，判定 `F3_80_HOLDS_UNDER_APPEND_2`，否則 `F3_80_APPEND_2_RED`；每個抽出的數字都進紀錄。對**每一份** generation 80 的報告：

- (A) aborted-gesture：outcome 為 NOT_ESTABLISHED；control／reference／pointercancel／blur 的 `copyToast` 都符合 `^已複製 (\d+) 字$`，得 c、r、a1、a2；control 與 reference 的 `aRangeIsSelectedAfterAbortAndMove` 為 true；r > 0 且 r ≠ c；兩個 abort 臂 `aRangeIsSelectedBefore` 為 false 且 aᵢ＝r；四臂的瞄準（`x1`、`y`、`band`、`scanWidth`）相同，control 與兩個 abort 臂的 `abortAtFraction` 相同，各臂的 `aim` 與基準同一臂相同；c、r、aᵢ 各等於基準同一臂 `selectedText` 的 code point 數（23、12、12）。
- (B) inline-format：outcome 為 FAIL；`selected`＝基準的 `selectedText`（空的就紅）；`savedIsOdt` 為 true；`buttonAfterDrag.disabled` 為 false；去空白後 `selected` 不在 `boldBefore`、在 `boldAfter`，且 `boldAfter` 去掉第一次出現的 `selected` 之後等於 `boldBefore`（也就是只有它新變粗）。
- (C) page-agrees：outcome 為 NOT_ESTABLISHED；`copyToast` 符合 `^已複製 (\d+) 字$`，n > 0 且 n＝基準的 `engineCodePoints`（5）；`pageSaysARange` 為 true；`pageAfter.shape` 為 `range-single` 或 `range-cross`；`pageAfter.unreadable` 不是 true。
- (B′)、(C′)（主 session 加的，比裁決嚴）：兩格的 `drag` 與基準相同——數字比的是同一個位置。
- (D) `read-01.json`：`F3_RED`，`problems` 恰好是那三句；`equal-01.json`：`F3_80_MOVED`，`moved` 恰好是那三筆，Chrome 46 格中 43 相同、Firefox 46／46。
- (E) 兩份 generation 80 的報告在 (A)–(C) 抽出的每個數字上一致。
- (F) 非空洞：基準的提示含 `U+`；generation 80 的提示不含 `U+`；基準的文字非空。

**紅案**（`--self-test`，在記憶體裡改真的輸入，輸出 `f3/append2-self-test.json`，每一個都紅才是 `ALL_RED`）：m1 blur 字數 12→13；m2 control 字數 23→12；m3 page-agrees 字數→0；m4 `pageSaysARange`→false；m5 `boldAfter` 拿掉 `KITAL`；m6 `savedIsOdt`→false；m7 基準 `selectedText`→空；m8 read-01 多一句 problem；m9 read-01 少一句；m10 equal-01 多一筆 moved；m11 blur 的 `x1` 改掉；m12 F4-80 的 blur 字數 12→11（兩次不一致）；m13 一則 generation 80 的提示換回舊的 `U+` 形式；m14 inline-format 的 `drag.x1` 改掉（B′）。先跑紅案，再跑真的讀取；兩個檔都 commit。

**宿主的閘門**（`findings/evidence/host-0.2.42/prepare-release.py`，還沒跑過；docstring 的差異清單要寫進這一條）：`F3-80-spec16` 改成要求 `('F3_RED', 恰好那三句)`；`F3-80-equal` 改成要求 `('F3_80_MOVED', 恰好那三筆, chrome 46/43、firefox 46/46)`；新增 `F3-80-append2` 要求 `F3_80_HOLDS_UNDER_APPEND_2`、`F3-80-append2-selfTest` 要求 `ALL_RED`；兩個檔加進必備清單；`countBasis` 與 ATTRIBUTION 的句子寫「F3-80 under spec v26 append 2: three Chrome cells count-only (L-175-blinds-three-F3-cells)」；`release.json` 原樣帶三個判定字串。F3-80 的其他任何說法都拒絕。

**具名限制 L-175-blinds-three-F3-cells**：從 generation 80 起，這三個性質在兩個瀏覽器都沒有「文字」的觀測（Chrome 的提示只有字數；Firefox 的複製被拒，L-firefox-copy）。Chrome 上由本節的讀取工具只看字數、對 F3-79 的文字長度比；inline-format 那格由存檔的粗體差異讀。從 80 起 F3 的綠**不得**被引用為「拖曳中止後的選取文字相等」或「選取的是哪些字」的證據。

**工作項 W-f3-text-observable**：由被綁的 runner 衍生 `run_e2_c_product_path_clipboard.py`（封閉的差異清單：三處改讀剪貼簿，比照 `check_v26_select_all.py` 讀 `follow.clipboard`），衍生後做舊值掃描；在 **generation 80 自己的位元組**上跑 Chrome；預期三格 PASS、文字與 F3-79 相同（`E1-LC-ISOLATED 前後都不是清單的`／`E1-LC-ISOLAT`／`KITAL`），之後 `read_v80_f3_equal.py` 對那個目錄得 `F3_80_EQUAL`。文字不同就開 finding，並重開 0.2.42 的 F3 判讀。排在下一次 K 計數鏈之前、也排在任何改動拖曳選取、手勢中止或範圍上 inline format 的規格之前。**不是**打包或擁有者安裝時段的前提。Firefox 照舊沒量。

**預設（工作項永遠沒做）**：三個性質從 80 起在 Chrome 只看字數、在 Firefox 沒量；之後每一次 F3 的判讀都要帶本節的讀取工具，它的預期文字停在 F3-79、隨每一代變舊；之後的規格不得引用 F3 涵蓋這些路徑；下一個碰到這些路徑的規格要先做工作項，或在自己的限制裡把這些性質列為沒量。

**§9 的四個條件**：(1) 先於滿足——瀏覽器執行照原本釘死的判準做完、不重跑；讀取工具在第一次真的讀取之前 commit；判定式是各格自己的判定式、把文字換成字數，預期值全部來自 F3-79 的報告，不來自 generation 80；(2) 被逼出來且指名——`equal-01` 的 `F3_80_MOVED`、`read-01` 的 `F3_RED`、`MOVED-CELLS.md`、finding 175、175 裁決第 6 條；(3) 形式二——本節的三格封閉清單要等於兩條讀法輸出的集合，多一格或少一格都紅，全部從報告算；(4) 截止——`append2-read-01.json` 在現有兩次 generation 80 執行上成立即封閉，之後的顧慮變成 finding。計數：F3-80 的執行照算、不歸零；S1、S2 不受影響。

**§8 追加**：因執行而修 +1（F3-80 三格移動 → 新讀取工具＋宿主閘門的例外）。新讀取工具 `read_v80_f3_append2.py` 依 §34 審一次。

| 日期 | 修改 |
|---|---|
| 2026-10-30 | 追加二：F3-80 的三格移動（fable 代擁有者裁決 B 修改版）。 |
