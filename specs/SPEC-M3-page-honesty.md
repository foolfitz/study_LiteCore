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

## 6. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-09-29 | 初版。依據：finding 107（同日量到）、finding 106、擁有者對唯讀的裁示 A。寫在頁面、殼層、宿主改動與 runner 之前。 |
