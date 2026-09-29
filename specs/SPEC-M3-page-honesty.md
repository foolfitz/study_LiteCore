# SPEC M3：頁面誠實化（107 離頁守衛、106 按住 Ctrl+S、唯讀只能看）

> 2026-09-29 立。判準寫在任何實作、runner 與瀏覽器量測之前（第 4 節）。
> 證據標記照 `doc-conventions`：**已觀察**＝量過、**讀原始碼**＝沒量、**推論**。

## 1. 為什麼要有

三件事都要換產品頁的身分（`e2-editor-app.js`，現為 `fbfb59a4…`）。頁面一換，所有綁在它上面的計數判定都要重跑，
所以三件併成一輪，只重跑一次：

- **finding 107（資料遺失，已觀察 Chrome 3/3）**：編輯之後沒按儲存就離開，頁面什麼都不問，修改無聲消失。
- **finding 106（已觀察）**：按住 Ctrl+S，每一次鍵盤重複都是一次完整存檔（一秒 30 個 PUT，0.2.2 之後拖約 35 秒）。
- **唯讀模式（擁有者 2026-09-29 裁示 A：只能看）**：唯讀檔現在可以編輯，存檔被 403 之後宿主另存副本到使用者自己的資料夾、
  事後才說。改成開成檢視模式：能讀、能移動游標、報讀照常，不能修改也不能存檔。

## 2. 事實

- **已觀察**：107 的量測（`findings/evidence/m3-unsaved-leave/`）；106 的量測（`findings/evidence/m3-same-second/`
  條件 4）；讀回成本到 52.4 MB 都在一個 PUT 之內（`findings/evidence/m3-same-second/readback-size/`），**本輪不動宿主的讀回**。
- **讀原始碼**：殼層 `snapshot.dirty` 由佇列在每一個 `mutation: true` 的項目完成時設起（`editor-shell/editor-session.js:309`），
  在 `save()` 的 finalize 清掉（`:577`，宿主收下之前）；從檢查點回復時設成 `useCheckpoint`（`:193`）。
- **讀原始碼**：基礎類別的改內容方法都標 `mutation: true`（`commitText`、`delete`、`insertBreak`、`setInlineFormat`、`undo`），
  `moveCharacter` 不標；子類別 `NarrowEditorV2Session.action()` 依 `BOUNDARY_CAPABLE_MOVES`（六個移動）標非 mutation、其餘都標
  （finding 098 的修法），`redo()` 標 mutation（`editor-shell-v2/narrow-editor-v2-session.js:421`、`:485`）。
- **讀原始碼**：宿主遇到 `writable: false` 不上鎖、宿主列寫「唯讀：…存檔會另存副本。」（`js/litecore-editor.js:142-145`）；
  `liteCoreHost.load()` 只回 `{ bytes, name }`。
- a11y 的 cutover 閘門目前 soak 0/12、排在開發最後（`HANDOFF-2026-09-28f`），這次換頁面不作廢任何已押的 soak。

## 3. 改動範圍（先寫死）

- **頁面** `wasm_sdk_probe/web/e2-editor-app.js`（必要時 `e2-editor.html`）：
  - **U（107）**：掛 `beforeunload`，在「有未交出的修改」時詢問。有宿主：`snapshot.dirty` **或**「最後一次 `session.save()` 的位元組
    已交給宿主、但宿主還沒有收下（寫進原檔或另存副本）」。沒有宿主（下載模式）：`snapshot.dirty`（觸發下載＝交出，沿用既有語意）。
    宿主存不出去（stranded）時宿主自己的守衛照舊。
  - **K（106）**：Ctrl+S 的 `event.repeat` 為真時只 `preventDefault()`，不存檔。
  - **V（唯讀）**：`HOST.load()` 回 `readOnly: true` 時進檢視模式：請 session 進 view-only；工具列每一顆 `button[data-action]`
    只有在 session 說它**不改內容**時才保持可按（見下一點），其餘 `disabled`；`#text` 停用；儲存停用；Ctrl+S 只 `preventDefault()`。
- **殼層 v2 子類別** `editor-shell-v2/narrow-editor-v2-session.js`：
  - `setViewOnly(true)` 之後，`_enqueue` 對 `mutation: true` 的項目**不排入佇列**、以 `EDITOR_VIEW_ONLY` 拒絕，不改 state、不擋佇列、
    不進回復。
  - `actionMutates(name)`：`name` 在 `BOUNDARY_CAPABLE_MOVES` 裡回 false，**其他任何名字（含不認得的）回 true**（fail-closed，
    和 `action()` 的旗標同一個來源）。
- **不動**：`editor-shell/editor-session.js`（E1-C 綁定）、引擎、worker、宿主的讀回與間隔。
- **宿主 0.2.3**：`load()` 多回 `readOnly: !config.file.writable`；唯讀的宿主列改成「唯讀：只能檢視，不能修改或存檔。」；403 → 另存副本的
  路徑**保留**（開檔之後權限才被收回時仍會走到）。只動 `js/litecore-editor.js` 與 `appinfo/info.xml`。
- **殼層 generation**：本輪頁面與子類別都改完、審核處置完之後才凍（CLAUDE.md「殼層 generation 要等該輪的殼層改完再凍」）。

## 4. 驗收判準（先於 runner 與任何瀏覽器量測寫下）

新 runner `wasm_sdk_probe/tools/check_m3_page_honesty.py`，dev 實例，Chrome 與 Firefox 各 3 輪，每一格都是全新開檔。

**離頁詢問的觀測法（兩個瀏覽器）**：開檔完成之後，runner 在 `window` 上**最後**加一個 `beforeunload` 監聽器，把
`event.defaultPrevented` 寫進 `sessionStorage`（同源、同分頁，導覽之後讀得到）；「頁面問了」＝這個值為真。Chrome 另外以 CDP
`Page.javascriptDialogOpening` 觀測對話框（真的點擊給使用者啟動，同 `check_m3_locks.py` 的 K10）。**U0 是這個觀測法的正向對照**，
它不成立，U 的其他格一律不算。

### U（107）

| 格 | 做法 | 通過條件 |
|---|---|---|
| U0 對照 | 開檔、編輯、runner **自己**加一個會問的監聽器（在記錄器之前）、離開 | 記錄器讀到 `defaultPrevented` 為真；Chrome 看到對話框 |
| U1 未存 | 開檔、編輯、離開 | 問了（Chrome：對話框，取消後留在頁面；Firefox：記錄器為真） |
| U2 已存 | 開檔、編輯、按儲存（204）、等宿主結束、離開 | **沒問**；伺服器位元組＝送出的位元組 |
| U3 存後再改 | 開檔、編輯、存（204）、再編輯、離開 | 問了 |
| U4 衝突副本 | 開檔、編輯、讓下一次存檔 412（沿用 K12：別人對這個檔送 OCS 解鎖，被拒但 ETag 被改）、存（進衝突副本）、離開 | **沒問**；副本位元組＝送出的位元組 |
| U5 沒改 | 開檔、離開 | **沒問**（「永遠都問」會被這格抓到） |
| U6 下載模式 | 沒有宿主的頁面（`dist/e2-editor.html`）：編輯、離開；再開、編輯、按儲存（下載）、離開 | 第一段問了；第二段沒問 |

### K（106）

| 格 | 做法 | 通過條件 |
|---|---|---|
| K-held | 開檔、編輯、按住 Ctrl+S：30 個 `keydown`、間隔 33 ms、第一個 `repeat: false` 其餘 `true`；等佇列清空 | 宿主紀錄**恰好 1 次**存檔、1 個 PUT、204；30 個 `keydown` 都被 `preventDefault()`（`dispatchEvent` 回 false） |
| K-two | 按存檔按鈕，立刻 Ctrl+S（`repeat: false`） | 恰好 2 次存檔（R2 的成對形狀沒被這個修法吃掉） |

### V（唯讀，擁有者裁示 A）

`lcprobe` 開一份以唯讀分享給他的檔（同 K9 的布置）；可寫對照＝同一份檔以可編輯分享（或 admin 自己的檔）。

| 格 | 做法 | 通過條件 |
|---|---|---|
| V1 開檔 | 開唯讀檔 | 宿主沒有送 `LOCK`；宿主列含「只能檢視」；`ready`；`HOST.load()` 的結果 `readOnly: true`（宿主紀錄） |
| V2 普查 | runner 從頁面讀出**每一顆** `#toolbar button[data-action]`（清單由頁面產生，不寫在 runner 裡），逐顆按；再打字、Backspace、Delete、Enter、Ctrl+V、Ctrl+X、Ctrl+Z、Ctrl+Y、Ctrl+B／I／U、一次 IME 組字提交 | **唯讀**：每一項之後 revision 不變、pending 0、`ready`、沒有 `失敗` 以外的錯誤狀態。**可寫對照**：同一份普查逐項記錄 revision 是否前進。**判準**：可寫時會前進的每一項，唯讀時都不前進；而且可寫對照裡「打字」與至少一顆按鈕會前進（否則普查是空的） |
| V3 關卡 | 殼層單元測試：view-only 下 `_enqueue(..., { mutation: true })` 以 `EDITOR_VIEW_ONLY` 拒絕、operation **沒有被呼叫**；`mutation: false` 照常執行；`actionMutates` 對不認得的名字回 true | 全過；**紅案**：拿掉關卡那一行 → 測試紅；把 `actionMutates` 的預設改成 false → 測試紅 |
| V4 還能讀 | 唯讀檔、多段 fixture：點畫布定位游標、按 ArrowDown | 狀態列出現「定位游標」；`#a11y-para` 的文字換成下一段 |
| V5 不能存 | 唯讀檔：儲存按鈕 `disabled`；送 Ctrl+S | 沒有 PUT、沒有副本；`keydown` 被 `preventDefault()` |
| V6 離開 | 做完 V2–V5 之後離開 | **沒問**；伺服器位元組＝開檔前 |

V2 的鍵盤那半是**手工枚舉**（第 1 節形式三），只當一次性量測登錄；保證住在 V3 的關卡（每一個標 `mutation: true` 的項目，
逐實例）。按鈕那半由頁面產生（形式二）。

### 回歸（新頁面＋新殼層 generation＋宿主 0.2.3；綁定值在任何計數執行之前寫下）

- `LOCKS LAND`（`check_m3_locks.py`）：K1–K8、K11、K12 期望不變。**K9、K10 改寫**，理由：處方換了——唯讀檔不能再編輯，舊的
  「開唯讀檔 → 存檔 → 403」這條路依設計走不到。新形：**K9′／K10′＝開檔時可寫，開檔之後才把分享改成唯讀，再存檔**，期望與原
  K9／K10 相同（403 → 另存副本；K10′ 另存也 403 → stranded、下載、擋離頁）。收回權限之後 PUT 是不是 403 **要先在 shakedown 量**，
  不是的話停手回報，不改期望。舊 K9 的「開唯讀檔」那一半由 V1 接手。
- `VERSIONS CORRECT`、`ASSETS DELIVERED`、`HOST_ENTRY LANDS`、`SAME-SECOND SAVES KEPT`：期望不變，只更新綁定
  （`PAGE_SHA256`、`HOST_COMMIT` 等），綁定寫在計數之前。
- 產品路徑回歸網（`run_e2_c_product_path.py`，v8／v14，沒有宿主）：逐格與上一次的基線相同。
- **任何既有 runner 若因 U 的新守衛而卡在離頁**（它離開時有未存的修改）：那一格的期望要改，**寫下是哪一格、為什麼**，不得靜默
  繞過（例如偷偷先存檔）。在 shakedown 找出來。
- `INSTALLS ELSEWHERE` 不在本輪重跑（第 3 步 H＋J 用最終版本做）。

**每一格「如果永遠沒做」的預設結論**：U、K、V 任何一格沒有計數執行＝那件事沒修好（107／106 維持「未修」、唯讀維持現況），
不因為程式碼寫了就算。

## 5. 明確不承諾

- Firefox 的離頁**對話框本身**沒有觀測（只觀測「頁面要求詢問」）；關分頁、關視窗、重新整理這幾條離開的路不量（同一個監聽器，推論）。
- 檢視模式是**用戶端**的保證；伺服器端的保證仍是 Nextcloud 的權限（403），宿主的另存副本路徑保留。
- `mutation` 旗標正確與否只量到今天的清單（V2 的可寫對照）；之後新增的動作若標錯旗標，V3 不會知道——那是 V2 重跑的事。
- 「按住 Ctrl+S」只量合成的 `keydown`（同 106），不量真鍵盤的自動重複延遲。

## 7. 審核之後的修訂（2026-09-29，任何實作、runner 與瀏覽器量測之前）

對抗性審核（opus，唯讀）26 項，原文與逐項處置在 `findings/evidence/m3-page-honesty/review-2026-09-29-opus.md`。
BLOCKING 的四項（1–4）我讀過它引用的原始碼、都成立。本節**取代**第 3、4 節裡被點名的部分；原文留著，沒被點名的照舊。

### 7.1 改動範圍的修訂（取代 §3 的 U 條件與宿主範圍）

- **「未交出的修改」的定義**（取代 §3 U 的條件）：`snapshot.dirty` **或** `snapshot.pending > 0` **或**「有一次存檔已經被要求、
  還沒有結束」。有宿主時「結束」＝`HOST.save()` resolve 或 reject（**結束，不是收下**：頁面分不出副本存到了還是 stranded，
  兩者用同一個 code；stranded 由宿主自己擋）。沒有宿主時「結束」＝下載的 anchor 被點了。從要求存檔的那一刻起算，所以涵蓋
  `session.save()` 完成到 `HOST.save()` 開始之間那段 `renderDocument()`（審核第 1 項）。`pending > 0` 涵蓋第一個編輯還在引擎裡的
  那段（第 8 項），代價是游標移動進行中離開也會問一次。**不得用 revision 判斷**（099 的類型；Worker 重開時 revision 歸零）。
- **有宿主時，宿主是唯一決定的監聽器**（審核第 2 項）：宿主的 `beforeunload` 比頁面早註冊，而且不擋的時候會先放鎖；頁面若自己
  再擋，使用者選「留下」時手上已經沒有鎖、下一次存檔變衝突副本。所以宿主 0.2.3 加 `liteCoreHost.watchUnsaved(fn)`：頁面把上面的
  判斷交給宿主；宿主的 `beforeunload` 在 `stranded || inFlight > 0 || fn()` 時擋、**不放鎖**，其餘才放鎖；每一次擋都記下理由
  （`stranded`／`inFlight`／`page`）。頁面有宿主時只走 `watchUnsaved`；宿主沒有這個方法時頁面自己掛監聽器並在宿主紀錄旁記下
  （版本不配對，不是出貨組態）。沒有宿主時頁面自己掛。
- **宿主 0.2.3 的範圍**（取代 §3 的宿主那一點）：`js/litecore-editor.js` 與 `appinfo/info.xml`；`load()` 多回 `readOnly`；
  `watchUnsaved`；擋的理由記錄；唯讀的宿主列文字。**不修**：`tokenOnServer` 的 `.text()` 丟例外時存檔以「沒有副本也沒有 stranded」
  結束（審核第 11 項，讀原始碼，走不到的修法不寫——059 的教訓），登錄在 §7.5。
- **頁面**：每一顆 `#toolbar button` 帶 `data-mutates`（`session.actionMutates(dataset.action ?? id)`，不認得的＝會改）；檢視模式下
  `disabled` 由它決定，而且寫在 `updateGestureAffordance()` 裡（它每次狀態更新都重設按鈕，第 15 項）；`EDITOR_VIEW_ONLY` 在
  `run()` 與輸入 trace 的 toast 都對應成一句「唯讀：只能檢視」。
- **§1 的「報讀照常」**限於提供段落文字的 profile；出貨的 v8 沒有（`#a11y-para` 是固定句），v8 上能保證的是「能移動游標」。

### 7.2 離頁的觀測法（取代 §4 的觀測法段落）

開檔完成之後，runner 包住 `Event.prototype.preventDefault` 與 `BeforeUnloadEvent.prototype.returnValue` 的 setter：對
`type === 'beforeunload'` 的每一次呼叫，把 `{nonce, what, value, stack}` 追加進 `sessionStorage` 裡**這一格自己的 nonce** 底下；
另加一個監聽器記 `{nonce, fired: true}`。判讀：

- **「問了」**＝有一筆 `preventDefault` 或非空 `returnValue`；**是誰問的**看 stack（`litecore-editor.js`＝宿主、`e2-editor-app.js`＝頁面、
  runner 自己的腳本＝runner）。
- **沒有 `fired` 那一筆＝這一格不算過**（不是「沒問」）。負向的格（沒問）要 `fired` 在、而且沒有任何一筆 ask。
- Chrome 另外以 CDP 對話框觀測（真的點擊給使用者啟動）。Firefox 在 WebDriver classic 下自動接受，所以 Firefox 只有記錄器。

### 7.3 判準的修訂

| 格 | 修訂（取代同名格或新增） |
|---|---|
| **U0**（取代） | **不編輯**，runner 自己加一個會問的監聽器，離開：記錄器看到 ask、而且**只有** runner 的 stack。它不成立＝**同一個瀏覽器同一輪**的 U 格一律不算。 |
| **U1**（取代） | 編輯、離開：宿主紀錄多一筆擋、理由含 `page`；ask 的 stack 是宿主。Chrome：對話框、取消；**宿主鎖仍是 `held`、伺服器 token 與開檔後相同**；再離開一次（leave2），同樣擋、同樣取消；再按儲存：**204 寫進原檔**（不是副本）；再離開：沒問。Firefox：自動接受，記錄器看到宿主的 ask，伺服器檔案＝開檔前。 |
| **U-window**（新增） | 編輯；runner 在 `#s-latency` 上掛 MutationObserver，一出現「儲存 N ms」而宿主紀錄的存檔數還沒增加，就導覽離開：問了（宿主、理由 `page`）。Chrome 取消之後，這次存檔照常結束（204）。 |
| **U2／U4／U5**（補） | 負向：`fired` 在、沒有任何 ask。 |
| **U3**（補） | 頁面的判斷只讀 `dirty`／`pending`／存檔進行中，不讀 revision：殼層單元測試斷言它（改成 revision 比較的突變要紅）。 |
| **U6**（補） | 下載模式：ask 的 stack 是頁面；第二段負向照上。 |
| **U7**（新增） | 按「標題」並在**同一個 task** 裡導覽離開：問了（`pending > 0`）。 |
| **K-held**（補） | 最後一個 `keydown` 之後等 5 秒沒有新的存檔；頁面層的存檔完成次數（runner 在 `#s-latency` 上數「儲存 N ms」）＝1，宿主存檔＝1。 |
| **K-sep**（新增） | 兩個 `repeat: false` 的 Ctrl+S，中間插入一段標記文字，前後相隔 < 300 ms：恰好 2 次存檔、2 個 PUT，伺服器最後的位元組含標記。 |
| **K-two**（補） | 兩個按壓在同一個 evaluate 裡；緊接著讀 `#s-pending`，要 > 0（第二個按壓落在第一次存檔結束之前）。 |
| **V2**（取代） | 普查＝**每一顆** `#toolbar button`（含 `#clear-format`）加 `#text`＋鍵盤那半。**唯讀**：runner 先拿掉每一顆按鈕的 `disabled`（模擬 UI 層失守），再逐項按；每一項之後 revision 不變、pending 0、pill `ready`、`#toast` 為空或含「唯讀」。**可寫對照**：同一份普查，事前布置好前提（插入欄位先填字、Ctrl+X 前先用 Shift+方向鍵選一段、Ctrl+V 用帶 `DataTransfer` 的 paste 事件、復原在編輯之後、重做在復原之後）；**每一項都要讓 revision 前進**，只有這幾個例外（理由）：`data-mutates="0"` 的按鈕（移動，本來就不改）、`save`（存檔不改文件）、`open-file`（有宿主時停用）。只有**按鈕那半**是硬判準；鍵盤那半是一次性量測（第 23 項）。 |
| **V3**（補） | 加：被拒時 state 與 pending 都沒變；`restart()` 之後仍是 view-only；測試讀的樹內檔案 sha256＝宿主實際送出的那份。 |
| **V4**（取代） | 多段 fixture、唯讀：點畫布 → `#s-latency` 符合 `/^定位游標 \d+ ms$/`；ArrowDown → 符合 `/^下移一行 \d+ ms$/`，而且 `#sink`（跟著游標走）的 top 嚴格變大；pill `ready`。 |
| **V7**（新增） | 唯讀、至少一次狀態更新之後（例如一次游標移動）：每一顆 `#toolbar button` 的 `disabled` ＝（`data-mutates === "1"`）；`#text` 停用；`move-character-left/right` 可按。 |

### 7.4 K9′／K10′ 的判定式（取代 §4 回歸段「期望與原 K9／K10 相同」）

布置：`lcprobe` 開的檔在開檔時**可寫**（K9′：直接分享給他、權限 3；K10′：放在分享給他的資料夾裡、權限 3）；編輯；runner 以
admin 把那個分享改成權限 1，並**讀回**確認已是 1；存檔。

- 改寫的判定式：開檔時宿主**有** `LOCK` 且 `held`（取代「沒有送 LOCK」）；收回權限的那一刻伺服器 `nc:lock` 是 1；存檔的 attempts
  ＝`[(403, True)]`（**帶 token**，取代 `(403, False)`）；開檔時宿主列**不**含「唯讀」（取代「含唯讀」）。
- 照舊的判定式：K9′ 一份「另存副本」在收件人自己的資料夾、位元組＝送出的；頁面 `存回 失敗`＋副本檔名；擁有者的檔沒變。K10′ 副本也
  403、`failed`；stranded 的宿主列；下載鈕；leave1、leave2 **各有一筆宿主的擋、理由含 `stranded`**（第 12 項）。
- wire order（`check_m3_locks.py:731`）：K9′／K10′ **不再豁免**。
- 紅案：刪掉「readonly: sent a LOCK（host record／wire）」兩個；新增「收回沒生效（讀回仍是 3）」「PUT 沒帶 token」「PUT 是 412 不是 403」
  「K10′ 的擋沒有 `stranded` 理由」；「副本位元組不同」「擁有者的檔變了」照舊。
- **每一趟**的前提：收回之後的 PUT 是 403。是 412（改權限動了 ETag）＝那一趟走的是別條路，**算紅**，停手回報，不改期望。

### 7.5 登錄（不在本輪修，也不當判準）

- **Firefox 的「問了才離開」**：宿主在擋的時候不放鎖，使用者選「離開」之後只剩 `pagehide` 的 UNLOCK——finding 105 那條沒修的路，
  現在每一次帶著未存修改離開都會走到。解法（例如 `sendBeacon` 到 app 自己的解鎖路由）是新機制，不在本輪。
- `tokenOnServer` 的 `.text()` 丟例外 → 存檔以「沒有副本也沒有 stranded」結束、沒有守衛（讀原始碼）。
- V2 量的是 revision，不是內容：runner 拿不到 module 範圍裡的 `session`，為了測試給產品加除錯把手是為測試改產品。這裡 revision
  夠用的理由：關卡在**排入佇列之前**拒絕；會改內容卻不動 revision 的路（`failFormatBarrier`）只在 mutation 操作**裡面**跑。
- 下載模式下切換範例文件或開本機檔，會丟掉未存的修改而不問（同 107 的類型；M3 產品有宿主時兩個選擇器都停用）。
- `placeCaret` 的點擊標為非 mutation，但 LOK 的點擊可能改內容（例如核取方塊內容控制項）——推論，未量。
- 跨 Worker 回復的 U3（revision 歸零之後）沒有格；由 U3 的單元測試擋「改用 revision」。

### 7.6 回歸的綁定（取代 §4 回歸段「只更新綁定（…等）」）

要改的常數**就這四個**：`check_m3_locks.PAGE_SHA256`、`check_m3_assets.PAGE_SHA256`、`check_m3_versions.HOST_COMMIT`、
`check_m3_same_second.HOST_VERSION`（`check_m3_host_entry.py` 沒有寫死的綁定）。`check_m3_versions`、`check_m3_assets`、
`check_m3_host_entry`、`check_m3_same_second` 的 diff 只能碰這幾行；`check_m3_locks` 的 diff＝那一行加 §7.4。**其他任何需要改的
地方**：停手，先把哪裡、為什麼寫進本節，才跑。

**離頁的靜態普查**（第 22 項）：任何 shakedown 之前，逐一列出每一支 runner 每一格離開頁面時是否帶著未存的修改；結果附在本節之後。

### 7.7 離頁靜態普查的結果（2026-09-29，唯讀 Explore agent，任何 shakedown 之前）

對象：`check_m3_locks`、`check_m3_versions`、`check_m3_assets`、`check_m3_host_entry`、`check_m3_same_second`、
`run_e2_c_product_path`（下載模式）。逐一看每一個讓頁面離開或換文件的點：當下有沒有未交出的修改、Chrome 有沒有使用者啟動、
出現詢問時 runner 會怎樣。**沒有任何一點會卡死**（Chrome 的 `Browser.close` 不跑離頁詢問；Firefox 的 WebDriver 自動接受）。

- **會改變結果的只有一處：`check_m3_assets` 的 K2**（兩次開檔都做了段落動作、沒存，就 `leave_and_watch` 導向 Files）。
  Chrome 沒有使用者啟動，不跳對話框、導覽照走；但 0.2.3 的宿主會以 `page` 為由擋、**不放鎖**，只剩 `pagehide` 的 UNLOCK。
  Chrome 的 `pagehide` UNLOCK 實測 4/4 會到；**Firefox（該 runner 開著 HTTP 快取）正是 finding 105 修法之前的那條路**，
  K2-5（離頁 10 秒內鎖放掉）很可能轉紅，第二次開檔可能遇到 423。**處置待決（計數之前）**，選項：
  A）K2 在離開前先存檔——K2 量的是資產派送，不是離頁語意；帶著未存修改離開這件事改由本規格的 U1 量；
  B）不改 runner，K2-5 在 Firefox 的紅登錄成 105 的後果、改期望；
  C）宿主在「只有 `page` 理由」時仍先放鎖——使用者選「留下」就回到審核第 2 項的問題（手上沒有鎖），不採用。
  傾向 A，理由寫在上面；改的是 runner 的步驟，§7.6 說「其他任何需要改的地方先寫進本節」，這裡就是那一筆，決定之後再動。
- `check_m3_locks` 的 readonly／nowhere：照 §7.4 改寫（普查也確認舊的 nowhere 在 0.2.3 下 leave1 會真的離開，接著
  `real_click("#litecore-host-download")` 在 Files 頁上會丟例外）。
- `check_m3_locks` hold、`check_m3_versions`、`check_m3_host_entry`、`check_m3_same_second`：正常路徑都是存完才走，**否**；
  只有存檔逾時的失敗路徑才會帶著未存修改離開。
- `run_e2_c_product_path`：頁內換文件（`OPEN_FILE`、`SWITCH_FIXTURE`、長文件那幾臂）會丟掉未存的修改——那不是導覽，不觸發
  `beforeunload`，行為與改動前相同（§7.5 已登錄）；結尾的 `session.close()` 在 Firefox 帶著未存修改，WebDriver 自動接受，不影響結果。
- 普查順帶指出一個**修法本身的時序瑕疵**，已修（讀原始碼確認）：`savesUnsettled` 原本在 `run("存回")` 重繪完才歸零，比 runner
  等的「存回 N ms」晚一次繪製；現在在 `HOST.save()` 結束（或下載交出）的那一刻歸零。

### 7.8 `check_m3_assets` K2 的處置：裁決 A′（2026-09-29，fable 代擁有者裁決，任何 runner 改動之前）

**取代** §7.7 第一點的「處置待決」；**取代** §7.6 對 `check_m3_assets` 的 diff 上限——該 runner 的 diff＝`PAGE_SHA256` 一行加本節第 2–6 條。
擁有者 2026-09-29 授權 fable 代為裁決這一題；題目、事實清單（F1–F10）與原始裁決文字留在本 session 的委派紀錄，此處是可執行的摘要。

**裁決：A′。**K2 在每一次離開前先存檔，並且**每一次**自證那次離頁沒被攔；另外登錄一次性的量測（不是閘門判準）。B、C 駁回。

**理由（給擁有者，原文照貼）：**
K2-5 這一格是 finding 105 修法的回歸網：它問的是「沒被攔下來的離頁，在 Firefox 開著快取時，鎖有沒有在 10 秒內放掉」，修法就是在這條路上量到 12/12 的。宿主 0.2.3 之後，帶著沒存的修改離開會被攔下來、不走這條路；K2 以前沒存就走，是因為舊宿主不會攔，不是因為 K2 要測「沒存就走」。所以讓 K2 離開前先存檔，是把它放回它本來就在量的那條路。改成 B 的話，K2-5 在 Firefox 會變成在量一條已登錄、還沒修、大約一半會失敗的路，等於拆掉回歸網；而且鎖一卡住，runner 下一輪的上傳（`check_m3_assets.py:379`，在 try 之外）會直接讓整份報告當掉。「沒存就走」由本規格的 U1 量；「沒存就走＋Firefox＋快取開」目前沒有任何計數執行量得到——這不是 A 造成的缺口（K2 從來沒量過被攔下來的離頁），但 0.2.3 讓它變成每一次未存離開都會走到的路，所以另外登錄一次性的量測，用既有探針的 edit 臂跑 12 次，把 105 裡「約一半」那句從推算換成數字。先存檔這一步要公開寫在三個地方、runner 要自己證明那一次離頁確實沒被攔（存檔 204、離頁紀錄裡沒有 guard），否則就真的成了規則要禁止的「偷偷先存」。

**與 §4 回歸段那條規則（「不得靜默繞過（例如偷偷先存檔）」）的關係，明寫**：那條規則的觸發條件是 runner「卡在離頁」，§7.7 已記下沒有任何 runner 會卡住，而且 K2 的**期望不變**，所以規則的字面沒有被觸發；它的正面處方（「改那一格的期望」）是 B 形的，這裡**不照它走**，理由如上。它點名的惡行（偷偷先存）靠三件事避開：存檔寫在三處（本節、`SPEC-M3-asset-delivery.md` 的修訂紀錄、finding 105），以及 runner 逐次證明離頁沒被攔（下面第 4 條）。

**執行條件**（逐條，別人可查）：

1. 本節先落地，才動任何 runner。
2. `check_m3_assets.py` 的 `run_browser`：每次 `open_and_smoke` 之後按儲存，等宿主 `saves` 的最後一筆 `settled === true`（同 `check_m3_host_entry.saves_reached`），再等狀態列 `存回 N ms`；記下 `saved`（狀態與宿主那一筆存檔）與 `secondsDoneToLeave`（不設門檻）。**`open_and_smoke` 本身不動**——`probe_m3_leave_unlock.py:35` import 它，它的 edit 臂必須繼續帶著未存修改離開。
3. 離開前裝上本規格的離頁記錄器（`check_m3_page_honesty.RECORDER`／`READ_RECORD`，import 不複製），離開後讀回存成 `leftRecord`。
4. `score_run` 加兩條，前綴 `K2 instrument`：（a）離頁前的存檔沒有落地（第一次嘗試不是帶 token 的 204，或狀態列不符 `^存回 \d+ ms$`）；（b）離頁被攔或沒有 `fired`（`leftRecord` 要有一筆 `fired`，其 `lastGuard` 為 null、`guards` 為 0 或 null）。K2-1～K2-5 的字串與 `PLAN` 逐位元不變。
5. 紅案加三個：存檔 412；`fired.lastGuard` 改成 `{"reasons": ["page"]}`；拿掉 `fired`。在 0.2.3 上第一份乾淨的 shakedown 上跑 `--red-cases`：這三個以 `K2 instrument` 轉紅，既有的每一個仍紅。
6. 模組 docstring 的 K2 一行改成「open from Files, smoke, save, back to Files, open again, smoke, save, back」。
7. `specs/SPEC-M3-asset-delivery.md` 修訂紀錄 append：K2 每次離開前先存（理由＝上文）；K2-5 現在讀的是「沒被攔的離頁 10 秒內放鎖」（105 修法量的那一臂）；K2 的離頁比探針晚一個存檔（記成 `secondsDoneToLeave`，登錄差異、不設門檻）；§3.5 的殘留那句照舊成立——沒有計數執行量被攔的離頁。
8. finding 105 append（時間軸＋「沒有修到的一條路」底下）：K2 只量沒被攔的離頁（0.2.3 之前沒被攔是因為 0.2.2 不因編輯而攔，現在是因為它先存）；第 9 條登錄與其預設結論；狀態列維持「未量」直到第 9 條做完。
9. **一次性量測（登錄，不擋任何閘門）**：`probe_m3_leave_unlock.py` 加上本規格的記錄器（smoke 之後裝、導覽之後讀）；臂 `firefox:warm:edit`（0.2.3 上會被攔）與 `firefox:warm:none`（正向對照，不被攔），各 `--repeats 12`；宿主 0.2.3 最終 commit、頁面＝釘住的 `PAGE_SHA256`。edit 臂的 `fired.lastGuard.reasons` 不含 `page`、或 none 臂出現擋，該次作廢並記為儀器失敗。記錄：每臂 10 秒內放鎖的次數、每次的 UNLOCK 數、`secondsDoneToLeave`。產物 `findings/evidence/m3-assets/leave-unlock-<UTC>.json`＋README 一列，數字寫進 finding 105 取代「約有一半」。不得與任何 M3 runner 同時跑。建議在 0.2.3 的 release archive（H＋J）之前做；時機由擁有者定。**如果永遠沒做**：105 的「約有一半」維持為從修法前 6/13 那一臂推算的外插，狀態列維持「未量」，沒有任何閘門結論依賴它。
10. `check_m3_assets.py --label shakedown` 在 0.2.3 上兩個瀏覽器各至少 1 次，**在釘 `PAGE_SHA256` 與任何計數執行之前**：第二次開檔（開的是存過的文件、再做一次同一個段落動作）K2-4 乾淨、兩條 instrument 乾淨、第 5 條的紅案全紅。
11. 「未存就離開由 U1 量」這句話，要等 U1 在**兩個**瀏覽器都有計數格才成立；在 Firefox 的 U1 shakedown 落地之前，任何地方都不寫「U1 涵蓋它」。
12. 登錄（不是條件）：`run_browser` 的上傳在 `try` 外，任何被卡住的鎖（真的 105 回歸）會讓報告當掉而不是把 K2-5 判紅。修它超出本輪 §7.6 的 diff 上限，登錄為已知的儀器極限。

### 7.9 本規格 runner 的 shakedown 逼出的修正（2026-09-29，Chrome 第一輪，任何計數執行之前）

判準沒有改；改的是 runner 的步驟（瞄準點與前提），理由逐條寫下。證據在 `findings/evidence/m3-page-honesty/shakedown/`。

- **V4 與 V2 的瞄準點改成文件第一行**（取代 runner 原本的畫布 y＝0.28）。**已觀察**（`2026-09-29T091816+0000.json`）：兩個 V 臂都在普查開始之前死掉——y＝0.28 在這份 fixture 的文字下方（五段文字的墨帶在畫布高度的 0.10–0.21），點下去游標落在**最後一行**，接著 ArrowDown 就是 finding 096（出貨的 v8 在末行按下鍵，30 秒逾時、session 進 `recoverable-error`）；可寫對照也一樣死，所以不是唯讀關卡的問題。對照（scratchpad 診斷，同一個 dev 實例）：點第一行再 ArrowDown，`下移一行 38 ms`、`ready`、`#sink` top 497→519。runner 現在開檔後先讀畫布墨帶（`TEXT_LINES`：每列暗且不透明像素 >2、至少 5 列高），瞄第一行的中線；找不到兩行以上就讓那一格明確失敗。V4 的判準（`下移一行 N ms`、`#sink` top 嚴格變大）沒有規定點哪裡，所以不改判準。
- **這件事對產品的意思**（登錄，不修）：M3 的 Nextcloud app 服務的是 `e2-editor-v8`（`MANIFEST.json` 的 `source.profile`，wasm `4a2710bb…`），所以在 M3 產品裡點在文字下方再按下鍵，會照 096 死掉。096 的引擎修法在 v14，沒有出貨。
- **V2 可寫對照的 `delete-forward` 前提：先把游標左移一格**。**已觀察**（`2026-09-29T093035+0000.json`）：游標在段尾時按前刪＝跨段刪除，殼層依契約回 `EDITOR_BOUNDARY_UNSUPPORTED`、session 進 `restart-required`（`SPEC-E1-C-editor-validation.md:139`，finding 016 的修法），後面每一項都被擋。這屬於 §7.3 V2 的「事前布置好前提」，不是豁免。修正後（`2026-09-29T093656+0000.json`）可寫對照 17 顆會改內容的按鈕逐一前進。
- **可寫對照裡的 `move-character-left/right` 顯示「失敗」**：那時有一段範圍選取（格式那幾項前拖出來的），頁面本來就停用移動鍵，runner 強制拿掉 `disabled` 去按，session 以 `EDITOR_FORMAT_GESTURE_UNSUPPORTED` 拒絕、文件沒變、狀態仍 `ready`——設計好的手勢遮罩。移動依 §7.3 本來就豁免「要前進」；「移動能用」由唯讀臂的 V4 與 V7 量（唯讀臂沒有選取，兩個移動都成功）。
- **K-two 的實作與 §7.3 的字面不同（交接文件第 3 項，計數之前登錄）**：§7.3 寫「緊接著讀 `#s-pending`，要 > 0」；runner 實作的是「第二次按壓的宿主時鐘時間＜第一次存檔 PUT 的 `respondedAt`」（`check_m3_page_honesty.py` 的 `PAIR_AT` 與 K-two 評分）。理由：`saveOnce` 在之後的 microtask 才開始，同一個 task 裡讀 `pending` 可能還是 0，那個讀法會把一個真的落在存檔之前的第二次按壓判成沒有。兩者要證的是同一件事（第二次按壓落在第一次存檔結束之前），實作的讀法直接比時間。

### 7.10 紅案與突變普查逼出的補強（2026-09-29，任何計數執行之前）

判準的文字都沒改；改的是**量它的工具**，因為工具量的比判準說的少。三件都是自己找到的，不是審核。

- **U3 的單元測試有一個它抓不到的突變（已觀察）**。U3 要求「改成 revision 比較的突變要紅」。重跑上一輪的四個紅案時多加了第五個：
  用 `!==` 比 revision（「revision 不是存檔時那個號碼就算未存」）——**42 個測試全過**
  （`findings/evidence/m3-page-honesty/unit-red-cases/2026-09-29-unit-red-cases-before-strengthening.json`）。
  它在產品裡的失敗：回滾到檢查點之後新 Worker 的 revision 從 0 重算，再改到跟上次存檔同一個號碼，頁面就判成「已存」、離開不問
  （099 那一類）。處置：finding 107 那個單元測試加兩句斷言——回滾之後 `set-bold` 到 revision 回到存檔時的號碼，`hasUnsavedEdits()`
  仍須為真。補強後五個突變全紅、各紅在自己那一句（`…-after-strengthening.json`）；v2 套件 112/112、基礎殼層 65/65。
  **產品程式碼沒動**（`narrow-editor-v2-session.js` 仍是 `747eea71…`）；動的是測試檔。
- **V2 的普查可以空著過（讀原始碼）**。§7.3 寫「否則普查是空的」，但評分只檢查「列出來的按鈕都前進／都不前進」，普查一列都沒有時兩臂都綠。
  補：兩臂都要求普查涵蓋頁面列出的每一顆按鈕（`controlsAtCensus`，由頁面產生，第 1 節形式二），`open-file` 依 §7.3 除外，且清單非空、含
  `insert-text`。
- **U7 沒驗「是 pending 讓它問」（讀原始碼）**。§7.3 U7 寫「問了（`pending > 0`）」，但評分只看有沒有問；那一下動作若已完成、是 `dirty`
  讓它問，U7 照樣綠，而那是 U1／U3 的事。補：記錄器在 `beforeunload` 的那一刻讀 `#s-pending`，U7 要求它 > 0。
- 紅案（第 4 步）：`check_m3_page_honesty.py --red-cases REPORT…`，每一條判準一個突變、必須紅在**它自己**那一條（比對問題字串），另加
  「U0 不成立時同瀏覽器同輪的 U 格不算」一個報告層的紅案。乾淨基底取自最終版 runner 的 shakedown。

## 6. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-09-29 | **加 §7.10：量測工具的補強。**U3 的單元測試抓不到 `!==` 版的 revision 比較（量到 42/42 全過），補兩句斷言後五個突變全紅；V2 普查不得為空（涵蓋頁面列出的每一顆按鈕）；U7 要在離頁那一刻驗 `pending > 0`；新 runner 加 `--red-cases`。判準文字沒改、產品程式碼沒改。 |
| 2026-09-29 | **加 §7.8、§7.9。**§7.8：`check_m3_assets` K2 的處置由 fable 代擁有者裁決＝A′（K2 離開前先存、逐次自證沒被攔；另登錄一次性量測「Firefox 快取開、被攔之後離開」×12，不擋閘門），取代 §7.7 的「處置待決」與 §7.6 對該 runner 的 diff 上限。§7.9：Chrome 第一輪 shakedown 逼出的 runner 修正——V4／V2 瞄準第一行（y 0.28 落在末行、撞 096）、`delete-forward` 先左移一格（段尾前刪是契約上的結構邊界）；可寫對照的移動被手勢遮罩拒絕是設計；K-two 的實作讀法登錄。判準都沒改。 |
| 2026-09-29 | **加 §7.7：離頁靜態普查的結果。**唯一會改變結果的是 `check_m3_assets` K2（帶著未存修改離開 → 0.2.3 不放鎖 → Firefox 走 105 的舊路），處置待決、傾向 A（K2 離開前先存）；順帶修掉 `savesUnsettled` 晚一次繪製才歸零的時序瑕疵。 |
| 2026-09-29 | **加 §7：對抗性審核（opus，唯讀）之後、任何實作之前的修訂。**處置全表在 `findings/evidence/m3-page-honesty/review-2026-09-29-opus.md`。判準層：未交出的定義改成「dirty 或 pending 或存檔未結束」；有宿主時由宿主唯一決定（`watchUnsaved`，擋時不放鎖）；觀測法改成包住原型並以 stack 歸屬、缺紀錄算不過；U0／U1／V2／V4 取代，U-window／U7／K-sep／V7 新增，K9′／K10′ 判定式逐條寫出；回歸的綁定列舉成四個常數。事實層：§1 的報讀限於提供段落文字的 profile。登錄六項（§7.5）。 |
| 2026-09-29 | 初版。依據：finding 107（同日量到）、finding 106、擁有者對唯讀的裁示 A。寫在頁面、殼層、宿主改動與 runner 之前。 |
