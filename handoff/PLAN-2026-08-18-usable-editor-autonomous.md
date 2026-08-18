# 計畫 2026-08-18 — 「能用的編輯器」這條線上，我一個人做得完的五件事

依據 [`HANDOFF-2026-08-17-usable-editor.md`](HANDOFF-2026-08-17-usable-editor.md)。
**只收自主可執行的項目**：不需要一次連結、不需要重編 core、不需要真人操作員。
連結的時機是使用者的決定（目前「等一等」），不排進來。

> **本篇第一版被 codex 對抗性審查退回過一次**（2026-08-18）。退回的理由與退回之後
> 改了什麼，寫在 [§9](#9-第一版被退回的地方)。其中一條不是「計畫寫得不好」，
> 是**一個已經寫進 finding 059 和佇列項的候選判準，讀原始碼就知道它不可能成立**
> ——見 T1.0。

## 0. 這一輪要往哪裡走

驗收清單（`e2/usable-editor-checklist.json`）自己寫了「做完」的定義：

> **清單綠 ＋ 每個 `done` 的檢查綠 ＋ 沒有 `blocked`。**

今天是 7 done／2 partial／3 unverified／1 missing／3 blocked。三個 `blocked` 全部
要連結，所以**這一輪不可能把清單做綠**——這一輪的目標是另一件事：

| | |
|---|---|
| **把不需要連結的格子全部關掉** | 3 個 `unverified` ＋ 1 個 `missing` |
| **把擋著連結的那一格量到可以決定** | 059 的判準，以及它在 WASM 上沒量過的那一半 |
| **讓「清單綠」這句話有意義** | 清單今天不會因為 `done` 的檢查變紅而變紅——那正是 044 的形狀 |

做完之後，`blocked` 的三格會是**唯一**剩下的東西，而它們全部在同一次連結裡。
那時候「要不要連結」才是一個乾淨的問題。

## 1. 不排進來的，以及為什麼

| | 為什麼不排 |
|---|---|
| relink | 使用者的決定，不是我的 |
| core 重編（056／057） | a11y 已移到長期目標；**不得拿它當推力** |
| D0 | 一跑，殼層再動就得換矩陣；這一輪殼層很可能要動（T2b） |
| 上游送出 | 2026-08-15 起擱置 |
| D5 人工輪 | 要真人；剪下的「文字真的被移除」那一半屬於這裡 |
| `queue-engine-must-report-core-lacks-accessibility` | 引擎原始碼一行，但它是 a11y 線；下一次連結搭便車，不值得現在動 |

## 2. 五件事，以及順序

| | 做什麼 | 為什麼是現在 | 需要 |
|---|---|---|---|
| **T0** | 清單與回歸網對帳的守衛 | 便宜，而且它是後面四件事的量尺 | — |
| **T1** | 059 的判準 | **擋著連結**；而且**兩個候選已經死掉一個** | 讀原始碼 ＋ native |
| **T2** | 059 在 **WASM** 上到底做到了沒有 | 交接自己標「明確沒量而且重要」；答案會改變**今天**該告訴使用者什麼 | browser |
| **T3** | 三個 `unverified` 接進回歸網 | 這棵樹被「按鈕在、沒人按過」咬過五次 | browser |
| **T4** | 真實長度文件：先量牆在哪 | `missing` 那一格；而且牆的位置**隨 devicePixelRatio 變**，harness 站在最寬鬆的那一格 | browser |

T1 的第一步是讀原始碼、第二步是 native；T2／T3／T4 是 browser，都要改
`tools/run_e2_c_product_path.py`，**必須依序做**（見 §8 的索引位移陷阱）。

---

## T0 — 清單今天不會紅，而它應該會

### 問題

`check_usable_editor.py` 只解析「參照指到的東西存不存在」。它**不看那個檢查是不是
綠的**。所以一格標 `done`、它的檢查在回歸網裡紅著，清單仍然全綠——這正是 044
（判定綁定的 summary 還說「沒有判定」）的形狀，只是換了一個檔案。

### 做法

`check_usable_editor.py` 加 `--report <product-path 的 JSON>`，四條規則：

| 情形 | 判定 |
|---|---|
| `done`／`partial` 的列**一個 `check` 都沒有**（只有 finding／queue） | 紅——狀態字彙自己說 done ＝「有一格會失敗的檢查在跑」 |
| `done`／`partial` 的 `check` 在報告裡不存在，或是紅的 | 紅 |
| `unverified`／`blocked`／`missing` 的 `check` 在報告裡**是綠的** | 紅，訊息是「這一格的狀態過期了」 |
| 報告本身不是一次**乾淨的基線跑** | 紅，而且是先判的（見下） |

**「乾淨的基線跑」是這一項的核心**，不是細節：報告要帶 `mutation: none`、
**沒有** T2 的 shim、而且它跑的是**現在這一代殼層**。今天的報告只記
`browser`／`fixture`／`shims`，沒有記殼層 digest，所以一份 v15 的舊報告、
或一份開著 shim 的報告，都可以被端出來當 v16 的驗收證據。
→ **runner 要在報告裡寫下殼層 bundle 的 digest 與 artifact 雜湊**，
T0 拿它跟今天的綁定比。

後兩條規則是重點：`KNOWN_RED` 的 runner 已經會在紅檢查變綠時主動說宣告過期，
**清單要有同一個性質**——一份只會往壞的方向紅的清單，會把「已經修好了」變成
沒有人會發現的事。

### `KNOWN_RED` 與清單狀態的對應（第一版在這裡自相矛盾）

第一版寫「報告裡有 `KNOWN_RED` 而清單那一格不是 `blocked` → 紅」，而 T4 又打算
把長文件那一格宣告成 `KNOWN_RED ＋ partial`。兩條合不起來。正確的規則是**綁
finding，不綁狀態字**：

> 一個 `KNOWN_RED` 的檢查是可接受的，**若且唯若**清單上引用它的那一列，
> `evidence` 裡有**同一個 finding 編號**，而且那一列的狀態**不是 `done`**。

這樣「紅著是因為某個具名缺陷」是說得出來的，而「紅著卻宣稱做完了」說不出來。

### 驗收

`--self-test` 至少六組合成資料，**每一條規則各紅一次**，另外兩組是第一版漏掉的：
一份把某列改成 `done` 但拿掉所有 `check` 的清單、一份 shim 開著的報告。
不加 `--report` 時行為與今天一模一樣（既有呼叫端不變）。

---

## T1 — 059 的判準：**一個候選已經死了，而且是讀出來的**

### T1.0 先更正兩份文件（這一步不需要量測，而且要先做）

finding 059 與佇列項 `queue-inline-format-argument-is-rejected-by-core` 都寫著
**「`wasModified` 是明顯的候選」**。

**那是錯的，而且核心的原始碼直接說死了：**

```
desktop/source/lib/init.cxx:5517-5518
    new DispatchResultListener(pCommand, ...,
                               pDocSh && pDocSh->IsModified()));
```

`wasModified` 是 `DispatchResultListener` **建構時**捕捉的 `IsModified()`，
在 `dispatchCommand()` 被呼叫**之前**（`init.cxx:5073` 的成員宣告自己寫著
「the document was modified **before** saving」），而 `dispatchFinished()`
只是把那個值原樣寫回酬載（`:5098`）。

⇒ **`wasModified` 說的是「這個命令跑之前，文件是不是已經髒了」**，
不是「這個命令改了東西沒有」。一份先前已被編輯過的文件，會讓一個什麼都沒做的
命令回報 `true`；一份剛存過的乾淨文件，會讓一個成功的命令回報 `false`。

原生那一輪觀察到的 `wasModified: true`，**完全可以只是因為探針在每一臂之前都先
打了一個標記**（`f059_native_inline_format_argument.cpp:112`／`:156`：共用一份
文件、每臂先打字、全部跑完才存檔）。

所以 T1 的內容變了：**不是「量兩個候選」，是「一個候選已經出局，量剩下的那個」。**

- finding 059 原地修訂 ＋ 修訂紀錄；「候選」那一段改寫。
- 佇列項的 `note` 同步（**這是刻意的改動，要出現在 diff 裡**）。
- 這一步的產出是**取消一次量測**，不是多做一次。

### T1.1 PREDICTION.md（英文，證據命名空間）

`findings/evidence/059/native/predicate/PREDICTION.md`，**在探針改出來之前**。
剩下的候選只有一個：**barrier 的 readback**。要預測的是它在**四個 slot 上各自**
成不成立——四個是不同的 slot、不同的酬載名稱，而且 Underline／Strikethrough
沒有 Bold／Italic 那一套 state cache（`probe_engine.cpp:4296`、`:4308`）。

| | 預測 | 不成立的話代表 |
|---|---|---|
| P1 | 收合游標、純文字段落上，readback 讀得回 **bold** 的開關狀態 | 這個候選在最基本的一格上就不可用 |
| P2 | italic 同上 | — |
| P3 | **underline 同上** | 判準只覆蓋兩個 slot，另外兩個要別的做法 |
| P4 | **strikethrough 同上** | 同上 |
| P5 | 有一個**確實被拒絕**的臂，readback 顯示狀態**沒有**改變 | 判準分不開成功與失敗，等於換一個等價的缺陷 |

**四個 slot 各自要預測、各自要量。** 只量 bold 然後把結論套到四個上，正是這一輪
要防的形狀。

### T1.2 探針

擴充 `tools/f059_native_inline_format_argument.cpp`（**不是**新寫一支：既有四臂是
既有證據，新臂加在後面，一輪一筆紀錄、拒絕覆蓋），加上：

- **四個 slot 各一組臂**，每臂放游標、dispatch、讀 readback、打標記、**各自存檔**。
- **拒絕臂必須是核心「認得但當下不能跑」的命令**。
  **不可以用不存在的 slot**：`comphelper::dispatchCommand()` 在
  `queryDispatch()` 回 null 時直接 `return false`（`dispatchcommand.cxx:48-50`），
  **`LOK_CALLBACK_UNO_COMMAND_RESULT` 根本不會發**——那一臂什麼都沒量到。
- **每一臂都要證明自己收到一次新的回呼**：記回呼的序號或 `startUnixTimeMics`，
  分析器**必須拒絕**沒有新回呼的臂。沒有這一條，一個「欄位缺席時給預設值」的
  分析器會讓拒絕臂假性通過。
- **判準讀存檔**：不是 grep `fo:font-weight`——語料裡本來就有沒用到的 `E1Bold`
  宣告與粗體的標題樣式（`create_e1_corpus.py:36`／`:48`），grep 會在標記其實是
  normal 的時候通過。要**解析標記那一段文字實際掛著的 style，再讀那個 style 的
  屬性**。

配套 `tools/run_f059_native.sh`（照 `run_f045_native.sh` 的骨架），離線判讀
`tools/analyze_f059_predicate.py` 自帶 self-test。

### T1.3 決定與寫入

- readback 在四個 slot 上都成立 → 引擎改判準，佇列項從 `absent` 翻成 `present`。
- 只在部分 slot 上成立，或一個都不成立 → **這是要問使用者的岔路**（§7 J2）。

**佇列項的驗收不可以只是「原始碼裡出現 `inlineFormatArgumentResolved` 這個字」**
——一個死函式、一段註解、一個沒被呼叫的宣告都能讓它翻面而引擎照樣壞著，甚至
編不過。佇列檢查照舊（它的語意是「翻面要出現在 diff 裡」），但**這一項的驗收
另外要求**：那條路徑編得過、而且被一個會失敗的檢查走過。

**動引擎原始碼之前**：`make -n` 對三個 static target 各跑一次，證明沒有任何
artifact 會被重連結（041／042 的教訓）。**`make -n` 不驗證改過的原始碼**，
兩件事分開記。

---

## T2 — WASM 上到底做到了沒有

### 為什麼這件事不能等連結

如果 WASM 上也是「照做了、回報失敗」，那**今天出貨的產品是在一個成功的動作上
叫使用者回滾**。那不是「格式功能不能用」，是「按一下粗體，然後被建議丟掉這段時間
所有的編輯」。嚴重度、finding 的措辭、以及**產品端有沒有事可做**，三件事都會變。

交接寫「產品端沒有可做的事」——那句話對「讓粗體能用」成立，對「不要叫使用者
回滾一個成功的動作」不成立。

### 量不到的原因，以及它在哪一層

四個 inline 格式不是 paragraph action，錯誤上沒有 `formatBarrier` 欄位，所以
`formatFailureDisposition()` 走到最後一條 `unknown-rollback` → `recoveryFor()` 回
`rollback` → `_blockQueueIfDispatched()` 擋佇列 → 打不了字也存不了檔。

**這一整條都在 JS 裡**，而且 `run_e2_c_product_path.py` 已經有現成的
`build_mirror(dist, root, overrides)`——`--mutate` 就是用它做出一份 symlink 鏡像、
只覆寫一個檔案，**dist 本身永遠不被寫**。artifact 不動，不需要連結。

### 做法

新增 `--shim inline-format-review`（**不是** mutation：mutation 的語意是「重新引入
一個缺陷、要求某一格變紅」，這裡是「打開一扇門好把量測做完」，兩者不可混用）。

鏡像裡只改**一個檔案的一處**：`dist/editor-shell-v2/paragraph-editor-client.js` 的
`formatFailureDisposition()`，讓沒有 barrier 的 `LOK_COMMAND_FAILED` 回
`dispatched-unverified` 而不是落到最後一行的 `unknown-rollback`。

**這一處就夠，已經對著原始碼確認、並經 codex 獨立追過一次**：
`_blockQueueIfDispatched()`（`narrow-editor-v2-session.js:196`）第一行就是
`if (recoveryFor(error) !== "rollback") return;`；`action()` 的 catch 在
`review` 時以 sentinel **resolve**，基底類別的 `RECOVERY_ERRORS` 那條路不會走到；
之後 `insertText()` → `session.commitText()` 與 `saveDocument()` → `session.save()`
各自 `_enqueue` 進同一個沒被擋的佇列。

**已知的自我撤銷**：sentinel 沒帶 `state`，drain 會向引擎要一次 `getState`；
引擎若無回應就 `TIMEOUT`，而 `TIMEOUT` 在 `RECOVERY_ERRORS` 裡——shim 會自己失效。
這不是缺點，但**報告要寫**，否則一次 TIMEOUT 會看起來像「量到了 bold 沒生效」。

### 臂

**四個 slot 各跑一次，不是只跑 bold。** T2b 要改的是四個動作的處置，只量 bold
然後套到四個上，就是這一輪要防的形狀。既有證據甚至**根本沒有 dispatch 到
strikethrough**——它是在 session 已經進了 `recoverable-error` 之後才輪到，回的是
`EDITOR_NOT_READY`（`findings/evidence/059/format-actions-on-a-collapsed-caret.json:17`）。

每個 slot 三臂，各自開一次乾淨的 session，照原生那份的形狀：

| 臂 | 動作 | 存檔裡的標記應該是 |
|---|---|---|
| 對照 | 放游標、打標記 | 不套用 |
| 按一次 | 放游標、按鈕、打標記 | **這一格是答案** |
| 按兩次 | 放游標、按鈕、按鈕、打標記 | 若第二次送 `enabled:false`，不套用 |

**判準讀存出來的 ODT**，不讀 toast、不讀 `aria-pressed`，而且**要解析標記那一段
文字實際掛著的 style**（理由同 T1.2）。

### 紀律

- **原生的結果不描述 WASM，WASM 的結果不描述原生**（048 的先例）。兩邊各自量，
  最後並排，不互相推論。
- 對照臂不可省。沒有它，「標記是粗的」也可能是語料自己的樣式。
- shim 打開的門要在報告裡寫清楚**它使量測失去了什麼**：這一輪測不到「產品在
  真實 disposition 下的行為」，那仍然是 `rollback`。

### 驗收

`findings/evidence/059/wasm/`（英文），finding 059 的「未確立的一格」關掉——
**兩個方向都算關掉**：做到了，或沒做到，**而且是四個 slot 各自的答案**。

### T2b（條件式，要先問）— 產品端的處置

**只有在 T2 量到「WASM 上也照做了」時才成立**，而且它是判斷題（§7 J1），
不是我自己決定的：把四個 inline 格式的 disposition 從 `rollback` 改成 `review`
（殼層 v17，不需連結）。

支持：`LOK_COMMAND_FAILED` 是在**命令結果回呼抵達之後**才產生的，所以
「dispatched」是知道的，不是猜的；而 `review` 這個值就是為「送出去了、這個 build
驗不了、不要叫使用者丟掉東西」造的（SPEC E2-C 2.6b）。

反對：046 那次**刻意**把 `dispatched-unverified` 收窄到**一個形狀**，程式碼註解
明白寫「任何其他未驗證的 dispatch 保留它今天的 rollback」。放寬它正是那句話防的事。
而且放寬的範圍要跟量到的範圍一致：**量到幾個 slot，就只放寬幾個。**

---

## T3 — 三個 `unverified` 接進回歸網

三格各自帶一個**會紅的突變**，否則不算檢查。

### T3a `put-the-caret-where-i-clicked`

**第一版的判準（點左三分之一 vs 右三分之一，caret.x 要遞增）不夠，已作廢。**
任何**單調但錯誤**的實作都能通過它：永遠往右偏一個字、x 乘錯比例、兩條 y 都
低一行——三種壞法全部保持單調。而且現有的確認本來就不看 x：`caretIsOnLine()`
（`editor-shell/editor-session.js:52`）只驗 y。

判準改成**錨定的**，而且讀**畫面像素**——那是使用者看到的東西，也是 058 已經
證明過管用的技術（同一條帶狀區域的深色像素差）：

1. 用產品自己的搜尋／既有錨點取得一段**已知文字**的矩形（引擎回報的）。
2. 點在那段文字的**起點**與**終點**。
3. 判準：**畫出來的游標**兩次都落在那段文字的矩形內，而且兩次的位置差
   ≈ 那段文字的寬度（容差由該段矩形自己決定，不用常數——常數在別的語料上會變成
   「兩個字」）。
4. 換一行再做一次，y 要落在那一行的矩形內。

**產品沒有對外吐出 caret 座標**（`session` 是模組私有，`READ_STATE` 只讀 DOM 狀態），
所以**不要為了測試加一個回傳請求座標的欄位**——那種欄位會用「我剛才叫你去的地方」
回答「你到了哪裡」，永遠通過。像素是這一格唯一誠實的來源。

突變：讓 placeCaret 忽略 x（永遠回同一個位置）；**讓它固定偏移一個字**；
讓它固定低一行。三個都必須紅——第三個是第一版抓不到的那一類。

**不涵蓋的要具名**：052 的殘留（點在所有行框之外）不在這一格，它有自己的佇列項。

### T3b `format-a-paragraph`

按**產品自己的**工具列按鈕，判準讀**存出來的 ODT**（不是修訂號——049 的形狀）。

**五個動作，不是四個**：`set-paragraph-heading` 也要進來。清單那一格的使用者
語句是「把一段變成**標題**、內文、項目符號或編號」，而 heading 今天唯一的覆蓋是
page smoke 的「修訂號要 +1」——一個改錯段落的實作也能讓修訂號 +1。

三條紀律，第一版全缺：

- **目標段落的狀態必須真的會變。** `set-list-none` 打在一個本來就不是清單的段落上、
  `set-paragraph-body` 打在一個本來就是內文的段落上，**什麼都不做也會通過**。
  每個動作要挑一個處於**相反狀態**的段落。
- **判準錨在確切的段落文字上**，不是全文件的存在性檢查。語料
  （`list-contexts.odt`）裡本來就有標題、項目清單、編號清單各一——全文件 grep
  會在「改錯段落」和「什麼都沒改」時通過。既有的 D3 分析
  （`analyze_e2_c_d3.py:125`）就是這樣錨的，照抄。
- **鄰居要活著**：目標段落改了，前後兩段的文字與樣式不得變（046 的形狀）。
- 空白行那一格**不在這裡**：046 的殘留是引擎那一側，佇列項
  `queue-quantifier-check-for-multi-block-readback` 是它的家。這一格若把空段落
  含進來，會變成在量那個缺陷。

突變：工具列吞掉動作；按鈕送錯 action；**動作打在鄰居身上**。

### T3c `recover-from-an-error`

新誘發手段 `INDUCE_FOOTNOTE_APPARATUS`（佇列項指定了這個名字）：
用 `test-docs/e1/endnote-frame.odt`（finding 038），**走產品自己的開檔路徑**——
產品現在開得了任意檔案，不需要第二個 fixture 參數。

**可達性已經追過（codex，2026-08-18）**：產品的 `pumpDrag()` →
`session.selectRange()` → `editorSelectRangeV2`，正是 038 量到的卡死路徑之一；
逾時被 `_drain()` 接住，`TIMEOUT` 在 `RECOVERY_ERRORS` 裡 → `recoverable-error`
→ notice 顯示。恢復也在同一輪測得到：`rollback()` ＝ `restart()`，換一個 worker。

**判準不是「之後存得出一份合法的 ODT」。** 那個判準在「重開一份原封不動的
authority bytes」時也會通過。

### fable 的裁決（2026-08-18）推翻了我這一格的第二個前提

我原本寫「`M1` 必須在，`M2` 在不在兩種都可以、寫下來就好」，依據是 038 量到
restart 之後未存檔的標記消失。**那個依據過期了。**

`editor-session.js:466` 起的 `_checkpointBeforeSelection()` 在**每一次選取手勢
之前**、文件是 dirty 時，先存一份檢查點；`_openFresh()` 用檢查點與 authority
之中**較新**的那一份（`:163-167`），並把 `dirty` 設成 `useCheckpoint`（`:193`）。

而 038 的誘發器**本身就是一次拖曳選取**，產品的拖曳確實走
`session.selectRange`（`web/e2-editor-app.js:405`，已回讀確認）。

⇒ **在今天的殼層上，走 038 這條路，`M2` 應該要活著回來。**
我那條「兩種答案都可以」的判準，會把「`_checkpointBeforeSelection` 退化成
no-op」評成 PASS 加一句話——**沒有任何東西會變紅**。那正是 046 教過的形狀。

### 判準改成三分支：拿產品自己的宣告去審它

產品在使用者按下按鈕**之前**就已經宣告要回到哪裡，而且宣告在**使用者看得到的
地方**——`#s-checkpoint` 顯示「有（rN）」／「寫入失敗」／「無」
（`web/e2-editor-app.js:94-96`），`READ_STATE` 本來就在讀它。

1. 打標記 `M1` → 存檔。2. 打標記 `M2`。3. 誘發卡死 → notice → 按下去。
4. 判準按**通知出現當下 `#s-checkpoint` 的值**分支：

| 產品宣告 | 按下去之後必須 |
|---|---|
| 「有（rN）」 | `M1` **和** `M2` 都在 |
| 「無」 | `M1` 在、`M2` 不在（回到 authority） |
| 「寫入失敗」 | `M2` 可以不在，**但那個失敗必須被呈現給使用者** |

**外加一條能力條款**：誘發路徑是 dirty 狀態下的選取手勢時，通知出現的那一刻
`#s-checkpoint` **不得是「無」**——三分支一致性本身抓不到 no-op 突變（承諾與
兌現一起縮水，形式上仍然「一致」），這一條才抓得到。

突變：`_checkpointBeforeSelection` 改成 no-op；`checkpointError` 吞掉不上報。

### 順帶掉出來的產品缺口：`dirty` 沒有被呈現

從檢查點救回來時 `dirty` 是 `true`（`:193`），意思是「救回來的東西還沒進
authority」。**產品沒有任何地方顯示 `dirty`**（已 grep 過整頁）。一個把內容救回來
卻顯示得像已存檔的產品，會誘使使用者關掉分頁、把剛救回的東西再丟一次。
這是殼層側、不需連結——但它是**新的一格**，不是這一格，要另外開。

### 這一列的文字要改

「救得回來」的自然讀法是「我打的字回得來」，而那對「檢查點之後又編輯過、
而且沒有觸發選取手勢」的使用者是設計上不成立的。與其把檢查寫寬，不如不要許諾
產品不打算兌現的事。列句改成：

> `user: 出錯的時候救得回來——回到哪一點，按下按鈕之前產品就講清楚；
> 最壞是上次存檔（沒存過＝剛開檔的樣子）`

**「沒存過檔的使用者沒有檢查點」不會讓這一列不可達成**（我原本的擔心也錯了）：
`_openFresh()` 沒有較新檢查點時退回 `_authorityBytes`，那是 `open()` 當下存下的
開檔位元組。他丟的是全部輸入，但文件與 session 都回得來。

其他：

- **排在最後，或之後強制開一份新文件**：038 卡的是引擎 pthread，不重啟就不會好，
  留在同一個 session 裡會污染後面每一格。
- **如果按下去救不回來**：那**既是**一個新 finding，**也是**這一格 KNOWN_RED 綁
  那個 finding。第一版寫「那是 finding，不是這一項失敗」——那句話會讓這一格在
  復原按鈕壞掉的情況下關掉，不可以。
- **這一項有一個結構弱點，要寫進登記表而不是藏起來**：它把回歸網的復原覆蓋率
  綁在一個**未修的上游缺陷**上。038 哪天修好，誘發手段又會靜靜消失——那正是
  046 軟化之後發生的事。所以檢查在「誘發不起來」時必須報 NOT_ESTABLISHED
  並具名說是 038 不再誘發，**不得靜靜通過**。
- **037 不是備案**：038 自己記著 037 的形狀是**被擋法具名拒絕**、不卡死，
  到不了 `RECOVERY_ERRORS`。第一版把它寫成備案是錯的。
- **欠一個與缺陷無關的第二誘發器**（fable 裁決的條件三），排進佇列並標明驗證
  義務。候選兩個，都用公開 API 打得到：`selectRange` 帶一個刻意過短的
  `timeoutMs`（`TIMEOUT` 在 `RECOVERY_ERRORS` 裡）、或從頁面終止 worker
  （`worker-crashed` → `_enterRecovery`）。兩者都要先驗證真的落進
  `recoverable-error` 而不是被守衛具名拒絕（037 的教訓），而且要標明它們量的是
  **恢復機器**、不是使用者進入那個狀態的**路**——所以是補充，不是替代。
- **誘發器的前置條件是它自己的斷言步驟**：「038 這份 fixture 確實把佇列堵住了」
  必須大聲失敗或大聲 NOT_ESTABLISHED，而且要像既有的 `recipe_ran` 那樣先證明
  配方真的跑過。**絕不允許「誘發器死了」和「恢復壞了」共用一個安靜的出口。**
- **oracle 與誘發器解耦**：三分支是按 session 自己宣告的狀態分的，所以 038 哪天
  修好、誘發器換掉時，oracle 原封不動，只換進場配方。046 的檢查會蒸發，正是因為
  它焊死在單一誘發器的 disposition 上。

---

## T4 — 真實長度文件：**先量牆在哪，不要先修**

### 事前推算（寫進 PREDICTION，量測之前先不看）

`layoutCanvas()`（`web/e2-editor-app.js:158`）：

```
cssWidth      = min(desk 寬 - 40, 900)
backingWidth  = min(2400, round(cssWidth × devicePixelRatio))
canvas.height = round(backingWidth × heightTwips / widthTwips)
```

`heightTwips` 是**整份文件**的高，不是一頁——已從 core 原始碼確認：
`doc_getDocumentSize`（`desktop/source/lib/init.cxx:4572`）→
`SwXTextDocument::getDocumentSize`（`sw/source/uibase/uno/unotxdoc.cxx:3396`）
＝ `GetDocSize() + 2 × DOCUMENTBORDER`，而版面把每頁堆成一欄、每頁再加一個頁間
間隙（`sw/source/core/layout/pagechg.cxx:2423`）。**而且已有實測旁證**：
`findings/evidence/sdk-r6/discovery/summary.json` 記著 1 頁 17,406 twips、
22 頁 376,968 twips——每頁約 17,116，比 A4 的 16,838 高。

所以**不要用 A4 的原始尺寸算**，用實測的每頁有效高。取 22 頁那筆
（每頁比 ≈ 1.3737）與瀏覽器單邊上限 32767 px：

| devicePixelRatio | backingWidth | 撞牆頁數（估） |
|---|---|---|
| 1（headless 預設） | 900 | **≈ 26.5** |
| 2 | 1800 | **≈ 13.3** |
| ≥ 2.67 | 2400（封頂） | **≈ 9.9** |

**牆的位置差 2.7 倍，而 harness 站在最寬鬆的那一格。** 這正是「harness 的路
vs 使用者的路」：只在 dpr=1 的 headless 量，會把使用者十頁就撞到的牆記成
二十六頁。**這一格必須掃 dpr。**

候選的牆有四道，量測要分得開：

| | 徵狀 |
|---|---|
| **canvas 尺寸上限** | 設定 width/height 之後畫布不可用，且瀏覽器不同、值不同 |
| **tile 配置** | `render()` 要一張 `backingWidth × canvasHeight` 的 RGBA；dpr=1、26 頁約 120 MB |
| **每次編輯整張重畫的延遲** | 不是「壞掉」，是變成不能用 |
| **重排之後幾何沒有更新** | 見下，這是第一版完全漏掉的一道 |

### 第四道牆：`heightTwips` 開檔之後就不再更新

`DocumentHandle.heightTwips` 只在 open 的 metadata 指派一次
（`sdk/document-sdk.js:365`）；`document-invalidated` 只呼叫 `renderDocument()`，
**沒有重讀 metadata、也沒有再呼叫 `layoutCanvas()`**（`web/e2-editor-app.js:609`）。

⇒ **一個讓文件多一頁或少一頁的編輯之後，canvas 尺寸與 render 區域都是舊的。**
一個只在頂端插字、不跨頁的測試會漂亮地通過，而一個真的把文件撐長的編輯會讓
底部靜靜消失。這一格**必須**包含一個會改變頁數的編輯。

### 做法

1. **語料產生器**（`tools/create_long_document.py`）：產出 1／5／10／20／40 頁的
   ODT。頁數不用猜——開檔之後讀 `document.heightTwips` 換算，那是判準。
   語料不進凍結集。
2. **瀏覽器上限探針**：不要引用網路上的常數，在**本機兩個瀏覽器**各量一次
   （二分法建 canvas，記錄第一個失敗的尺寸）。
3. **長文件一定要走產品自己的開檔路徑**（`listener:change#file`，既有的
   `OPEN_FILE` 就是走這條）。**不可以用 `--fixture`**：那個參數今天只被寫進報告，
   `navigate()` 不帶它，頁面開機永遠開 `list-contexts`
   （`web/e2-editor-app.js:689`）。用它會做出一份寫著「40 頁」而其實開著一頁的報告。
   **順手要修的**：`--fixture` 是一個不控制任何東西的報告欄位（029 的形狀），
   要嘛接上去，要嘛拿掉。
4. `LONG_DOCUMENT_CELL` 進 `run_e2_c_product_path.py`：每個長度 × 每個 dpr，
   記錄開檔是否成功、canvas 實際尺寸、render 是否回錯、**一次編輯的重畫延遲**、
   **一個會改變頁數的編輯之後底部像素是否還在**、以及畫面上到底有沒有東西
   （058 的教訓：資料到了不等於畫出來了）。

### 這一格的檢查要判什麼（否則它是一份報告不是檢查）

**不是「二十頁要能編」**——那是修好之後的目標。要判兩件事：

- **誠實**：在一個渲染已經壞掉的長度上，產品必須**說出來**；靜默地給一張空白或
  截斷的畫布是不合格。
- **可用**：**事前登記一個延遲門檻**（PREDICTION 裡就要寫死一個數字與一條斜率），
  超過就是紅。沒有門檻，這一格會在「每次編輯要等三十秒」的情況下通過——
  `renderDocument()` 給了 60 秒的 timeout，所以它真的通得過。

實測若是靜默失敗 → 開一個 finding，這一格宣告 `KNOWN_RED` 綁那個 finding
（狀態不得是 `done`，見 T0 的規則）。
突變：把 `MAX_BACKING_WIDTH` 調小，牆會移動，這一格要跟著動——證明它量的是牆
而不是某個常數。

---

## 3. 做完之後清單長什麼樣

| 格 | 今天 | 這一輪之後（預期） |
|---|---|---|
| `put-the-caret-where-i-clicked` | unverified | **done** |
| `format-a-paragraph` | unverified | **done**（空段落那一半具名不涵蓋） |
| `recover-from-an-error` | unverified | **done**，或 KNOWN_RED ＋ 一個新 finding |
| `edit-a-real-length-document` | missing | **partial ＋ 一個具名的牆**（修不在這一輪） |
| `turn-formatting-off` | blocked | 仍 blocked，但**判準已決定、原始碼已進佇列** |
| `redo`／`move-by-line` | blocked | 不動（見 §7 J3） |

「沒有 `blocked`」仍然不成立，而那時候它**只**卡在一次連結上。

## 4. 這一輪不做、但要在計畫裡具名的

- **工具列上的「游標左移」「游標右移」「刪除」按鈕**：清單自己說「沒有任何使用者
  需要那種東西」。它們是覆蓋率登記表裡剩下的 uncovered 大宗。**把它們補上檢查**與
  **把它們從產品上拿掉**是兩個不同的答案，而後者是產品決定，不是我的。
- `queue-quantifier-check-for-multi-block-readback`：引擎側，要自己的 PREDICTION，
  下一次連結的候選；這一輪只確保 T3b 不去踩它。
- 剪下的「文字真的被移除」：WebDriver 拒絕剪貼簿寫入，屬於 D5。

## 5. 覆蓋率登記表的一個小修正

交接寫「十四個動作 uncovered」。今天實測是 **19 條 uncovered 路徑，其中 13 條是
工具列動作**（`tools/audit_product_path_coverage.py`，2026-08-18）。差異不影響結論，
但這一輪會動這個數字，所以先把基準寫對。

## 6. codex 的分包

對錯有客觀判準的，交出去；回來的結論**仍然自己跑變異控制**——本篇兩條關鍵結論
（`wasModified` 的語意、`--fixture` 不控制任何東西）我都自己回去讀過原始碼確認。

| 交給 codex | 驗收條件（隨指令一起給） |
|---|---|
| 對抗性審查（**已做一輪**，thread `01a01377-4ab2-7481-8658-e4f76e15ee30`） | 「哪一項的驗收條件，可以在東西是壞的時候通過？」 |
| `run_e2_c_product_path.py` 的索引位移稽核 | 列出所有以位置索引讀存檔的檢查，指出新檢查唯一能插入的位置 |
| 長文件語料產生器 ＋ 瀏覽器 canvas 上限探針 | 產出的 ODT 開起來 `heightTwips` 落在目標頁數 ±5%；探針在兩個瀏覽器各印出一個具體失敗尺寸 |
| T0／T1 分析器的 self-test | 每一條規則／每一條預測各要有一組合成資料使它判「不成立」 |
| 收工前再一輪對抗性審查 | 同第一題，對著**寫出來的檢查**問，不是對著計畫問 |

## 7. 要問使用者的三個判斷題（可能要叫 fable）

fable subagent `a049290c1399c57f2` 仍可用 SendMessage 續談——**續談既有那一個**，
它已經有 046／盤點的上下文，不要另開。

| | 什麼時候會問 | 我的傾向 |
|---|---|---|
| **J1** | T2 量到「WASM 上也照做了」之後：要不要現在把 inline 格式的 disposition 改成 `review`（T2b） | **傾向要，但只放寬到量到的那幾個 slot**——`LOK_COMMAND_FAILED` 在結果回呼之後才生成，dispatched 是知道的；但 046 刻意收窄到一個形狀，放寬正是註解防的事 |
| **J2** | T1 量完，readback 只在部分 slot 上成立時 | 沒有傾向——那時候要重新設計判準，四個 slot 的數字會一起附上 |
| **J3** | 現在（範圍題） | `redo`／`move-by-line` 要改 SPEC E2-C 4.2 的「明確不承諾」，那是契約修訂不只是連結；**傾向這一輪不碰** |

## 8. 這一輪的操作紀律（上一階段各犯過一次）

- **動手加 handler 之前，先確認沒有別人在處理同一個事件。**
- **新檢查放在所有以位置索引取存檔的檢查之後**（踩過兩次）。T2／T3／T4 都會加
  檢查，所以先做一次稽核再動（§6 已分包）。
- **檢查要指對檔案**——指著沒人會改的檔案的檢查，不管做了什麼都不會變綠。
- **`--write` 不重寫既有殼層世代**：T2b 若成立，是 v17，不是改 v16。
- **D0 沒跑**：殼層動了就還是沒跑，這一輪不會讓它變得更貴，但也不要順手跑掉。
- **不得指認肇因**（040／048 的先例）：核心為什麼對做成了的命令回報
  `success: false`，這一輪不會知道，也不要寫。

## 8.5 執行紀錄（2026-08-18，隨做隨記）

**T0 —— 做完。**

- runner 現在把它**實際服務的**殼層身分寫進報告（`servedShell`）：拿 v16 bundle
  宣告的十二個模組、從**伺服器指到的那個 root** 逐檔雜湊，用的是 bundle manifest
  自己的 digest 函式（匯入，不重寫）。**不是旗標，是導出值**——三個突變鏡像實測各
  產生不同 digest，乾淨跑則與宣告值逐位元相符。
- `check_usable_editor.py --report` 四條規則上線，self-test **22/22**
  （原本 8 條，新增 14 條，每一條規則各紅一次）。
- **第一次跑在真報告上就掉出一張單**：見下。

**T1.0 —— 做完。** `wasModified` 的更正已寫進 finding 059、
`findings/evidence/059/native/README.md`（英文）與佇列項的 `note`。
佇列檢查 37 項 0 drifted，`P1 complete: False`（擋的仍是 059）。

**掉出 finding 060 —— 游標那一格的檢查，綠不綠取決於瀏覽器視窗多大。**

乾淨基線跑把 `the-caret-is-drawn-where-it-was-placed` 判成 FAIL
（`2051 == 2051`），而 `dist/`／`web/` 一個位元組都沒動。
**游標是有畫的**——對著 `caret` 突變鏡像做逐列隔離，第 276–283 列、八列一像素寬，
只在畫游標那一行還在時出現。壞的是判準：它取樣寫死的視窗比例，而畫布大小是
`el.desk.clientWidth` 的函數。單次點擊後 1／3／6／12 秒重採樣排除了「等太短」。

⇒ `see-where-the-caret-is` **從 `done` 降回 `unverified`**，引用 060。
修法不另開：與 T3a 是同一件事（錨定引擎回報的文字矩形），T3a 完成時一併收復。

**這一格是 T0 的第一個產出**，也是它存在的理由：在它之前，一格 `done` 配一個紅著
的檢查，清單是全綠的。

**T1.1／T1.2 —— 做完，而且判準決定了。**

預測先寫（`findings/evidence/059/native/predicate/PREDICTION.md`），再寫探針。
十臂、鍵盤走位（Ctrl+Home、Down×N、End）而不是點猜出來的 y、專用語料
（`create_f059_predicate_fixture.py`，self-test 7/7）、判準解析標記那一段實際掛的
style。分析器 `analyze_f059_predicate.py` self-test 9/9。

**九臂的存檔結果與要求完全一致，四個 slot 全部照做。** 三件掉出來的事：

1. **判準不能是「有沒有收到廣播」（P2 不成立）。** 核心廣播的是狀態**改變**；
   `value:false` 那幾臂一個廣播都沒有，而文件結果完全正確。
   ⇒ 站得住的是 barrier 已經在用的 **postcondition**（比對觀察狀態與要求狀態），
   在這十臂上九次全對。
2. **P4／P5 成立，而引擎裡有一句關於核心的話是錯的。** 底線與刪除線
   **都在** `GetKitUnoCommandList()` 裡、都會廣播；`probe_engine.cpp:4308-4310`
   說它們不在，那是不留 cache 的理由，而理由是假的。
3. **拒絕臂沒有拒絕（P6 未確立）。** `setViewReadOnly` 之後核心照樣把字變粗。
   所以這一輪證明了判準**會同意**，沒有證明它**說得出不**。

⇒ **T1.3（動引擎原始碼）先不做**，欠兩件：一個真的負向臂，以及 state cache 的
priming（finding 021 的形狀）。這是「量到什麼寫什麼」，不是延後。

**T2 —— 進行中，前四輪各自量到了不一樣的「什麼都沒量到」。**

這一段留著，因為它本身就是這一輪最貴的教訓：**四輪都產生了看起來可以解讀的
null，而四個 null 的原因都不是「核心沒做」。**

| 輪 | 為什麼沒量到 | 之後加了什麼守衛 |
|---|---|---|
| 1（範圍選取） | v3 manifest 對四個 inline 格式宣告 `gestures: ["collapsed"]`，所以範圍選取時**頁面把按鈕 disable 掉**，而 `button.click()` 對 disabled 按鈕不發事件 | 每一臂記錄按鈕的 `disabled`；沒發出去的臂不計分 |
| 2（收合游標，固定 sleep） | 每一臂讀回 `busy` ＋ 空 toast | 所有固定 sleep 換成等條件 |
| 3 | **游標定位每一臂都失敗**（`定位游標 失敗`）——x=0.30 落在八個字的行尾之外，正是 052 的形狀 | 加寬語料；游標定位變成**要證明成立的前置條件**，多點嘗試並記錄哪個成立 |
| 4 | **產品開的是一張 404 錯誤頁**：`build_mirror` 只走**來源樹**，dist/ 裡不存在的路徑，它的 override 會被靜靜丟掉 | fixture 直接寫進鏡像根目錄；而且**用位元組驗開檔，不用標籤** |

第 4 輪那一條最值得記：**「檔案開起來了」原本是比對頁面狀態列的檔名，而那個檔名
是頁面被「交給」的名字，不是它讀到的位元組。** 404 頁被當成文件打開，檔名照樣顯示
成 fixture 的名字，下游每一格都同意。產品路徑的
`product-opens-a-document-the-user-chose` 早就用「只存在於那個檔案裡的文字」當判準
——**這支探針沒有照做，就踩了同一個坑**。

**一個被撤回的中間結論**：第 4 輪的「已經是粗體的語料裡插入標記，回來是沒有樣式的」
一度被我讀成「產品的插入路徑不帶游標格式」。**那是 404 頁面上量到的，撤回。**
（原生那一輪相反：`paste` 會帶 pending 粗體，見
`findings/evidence/059/native/paste-pending/`。）

第 8 輪把範圍那條路關掉並且**量到它為什麼關著**：把頁面的 gesture mask 拿掉之後，
四個派送全部回 `EDITOR_FORMAT_GESTURE_UNSUPPORTED`——mask 在**引擎那一側也有**
（`editorGesturePermitted`，`probe_engine.cpp:4247-4252`），引擎自己說
「nothing was dispatched and the document is unchanged」。順帶：這是佇列項
`p1-2-gesture-mask-inherited` 的**第一個執行期見證**，在此之前它只有靜態計數。

**T2 —— 第 9 輪答完了，而且是壞的那個答案。**

六臂，全部走產品自己的路（開檔、放游標並確認、按工具列、按插入鈕、按存檔鈕），
判準是存出來的 ODT 裡標記那一段掛的樣式：

| 臂 | 命令結果 | 標記的樣式 |
|---|---|---|
| 對照，不派送 | — | **無樣式** |
| `set-bold`／`set-italic`／`set-underline`／`set-strikethrough` | 四個都 `LOK_COMMAND_FAILED` | **粗體／斜體／底線／刪除線** |

**每一臂拿到的正好是它按下去的那個 slot。** ⇒ **出貨的產品按下 B 會把字變粗，
然後告訴使用者失敗了、請回到檢查點——叫人丟掉工作去撤銷一個成功的改動。**

一個沒解釋的鬆頭：`insert-path-carries-formatting` 那個控制臂自己回來是沒有樣式的
（而產品的 `aria-pressed` 說游標是粗體）。它的用途是讓 null 可讀，而四臂都是正的，
所以上面的結論不依賴它——但它的 null 沒有解釋，游標在粗體 run 裡的 offset 也沒有
確立。**具名留著，不掃掉。**

**T2b —— 做了（使用者裁示「直接改，不用裁決」），殼層 v17 `34289a7b…`，不需連結。**

`formatFailureDisposition()` 對 `LOK_COMMAND_FAILED` 回 `dispatched-unverified`，
不再落到 `unknown-rollback`。**依據是可查的，不是類比**：那個碼**只**從引擎的 UNO
command **result** handler 產生，而且是在酬載已與送出的命令比對成功之後
（`probe_engine.cpp:2279-2291`）——核心針對這個命令回答了，所以「派送出去了」是
知道的。046 收窄要防的是「把猜的當成知道的」，這一組正是知道的那一邊。

同批：提示文字依 `error.code` 分成兩種（把 046 的「涵蓋了不只一個段落」拿給 059 的
使用者看是錯的解釋）；SPEC E2-C **2.6c** 與殼層同一次寫；頁面裡那句重複引擎錯誤
宣稱的註解也改掉了。

### 它掉出一個我沒預測到的後果

佇列不再被擋之後，**兩次按下都跑得完，`bold-can-be-turned-off-again` 變綠了**——
從使用者的位置看，粗體現在真的關得掉。runner 立刻宣告它的 KNOWN_RED 過期，
那正是那個機制的用途。

所以宣告重新排過，而不是留著一個已經綠了的宣告：

| 檢查 | 狀態 |
|---|---|
| `bold-can-be-turned-off-again` | **綠**，從 KNOWN_RED 拿掉 |
| `a-format-that-worked-is-not-reported-as-failed` | **新增，KNOWN_RED 綁 059** —— 產品仍把一個成功的動作回報成失敗，這才是引擎那一半真正剩下的缺陷 |
| `the-caret-is-drawn-where-it-was-placed` | **KNOWN_RED 綁 060** —— 它本來在突變輪裡默默 confound |
| `a-failed-format-does-not-block-the-session` | 新增，擁有 `inline-format-rollback` 突變（**刻意不與 bold 那格共用**：一個已經紅著的檢查證明不了突變被抓到） |

⇒ `turn-formatting-off` **從 `blocked` 改成 `partial`**，沒涵蓋的部分具名。
`blocked` 從三格降到兩格（redo、move-by-line）。

T0 的規則跟著補一條：**`partial` 可以引用一個具名的 KNOWN_RED 當「沒涵蓋的部分」，
但仍然必須有一格自己的綠檢查**；`done` 一律不准引用。self-test 22 → 24。

基線輪：`ok=True`，「1 not established、2 known red」，沒有過期宣告。

**T3a —— 做完，兩格都收復，060 關掉。**

判準錨定在**那一行自己的墨水**：同一行點兩次（靠近行首、遠過行尾），文字不動，
所以多出墨水的那一欄是游標的第二個位置、少掉的那一欄是第一個。不需要引擎座標，
也不需要 block identity。

**它第一次跑就抓到我自己判準的一個缺陷**：`inkSpan` 回報 724 而畫布寬 725——
兩端的「墨水」是**頁面邊框**，所以「沿著這一行的比例」其實是「橫跨畫布的比例」。
修法是排除填滿整個帶高的欄。之後 span 是 355，量到的是真的文字寬度。

| | 靠近行首 | 遠過行尾 |
|---|---|---|
| 游標在行墨水上的位置 | **-0.006** | **1.003** |

突變 `caret-ignores-x`（游標照畫、照畫在對的行，只忽略 x——舊判準對它是綠的）
兩格都紅，run 判「detected by the check that owns it」。
**具名極限**：這個判準靠看游標**移動**認出它，所以釘在固定欄位的游標與根本沒畫的
游標讀起來一樣。

⇒ `see-where-the-caret-is`、`put-the-caret-where-i-clicked` 兩格 → `done`。
清單現在是 **8 done／3 partial／2 unverified／1 missing／2 blocked**。

## 9. 第一版被退回的地方

codex 的對抗性審查問的是一個問題：**哪一項的驗收條件，可以在它宣稱要建立的東西
其實是壞的時候通過？** 七條，全部有原始碼佐證，全部改了：

| | 第一版錯在哪 | 現在 |
|---|---|---|
| T1 | 把 `wasModified` 當候選——**它是 dispatch 之前的髒旗標** | 候選出局；T1.0 先去更正 finding 與佇列項 |
| T1 | 拒絕臂用「核心不認得的 slot」——**那不會發回呼**，等於沒量 | 改用「認得但當下不能跑」；每臂要證明收到新回呼 |
| T1／T2 | 只量 bold 就套到四個 slot | 四個 slot 各自預測、各自量、各自結論 |
| T1／T2 | grep `fo:font-weight` | 解析標記那段文字實際掛的 style |
| T0 | 沒綁報告身分；`done` 可以沒有任何 `check`；與 T4 的 KNOWN_RED 規則自相矛盾 | 三條都補上，KNOWN_RED 改綁 finding 不綁狀態字 |
| T3a | 次序判準——**單調但錯誤的實作全部通過** | 改成錨定文字矩形 ＋ 讀畫面像素；加「固定偏移」突變 |
| T3b | 漏掉 heading；目標段落可能本來就在目標狀態；全文件存在性檢查 | 五個動作；狀態必須真的會變；錨在確切段落；鄰居要活著 |
| T3c | 「存得出合法 ODT」＝復原；037 當備案；失敗只當 finding | 改問「檢查點的標記回來了嗎」；沒有備案要說沒有；失敗要 KNOWN_RED |
| T4 | 用 `--fixture`（**它不控制任何東西**）；沒有延遲門檻；漏掉重排之後幾何不更新 | 走 change#file；事前登記門檻；加一個會改變頁數的編輯 |
