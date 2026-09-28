# 099 — 半 C 的省錢守衛拿 revision 當內容的替身，於是會漏存檢查點（跨 Worker 與 Worker 內各一種）

**狀態**：**已修**（2026-09-28，殼層 generation v52，與 098 同一個改動）。原始碼確認
＋單元層級實測（產品 session 程式碼＋測試檔自己的 fixture 引擎）。**瀏覽器層級未重現**
（見未做）。
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

- **瀏覽器層級未重現。**需要連續兩次誘發死亡再加上 revision 巧合（跨 Worker），或一個
  可控的 review 路徑誘因（Worker 內）；目前只有單元層級。fixture 的「開檔 revision 歸零」
  與「review 路徑 revision 不動」都與引擎原始碼一致（第 1、3 節），但不是從引擎量來的。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-09-28 | 初稿（跨 Worker 一種、單格測試）。 |
| 2026-09-28 | 審核後改寫：加入 Worker 內的 review 路徑（opus 指出、原始碼確認）；更正初稿「同一個 Worker 內成立」的錯誤；實測改為三支測試＋自我檢查表；登錄裁決與修法。 |
