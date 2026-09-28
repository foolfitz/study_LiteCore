# 098 — 只移動游標就把文件標成 dirty，於是「沒有東西可失去」的守衛失效

**狀態**：**已修**（2026-09-28，殼層 generation v52，與 099 同一個改動）。原始碼確認 ＋
T9 的 shakedown 觀測到（2026-09-10）＋最小重現已在頁面與單元層級各跑過（2026-09-28）。
**來源**：T9（finding 095 是不是 096 的死前窗口）跑 shakedown 時掉出來的——
走到邊界的那幾次 `ArrowDown` 把乾淨文件標成 dirty，讓半 C 的檢查點先跳進來，
`rescue` 從釘住的 `none` 變成 `checkpoint`
（`handoff/tasks/TASK-2026-09-10-095-is-it-096s-window.md` 的 Execution record
第 191–202 行；也記在 `findings/095-*.md` 第 74–78 行）。當時只寫「觀測到、未解釋」。
這一張把成因從原始碼讀出來。

## 宣稱

**一次純游標移動（方向鍵）會把 session 的 `dirty` 旗標翻成 true，即使那一按沒有
改動任何位元組。**於是一份從沒被打過字的文件，在按過兩次「可觸邊界的移動」之後，
會回報「尚未儲存」、押下一個檢查點、並把 `hasCheckpoint` 設成 true。

## 原始碼鏈（逐段可核）

1. **頁面把方向鍵映射成移動動作。**`web/e2-editor-app.js:1322-1329` 的
   `KEY_ACTIONS` 把 `ArrowLeft/Right/Up/Down`、`Home`、`End` 映射到
   `move-character-*` 與 `move-line-*`；keydown 處理器
   （`:1431-1436`）過 `session.offers(action)` 之後呼叫 `session.action(action)`。

2. **v2 session 的 `action()` 一律用 `mutation: true` 入列。**
   `editor-shell-v2/narrow-editor-v2-session.js` 的 `action()`（約 :357）把每一個
   動作都以 `this._enqueue(..., { mutation: true })`（:388）送進佇列——**六個純移動
   也不例外**。這個檔案自己的註解就寫著這件事（:314-322）：「`action()` enqueues
   every one of the fifteen with `mutation: true`, so the drain bumps that stamp
   after a MOVE as well」。

3. **base drain 用那個旗標設 `dirty`（黏著的 OR）並跳 content stamp。**
   `editor-shell/editor-session.js:304-309`：`if (item.mutation)
   this._currentContentStamp = ++this._contentSequence;` 以及
   `dirty: this.state.snapshot.dirty || item.mutation`。所以一次移動（`mutation:
   true`）會把 `_currentContentStamp` 往前跳、把 `dirty` 設成 true，而且因為是 OR，
   之後除非存檔（:577 才 `dirty: false`）否則一直是 true。

4. **移動不會讓 revision 前進。**v2 client 的後置條件要求移動的
   `result.revision === expectedRevision`、`changed: false`
   （`editor-shell-v2/narrow-editor-v2-client.js:269-275`），所以
   `document.revision` 不動。（若引擎真的動了 revision，那個後置條件會擋下來。）

5. **半 C 的守衛讀的是 `dirty`，於是被騙。**
   `narrow-editor-v2-session.js:331-342` 的 `_checkpointBeforeBoundaryMove`：
   - `if (!this.state.snapshot.dirty) return;`（守衛一：乾淨就跳過）
   - `if (hasCheckpoint && this._checkpointRevision === document.revision) return;`（守衛二）
   - 否則 `await this._checkpointBeforeSelection(document)`；
   而 `_checkpointBeforeSelection`（`editor-session.js:472-486`）：
   `if (!dirty || contentStamp === this._checkpointStamp) return;` 否則存一份 ODT。

## 從全新、沒打過字的文件推出的逐按行為（源自第 3–5 節）

| 動作 | dirty | revision | contentStamp | hasCheckpoint | 這一按做了什麼 |
| --- | --- | --- | --- | --- | --- |
| 開檔 | false | R0 | 0 | false | — |
| 第 1 次 ↓ | false→**true** | R0 | 0→1 | false | 守衛一在動作開頭仍看到 false → 不押；移動 drain 後把 dirty 翻 true |
| 第 2 次 ↓ | true | R0 | 1 | false→**true** | 守衛一過、守衛二（無 checkpoint）過 → **存一份 ODT**（clean bytes） |
| 第 3 次＋ ↓ | true | R0 | 1 | true | 守衛二：`_checkpointRevision(R0)===revision(R0)` → **跳過** |

所以只多押**一次**多餘的檢查點，但那一次存的是和 authority／上次存檔**逐位元相同**的
bytes，而且 session 從此對外宣稱「尚未儲存、有檢查點可救」——使用者只移動過游標。

**這一格是原始碼推的預測，不是這一張獨立跑出來的觀測。**（2026-09-28 更新：已實測，見「最小重現」一節——頁面上第 1 按「無」、第 2 按起「有（r0）」，3/3。）已觀測到的是 T9 的
shakedown：在 v8 上做邊界 walk（連按 `ArrowDown`）時，那些按鍵把文件標髒、半 C
在受測那一按之前押了檢查點，`rescue` 變成 `checkpoint`。walk 是多按，不是這裡列的
「乾淨文件第二按」最小重現；兩者機制相同，但最小重現尚未單獨跑過（見未做）。

## 為什麼這是缺陷，而不是「本來就這樣」

`_checkpointBeforeBoundaryMove` 守衛一的註解白紙黑字寫著它的用意：「Nothing typed
since the last save: there is nothing to lose, and a save here would be a cost
with no beneficiary.」——**它想區分的是「有沒有打過字」。**但它讀的是 `dirty`，而
`dirty` 被一次移動設成 true，所以這個守衛**在實作上分不出「打過字」和「只移動過
游標」**。用意與實作互相矛盾，這就是這張單。

作者的註解（:314-322）確實知道「移動也會跳 stamp」，並為此把 revision 守衛當成價格
控制——但那個守衛只把多餘的存檔**限成一次**，它**沒有**阻止 `dirty` 說謊，也沒有
阻止那第一次針對 clean bytes 的存檔。而且註解通篇假設文件「on a dirty document」
（已經打過字），沒有處理「只移動、從沒打字」這個情況。

## 判別法（AGENTS.md §1 動態）

往真值源塞一個虛構成員看哪個檢查轉紅：**在乾淨文件上按兩次方向鍵，然後斷言
`snapshot.dirty === false`——沒有任何產品路徑檢查在做這件事**，而「移動不算修改」
這個性質已經假了。產品路徑目前唯一碰到這附近的是
`recovery-returns-what-the-product-promised`，而它**刻意**先用插入欄位打字讓文件
真的變髒（`run_e2_c_product_path.py` boundary arm 的 "WORK WORTH LOSING" 段），
所以它永遠不會踩到「只移動」這一格。

## 嚴重度

**低，但是真的。**不是資料遺失：移動不動 revision，救回來的 bytes 等於 authority
bytes。實際傷害有兩處：(a) 只移動過游標的 session 對外顯示「尚未儲存 ／ 有檢查點」，
狀態指示與復原通知因此誤導；(b) 一次針對乾淨 bytes 的多餘 ODT 存檔——正是守衛一
想避免的「沒有受益者的成本」。**復原通道的互動未完整追蹤**（見未做）。

## 處置（2026-09-10 原文）：**只登錄，不修，不建機制**（AGENTS.md §4）

（2026-09-28 更新：已裁決並修好，見下方「裁決與修法」。本節原文保留。）

成因那一行 `dirty: ... || item.mutation` 住在 `editor-shell/editor-session.js:309`，
那個檔案被 E1-C 雜湊綁定、**不能改**。能動的槓桿有兩個，兩個都是會改動產品位元組、
會移動 `pageSha256`、需要一次 generation／連結考量的改動，因此是**擁有者的決定**：

- **候選甲**：v2 session 的 `action()` 對六個純移動改用 `mutation: false`。drain 只
  用 `item.mutation` 做兩件事（跳 stamp、設 dirty），後置條件在 client 端按動作類型
  判、不看這個旗標，所以移動改成非 mutation 看起來是**正確的**修法。**但尚未查有沒有
  別的消費者依賴「移動會跳 content stamp」**（例如某個測試或 stamp 相關邏輯），落地
  前必須查。
- **候選乙**：把 `_checkpointBeforeBoundaryMove` 守衛一從讀 `dirty` 改成讀 revision
  對 authority 的差（`document.revision !== this._authorityRevision`）。範圍更小，
  但一樣是產品位元組。

**這個修法決定應先送對抗性審核（B′ 的 opus／codex 席）再落地**，因為它動的是「使用者
未存的工作」那一塊，正是 subtly wrong 代價最高的地方（這個檔案自己的 header 這麼說）。

## 範圍：出貨殼層 v48 也有這個說謊的 `dirty`（2026-09-28 補充）

`mutation: true` 從 v2 session 一開始就在（出貨殼層 v48，`2d319677` 的
`narrow-editor-v2-session.js:311`），但 v48 **沒有半 C**，所以在 v48 上「方向鍵押檢查點」
不會發生。v48 上剩下的是**推論**（未在 v48 上量）：只移動過游標的乾淨文件，接著做一次
拖曳選取，基底類別的 `_checkpointBeforeSelection` 會因為 `dirty` 為 true 而押一份乾淨
bytes 的檢查點。**v52 的修法要等 cutover 才會到出貨位元組**；出貨頁面仍指向 v8、殼層 v48。

**（2026-09-28 稍晚：已在 v48 上量過，推論成立。）**
`findings/evidence/098/probe_098_v48_arrow_then_drag.py`：v48 殼層從凍結它的 commit
`2d319677` 逐檔取出（13 個檔），探針自己重算服務出去的 bundle 雜湊，**等於 v48 宣告的
`ecfb6866…` 才准量**；`e2-editor.html` 在雜湊網外（094），取同一個 commit 的版本。
同一組三格在目前的 `dist/`（v52，`7a1e8815…`）上當對照。每格 3 次，交錯執行。

| 殼層 | 只拖曳（對照） | **按一次 → 再拖曳** | 打字後拖曳（正向對照） |
| --- | --- | --- | --- |
| v48（出貨） | 無 3/3 | **有（r0） 3/3** | 有（r1） 3/3 |
| v52（已修） | 無 3/3 | 無 3/3 | 有（r1） 3/3 |

所以**今天出貨的產品**上，一份從沒被打過字的文件，只要按過一次方向鍵再拖曳選取，就會
押下一份和開檔 bytes 相同的檢查點、畫面顯示「有（r0）」；那次拖曳多花約 0.6 秒（存檔）。
不是資料遺失。v52 上同一個動作什麼都不押，是 098 修法經由**另一個消費者**（基底類別
`_checkpointBeforeSelection`，不是半 C）也生效的直接量測。

## 最小重現（2026-09-28）

**頁面層級**（`findings/evidence/098/probe_098_a_caret_move_banks_a_checkpoint.py`，
`red-case-v8-2026-09-28.json`）：使用者的路徑——產品的開檔、畫布上點中間一行、CDP 送真的
`ArrowRight`（行中，所以在 v8 上不會碰到 096 的邊界楔住）。兩份 `dist/` 鏡像只差修法那兩行，
服務同一個頁面（pin `4a2710bba1ef07d9`＝v8）。

| 臂 | 乾淨文件第 1–5 按後的 `#s-checkpoint` | 正向對照（打字後再按一次） | 結果 |
| --- | --- | --- | --- |
| 修法前 | 無、有（r0）、有（r0）、有（r0）、有（r0） | 有（r1） | 3/3 押了乾淨文件 |
| 修法後 | 無、無、無、無、無 | 有（r1） | 3/3 沒動 |

修法前第 2 按花 0.61 秒、其他按 0.15 秒——那次多餘的存檔在延遲上看得到。**這支探針看
不到 `dirty`**：只修守衛（候選乙）也會給出相同的標籤；「移動不是修改」這件事只由單元
測試釘住。

**單元層級**：`narrow-editor-v2-session.test.mjs` 的 098 測試（乾淨文件六種移動各按十次；
逐一走過 client 提供的每個動作，`dirty` 必須和引擎回報的 revision 變化一致，並和 client
後置條件的分類一致；Shift＋方向鍵）。修法前紅、修法後綠，自我檢查表見
`findings/evidence/098/unit-selfcheck/`。

## 裁決與修法（2026-09-28）

**裁決**：擁有者今天不在座位，授權 fable 代為決策。fable 裁定**採候選甲**。
**白話理由**：按方向鍵不會改動文件，v2 的 session 卻把它跟打字一樣標成「有修改」。候選甲
只在 v2 自己的檔案裡把六個純移動改成「不算修改」，跟基底類別（`editor-session.js` 的
`moveCharacter` 本來就不算修改）、client 的後置條件（移動必須 revision 不變、`changed:
false`）、引擎自己的分類（posted key、`mutation = false`）三邊對齊，改動只有一行。否決
候選乙：它要新增一個 `_authorityRevision` 欄位、跨 Worker 會像 099 一樣壞掉、`dirty` 與
檢查點標籤照樣說謊，而且移動仍會推進 stamp。

**修法**：`narrow-editor-v2-session.js` 的 `action()` 改用
`{ mutation: !BOUNDARY_CAPABLE_MOVES.has(action) }`；同一個集合的註解寫明它承載同一條引擎
路徑的兩個後果（會楔住、不修改）。099 的修法（守衛比 stamp）靠這一條才成立，兩者同一次
落地為殼層 generation v52（頁面仍指向 v8，不連結、不 cutover）。

**消費者普查**（原「未做」第三項）：content stamp 的讀者全在 `editor-session.js`（重開時
選來源、drain 推進、檢查點略過、存檔記錄 authority stamp）；產品頁面不讀 `dirty`；
`tools/run_e2_c_product_path.py` 的 51 個突變 `find` 字串都仍各自恰好對到一處（codex 核對）。
沒有任何消費者依賴「移動會推進 stamp」。

**審核**：落地前兩席對抗性審核（codex exec、opus）。修法本身兩席都沒打穿；兩席打穿的是
**測試**——共五個「錯的修法但測試全綠」的版本，處置是補測試（099 的直接掃 revision、
Worker 內 review 路徑、存檔失敗後重試、Shift＋方向鍵），五個現在各自至少紅一支。

## 未做

- ~~v48 上「方向鍵＋拖曳押乾淨 bytes」只是推論~~ → 已量（上方「範圍」一節的補充）。

- ~~最小重現未單獨跑過~~ → 已跑（上方「最小重現」）。
- **復原通道互動**：修法後只移動不會押檢查點，所以「只移動就 `hasCheckpoint: true`」這條
  路已經不存在；原本要追的問題隨之消失，沒有另外追蹤。
- ~~沒查候選甲的其他消費者~~ → 已普查（上方「裁決與修法」）。
- **產品路徑回歸網沒有新增檢查**（fable 裁定：缺陷完全在 session 邏輯內、有直接的單元
  覆蓋，閘門不是放它的地方，AGENTS.md §9）；頁面層級的探針留在證據目錄，登錄為工作項。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-09-10 | 登錄（只登錄，不修）。 |
| 2026-09-28 | 最小重現在頁面與單元層級跑過；fable 代擁有者裁定候選甲並與 099 一起修（殼層 v52）；補範圍（出貨殼層 v48 也有 `mutation: true`）、消費者普查、兩席審核結果；「未做」逐項更新。 |
| 2026-09-28 | 出貨殼層 v48 上的推論實測：方向鍵後拖曳押乾淨 bytes 3/3，v52 上 0/3，兩組對照成立（`findings/evidence/098/v48-arrow-then-drag-2026-09-28.json`）。 |
