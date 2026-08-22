# 071 — 重做把 session 卡死，因為沒有人在聽它的完成回覆

| | |
|---|---|
| **狀態** | **已修**（2026-08-22 同日量到、同日修） |
| **Bugzilla** | —（**不是上游**：worker 少一個 case） |
| **發現日** | 2026-08-22，ABI 4 連結後**第一次**跑產品路徑回歸網 |
| **嚴重度** | **高**——它不是「功能沒作用」，是**功能把 session 弄壞**：按下重做之後，那個 session 再也不能存檔 |
| **可重現** | 100%（回歸網第一次跑就抓到） |
| **是否上游** | **否** |

## 機制

引擎從 redo 被加進來的那天起就會送出 `redone` 完成事件
（`src/probe_engine.cpp:3333`，`startUnoMutation(command, "redone", ".uno:Redo", {})`）。

`sdk/sdk-worker.js` 的回覆分派**只有 `case "undone"`**。`redone` 落到 default，
於是：

- 那個請求**永遠不會完成**
- session 停在 busy
- 工具列的 `run()` 沒有 resolve，所以**連一則失敗 toast 都沒有**
- 下一次存檔排在它後面，90 秒後逾時

**一個會把 session 掛住的能力，比一個不存在的能力更糟。**

## 量到的

`findings/evidence/071/product-path-with-the-hang.json`，
`product-redo-button-restores-what-undo-removed`：

```
buttonOffered      {present: true, hidden: false}
markerGoneBeforeRedo  true
revisionBefore     5
revisionAfter      5        ← 沒有推進
markBackInSavedOdt false
toast              ""       ← 連錯誤都沒有
savedBytes         null     ← 後面的存檔逾時
```

同一輪裡 slot 0–3 的存檔都正常（12511／12752／12506 位元組），**只有排在 redo 後面
的第 5 次沒有到**。存檔 shim 沒有數量上限，所以那不是容量問題，是它排在一個永遠不會
完成的請求後面。

## 為什麼在連結之前抓不到

**redo 在這顆 profile 之前沒有任何通往產品的線。** 引擎的 `oxsdk_document_redo` 是
編譯匯出，v3 的 binary 沒有它；contract 也沒有 `redo` 宣告，所以頁面的按鈕是隱藏的、
兩個快捷鍵直接 return。整條路在 v4 宣告它之前是關著的。

這也是為什麼覆蓋稽核當時把 `action:redo` 記成 **waived** 而不是 uncovered——它不是
「沒有人去驅動」，它是**不可達**。那張豁免的理由**綁在 v3 的 manifestSha256 上**，
所以 v4 一出貨它就過期、稽核立刻要求這條路必須被驅動。**這張單就是那次要求的產物。**

## 這是同一種落後的第四層

ABI 4 這次連結一共找出四層各自獨立的「什麼存在」清單，每一層都要單獨更新：

| 層 | 症狀 |
|---|---|
| `narrow-editor-v2-client.js` 的 `APPENDED` | 已在寫的時候更新 |
| `NarrowEditorV2Session` 的 `ACTIONS` | `EDITOR_ACTION_UNSUPPORTED` |
| 頁面的 `editorAction()` 標籤查詢 | TypeError，按鍵被吃掉、什麼都沒派送 |
| **worker 的回覆分派** | **本張單：session 卡死** |

前三層都會**吵**（錯誤、toast、例外）。第四層**安靜**，而且它壞的東西最多。

## 修法

`sdk/sdk-worker.js` 的 `case "undone":` 旁邊加一個 `case "redone":`——它們回同一個
形狀 `{ revision }`。

**代價要寫清楚**：`sdk-worker.js` 是 profile 綁的五個身分之一，所以這一改動了
`workerSha256` 與 `manifestSha256`。**沒有重新連結**——builder 只是複製位元組，wasm
一個位元都沒動（`f923cfa5aba30749` 前後相同），而 Makefile 的 `refuse_unasked_relink`
守在 `probe.js` 那個 target 上，它本來就是最新的。

兩份 v4 封存都留著：`…-worker-bc64be22`（連結當下的樣子，**這張單講的就是那顆
artifact 的缺陷**）與 `…-worker-e6ee92ca`（修法後、這一輪量測用的）。目錄名帶 worker
雜湊而不只是 wasm 雜湊，理由正是這種情況。

## 修法後重跑（`product-path-after-the-fix.json`）

`ok: True`，redo 那格 **PASS**：

```
revisionBefore     5
revisionAfter      6
markBackInSavedOdt true
witnessesKept      甲一 乙二 丙三 E1-LC-END   ← 四個全在,所以它沒有多重播
savedBytes         12749
```

**先前那兩格確實有一格是被污染的**：`notice-action-recovers-the-session` 從 FAIL 回到
NOT_ESTABLISHED，也就是它在 v3 時的狀態——它排在 redo 後面，而卡住的 session 是它的
上游。

**另一格不是**：`recovery-returns-what-the-product-promised` 仍然 NOT_ESTABLISHED
（v3 是 PASS），成因獨立，見 [finding 072](072-a-correct-caret-moved-the-harness-aim.md)。
