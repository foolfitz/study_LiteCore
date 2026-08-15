# DEVLOG 2026-08-15 — E2-C 開場：manifest 承諾了十五個動作，殼層到得了五個

接續 [`HANDOFF-2026-08-15e`](../handoff/HANDOFF-2026-08-15e-e2b-go.md)。
那份交接說下一步是「E2-C：規格還沒寫」。寫規格之前先照
memory 那條規矩重讀自己的樹，**在讀的過程裡撞到一件沒有人量過的事**。

## 撞到什麼

出貨的 v2 profile `e2-editor-v2`（artifact `572035ac…`）的 manifest 宣告
**十五個動作**，worker 的 `editorActionV2` 也吃十五個
（`EDITOR_V2_ACTION_IDS` 展開 v1 的十個再加五個）。但是：

| profile | 殼層 | 十個 v1 動作到得了幾個 | 擋在哪 |
|---|---|---|---|
| `e2-editor-v2` | `editor-shell/editor-client.js` | **0／10** | `UNSUPPORTED_OPERATION`——它要求 capability `narrow-editor-v1` **且** `editorContract.version === 1`，v2 兩個都不是 |
| `e2-editor-v2` | `editor-shell-v2/paragraph-editor-client.js` | **0／10** | `EDITOR_ACTION_UNSUPPORTED`——allowlist 只有五個段落動作 |
| `e1-editor-v1` | `editor-shell/editor-client.js` | **10／10** | —（對照組） |

**引擎與協定是完整的，洞在殼層。** 也就是說：出貨的 manifest 承諾了一個
沒有任何 host 用得到的 surface。

## 為什麼既有的檢查看不到

E2-B 第 5 節第 7 項的四路清單檢查（`check_e2_b_inventory.py`）問的是
「header／manifest／worker／client 有沒有指同一組動作」。它的 client 那一份是
**兩個殼層的聯集**，聯集確實是十五個——只是聯集裡有一個殼層**接不上這顆
profile**。

> **「四份清單一致」與「host 真的做得到這十五件事」是兩個宣稱，
> 過去只檢查過第一個。**

這不是那個檢查壞了，它做的事沒有錯。是 E2-B 9.10 的表格那一列被我讀得太寬。
已就地補記（E2-B v13），**判定不變**——E2-B 的範圍是那五個段落動作，
它們確實跑過 132 個 run。

## 處置

新的 `editor-shell-v2/narrow-editor-v2-client.js`，十五個動作。否決的另外兩條：

- **改 `editor-shell/editor-client.js` 讓它接受 v2**：那個檔案由 E1-C 的
  bundle `f9b1a52f…` 逐檔 hash 綁定，改它就解除 `E1_GO_ODT_EDITOR`。
- **從 manifest 砍掉那十個**：要重跑 builder → 新 hash → E2-B 的 132 個 run
  與 12 列全部斷綁。**讓殼層追上承諾，比讓承諾縮回去便宜一個數量級**，
  而且不丟掉已經量到的東西。
- （**出兩顆 profile**：一份文件只能開在一個引擎裡，不成立。）

五個段落動作**委派**給 `ParagraphEditorClient`，不重寫——路線 C 的
`changed: null` ＋ `verified-format-readback` 規則只有一份。
十個 v1 動作在新檔案裡自己驗。

## 兩份複本要怎麼才不會漂

十個動作的驗證規則現在有兩份（v1 那份是 hash 綁定的，動不得）。
**比對原始碼沒有用**——規則可以被改寫、重排、只套一半，看起來仍然很像。
所以比對的是**行為**：

同一個呼叫、同一個引擎回覆，兩個客戶端各跑一次，判決必須逐格相同。
**1 600 格**（10 個動作 × 10 種呼叫參數 × 16 種引擎回覆），
其中 **84 格接受**、364 格 `EDITOR_RESULT_INVALID`、1 152 格 `INVALID_ARGUMENT`，
**兩邊 1 600 格全等**。

回覆的突變清單裡有一格是具名的：`documented-state-noop`。
那是 finding 022 從 stale cache 產出的 completion，兩側都移除過，
所以它必須在兩邊**都**被拒絕。

矩陣自帶兩個守衛：

1. `accepted > 0`——否則「兩邊一致」可能只是兩邊都拒絕全部；
2. 一個把 `_validateInherited` 拿掉的子類別，**必須**讓判決出現差異
   ——否則這個比對證明不了任何事。

## 這一輪的紅先於綠

可達性測試
（`editor-shell-v2/tests/manifest-reachability.test.mjs`）
是**先寫的，而且寫出來就是紅的**，紅的內容逐字是上表第一、二列；
兩個對照組（v1 殼層在 v1 profile 上十個全到／沒宣告過的動作誰都到不了）
當時就是綠的。實作之後才轉綠。

順帶記一個自己的錯：對照組第一版是紅的，因為我的 stub 回了
`{reached: true}` 這種不成形的結果，被殼層的後置條件檢查擋掉——
**「到得了引擎」和「stub 的回覆能通過驗證」是兩件事，混在一起會讓
關著的閘門和寫壞的 stub 長得一模一樣**。stub 改成記錄「請求有沒有離開殼層」。

## 產出

- `specs/SPEC-E2-C-paragraph-format-validation.md` v1（草擬，未執行）
- `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js`／`.d.ts`
- `wasm_sdk_probe/editor-shell-v2/tests/manifest-reachability.test.mjs`
- `wasm_sdk_probe/editor-shell-v2/tests/narrow-editor-v2-client.test.mjs`
- `make test-e2-c-static`（無前置目標——E2-C 的範圍是殼層、runner、判定工具，
  任何需要重連結的改動都不是 E2-C 的）

**零 relink、零 artifact 變動**：`validate_e2_b.py` 重跑仍是
`GO_TO_E2_C | problems: none`，`findings/` 與 `dist/` 逐位元未動。

## 規格裡兩件從樹裡讀出來、不是想出來的事

1. **D3 語料的第六份不是本輪想加的。** E1-C 9.2 在 08-13 就寫下
   「清單動作要進出貨契約之前，必須先補語料或具名排除」，語料
   （`test-docs/e1/list-contexts.odt`）也已經補好。清單動作**現在就在**
   出貨契約裡，所以那條義務到期了，E2-C 是它第一次真的被用到的地方。
2. **D2 那個 `dispatched-rollback` 格要用「有註腳、但註腳本文沒有 frame」的
   fixture。** E1-C 9.1 量過四格：`footnote-no-frame-full` 是 8 ms 可用的，
   `note-full`（註腳裡有 as-char frame）會讓引擎停止回應。
   **拿錯 fixture 這一格不會失敗，會讓引擎不回應**，然後整輪什麼都證明不了。

---

## 第二段：對抗性審查（codex）把「進場工作」的規模改掉了

規格 v1 寫完之後送 codex 做對抗性審查。回來 16 項，**全部處理過**：
15 項改寫規格或程式碼，1 項判為可行但不採用並記下理由。

**最重的三項是同一種錯：我把「有一個能送出動作的客戶端」當成了「產品修好了」。**

1. **沒有任何產品頁面在用那個客戶端。** asset 目標沒複製它，而
   `demo-structure` 只有五個段落動作、**而且沒有拖曳選取**
   ——D5 的「真實指標拖曳」在產品頁面上根本做不到。
2. **出貨的 `EditorSession` 在 v2 profile 上開不起來。** 它在
   `_openFresh()` 建 v1 客戶端（`:125`）然後 `await this.editor.getState()`
   （`:140`），v2 上那個客戶端拒絕，`open()` 直接失敗停在 `recoverable-error`。
   `ParagraphEditorSession` 包著它、繞過 `_enqueue`，補不上。
   **於是 D1／D2 承諾的 session、queue、checkpoint、rollback、三代上限
   在 v2 上沒有任何實作。**
3. **判定只綁三個雜湊**，而 E2-C 要證的東西有一半在殼層。
   E1-C 早就學過要綁第四個（殼層 bundle `f9b1a52f…`）。

其餘幾項也都是真的：`PARTIAL` 的定義會逼我去改凍結的 manifest；
D3 原本在「沒有清單的段落」上驗清單動作；D1 用 typed completion 當判準，
但四個 inline 格式回同一個 `uno-command-result`；D2 四個處置只寫了一格；
D4 的「無連續成長」不可否證；沒有凍結矩陣。

### 一個真缺陷，跟著審查掉出來

`formatFailureDisposition()` 對沒有 barrier 欄位的錯誤一律回 `unknown-rollback`，
而客戶端自己丟的 `INVALID_ARGUMENT` 沒有 barrier ——
**「呼叫端打錯一個參數」的處置變成從 checkpoint 重開、丟掉自那之後的全部編輯。**

fail closed 是對的，但它適用的是「不知道有沒有派送」。三個碼是知道的
（客戶端的參數檢查與 worker 的兩道閘都在 `accept()` 之前 return，
E2-B 9.10 在出貨 artifact 上量過 worker 那半）。已修，順序排在 barrier 之後。

## 第三段：三件進場工作做完

**2.3 的 session 接在唯一真正有差別的那個接縫上。** v1 與 v2 的差別只有一處：
建哪一個客戶端類別。之後一切都走 `{document, editor, scheduler}` 這個 runtime
物件，而 `NarrowEditorV2Client` 對 `EditorSession` 會呼叫的每個方法都有答案。
所以子類別攔截那一次指派——依賴基底的私有欄位，一般是壞交易，這裡不是：
那個檔案由 E1-C 的 bundle 逐檔綁 hash，**它不可能在沒有人刻意解除一個已出貨
判定的情況下改動**。而且依賴是釘住的：基底若不再指派，`clientReplacements`
留在 0，測試會說。複製五百行 checkpoint 與 generation 邏輯才是比較大的風險。

**2.4 的頁面做完之後，順手抓到一個已經出貨的缺陷。**
`demo-structure-app.js` 遷到產品 v2 之後仍呼叫 `client.placeCaretByClick`，
而那是**診斷客戶端**的方法。所以那一頁**每一次點擊都丟 TypeError**。
上一輪檢查過「開得起來」——而開不起來正是它前一次壞掉的方式。

> **這是同一個教訓的第三次**：檢查上一次壞掉的地方，不等於檢查這一次會壞的地方。
> 新的通用檢查 `product-page-calls.test.mjs` 把頁面裡 `client.foo(` 的名字抽出來
> 問類別有沒有；`node --check` 看不到，因為 `client.foo()` 不管 `client` 是什麼
> 都是合法語法。

**兩個瀏覽器都實際跑過**：`tools/run_e2_c_page_smoke.py` 各 `ok: true`——
開到 `ready`、用頁面自己的指標處理器放游標（各 4 ms）、
用頁面自己的工具列按「標題」（47 ms）、revision 0 → 1。

## 本段我犯的錯

| | 怎麼抓到的 |
|---|---|
| 可達性 stub 回 `{reached:true}`，被殼層的後置條件擋掉 | **對照組是紅的**——「到得了引擎」和「stub 的回覆能通過驗證」是兩件事 |
| session 對照組的 state stub 少了 `documentHandle`、少了 `selectionText` 等欄位 | 同上，對照組紅了兩次才對 |
| 規格 v1 把「客戶端能送出動作」當成產品修好了 | **對抗性審查**，三項都指著同一件事 |
| 注入腳本用 `return` 但 Chrome 那條路是 evaluate 運算式 | 跑起來就是語法錯誤 |
| 用 `pkill -f` 停伺服器，樣式打到自己的 shell | 指令回 144——**這條在上一份交接就寫過，我又做了一次** |
| 產品頁面用 harness 的 `__probe_metrics` 慣例當載入判準 | navigate 逾時；改成等 `readyState`，產品不該為了 runner 帶欄位 |

---

## 第四段：D0 過、D1 23／28、finding 045，以及外部裁決

- **D0**：兩瀏覽器九格全過。十五個動作由**單一客戶端**在真引擎上到達
  （不是樹裡所有殼層的聯集），逐欄比對整個請求信封；分析器 11 個突變全紅。
- **D1**：三輪 × 兩瀏覽器，**23／28**，比較投影 81 項逐項相同——**連紅的那幾格
  都相同**，所以不是 flake。
- **[finding 045](../findings/045-inline-format-actions-discard-the-enabled-flag-and-toggle.md)**：
  四個 inline 格式動作把 `enabled` 丟掉、派送不帶參數的 `.uno:Bold`，而 core 的
  slot 是 `Toggle = TRUE`。**`enabled: false` 關不掉格式。** 是 030 缺陷一的同一
  形狀，030 只修了兩個清單命令。**出貨的 E1 契約走同一段程式碼。**

### 外部裁決（fable）

使用者裁示由 fable 判定 finding 045 的處置。**agent id `a61d0b4b0308073bb`**
（之後要續談用 `SendMessage`；compact 之後那個 agent 不會留著，要重開就得重帶脈絡）。

送去的四個選項：修（照 030 送參數）／縮限（manifest 寫明是 toggle）／只記錄
（判 `E2_STOP_OR_RESCOPE`）／一次 relink 兩件一起做。並明確請它先查我的前提——
過去兩次它都是在前提上抓到東西，那比回答問題本身更有價值。

**這次的關鍵成本**：任何 relink 都會讓 E2-B 的 132 個 run **以及剛做完的 D0／D1
證據**一起斷綁。所以在裁決之前不往 D2 走——不然做出來的東西可能整批作廢。

### 本段又犯的錯（D1 harness 那三個）

| | 怎麼抓到的 |
|---|---|
| 判準拿被編輯過的錨點去認段落，於是回報「段落不見了」而它就在那裡、少一個字 | **去看存出來的文件**，不是去想 |
| 每一格拿「開檔時的樣子」當 before 圖，等於把前面每一格的編輯都算到這一格頭上 | 分段那格報「split 改變了文件文字」 |
| before 圖存在建立手勢**之後**，存檔擾動了選取 | delete 回 `EDITOR_BOUNDARY_UNSUPPORTED`，而同一段序列沒有那次存檔時是好的 |

> **這三個都是判準錯不是產品錯，而同一輪裡的另外四格是產品錯。**
> 分辨的方法只有一個：**去讀存出來的位元組。**
