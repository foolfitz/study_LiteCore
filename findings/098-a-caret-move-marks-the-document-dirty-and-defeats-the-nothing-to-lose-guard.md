# 098 — 只移動游標就把文件標成 dirty，於是「沒有東西可失去」的守衛失效

**狀態**：原始碼確認 ＋ 已由 T9 的 shakedown 觀測到（2026-09-10）。
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

**這一格是原始碼推的預測，不是這一張獨立跑出來的觀測。**已觀測到的是 T9 的
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

## 處置：**只登錄，不修，不建機制**（AGENTS.md §4）

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

## 未做

- **最小重現未單獨跑過**：乾淨文件、第二次方向鍵、斷言 `dirty` 與 `hasCheckpoint`
  被翻。目前只有 T9 的多按 walk 觀測。**這一節是「沒獨立量」，不是「量了沒有」。**
- **復原通道互動未完整追蹤**：只移動就 `hasCheckpoint: true` 之後，若 session 卡死
  （v8 的 096）或 worker 崩潰，復原通知會說「回到檢查點」並救回等於 authority 的
  bytes。無害但語意可疑，這條路沒有走完。
- **沒查候選甲的其他消費者**：`mutation: true` 除了設 dirty／跳 stamp 之外有沒有別的
  依賴，只讀了 drain（:304-309），沒有普查全樹。
