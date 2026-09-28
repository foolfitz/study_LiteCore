# 099 — 半 C 的省錢守衛拿 revision 當內容的替身，於是會漏存檢查點（跨 Worker 與 Worker 內各一種）

**狀態**：**已修**（2026-09-28，殼層 generation v52，與 098 同一個改動）。原始碼確認
＋單元層級實測（產品 session 程式碼＋測試檔自己的 fixture 引擎）。**Worker 內那一種已在
瀏覽器層級、真引擎上重現**（2026-09-28，v8 與 v14 各三臂 × 3 次，見「瀏覽器層級」）；
**跨 Worker 那一種仍只有單元層級**（見未做）。
**來源**：處理 098 時讀 `_checkpointBeforeBoundaryMove` 的守衛二掉出來的（跨 Worker 那
一種）；Worker 內那一種是第二席對抗性審核（opus）指出、主 session 讀原始碼確認的。
**引入點**：finding 096 的半 C（殼層 generation v51，2026-09-09）。出貨殼層 v48
（`2d319677`）沒有這段程式碼，所以**不在出貨位元組裡**。

## 宣稱

修法前，半 C 的守衛二在 `_checkpointRevision === document.revision` 時跳過檢查點，
理由是「revision 相等＝內容相等」。**這個等式有兩種破法，兩種都會讓方向鍵跳過一個
使用者的工作需要的檢查點**；接著 session 若死掉，回復會回到**較舊**的 bytes，而通知
寫的是「回到檢查點」。

1. **跨 Worker。**session 回復過一次之後，新 Worker 的 revision 從 0 重數，只要剛好等於
   舊檢查點的 revision，就跳過。
2. **同一個 Worker 內。**格式動作回成「已派送、未驗證」（`recoveryFor` → `review`）時，
   session 把它算成一次修改（推進 stamp、標 dirty），但引擎在那條路上**不推進
   revision**。之後的方向鍵看到 revision 相等，就跳過。

## 原始碼鏈（逐段可核）

1. **引擎每次開檔都把 revision 歸零。**`src/probe_engine.cpp:2886`（`open` 之後
   `gState.revision = 0`；`closeDocument` 在 :2441 也歸零）。基底類別自己的註解也這樣寫
   （`editor-shell/editor-session.js:117-120`）。
2. **檢查點撐過回復。**`restart()`／`_openFresh()` 不清 `_checkpointBytes`、
   `_checkpointRevision`、`hasCheckpoint`（只有 `save()` 的 finalize 在 :572-575 清）。
   這是對的——檢查點本來就是要撐過回復用的。
3. **格式屏障失敗時引擎不推進 revision。**`completeFormatBarrier`
   （`probe_engine.cpp:1543-1546`）呼叫 `advanceRevision()`；`failFormatBarrier`
   （:1579 起）**沒有**。v2 session 對 `review` 處置把錯誤包成結果交給 drain
   （`narrow-editor-v2-session.js` 的 `action()`，`DISPATCHED_UNVERIFIED`），drain 照
   `mutation: true` 推進 stamp、設 dirty（`editor-session.js:304-311`），revision 不動。
4. **守衛二比的是 revision。**修法前的
   `editor-shell-v2/narrow-editor-v2-session.js:334-338`：
   `if (hasCheckpoint && this._checkpointRevision === document.revision) return;`
5. **那段註解的宣稱因此為假，兩種情況都假。**修法前同檔 :322：「The guard can only
   ever cause an EXTRA save, never a missed one」。（本檔初稿寫「在同一個 Worker 內成立」，
   **那句錯了**——第 3 節的 review 路徑就在同一個 Worker 內。2026-09-28 更正。）

## 實測（單元層級）

`wasm_sdk_probe/editor-shell-v2/tests/narrow-editor-v2-session.test.mjs` 的三支 099 測試，
加上自我檢查表（`findings/evidence/098/unit-selfcheck/selfcheck-2026-09-28.json`，
每個變體＝修法前的檔案套上精確文字替換，配上現行測試檔）：

| 測試 | 內容 | 修法前 | 修法後 |
| --- | --- | --- | --- |
| 跨 Worker 格子 | 第一代 1–3 次編輯押檢查點 → 死 → 回復 → 1–5 次編輯 → 方向鍵必須押、緊接的第二按不得押 → 再死 → 必須從第二份重開 | **紅** | 綠 |
| 直接掃 revision | 檢查點押在 r20，把 `document.revision` 設成 0–40 逐一問守衛：內容變了必須押、沒變不得押 | **紅** | 綠 |
| Worker 內 review 路徑 | 押檢查點 → 列表動作回 `review`（revision 不動）→ 方向鍵必須押 → 死 → 必須從第二份重開 | **紅** | 綠 |

**判準的洞是審核打出來的，不是我找到的**：初版只有一格（兩次編輯、回復、兩次編輯），
codex 造出 `|| _checkpointRevision === document.revision + 1` 仍然全綠；改成格子後，
opus 又造出 `+ 3`（格子只涵蓋偏移 −4..+2）與「只在第一代比 revision」兩個仍然全綠的
錯版本。**直接掃 revision 那一支**才把「守衛不讀 revision」釘住；四個錯版本現在各自
至少紅一支（自我檢查表 V1–V4 與 codex 那一列）。

## 瀏覽器層級（2026-09-28，Worker 內那一種）

`findings/evidence/099/probe_099_within_worker_review_path.py`，證據與判讀在
`findings/evidence/099/README.md`。全部走產品自己的控制項（檔案輸入、畫布、插入欄位、
CDP 真按鍵、工具列、復原通知、存檔按鈕）；判準在第一次跑之前寫進探針的 docstring。

**步驟**：`multi-paragraph.odt` 第 2 行尾打字（r1）→ 分段（r2，游標在新的空段落）→
←（半 C 押 有（r2））→ →（回到空段落）→ 按「• 項目符號」（046 殘留的那一格，走 review
路徑）→ **←（受測的那一按）**→ 從外部讓文件 worker 丟一個未捕捉錯誤 → 按產品的
「回到檢查點」→ 用產品的存檔按鈕存出來讀 `content.xml`。

**三臂**只差 session 檔裡兩段精確文字：`prefix`（兩半都退回＝v51）、`a-only`（只有 098
那半，守衛仍比 revision）、`landed`（樹上的檔案，逐位元相同）。`a-only` 對 `landed` 只差
守衛那一個比較式，所以這一對就是 099 的修法本身。

| profile | prefix | a-only | landed | 項目符號前後的 revision |
| --- | --- | --- | --- | --- |
| `e2-editor-v8`（頁面照 `dist/` 的 pin） | **掉了 3/3** | **掉了 3/3** | **保住 3/3** | 2 → 2，9/9 |
| `e2-editor-v14`（頁面用 `repointed_page` 改指，候選） | **掉了 3/3** | **掉了 3/3** | **保住 3/3** | 2 → 2，9/9 |

**這一輪把什麼從「讀的」變成「量的」**：

1. **review 路徑從產品按鈕走得到**，兩個 profile 都是（toast 都是「無法單獨核對你的段落」
   那句）。
2. **真引擎在 review 路徑上不推進 revision**——原始碼鏈第 3 節原本只是讀出來的；現在
   v8 上 18/18（含第一輪儀器失敗前已走到項目符號的 9 次）、v14 上 9/9。
3. **後果**：修法前，回復回來的文件有打的字、有分段，**沒有那顆項目符號**；修法後三者
   都在。正向對照（打的字與空段落都回來＝還原的是 r2 那份檢查點）18/18 成立。

**第二個獨立見證是延遲**：受測那一按在 `landed` 是 0.46 秒（存了一份檢查點）、在另兩臂
是 0.15 秒（跳過）；每一臂都會押的第 3 步那一按都是 0.61 秒。

**標籤看不出來**：三臂在受測那一按前後，`#s-checkpoint` 都是「有（r2）」——`landed`
新押的那份也是 r2，因為 revision 沒動。**使用者在畫面上分不出項目符號有沒有被保護**，
這就是 099 的樣子。

**這一輪沒有證明的**：「掉了」的兩臂沒有在死前單獨驗證項目符號真的套上去（頁面不畫清單
狀態，而 barrier 驗不到正是 review 路徑本身）；排除「項目符號根本沒套上」靠的是
`landed` 在同一個配方、同一顆引擎上保住了它，而三臂的差別只在派送**之後**才執行的
session 程式碼。

**順帶觀察，未追**：v14 在這一格走的是 multi-block 那句，跟 v8 一樣，不是 083 在
v10 的 a11y core 上量到的「取不到任何內容」。產品路徑在 v14 上自己那一格也記
`multi-block`（09-10 起），所以不是這個 fixture 造成的；是哪一次連結改變了核心的回答，
沒有量。

**儀器**：死亡誘因 `induce_worker_failure` 在同一個 Chrome session 裡換頁之後第二次
叫不到 worker（第一輪 6/6 VOID，機制未隔離），探針改成每次嘗試開新瀏覽器。產品路徑
runner 有兩個呼叫點，目前每輪只觸發一個；若哪天兩個都要用，第二個會讓 check 42 報
FAIL（`B4: null`，runner 寫明的「接受的代價」）——是大聲的紅，不是安靜的綠。

## 觸發條件與嚴重度

**低機率，但後果是真的資料遺失**，而且發生在「保護機制宣稱有保護」的時候。

- **跨 Worker**：先死過一次並回復（v8 上一次邊界方向鍵就夠；v14 有半 A，要靠別的死因，
  例如 Worker 崩潰）；回復後第一次方向鍵剛好落在 revision 等於舊檢查點 revision 的那一刻；
  然後在下一次「編輯＋方向鍵」之前又死一次。在 v8 上，那個被跳過的方向鍵本身就可能是
  邊界按鍵，也就是它自己造成第二次死亡。
- **Worker 內**：押過檢查點之後，一個格式動作回成 `review`（finding 046／083 的形狀：
  派送了、很可能已套用、讀回驗不到），接著按方向鍵，然後死掉。

這正是 096 第 42 道檢查 B4 子句（「回來的東西包含打過的字」）在保護的性質，而那道檢查
每輪只死一次、而且受測那一按之前沒有 review 路徑的動作，所以兩種都碰不到。

## 處置：已修（2026-09-28）

**裁決**：擁有者今天不在座位，授權 fable 代為決策。fable 裁定 099 **與 098 一起修**，
採 C1——守衛二改比 content stamp（`this._checkpointStamp === this._currentContentStamp`）。
**白話理由**：stamp 是整個 session 唯一的內容編號，換 Worker 也不會重數，每次算作修改
都拿新號碼，回復時則恢復成所開那份 bytes 的號碼；所以「號碼相同」才真的等於「內容已經
存過了」。這個比較式只有在 098 修好之後才能當省錢守衛用（否則每按一次方向鍵號碼就變，
按住方向鍵就會每按存一次），所以兩個修法必須同一次落地。否決 C2（另存 generation 欄位
＝新機制，AGENTS.md §4）與 C3（刪掉守衛二，行為相同但失去計數）。

**審核**：兩席對抗性審核都在落地前跑過（codex exec、opus），修法本身兩席都沒打穿；
兩席打穿的都是**測試**，處置見上一節。

## 未做

- ~~瀏覽器層級未重現~~ → **Worker 內那一種已重現**（上方「瀏覽器層級」）：046 殘留的
  空白段落項目符號就是可控的 review 路徑誘因，「review 路徑 revision 不動」已從真引擎量到。
- **跨 Worker 那一種仍只有單元層級。**它需要連續兩次誘發死亡再加上 revision 巧合；
  「開檔 revision 歸零」仍是讀原始碼（第 1 節），沒有從引擎量。以這支探針的做法（每次嘗試
  開新瀏覽器、`induce_worker_failure`）應該做得到——同一次嘗試裡要誘發兩次死亡，而第二次
  會撞上上方記的儀器限制，所以要先解決「同一個瀏覽器第二次誘發」。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-09-28 | 初稿（跨 Worker 一種、單格測試）。 |
| 2026-09-28 | 審核後改寫：加入 Worker 內的 review 路徑（opus 指出、原始碼確認）；更正初稿「同一個 Worker 內成立」的錯誤；實測改為三支測試＋自我檢查表；登錄裁決與修法。 |
| 2026-09-28 | 瀏覽器層級：Worker 內那一種在 v8 與 v14 上各三臂 × 3 次重現（`findings/evidence/099/`）；review 路徑不推進 revision 由真引擎量到；登錄 v14 在這一格走 multi-block 的觀察與死亡誘因每個瀏覽器只能用一次的儀器限制；「未做」更新。 |
