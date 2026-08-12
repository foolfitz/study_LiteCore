# 037 — 對「含 as-char frame 的段落」派送格式動作會卡死 document handle，而 deadline 沒有救到

> **標題裡的「行內圖片」是錯的名字，2026-08-12 已更正。** 檔名保留（連結太多），
> 但觸發條件不是圖片：`image-variants` fixture 量到**一個完全沒有圖片、只裝文字方塊的
> as-char `draw:frame` 同樣是 `LOK_SELTYPE_COMPLEX`、同樣被擋**。
> 觸發的是 **as-char／char 錨定的 frame**，圖片只是最常見的一種內容。見〈擋法涵蓋範圍〉。

| | |
|---|---|
| **狀態** | **已確認、已定位到單一呼叫、我方已擋並實測關閉**（引擎 `c89f069e…`）／**core 端未修** |
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

## 覆蓋：五個動作與兩個瀏覽器（2026-08-12）

**這批必須在修法之前量。** 擋法一旦上線，那個讀取就不會再被呼叫，
「其餘四個動作會不會卡」從此無法量測——不是懶得補，是補不到。

Chrome，五個封閉動作各一輪，每輪都帶 `PC-PLAIN` 對照：

| 動作 | `PC-PLAIN` | `PC-IMAGE` |
|---|---|---|
| `set-list-none` | 完成 40 ms | **20001 ms 逾時** |
| `set-list-unordered` | 完成 40 ms | **20001 ms 逾時** |
| `set-list-ordered` | 完成 49 ms | **20000 ms 逾時** |
| `set-paragraph-heading` | 完成 50 ms | **20000 ms 逾時** |
| `set-paragraph-body` | 完成 48 ms | **20000 ms 逾時** |

五輪的 callback 串流**停在同一個位置**：段落選好（`TEXT_SELECTION` 寬 4380）之後、還原之前。

**`set-paragraph-heading` 那一輪順便回答了一個產品問題**：串流裡
`.uno:StyleApply` 的 result 是 `success: true`，游標矩形高度由 275 變成 413
——**樣式真的套上去了，然後引擎才死在驗證那一步**。所以這不是「動作沒發生」，
是「動作發生了、驗證卡死、復原手段（重啟 worker）把它丟掉」。
這正是路線 C 的失敗碼一律 `MUTATION_OUTCOME_UNKNOWN` 的理由，
只是這裡連那個碼都送不出來。

**Firefox 153.0.1 同一個形狀**：`PC-PLAIN` 完成 38 ms、`PC-IMAGE` 20005 ms 逾時，
串流最後六筆與 Chrome 逐筆相同，活性梯也相同（worker JS alive／wasm 主執行緒 alive／
引擎逾時）。**不是瀏覽器特有的。**

## 沒有做的事（誠實界線）

- **`getTextSelection` 裡面卡在 core 的哪一段，沒有量到。** 現在有的是「這個呼叫不返回」，
  不是堆疊。要拿到堆疊得有自己的診斷 build（**絕不能改出貨的 `e2-format-discovery`**，
  否則 A3／A4／A5 又要重掃一輪）。**沒有它也還是可以修**——見下一節。
- **原生重放的界線仍然成立**：它等的是「任何一個 UNO command result」而不是比對命令名稱，
  而且用輪詢加 sleep 推進、不在引擎的主迴圈裡跑，**所以它證明的是「這一串序列在 LOK 層做得完」**。
  現在有了 callback 串流，這一點的地位從「範圍縮小」變成「原生對照」：
  **同一個呼叫在原生 1 ms 回來，在 WASM 不回來。**
- **原生只重放了 `.uno:RemoveBullets`**，其餘四個原生沒跑（WASM 側五個都跑了，見上一節）。
- **沒查上游重複單。**
- **`getTextSelection` 的逾時上限沒量**：所有觀察都停在用戶端的 20 秒／30 秒逾時，
  沒有人讓它跑一小時看會不會回來。**「不返回」的證據上限是 86 秒。**
- **沒有量「圖片有多大才會卡」**：fixture 裡是一張手寫的 1×1 PNG，
  所以卡死跟資料量無關，但也還沒試過別種圖片來源（連結圖、SVG、metafile）。

## 已擋並實測關閉（2026-08-12，引擎 `c89f069e7c43e78e630e4f7d62ba5d016c7aaf434d9f4abf5a0e009e931f9d0f`）

擋法就是一個 `if`：讀取那一步先問 selection type，只有 `LOK_SELTYPE_TEXT` 才呼叫
`getTextSelection(…, "text/html", …)`。**這條路可行的唯一理由是型別查詢在會卡死的那個選取上
量過是安全的**（1 ms，2/2）——如果連問型別都會卡，就沒有東西可以問。

拒絕在 `finishFormatBarrierAfterRestore()` 判，而且**排在所有 readback 形狀之前**：
擋下來的時候根本沒有 readback，`parsed` 是 false、每個計數都是 0，排在後面會被判成
「文件不是你要的狀態」——那是一個沒有看過文件的 build 對文件下的結論。
擋法**只跳過讀取**，還原照跑，所以呼叫端不會拿到一個自己沒做的選取。

**同一列，修前修後：**

| | 修前（`ee185b3d`） | 修後（`c89f069e`） |
|---|---|---|
| `PC-IMAGE` 動作 | **20001 ms 卡死** | **37 ms 具名拒絕** |
| `failureShape` | 無（barrier 沒回來） | `selection-type-not-readable` |
| `selectionType` | 沒有這個欄位 | `3`，`readable=false` |
| 事後 handle | **不回應**，close 要重啟 worker | **可用** |
| 之後每一列 | 全部逾時 | 照跑 |

**`paragraph-content` 21 種形態全部跑完**（先前這一列會把後面的都拖下水）：19 列 verified、
`pc-footnote` 走 [035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md) 的
`footnote-apparatus-readback`、`pc-image` 走這一單的擋法，**每一列 37–42 ms，21/21 事後 handle 可用**。
`blockTag` 逐列與 035 定案相同（`h2`–`h6`、outline 7/10 讀回 `p`、`pre`、`blockquote`…），
所以擋法沒有動到那一輪的結論。

**A3／A4／A5 重掃並重綁**：44 輪（A3 18／A4 18／A5 8）、18.8 分鐘、
**每一輪跑之前都重新核對 artifact 雜湊**（44/44 同一個），零輪沒留下證據，
`validate_e2_a.py` 發 **A3_PASS／A4_PASS／A5_PASS**，全部 cell covered。

**殺傷範圍是量出來的，不是推論的。** `selectionType` 現在每一次 barrier 都會寫進證據，
於是「這個擋法會拒絕哪些段落」變成任何一次 sweep 都回答得了的問題。
`c89f069e` 上的 428 次 barrier：

| selectionType | readable | 次數 |
|---|---|---|
| 1（TEXT） | true | **426** |
| 3（COMPLEX） | false | **2** |

那 2 次都是 `PC-IMAGE`。**四份被掃的 fixture（含 `table-boundary` 的儲存格段落）
沒有任何一段被擋法碰到。**

**還是要開上游單**：擋的是我方不再呼叫，不是 core 不再卡。

## 擋法涵蓋範圍：把 frame 拆開量（2026-08-12，證據 `wedge-split/`＋`wedge-trace/chrome/image-variants/`）

**擋法的前提是「會卡的形狀恰好就是回報非 TEXT 的那些」，而那個前提原本只有一個樣本。**
一個回報 `TEXT` 卻照樣卡死的形狀會直接穿過擋法——所以新開一份 fixture `image-variants`，
一列一個屬性，先用 `wedge-split`（**只選取、只問型別，永遠不做 html 讀取**）安全地問過一輪，
再真的派送一次。

| 錨點 | 形狀 | selectionType | 派送結果 |
|---|---|---|---|
| `IV-PLAIN` | 沒有 frame（對照） | `text` | 完成 39 ms，526 bytes |
| `IV-ASCHAR` | as-char 內嵌 PNG | **complex** | 拒絕 29 ms |
| `IV-SVG` | as-char 內嵌 SVG | **complex** | 拒絕 30 ms |
| `IV-LINKED` | as-char 連結到 `file:///` 解不出來的檔 | **complex** | 拒絕 29 ms |
| `IV-CHAR` | `text:anchor-type="char"` | **complex** | 拒絕 29 ms |
| **`IV-TEXTBOX`** | **as-char frame，裡面完全沒有圖片** | **complex** | **拒絕 29 ms** |
| `IV-LIST` | 清單項裡的 as-char 圖片 | **complex** | 拒絕 28 ms |
| `IV-TAIL` | frame 後面的純段落（對照） | `text` | 完成 28 ms，528 bytes |
| **`IV-PARAGRAPH`** | **`text:anchor-type="paragraph"`** | **`text`** | **完成 29 ms，524 bytes** |

兩個結論：

1. **觸發的是 frame，不是圖片。** `IV-TEXTBOX` 沒有任何圖片，一樣 COMPLEX、一樣被擋。
   擋法當初是照**型別**設計的而不是照「有沒有圖片」，所以它涵蓋的範圍比推導它的那個樣本更寬
   ——**這次是運氣好，但也正是「照量到的性質設計、不要照故事設計」的理由**。
2. **`IV-PARAGRAPH` 是唯一穿過擋法的形狀，而它不會卡。** 段落錨定的 frame 讀回 `TEXT`，
   html 讀取 29 ms 回傳 524 bytes——**frame 沒有進到那個選取的序列化裡**，所以沒有東西可卡。
   它排在最後跑，就是因為萬一它卡了，前面八列才不會跟著變成「未量測」。

**九種形狀裡沒有任何一種是「回報 TEXT 卻卡死」。** 擋法的前提在目前量得到的範圍內成立。

**界線**：這九種是我想得到的形狀，不是 ODF 允許的全部（沒有量表格內的 frame、
註腳裡的 frame、OLE 物件、圖表、`draw:g` 群組）。**「沒有反例」不等於「不存在反例」。**

## 原本的擋法設計（保留，已實作如上）

拆解實驗順帶量到一件有用的事：**`getSelectionTypeAndText` 在會卡死的那個選取上 1 ms 回傳
`complex`**。所以 barrier 在讀之前先問型別是安全的，於是有一條不需要 core 修好就能擋下卡死的路：

> ReadQueued 那一步先取 selection type，遇到 `LOK_SELTYPE_COMPLEX`（或非 `TEXT`）就
> **不要叫 `getTextSelection("text/html")`**，改走還原＋`MUTATION_OUTCOME_UNKNOWN`
> 具名失敗（形狀比照 035 的 `footnote-apparatus-readback`）。

代價與界線（**都已發生，記在這裡是為了讓下一個同類決定有前例**）：

- 這讓「含行內圖片的段落」變成**具名拒絕**，動作已經派送出去、文件可能已經改了
  ——跟註腳那一刀同一個形狀，錯誤訊息也照那個樣子寫了。
- **重編了引擎**，A3／A4／A5 三個判定全部解綁並重掃一輪（[036](036-the-shipped-wasm-hash-is-not-a-function-of-the-source.md)）：
  44 輪、18.8 分鐘，比事前估的便宜很多。
- **擋的是我方不再呼叫，不是 core 不再卡**。上游那一單還是要開。

## 相關

- [034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md)——deadline 就是那一輪加的，這裡是它沒接住的一個 stall。
- [035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)——同一批 M2 量測逼出來的；那一單是 fail closed，這一單是卡死。
- **[012](012-r6-styled-document-close-timeout.md)——同一個內容特徵，另一個入口。** 那一單量到
  `destroy()` 在「`draw:frame` 直接掛在 `text:p` 底下」的文件上不返回，原生正常、WASM 跨瀏覽器重現；
  這一單量到 `getTextSelection("text/html")` 在**含同一種 frame 的選取**上不返回，原生 1 ms。
  這一輪順帶替 012 補上它缺的一塊：`paragraph-content` 是另外寫的 fixture、另外一張手寫 PNG、
  另外兩代引擎，**16/16 都要走 10 秒 close recovery**，而其餘五份 fixture 共 153 輪零次
  ——所以那個軸與 t2 那張圖片的任何屬性都無關。**兩個入口停在同一個內容特徵上，
  比一個入口更能指出是共用的下層**；但這是推論，兩處都沒有堆疊。
  **2026-08-12 再收窄**：`frame-no-image`（全檔零張圖片、只有一個裝文字方塊的 as-char frame）
  在 WASM 一樣 close 逾時走 recovery，而六份完全沒有 `draw:frame` 的 fixture 共 153 輪零次
  ——**012 那一單的觸發條件也是 frame 不是 image**，與這一單在選取型別上量到的完全一致。
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
- **2026-08-12（覆蓋）**：五個封閉動作在 Chrome 各跑一輪、每輪帶對照，**五個全卡、
  串流停在同一個位置**；Firefox 153.0.1 同一形狀。這批刻意排在修法之前——
  擋法上線後那個讀取不會再被呼叫，這些就再也量不到。
  順帶量到 `set-paragraph-heading` 的 `.uno:StyleApply` **成功了才卡**
  （游標矩形 275→413），所以是「改了、驗不了、復原時丟掉」。
- **2026-08-12（我方已擋，實測關閉）**：引擎 `c89f069e…`，讀取前先取 selection type，
  非 `TEXT` 即以 `selection-type-not-readable` 具名拒絕。同一列由 20001 ms 卡死變成
  37 ms 拒絕、事後 handle 可用；`paragraph-content` 21 種形態全部跑完且 blockTag 與 035 定案一致；
  A3／A4／A5 重掃 44 輪全過並重綁。**殺傷範圍改成量的**：`selectionType` 進了每一次 barrier 的證據，
  428 次裡 426 次是 TEXT，被擋的 2 次都是 `PC-IMAGE`。core 端未修，上游單未開。
- **2026-08-12（擋法涵蓋範圍）**：新 fixture `image-variants` 把 frame 拆成九列量。
  **觸發的是 as-char／char 錨定的 frame 而不是圖片**——一個完全沒有圖片的文字方塊 frame
  同樣 COMPLEX、同樣被擋；標題因此更正（檔名保留）。段落錨定的 frame 讀回 `TEXT`、
  html 讀取 29 ms 正常回傳，是唯一穿過擋法的形狀而它不會卡。**九種形狀裡沒有
  「回報 TEXT 卻卡死」的**。過程中我自己寫壞了 fixture：`IV-LINKED` 原本用相對路徑
  ＋`xlink:show="embed"` 指向不在包裡的檔，**LibreOffice 直接拒收整份文件**，
  而 WASM 那邊看起來像「open 逾時 180 秒」。用系統 soffice 0.5 秒就分辨出「我的檔壞了」
  與「core 卡住」；已加上不需要 LibreOffice 也能查的 gate（見 `validate_e1_corpus.py`）。
- **2026-08-12（順帶）**：比較各 fixture 的 close 時間時發現
  [012](012-r6-styled-document-close-timeout.md) 在 `paragraph-content` 上 16/16 重現，
  且擋法上線後仍然重現——**那是另一個缺陷，不是這一單的餘波**（擋法生效那一輪，
  引擎在 close 之前是活的、save 也成功了）。
