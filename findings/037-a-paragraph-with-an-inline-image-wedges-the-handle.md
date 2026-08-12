# 037 — 對「含行內圖片的段落」派送格式動作會卡死 document handle，而 deadline 沒有救到

| | |
|---|---|
| **狀態** | **已確認並已定位到單一呼叫**（`getTextSelection(…, "text/html", …)`）／**未修** |
| **Bugzilla** | —（尚未查上游；卡住的呼叫是 core 的，barrier 只是唯一的呼叫者） |
| **發現日** | 2026-08-12 |
| **嚴重度** | **嚴重**——不是拒絕而是**卡死**，引擎執行緒之後不再處理任何命令，只有重啟 worker 能救 |
| **可重現** | 2/2（`ee185b3d` 與 `38168306`）；callback 串流 2/2；拆解實驗 2/2 |
| **是否上游** | **是**（呼叫在 core 裡不返回；我方的責任是 barrier 沒有辦法從中脫身） |

## 摘要

對一個**含行內圖片**（`draw:frame` `text:anchor-type="as-char"`）的段落派送封閉格式動作
（實測用 `set-list-none`），barrier 不會回來：

```
editorDiscoveryAction   timed out after 20000 ms   ← 動作
search                  timed out after 30000 ms   ← handle 已經不回應
handleUsableAfter       false
（之後每一列）editorDiscoveryGetState timed out after 30000 ms
```

**引擎的 5 秒 per-stage deadline 沒有讓它以 typed 失敗收場。** 那個 deadline 是
[034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md) 那一輪
從「縱深防禦」升格為**必要配件**加進去的，理由正是「採用 `.uno:SelectText` 會製造出
可達的 stall」。這裡就是一個它沒接住的 stall：動作在 **20001 ms** 死於用戶端逾時，
而不是在 5000 ms 死於 `stage-deadline:*`。**下面〈deadline 為什麼結構上不可能生效〉
一節說明這不是漏接，是那個 deadline 從來就防不到這一類。**

卡住的是 `getTextSelection(gState.document, "text/html", nullptr)`
（`wasm_sdk_probe/src/probe_engine.cpp:3124`），也就是後置條件讀取本身。
**同一段落、同一個選取，原生 26.8 這個呼叫 1 ms 回傳 798 bytes；WASM 這邊不回傳。**

## 更正：文件並沒有關掉（2026-08-12）

初版寫「文件本身還關得掉（`closeMs: 10906`），所以卡死的是**操作**不是整個 worker」。
**這是誤讀，兩個 build 的證據都不支持。** `closeMs` 量的是
`documentHandle.close()` 這個 await 的牆鐘時間，而 SDK 的 close 逾時上限是
`closeRecoveryTimeoutMs = 10000`，逾時之後走 `_recoverTimedOutClose()`＝**重啟 worker**。
兩份 result.json 的 `editorStateEvents` 裡都有 `document-close-recovery-complete`。

所以 10906 ms 的意思是「close 在 10 秒逾時，然後花 0.9 秒重開了一個 worker」，
不是「文件關掉了」。**卡死的範圍是整個引擎執行緒，不是單一操作**，而目前唯一的復原手段
是把 worker 殺掉重開——未存檔的狀態全部丟失。嚴重度因此上調。

（怎麼會看錯：`closeMs` 有值、`closeError` 是 null，看起來就像成功。
恢復事件在另一個陣列裡，而我沒去看。**一個「成功」的欄位不等於那件事成功**。）

## 這一列有什麼不一樣

`PC-IMAGE` 是 M2 的 21 種段落形態裡**唯一 `selectionType` 是 3
（`LOK_SELTYPE_COMPLEX`）的一列**，其餘 20 列都是 1（`LOK_SELTYPE_TEXT`）。
原生 26.8 量到過（`paragraph-content/native-26-8/`），當時只記成一則註記，
因為 barrier 的判定**完全沒有讀 selection type**。

原生那一輪讀得回 markup（798 bytes，`<img …/>` 巢狀在 `<p>` 裡，錨點文字也在），
**所以問題不在序列化器**，而在 wasm 側 barrier 的階段推進。

## 不是這次改動造成的

`ee185b3d`（本次結構深度 parser）與 `38168306`（改動前、A3/A4/A5 現行綁定）
**各跑一次，同一列都在 20001 ms 逾時、同樣沒有 readback**。

這件事本來無法斷定：新 parser 是純字串處理、跑在 readback 之後，理論上造不出 20 秒停頓，
但「理論上」不是證據，而舊 build 從沒在這份 fixture 上跑過。
把 `build/archive/e2-format-discovery-38168306/` 換進 `dist/profiles/`
跑同一份 app、同一批 21 列，再換回來——**這是既存缺陷，只是新 fixture 才讓它被看見**。

證據：`paragraph-content/wasm-ee185b3d/` 與 `paragraph-content/wasm-38168306-control/`，
各自附 `ARTIFACT.sha256`。

## 為什麼 375 次判定派送一次也沒碰到

同 [034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md)／
[035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)
的形狀：A3／A4／A5 的錨點段落全是純文字，**沒有一份既有 fixture 的被派送段落帶行內圖片**。
`r7-t2-styled.odt` 裡有圖片，但它不是任何一輪的派送目標。
覆蓋軸從來沒進過矩陣——這是同一個病第三次以不同的軸出現。

## 它害掉了什麼（方法論代價）

第一次跑這批討論器時 `PC-IMAGE` 排在第 16 列。它卡死之後，**後面五列全部連鎖失敗**
（`pc-break`、`pc-cjk-bold`、`pc-section`、`pc-footnote`、`pc-list-item`），
其中 `pc-footnote` 正是整個 (a′) 裁決所依賴的那一列。

把它移到最後重跑才拿到那 20 列。**測項的順序影響了哪些事實能被觀察到**——
這不是整理癖，是證據完整性：一個會卡死 handle 的案例排在中間，等於讓它後面的每一項
都變成「未量測」而不是「失敗」，而兩者在報告裡長得很像。

## 原生重放：LOK 那一串序列不會卡（2026-08-12，證據 `barrier-replay/native-26-8/`）

引擎的 barrier 證據是**結束時才寫出來**的，所以一個永遠不結束的 barrier 什麼都不寫，
而「卡在哪一階段」正好就是缺的那個欄位。加診斷重編 WASM 可以問到，但**同時會鑄出新
artifact，把剛重綁到 `ee185b3d` 的 A3／A4／A5 判定再解綁一次**——為了一個診斷付
finding 027 的代價。原生重放不綁任何東西。

把 barrier 的階段照順序重放，每階段各自計時與設限，六個錨點一起跑
（**一個到處都慢的階段是序列的性質，只在一個形態上慢才是那個形態的性質**；
沒有其他列可比，「20 秒」就只是一個數字）：

| 錨點 | 動作 result | select result | 選取 callback | 讀取 | bytes | selType | 還原清空 | handle |
|---|---|---|---|---|---|---|---|---|
| PC-PLAIN | 10 | 10 | 0 | 2 | 563 | 1 | 10 | 可用 |
| PC-CJK-BOLD | 10 | 10 | 0 | 1 | 652 | 1 | 10 | 可用 |
| PC-LINK | 10 | 10 | 0 | 1 | 611 | 1 | 10 | 可用 |
| PC-FOOTNOTE | 10 | 10 | 0 | 1 | 987 | 1 | 10 | 可用 |
| **PC-IMAGE** | **10** | **10** | **0** | **1** | **798** | **3** | **10** | **可用** |
| PC-BREAK | 10 | 10 | 0 | 1 | 581 | 1 | 10 | 可用 |

（單位 ms。）**原生完全不卡**：COMPLEX 選取讀得回 798 bytes、還原 10 ms 清空、handle 事後可用。

**所以「LOK 對 COMPLEX 選取做了什麼」不是卡死的原因。** 問題落在 WASM 引擎的階段機器
或它的事件推進，不在命令序列本身。

**這一輪自己抓到一個假訊號。** 第一版用**同一個錨點**再搜一次來測 handle 可用性，
六列裡有五列回報 `handleUsableAfter=false`——**包括純段落的控制組 PC-PLAIN**。
那不是卡死，只是游標已經在唯一命中處之後，同一字串搜不到第二次。改成搜**別的**錨點後
六列全部 `true`。**一個在控制組上也會亮的訊號不是訊號**；如果當初只跑圖片那一列，
那個 false 會被讀成卡死的佐證。

## WASM 側卡在哪：callback 串流（2026-08-12，證據 `wedge-trace/chrome/paragraph-content/`）

上一節說「加診斷重編 WASM 會鑄出新 artifact」。**結果不必重編。** 引擎本來就把
**每一個 LOK callback 在處理之前**當成 `{"type":"lok"}` 事件送出（`onLokCallback`），
只是出貨的 worker 只轉發其中兩個 id、其餘丟掉。把整串轉發出來只需要 worker 副本多兩行，
`probe.wasm` 一個位元組都沒動——`e2-wedge-trace` 這個 profile 的 wasm 雜湊
**就是 `ee185b3d…` 本身**（`ARTIFACT.sha256` 兩行並列可對）。
**一個永遠不返回的 barrier 不會寫自己的證據，但它走過的每一個 callback 都留下了。**

兩輪各 245 筆，**最後六筆完全相同、順序相同**（時間為頁面時鐘 ms）：

| # | callback | payload |
|---|---|---|
| 238 | `UNO_COMMAND_RESULT` | `.uno:RemoveBullets` ← 動作的 result，barrier 進 SelectQueued |
| 239 | `STATE_CHANGED` | `.uno:SelectionMode=0` |
| 240 | `UNO_COMMAND_RESULT` | `.uno:SelectText` |
| 241–242 | `TEXT_SELECTION_START` / `_END` | `1418, 8465` → `5798, 8465` |
| 243 | `TEXT_SELECTION` | `1418, 8465, 4380, 275` ← **段落選起來了** |
| 244 | `INVALIDATE_VISIBLE_CURSOR` | `5798, 8465, 0, 276` |

**然後就沒有了。** 之後那 86 秒（動作逾時 16 秒＋search 30 秒＋save 30 秒＋close 10 秒）
**沒有再收到任何一個 LOK callback**。

對照組 `PC-PLAIN` 走完全相同的六步，然後第七筆是 `TEXT_SELECTION`（空）——**還原把選取清掉**，
barrier 收尾。也就是說：卡點落在「段落已選好」與「還原清空」之間，
而那段區間裡引擎只做三件事：

```cpp
checkFormatBarrierContainment();      // 純算術，讀 cache，不呼叫 LOK
readFormatBarrierPostcondition();     // getTextSelection(…, "text/html", …)
…
postFormatBarrierRestore();           // setTextSelection(RESET, …)
```

**兩件事同時被排除掉了**：不是「barrier 在等一個不會來的 callback」（那樣 deadline 會接到），
也不是 `LOK_SELTYPE_COMPLEX` 讓 core 改走圖形選取——串流裡
`GRAPHIC_SELECTION` 只出現一次而且在前導階段、payload 是 `EMPTY`，
這一列的選取是**文字選取**，鑑別在別的地方。

## 活性梯：卡的是哪一條執行緒（同一批證據，attempt-03 起）

「handle 不回應」沒有說是什麼不回應，而那決定了修法長什麼樣。三段梯子，
依需要用到多少層排序，**每一列都跑**（只在壞掉的那列跑過的檢查，證不了自己會失敗）：

| 梯 | 探法 | `PC-PLAIN` | `PC-IMAGE` |
|---|---|---|---|
| worker JS | 送一個 worker 在 JS 層就拒絕的操作 | alive (0 ms) | **alive (0 ms)** |
| 引擎執行緒 | 真的操作（`getState`，5 秒） | alive (2 ms) | **逾時 (5000 ms)** |
| wasm 主執行緒 | 逾時後 SDK 自動送出的 cancel | 不需要 | **alive (50 ms, status OK)** |

`cancel()` 會取 `gState.mutex`（`probe_engine.cpp:4732`）並且**回來了**。所以：
worker 的 JS 執行緒活著、**wasm 模組從 worker 執行緒仍可呼叫**、**引擎的全域 mutex 沒有被持有**。
唯一不動的是引擎 pthread，而它不動的位置在 `dispatch()` 裡面——不是在等命令。

**一個沒有成立的推論，記在這裡免得以後有人重犯**：動作那筆請求被 cancel 時回
`NOT_CANCELLABLE`，看起來像「它正在執行中」。**不能這樣讀**——`cancel()` 對
`executingRequest` 和 `asynchronousRequests` 回同一個碼，而 barrier 動作一律
`markAsynchronous()`，所以**不管卡不卡都會是這個碼**。它不是證據。

## deadline 為什麼結構上不可能生效

`engineLoop` 只在**命令佇列空著、正要去等**的時候才看 `stageDeadline`：

```cpp
while (gState.commands.empty()) {
  …
  if (formatBarrierActive() && gFormatBarrier.stageDeadlineArmed) { …wait_until(deadline)… }
  …
}
…
dispatch(command);          // ← 卡在這裡的話，上面那個 while 永遠回不去
```

所以那個 5 秒 deadline 防的是**一個停止推進的階段**，防不到**一個不返回的呼叫**。
兩者在證據裡長得一樣（動作沒回來），成因與可修性完全不同。
main-loop 版（`mainLoopDrainCommands`）同理：它也只在佇列空的時候合成逾時步驟，
而且是從 poll callback 進去的——卡住的執行緒根本不會回到 poll。

**這是 034 那一輪的 deadline 的界線，寫進 SPEC 之前它只是一個沒被講出來的假設。**

## 三個候選收斂到一個（證據 `wedge-split/chrome/paragraph-content/`，2/2）

上面把卡點框在三個操作裡，其中 `checkFormatBarrierContainment()` 讀 cache、不碰 LOK
（原始碼可讀出來），剩兩個 LOK 呼叫。**callback 串流分不開這兩個**——它們進去之前都不發訊號。
所以繞開 barrier，用產品既有的 `editorDiscoverySelect` 把**同一個選取**擺好，再一個一個單獨叫：

| 步驟 | 呼叫 | `PC-PLAIN`（對照） | `PC-IMAGE` |
|---|---|---|---|
| drag-select | `postMouseEvent` ×3 | 38 ms | 38 ms |
| 選取範圍 | — | 1418 → 4390 @ y1418 | **1418 → 5798 @ y8465** |
| get-selection-text | `getSelectionTypeAndText("text/plain…")` | 2 ms, type `text` | **1 ms, type `complex`** |
| selection-reset | `setTextSelection(RESET, …)` | 17 ms | **17 ms** |

**滑鼠拖曳做出來的選取與卡死那一輪 barrier 的選取端點完全一致**（`1418 → 5798 @ y8465`，
對上串流第 243 筆的 `1418, 8465, 4380, 275`），型別是 `complex`＝原生量到的
`LOK_SELTYPE_COMPLEX`。也就是說輸入狀態相同。

**在這個狀態上，`setTextSelection(RESET, …)` 17 ms 回來，`getSelectionTypeAndText` 1 ms 回來。**
兩個都不卡，而視窗裡只剩一個呼叫：

```cpp
// probe_engine.cpp:3124
char *html = gState.document->pClass->getTextSelection(gState.document, "text/html", nullptr);
```

`grep` 得出整份引擎只有兩處 `getTextSelection(`，另一處在
`LIBREOFFICEKIT_DOCUMENT_HAS(getSelectionTypeAndText)` 為假時才走，這個 build 走不到。
**所以是消去法，但消去的範圍是原始碼枚舉出來的，不是搜尋碰運氣。**

值得記一筆的界線：`text/plain` 那條路對 COMPLEX 選取**不會真的去序列化**
（core 把「沒有 plain flavor」摺成 `LOK_SELTYPE_NONE`／空字串，見 `readSelection()` 的註解），
所以上表證明的是「型別查詢與還原不卡」，**不是「transferable 那一整套都不卡」**。
真正做圖片序列化工作的只有 `text/html` 那一次，而原生那一次的產物是
`<img src="data:image/png;base64,…">`——**圖片是就地 base64 進去的**，
所以 html 這條路會叫到圖形匯出，plain 那條不會。差別落在那裡。

## 沒有做的事（誠實界線）

- **`getTextSelection` 裡面卡在 core 的哪一段，沒有量到。** 現在有的是「這個呼叫不返回」，
  不是堆疊。要拿到堆疊得有自己的診斷 build（**絕不能改出貨的 `e2-format-discovery`**，
  否則 A3／A4／A5 又要重掃一輪）。**沒有它也還是可以修**——見下一節。
- **原生重放的界線仍然成立**：它等的是「任何一個 UNO command result」而不是比對命令名稱，
  而且用輪詢加 sleep 推進、不在引擎的主迴圈裡跑，**所以它證明的是「這一串序列在 LOK 層做得完」**。
  現在有了 callback 串流，這一點的地位從「範圍縮小」變成「原生對照」：
  **同一個呼叫在原生 1 ms 回來，在 WASM 不回來。**
- **原生只重放了 `.uno:RemoveBullets`**，其餘四個封閉動作沒跑。不過現在知道卡點在讀取那一步，
  而五個動作共用同一段讀取，所以預期五個都會卡——**這是推論，沒有量。**
- **只量了 Chrome。** Firefox 沒跑。
- **沒查上游重複單。**
- **沒有量「圖片有多大才會卡」**：fixture 裡是一張手寫的 1×1 PNG，
  所以卡死跟資料量無關，但也還沒試過別種圖片來源（連結圖、SVG、metafile）。

## 可以怎麼修（尚未實作）

拆解實驗順帶量到一件有用的事：**`getSelectionTypeAndText` 在會卡死的那個選取上 1 ms 回傳
`complex`**。所以 barrier 在讀之前先問型別是安全的，於是有一條不需要 core 修好就能擋下卡死的路：

> ReadQueued 那一步先取 selection type，遇到 `LOK_SELTYPE_COMPLEX`（或非 `TEXT`）就
> **不要叫 `getTextSelection("text/html")`**，改走還原＋`MUTATION_OUTCOME_UNKNOWN`
> 具名失敗（形狀比照 035 的 `footnote-apparatus-readback`）。

代價與界線都要先講清楚：

- 這會讓「含行內圖片的段落」變成**具名拒絕**，動作已經派送出去、文件可能已經改了
  ——跟註腳那一刀同一個形狀，錯誤訊息也要照那個樣子寫。
- **要重編引擎**，於是 A3／A4／A5 三個判定全部解綁、要重掃一輪（[036](036-the-shipped-wasm-hash-is-not-a-function-of-the-source.md)）。
- **擋的是我方不再呼叫，不是 core 不再卡**。上游那一單還是要開。

## 相關

- [034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md)——deadline 就是那一輪加的，這裡是它沒接住的一個 stall。
- [035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)——同一批 M2 量測逼出來的；那一單是 fail closed，這一單是卡死。
- [016](016-lok-forward-delete-completion-gap.md)、[018](018-lok-line-navigation-completion-nondeterministic.md)——同屬「completion 訊號不來」這一族。**這一單不是**：它不是訊號不來，是呼叫不返回。
- [027](027-verdicts-are-bound-to-an-artifact-not-to-a-source-tree.md)／[036](036-the-shipped-wasm-hash-is-not-a-function-of-the-source.md)——為什麼這一輪的診斷刻意做成「不重編」。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md)

## 修訂紀錄

- **2026-08-12（初版）**：兩個 build 各一次重現、原生重放六個錨點，
  結論「不是 LOK 對 COMPLEX 選取做了什麼」，卡點範圍框在 WASM 引擎的階段機器。
- **2026-08-12（定位＋一處更正）**：
  1. **更正**：「文件本身還關得掉」是誤讀。`closeMs` 是 close 逾時 10 秒後
     **重啟 worker** 的時間，兩個 build 的證據裡都有 `document-close-recovery-complete`。
     卡死範圍是整個引擎執行緒，嚴重度上調。
  2. **不重編就拿到了現場**：引擎本來就送出每一個 LOK callback，只是 worker 丟掉了；
     `e2-wedge-trace` 用**同一份 wasm**（雜湊相同）加兩行轉發。串流 2/2 停在同一筆。
  3. **活性梯**證明 worker JS、wasm 主執行緒、`gState.mutex` 都還活著，只有引擎 pthread
     卡在 `dispatch()` 裡；順帶記下 `NOT_CANCELLABLE` **不能**當成「正在執行中」的證據。
  4. **deadline 結構上防不到這一類**：`engineLoop` 只在佇列空著時看 deadline。
  5. **拆解實驗**把三個候選收斂到 `getTextSelection(…, "text/html", …)`：同一個選取上
     `setTextSelection(RESET)` 17 ms、`getSelectionTypeAndText` 1 ms，2/2。
  6. 補上一條**不需要 core 先修**的擋法，以及它的代價（重編＝重掃）。
