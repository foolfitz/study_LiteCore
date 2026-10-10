# SPEC M3：段落交界不再丟資料、宿主不再蓋掉 Nextcloud、正式介面（109、110、A3）

> 2026-10-06 立。判準與預測寫在任何**計數**執行之前（第 4、5 節）。
> 證據標記照 `doc-conventions`：**已觀察**＝量過、**讀原始碼**＝沒量、**推論**。
>
> **順序上的偏差，照實寫**：交接要求「先寫判準再實作」。A1 的殼層與頁面改動、以及第 2 節的開發量測，是在本文件之前做的
> （同一個 session，2026-10-05 深夜到 10-06）。那些量測是開發量測，**不算進任何判準**；判準的滿足只能來自本文件 commit 之後的執行。

## 1. 為什麼要有

擁有者 2026-10-05 在開發實例（宿主 0.2.5）親手測，回報三件事，並選 **A**：三件一起做、M3 的重新計數只付一次
（`handoff/HANDOFF-2026-10-05-owner-chose-a-109-110-production-ui.md`）。

- **finding 109（資料遺失）**：段尾 Delete、段首 Backspace、工具列「⌦ 前刪」在段落交界被引擎拒絕，工作階段變成
  `restart-required`、存檔被拒、唯一的出路載回上次存檔的內容——未存的修改全部消失。
- **finding 110**：宿主把產品頁的 `<style>` 原封不動印進 Nextcloud 的頁面，`body` 規則蓋掉主題背景（頂欄的白色圖示落在淺灰上），
  全域的 `button`／`select`／`input` 規則改寫了 Nextcloud 自己的控制項；沒有關閉鈕。
- **A3**：「前刪、後刪、分段、換行不應該出現在正式軟體裡」——清單其實更長（第 3.3 節）。

不在本輪：**C**（真的支援併段＝引擎改動＋連結）、**B**（只修資料遺失）。

## 2. 事實

- **讀原始碼**：三個丟出 `EDITOR_BOUNDARY_UNSUPPORTED` 的引擎位置都在**派送之前**拒絕：selection barrier
  `verifyAndDispatchSelectionBarrierDelete`（`postUnoCommand` 之前；選取留著，訊息加「start a fresh Worker」）、
  `rejectSelectionBarrierAtDeadline`、a11y core 的語意前置檢查（`startUnoMutation` 之前，什麼都不留）
  （`wasm_sdk_probe/src/probe_engine.cpp` 約 :3396、:3428、:3441、:3813）。所以拒絕當下文件內容＝拒絕前的內容。
- **讀原始碼**：殼層 `recoveryFor` 把這個代碼一律對應到 `restart`；基礎類別依代碼把佇列擋成 `restart-required`
  （`editor-shell/editor-session.js:319`，E1-C 綁定、不可改）；`restart()` 開「比上次存檔新的檢查點」，否則開上次存檔的位元組。
  檢查點只在選取手勢與六個可能卡住的移動之前取（096 的 C 半），刪除之前不取。
- **已觀察（開發量測，不算數）**，Chrome 151 headless，獨立頁面＋假宿主（`load` 給擁有者那份 563,149 位元組的文件、`save` 收下
  位元組），真鍵盤經 CDP，存檔後解開 content.xml 數打進去的標記：
  - 修法前：段尾 Delete、段首 Backspace 都重現 109（`restart-required`、檢查點「無」、存檔 `EDITOR_NOT_READY`）。
  - 修法後：段尾 Delete、段首 Backspace、工具列「⌦ 前刪」三臂都**保住**標記；拒絕當下的檢查點存檔約 0.94 秒、重開約 1.2 秒，
    按鍵到可再編輯約 2.2 秒；重開期間工具列 21 顆按鈕全部停用、之後恢復。乾淨文件（沒打字）也自動重開、不存檢查點。
    段中 Backspace（正向對照）95 ms、世代不變。
  - 也就是交接的 **(a)「拒絕狀態下 worker 還能序列化」成立**——至少在這份文件、這個瀏覽器上。
- **已觀察**：Firefox 157 支援 CSS `@scope`（`CSSScopeRule` 存在；`@scope (#root)` 內的 `button` 規則不碰 `#root` 之外的
  `button`，`:scope` 規則套在 `#root` 上、不碰 `body`）。Chrome 自 118 起支援（**讀規格**，本輪的 S 臂會在 151 上量到）。
- **讀原始碼**：M3 runner 的「頁面身分」是 `e2-editor-app.js` 的 sha256（`check_m3_locks.PAGE_SHA256` 等），
  `e2-editor.html` 不在雜湊網內（finding 094）。A1 一定會換殼層 session（`747eea71…`）與頁面（`fc80050c…`）。
- **讀原始碼**：M3 runner 都用 `button.click()`（隱藏的按鈕照樣能按）與 `textContent` 讀狀態列（隱藏的元素照樣讀得到）。
  **唯一依座標驅動產品頁元素的是 `check_m3_page_honesty.py` 的 `activate()`：`real_click("#text")`**——用來給頁面
  user activation（Chrome 的 `beforeunload` 需要）。`#text` 一藏，矩形是 0×0，點擊落在 (0,0)＝Nextcloud 頂欄。
  另兩支（`probe_m3_unsaved_leave.py`、`probe_m3_save_throw.py`）是一次性探針，不在重新計數之列。

## 3. 改動範圍與選擇

### 3.1 A1（109）：拒絕當下就把內容存成檢查點，能零損失就自動重開

- **殼層** `editor-shell-v2/narrow-editor-v2-session.js`：`action()` 收到 `EDITOR_BOUNDARY_UNSUPPORTED` 時，在 operation 內、
  重新丟出之前呼叫基礎類別的 `_checkpointBeforeSelection`（乾淨或已存過＝不動作；失敗記成 `checkpointError`，不改變呼叫端拿到的錯誤）。
  另加 `restartKeepsContent()`：照 `_openFresh` 的選法算出「重開會打開哪個內容戳記」，等於目前戳記才回 true。
  **不是** `!dirty || hasCheckpoint`：新的檢查點存檔失敗時舊檢查點還在、`hasCheckpoint` 仍是 true，重開會回到較舊的內容。
- **頁面** `web/e2-editor-app.js`：`run()` 遇到這個代碼時，若 `restartKeepsContent()` 為真就自動 `restart()`（不問，因為沒有
  要使用者決定的事），toast 用白話說「目前還不能在段落交界刪除（把兩段合併成一段）。文件沒有被改動」＋重新載入的結果；
  為假（檢查點寫不出來）時不自動重開，照舊由回復通知說明。另外兩件 109 的附帶問題一起修：狀態不是 ready／busy 時工具列的
  按鈕全部停用（只還原自己停用的那些）；此時按鍵不再跳 `EDITOR_NOT_READY` 的 toast。
- **為什麼選 (a) 不選 (b)**：(b)＝有未存修改時每次刪除前先存檢查點。打字會換內容戳記，所以「打幾個字、按一次 Backspace」
  每一次都要付一次完整存檔——在這份文件上約 0.94 秒——而且是為了一個幾乎不發生的拒絕。(a) 只在拒絕真的發生時付一次。
- **代價（照實寫）**：重開後游標回到文件開頭、復原堆疊清空；a11y core 的語意前置拒絕其實不需要新 worker，這裡一樣重開
  （多付約 1–2 秒，不丟東西）。

### 3.2 A2（110）：宿主 0.2.6

- `EditorController::scopedStyle`：產品頁樣式裡的 `:root {` 與 `body {` 各換成 `:scope {`（**各恰好一次、且在規則開頭**，
  否則 500，同既有的「頁面形狀不對就拒絕」）；`templates/editor.php` 把整份包在 `@scope (#litecore-editor-root) { … }` 裡。
- 標題列：宿主 JS 在產品的 `.titlebar` 前端放檔名與「尚未儲存」提示（每 0.5 秒問一次頁面的 `watchUnsaved` 問題，或宿主自己有
  滯留的位元組時顯示），尾端放關閉鈕「✕」。關閉＝`location.assign` 到 Files 裡該檔所在的資料夾
  （`/index.php/apps/files/files/<fileId>?dir=<資料夾>`，**不帶** `openfile`）。離開的詢問照頁面誠實化 §7：宿主的
  `beforeunload` 唯一決定。
- `info.xml` 升 0.2.6（宿主 JS 有改；`?v=` 是 app 版本的雜湊），`occ upgrade`。

### 3.3 A3：正式介面——在宿主藏，不動頁面的位元組

`templates/editor.php` 的宿主樣式藏起：黃色開發說明（`.provenance`）、標題「LiteCore 編輯器／產品 v2 契約，十五個動作」
（`.brand`，由宿主的檔名取代）、範例選單 `#fixture`、「📂 開啟檔案」、◀ ▶、⌫ 刪除、⌦ 前刪、↵ 分段、↳ 換行、
「要插入的文字」＋「插入」、整條狀態列（修訂、佇列、世代、檢查點、上次操作、狀態代碼、檔名——檔名移到標題列），
以及因此相鄰的三條分隔線。

**保留**：↶ 復原、↷ 重做（profile 有的時候）、B I U S、清除格式、標題、內文、• 項目符號、1. 編號、移除清單、儲存 ODT、
狀態膠囊（就緒／處理中／載入中…）、回復通知、宿主列、toast。

鍵盤取代被藏的編輯鈕：Backspace／Delete、Enter（分段）、Shift+Enter（換行）。

**不在本輪：toast 裡的原始錯誤代碼**（例如 `EDITOR_NOT_READY：…`）。109 那一個已改成白話（3.1）。其餘的要動 `describeError`，
而產品路徑回歸網與 M3 runner 有多格以 toast 裡的代碼為錨（`check_m3_host_entry` 的 `CONFLICT`／`HOST_ENTRY_INVALID`、
`check_m3_locks` 的 `CONFLICT` 與副本檔名、產品路徑的 toast 紀錄）；一起改等於重錨好幾格，與「重新計數只付一次、驗證不加碼」
相衝。登錄為工作項。

### 3.4 runner 的一處改動（被 A3 逼出來的）

`check_m3_page_honesty.py` 的 `activate()` 改點 `#state-pill`（兩版宿主都看得見、沒有任何處理器）。理由：第 2 節最後一點。
這是儀器改動，不是判準改動；**預測**頁面誠實化各格結果不變。

## 4. 判準

新 runner `wasm_sdk_probe/tools/check_m3_production_ui.py`，對開發實例（`litecore`）跑，Chrome 與 Firefox 各自一個瀏覽器、
每臂重新登入。文件＝擁有者的 `PMPC指南.odt`（563,149 位元組，sha256 記進報告；不進 repo），每臂重新上傳成 `m3-109 測試.odt`。
點擊用頁面自己的指標處理器（`POINT_AT`，同其他 M3 runner），**鍵盤是真的鍵**（Chrome＝CDP `Input.dispatchKeyEvent`，
Firefox＝WebDriver actions）。座標沿用 `findings/evidence/109/README.md` 已校準的三點。

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **A1-1** | `action()` 每一個 `EDITOR_BOUNDARY_UNSUPPORTED` 拒絕：佇列擋住之前，內容不是已存（`restartKeepsContent()` 為真）就是記下 `checkpointError`；舊檢查點不得被報成保得住。單元測試六條（`narrow-editor-v2-session.test.mjs` 的 finding 109 節）；紅案：拿掉那行檢查點呼叫→紅 3 條，把 `restartKeepsContent` 換成 `!dirty \|\| hasCheckpoint`→紅 1 條（2026-10-06 已跑過） | 逐實例（單元） | — |
| **A1-2** | 使用者的路：B-del（段尾 Delete）、B-bs（段首 Backspace）每瀏覽器各 **3/3**：打標記（真鍵）→滑鼠點到交界→真鍵→不按任何東西等到 `ready`→按儲存→**伺服器上檔案的 content.xml 含標記**；**非空洞**：同一臂的世代從 1 變 2（拒絕真的發生、重開真的發生）。正向對照 B-ctl 每瀏覽器 1 次：段中 Backspace 修訂＋1、世代不變 | 逐實例（每一臂） | 109 維持「未修」 |
| **A1-2 紅案** | 同一支 runner 對**修法前**（宿主 0.2.5、頁面 `fc80050c…`）跑 B-del、B-bs 每瀏覽器各 1 次，必須**紅**（伺服器沒有標記） | 先紅一次 | runner 不得用來宣告 A1-2 |
| **A1-3** | B 臂錄下的每一筆狀態樣本：狀態不是 ready／busy 時，`#toolbar` 的每一顆按鈕都是停用的；每一個 B 臂至少要有一筆這種樣本 | 逐實例（每一筆樣本） | 109 的附帶問題維持未修 |
| **A2-1** | S 臂：在編輯器頁面上把產品樣式表停用前後，`#litecore-editor-root` **之外**每一個元素的計算樣式（固定 18 個屬性）**完全相同**；容器之內至少一個元素不同（非空洞） | 逐實例（頁面上每個元素） | 110 維持未修 |
| **A2-1 紅案** | 同一臂在 0.2.5 上必須紅（`body` 至少一個屬性變了） | 先紅一次 | 同上 |
| **A2-2** | S 臂：編輯器頁面 `body` 的 `background-color` 與 `background-image` 等於同一瀏覽器階段裡 Files 頁的 | 一次量測，兩個瀏覽器各一 | 同上 |
| **A2-3** | P 臂：標題列有檔名與看得見的關閉鈕；沒有未存修改時按關閉→網址路徑是 `/apps/files/files/<fileId>`、`dir` 是該檔的資料夾、沒有 `openfile`、落地頁沒有編輯器、伺服器上的鎖 10 秒內解除；有未存修改時按關閉→宿主問了（`out.guards` 多一筆、原因含 `page`）、使用者選留下後頁面還在 | 一次量測，兩個瀏覽器各一 | 關閉鈕不得宣稱可用 |
| **A3-1** | P 臂：開好之後，`#litecore-editor-root` 內、`#paper` 與 `#toast` 之外，**每一個看得見的控制項**（`button`／`select`／`input`／`textarea`）都在保留集合裡（3.3 的「保留」＋宿主的關閉鈕與下載鈕＋回復通知的按鈕），**每一段看得見的文字**都落在檔名、尚未儲存提示、狀態膠囊、保留的控制項、回復通知、宿主列之內 | 逐實例（頁面上每個看得見的元素） | 正式介面不得宣稱完成 |
| **A3-1 紅案** | 同一臂在 0.2.5 上必須紅 | 先紅一次 | 同上 |
| **A3-2** | P 臂：真鍵在段落中間的 Backspace、Delete、Enter、Shift+Enter 各使修訂＋1 且世代不變；打字後「尚未儲存」在 1.5 秒內出現，存檔落地後 3 秒內消失 | 一次量測，兩個瀏覽器各一 | 被藏的編輯鈕不得藏（退回 0.2.5 的樣式） |
| **R** | 六支 M3 runner 在 0.2.6 上重新計數全過、紅案全紅（PAGE HONEST、LOCKS LAND、VERSIONS CORRECT、ASSETS DELIVERED、HOST_ENTRY LANDS、SAME-SECOND SAVES KEPT）；產品路徑回歸網 v8／v14 與 v54 的 40 PASS／2 NE 逐格相同；`make test-e2-c-static` 結束碼 0 | 既有協定 | 0.2.6 不得稱為已計數；既有判定仍只綁 0.2.5 |

綁定（任何計數執行之前寫進 runner 的常數）：頁面 sha（新的 `e2-editor-app.js`）、session sha、宿主 0.2.6 的 commit、殼層 generation v55。

## 5. 預測（寫在執行之前）

- A1-2 紅案：Firefox 與 Chrome 一樣重現 109（拒絕在引擎、與瀏覽器無關）。修法後 12/12 保住；按鍵到 `ready` 2–4 秒（宿主多一層，
  比獨立頁面慢）。
- A2-1 紅案：0.2.5 上 `body` 的 `background-color`、`display`、`height` 會變；頂欄按鈕的 `padding`／`border` 也會變。0.2.6：零。
- A3-2：四個鍵兩個瀏覽器都過（Shift+Enter 擁有者實測過，Enter 走 input adapter）。
- R：頁面誠實化換了啟用點擊的目標，結果不變；其餘五支不受這次改動影響。產品路徑網逐格相同（自動重開只對段落交界拒絕發生，
  網裡沒有格會觸發它）。

## 6. 登錄（不在本輪）

- toast 的原始錯誤代碼（3.3）。
- 真的併段（C）：引擎把段落分隔符號排除在 barrier 的安全範圍外；要改引擎、要連結。
- 重開之後游標回到文件開頭、復原堆疊清空（3.1 的代價）；若要保留游標，要記住拒絕前的位置並在重開後放回去。
- 兩支一次性探針（`probe_m3_unsaved_leave.py`、`probe_m3_save_throw.py`）仍點 `#text`，在 0.2.6 上要改目標才能再用。
- install-elsewhere 不在 0.2.6 上重跑，除非擁有者要求。

## 7. 追加（2026-10-06，shakedown 之後、任何計數執行之前）

只追加，不改上文。

- **新事實（讀原始碼）**：barrier 的「邊界」字元集合是 `\r`、`\n`、`\t`、U+2028、U+2029、U+FFFC
  （`probe_engine.cpp` `selectionBarrierContainsBoundary`）。所以 109 不只段落交界：**Shift+Enter 換行之後按 Backspace、
  刪除一個 Tab** 也會被拒。修法後一樣是零損失自動重開。P 臂的按鍵順序因此只在段落中間按 Backspace／Delete，Enter 與
  Shift+Enter 放最後。真的支援這些刪除屬於 C。
- **紅案已跑**（宿主 0.2.5、頁面 `fc80050c…`，`findings/evidence/m3-production-ui/prefix/`）：B-del、B-bs 兩個瀏覽器都紅在預測
  的地方（世代不變、存檔 `EDITOR_NOT_READY`、伺服器檔案沒有標記）——**Firefox 157 同樣重現 109**；A1-3 也紅（`restart-required`
  時 21 顆只停用 1 顆）；S 兩個瀏覽器都紅（容器外 178 個元素被產品樣式表改動，含 `body` 的背景、`display`）；P 的 A3-1 紅
  （十個開發控制項與說明文字看得見）。B-ctl 兩個瀏覽器都過（正向對照在修法前就該過）。
- **shakedown 逼出的儀器修正**（都是 runner，不是判準）：
  1. Chrome 的 CDP 連線在存檔時斷線：`Network.requestWillBeSent` 帶著 PUT 本文，這份文件 JSON 跳脫後 1.37 MB，超過 websocket
     的 1 MiB 上限。runner 的 Chrome 端改成 `Network.disable`（不需要網路事件；每臂是新的 profile，第一次載入本來就是冷的）。
  2. `keyed()` 的世代讀錯欄位（`READ_STATE` 沒有世代），永遠是 `None`。改讀 `#s-generation`。
  3. 「尚未儲存」的 1.5 秒視窗從按鍵之前起算，而 `keyed()` 自己就要等 1.6 秒以上，迴圈一次都沒跑——第一次 shakedown 兩個 P 臂
     因此紅在 A3-2。改成從修改落地起算。判準文字不變（1.5 秒內出現）。
- **shakedown 逼出的產品修正**：關閉鈕的網址原本手拼 `/index.php/apps/files/files/<id>`，在 pretty URL 開著時落在
  `/apps/files/index.php/apps/files/files/<id>`（A2-3 的正規式仍然比對成功——**判分沒有抓到，是讀落地網址時看到的**）。宿主
  `fa08307` 改用 `linkToRoute('files.view.indexViewFileid', …)`（Files 自己 `showFile()` 用的路由，不帶 `openfile`），重跑落在
  `/apps/files/files/<id>?dir=/`。A2-3 的判分因此補一條：落地路徑必須以 `/apps/files/files/<id>` 或
  `/index.php/apps/files/files/<id>` **開頭**。
- 0.2.6 的 shakedown（`shakedown/`）：修正後全部臂兩個瀏覽器都過。

## 8. 審核結果（2026-10-06，opus 對抗性審核，任何計數執行之前）

原文：`findings/evidence/m3-production-ui/review-2026-10-06-opus.md`。

- **B1（BLOCKING，主 session 讀原始碼確認）**：Worker 世代上限預設 3（`editor-shell/editor-session.js:81`），頁面沒有覆寫；
  `restart()` 先釋放引擎、`_openFresh` 才檢查上限（:148）。所以**同一次頁面載入裡第三次段落交界拒絕**（或之前有過一次回復，
  則第二次）時，自動重開會丟掉引擎、進 `recoverable-error`（`WORKER_GENERATION_LIMIT`）、存檔被拒，內容只剩在檢查點位元組裡；
  重新整理頁面就全丟——109 換了個時間點回來。§7 已經說明 Tab、Shift+Enter 換行之後的 Backspace 也會觸發，所以這不是罕見路徑。
  **3.1 的「零損失」宣稱因此只對前兩次成立；修好之前不得跑任何計數。**瀏覽器上尚未量測。
- 處置方向（未決，交擁有者）：審核者建議 A——重開之前先問世代是否還允許；不允許時把 `checkpointBytes()` 交給 `HOST.save()`
  （沒有宿主就下載），再請使用者重新整理；並照 C 把宣稱寫成「每次頁面載入前 N 次」＋一支三次拒絕的臂。另一個方向是對「什麼都
  沒留下」的拒絕（a11y core 的語意檢查、deadline 拒絕）不開新 Worker，只能降低頻率。
- 其餘 20 條 NON-BLOCKING 未處置，下一輪逐條處置（照 §10 只追加）。其中產品面的：重開期間按的鍵會掉、但 toast 說「都還在」（2）；
  重開後沒有把焦點還給輸入槽、游標在文件開頭（3）；Ctrl+Z／Ctrl+Y／Ctrl+S 在重開期間仍跳 `EDITOR_NOT_READY`（6）；
  不支援 `@scope` 的瀏覽器會讓產品樣式整份失效（8）。

## 9. B1 的處置（2026-10-06，擁有者選 A；任何計數執行之前）

只追加，不改上文。本節取代 §8「處置方向（未決）」那一條；§3.1 的「零損失」宣稱照下面的「宣稱改寫」縮限。

### 9.1 修法

- **殼層** `narrow-editor-v2-session.js` 加兩個方法（基礎類別 `editor-session.js` 綁著 E1-C 的雜湊，不動）：
  - `restartAvailable()`：`_generation < _maxWorkerGenerations`。也就是 `restart()` 會不會撞上限——**在 `restart()` 之前**問，
    因為 `restart()` 先釋放引擎、`_openFresh` 才檢查上限。
  - `takeContentForRescue()`：只在停下的狀態（`restart-required`／`recoverable-error`）、且 `restartKeepsContent()` 為真時，
    回傳 `_openFresh` 會打開的那份位元組，並把它當成已存——authority 換成它、清掉檢查點、`dirty: false`，與 `save()` 的
    `finalize` 同一套。其餘情況回 `null`，不動任何狀態。
- **頁面** `e2-editor-app.js`：
  - `reopenAfterBoundaryRefusal` 第一件事問 `restartAvailable()`；為假就**不重開**，改走 `rescueAtGenerationLimit()`：
    沒有未存修改＝直接請使用者重新整理；有、而且 `restartKeepsContent()`＝把 `takeContentForRescue()` 的位元組交給既有的
    存檔路徑（有宿主＝`HOST.save()`，同一條 `hostSaves` 序列、`savesUnsettled` 照算；沒有宿主＝下載）；有、但保不住＝照實說。
  - 回復通知在 `restartAvailable()` 為假時改由頁面說話：狀態寫在 `#notice` 的 `data-limit`（`saving`／`saved`／`failed`／
    `clean`／`lost`／`pending`），按鈕是「重新整理頁面」（`pending` 時是「存回」，給不是從段落交界走到上限的路）。
    **不再**在上限呼叫 `rollback()`——那會先丟引擎再撞上限。
  - 不自動重新整理：擁有者選的是「請使用者重新整理」；存回失敗時宿主列會出現「下載這份內容」，使用者需要先看到它。
- **為什麼交出去的那一刻就標記乾淨**：與既有存檔同一個約定——`session.save()` 一產出位元組就標記乾淨，宿主寫入的空窗由
  `savesUnsettled` 蓋住，寫入失敗由宿主自己滯留位元組並守住離開（finding 108 的修法，宿主 0.2.4 起）。不標記的話，使用者照
  指示重新整理時宿主的 `beforeunload` 仍會問（交接文件點名的細節），而那一問是錯的。

### 9.2 宣稱改寫（取代 §3.1 的「零損失」）

每次頁面載入，世代上限 3（開檔用掉一個），所以**前兩次**段落交界拒絕自動重開、零損失（之前若有過一次回到檢查點，則前一次）。
**之後的每一次**不重開：拒絕那一刻的內容交給存檔；存回成功＝零損失，請使用者重新整理頁面；存回失敗＝宿主滯留＋可下載，
與一般存檔失敗相同。檢查點寫不出來（`restartKeepsContent()` 為假）時照實說保不住，與 §3.1 原本的那一支相同。

### 9.3 判準（新增；先於任何會算進它的執行，被 B1 逼出來）

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **A1-4** | 單元測試（`narrow-editor-v2-session.test.mjs` 的 B1 節＋頁面函式在測試裡編譯、只給指名的變數）：兩次拒絕重開後 `restartAvailable()` 為假；第三次拒絕時頁面**沒有**呼叫 `restart()`、引擎沒有被釋放、交給存檔的位元組＝第三次拒絕那一刻存的檢查點、之後 `hasUnsavedEdits()` 為假；檢查點寫不出來時 `takeContentForRescue()` 回 `null` 且 `dirty` 不變；`ready` 時回 `null`。紅案三個：拿掉頁面的 `restartAvailable()` 檢查、`takeContentForRescue()` 不標記乾淨、不檢查狀態——各自至少紅一條 | 逐實例（單元） | B1 維持未修 |
| **A1-5** | 新臂 **B-3x**，每瀏覽器計數 **2/2**：打標記 M1→交界拒絕→（重開，世代 2）→**不點擊直接**打 M2→點到交界→拒絕→（世代 3）→不點擊直接打 M3→點到交界→拒絕。**不按儲存。**之後：世代仍是 3；狀態是 `restart-required`（不是 `recoverable-error`）；`#notice` 的 `data-limit` 在 10 秒內變成 `saved`；伺服器上檔案的 content.xml 含 M1、M2、M3；宿主的 `watchUnsaved` 問題回 false；按「重新整理頁面」→宿主**沒有問**（`out.guards` 沒多一筆）、重新開好的文件含三個標記、世代 1。**非空洞**：第一、二次拒絕各使世代＋1 | 逐實例（每一臂） | §9.2 的宣稱只能寫「前兩次」，B1 維持未修 |
| **A1-5 紅案** | 同一臂對修法前的頁面（0.2.6 現行引擎包，頁面 `d41ae604…`）每瀏覽器跑 1 次，必須紅：第三次拒絕後 `recoverable-error`＋`WORKER_GENERATION_LIMIT`、伺服器沒有 M3 | 先紅一次 | runner 不得用來宣告 A1-5 |

計數語意：本輪還沒有任何計數執行，所以沒有計數要歸零；§4 的 R 列照舊，B-3x 加進 `check_m3_production_ui.py` 的計數計畫。

### 9.4 預測（寫在執行之前）

- 紅案：兩個瀏覽器都紅在預測的地方（上限與瀏覽器無關）。
- 修法後：第三次拒絕到 `data-limit=saved` 約 1–3 秒（檢查點約 0.94 秒已在拒絕裡付掉；剩下是一次 PUT＋宿主讀回比對）。
  M2、M3 不點擊就打得進去（第 3 條審核意見的修法，見 9.5）。
- 產品路徑網逐格不變（網裡沒有格會走到段落交界拒絕，更不會走到第三次）。

### 9.5 審核意見中產品面的三條，一起修

- **（2）** 重開之後的 toast 原本說「尚未儲存的修改都還在」，但拒絕之後到重開完成之間按的鍵會掉。改成只宣稱**按這一鍵之前**
  的修改還在（佇列先進先出，排在被拒那一鍵前面的都已經進了檢查點）。**沒有判準**，是措辭的範圍縮小。
- **（3）** 重開成功之後把焦點還給輸入槽。由 A1-5 的「不點擊直接打 M2、M3」量。游標在文件開頭仍是 §6 登錄的代價。
- **（6）** Ctrl+Z／Ctrl+Y／Ctrl+S 照工具列與按鍵的規則：狀態不是 ready／busy 時不做事、不跳 toast。**讀原始碼**：輸入槽在佇列擋住時
  被停用（`input-adapter.js` `setBlocked`），按鍵多半根本到不了這個處理器，所以這是補守衛，**沒有量**。
- **（8）** `@scope` 的瀏覽器下限是宿主的事，另寫（9.6，未寫）。

## 10. 審核意見的處置（2026-10-06，任何計數執行之前）

只追加。第一輪＝`review-2026-10-06-opus.md`（§8 引的那份，編號照它）；第二輪＝`review-2026-10-06b-opus.md`（審 §9 的修法 `ec951c41`，
沒有 BLOCKING）。「守著」＝哪一個測試或判準會在它退化時轉紅；沒有的照 CLAUDE.md §3 寫明是哪一種登錄。

### 10.1 §9.2 的宣稱再縮一次（第二輪 4，finding 111）

輸入轉接器自己排隊、一次送一個字；Delete／Backspace 直接進 session 佇列。所以**被拒那一鍵之前很快打的字**可能還在轉接器裡、
排在被拒的刪除後面，跟著被退回（單元層已重現）。§9.2 的「零損失」改成：**拒絕當下已經送進引擎的內容**零損失；轉接器裡還沒送出
的字不在保證之內。toast 不再宣稱「之前的都還在」，改成照實提醒「緊接在這一鍵前後打的字可能沒有打進去」。同一個機制在一般編輯會
讓刪除與方向鍵插隊（**順序錯，不是遺失**），另立 **finding 111**，不在本輪修。

### 10.2 修了的（`04d19fcd`、`c3bef9b4`、`2f923764`）

| 來源 | 內容 | 守著 |
| --- | --- | --- |
| 二-1 | A1-5 在「說 `saved` 的同一次讀取」要求宿主最後一筆存檔 `settled` 且 `outcome == saved`；重新整理後宿主的鎖是 `held` | runner 突變三條（`saved` 早於寫入、寫進副本、沒有鎖） |
| 二-2 | 通知按鈕改成具名函式 `onNoticeAction`；`rescueAtGenerationLimit` 改用 `limitState()`，不再自己再算一次；按鈕文字與停用由 `limitNotice()` 決定 | 單元：審核普查中存活的 S1、P1、P2、P4、P5、P16 各自轉紅 |
| 二-3 | `failed` 顯示宿主自己的句子（另存副本的檔名，或「請按下載這份內容」），不再一律叫人去按可能不存在的下載鈕 | 單元一條（丟掉宿主句子→紅） |
| 二-4、一-2 | toast 措辭（10.1） | 無（措辭的範圍縮小，不是行為） |
| 二-5 | 換文件時重設 `limit` | **有行為而沒有東西守著**：只有獨立頁面走得到（宿主停用了開檔），`openDocument` 太重不好在單元裡編譯 |
| 二-6、二-8、二-12 | 沒有宿主時 `saved` 改說「已交給瀏覽器下載、確認下載好了再重新整理」；`clean` 不再宣稱「沒有尚未儲存的修改」；`pending`／`saving` 在沒有宿主時說「下載」；上限時回復建議不再叫人按不存在的「回到檢查點」 | 無（措辭） |
| 二-10 | 重開後聚焦輸入槽加 `preventScroll`（與檔內另外兩處一致） | 無；A1-5 的「不點擊直接打字」量的是焦點有沒有回來，不是捲動 |
| 一-10 | S 臂加一條：容器本身解析得到產品樣式的 `--accent` | runner 突變一條 |
| 一-11 | A2-1 的屬性清單改成瀏覽器自己的 `getComputedStyle` 清單（形式二），報告記錄比了幾個屬性，少於 100 就紅 | runner 突變一條 |
| 一-13 | A3-2「尚未儲存」的計時從**按鍵那一刻**起算（這一鍵改成直接按，不經 `keyed()` 的等待） | 無新突變；`unsavedShownAfter` 不再是建構上的 0.0 |
| 一-14 | 報告的文件本身若已含標記，整份判不過 | 判分程式碼 |
| 一-17 | 報告帶 runner 的 sha256；計數前用最終判分器重算 `prefix/` 的 JSON 並 `--expect-red` | 計數前要做的一步（交接） |

### 10.3 登錄（不修，寫明是哪一種）

| 來源 | 內容 | 種類 |
| --- | --- | --- |
| 一-4 | 拒絕當下的檢查點存檔受 5 秒時限（`_selectionTimeoutMs`）；大文件或 038 型的引擎狀態下存不出來，就退回「照實說保不住」 | **具名極限**。擁有者 563 KB 文件 0.94 秒；拉長時限等於每次拒絕在大文件上卡更久 |
| 一-5 | 新檢查點存不出來、舊的還在時（未到上限），通知用的是「無法驗證」那一句，「回到檢查點」會丟掉之後的修改 | **有行為而沒有東西守著**（頁面 `!restartKeepsContent()` 那一支在任何層級都沒紅過） |
| 二-7 | 上限時有較舊的檢查點，報成 `lost`，沒有提供「至少存回那一份」；同一刻 `data-rescue="checkpoint"` 與 `data-limit="lost"` 並存 | 具名極限（並存是兩個決定各說各的，`data-limit` 優先） |
| 二-9 | 停下的 session 輸入槽是停用的，Ctrl+Z／Ctrl+Y／Ctrl+S 多半到不了頁面；Ctrl+S 因此落到瀏覽器的「另存網頁」。§9.5（6）的守衛是補的、沒有量 | 工作項（要做就是視窗層級接 Ctrl+S） |
| 二-11 | A1-5 紅案「伺服器沒有 M3」是多重決定的（修法前沒有救援、沒按儲存、焦點沒回來）。真正分辨 B1 的是第三次拒絕後 `recoverable-error`，加上通知按鈕被停用（只有 `WORKER_GENERATION_LIMIT`／`requiresPageReload` 會停用它）。這兩項已寫進證據 README 的表；`--expect-red` 接受任何原因的紅，所以紅案要讀報告，不能只看分數 | 量測的讀法 |
| 二-11 | §9.3 寫的「`out.guards` 沒多一筆」在重新整理之後讀不到；runner 改用 localStorage 的記錄器（與頁面誠實化 runner 同一支），並要求記錄器確實看到一次 `beforeunload`（非空洞） | 判準文字的更正，形式不變 |
| 二-Q5 | IME 組字若在約 1 秒的檢查點存檔期間開始，停用輸入槽可能把已確定的字留在 `#sink.value`，之後每次組字都 `INPUT_COMPOSITION_MISMATCH`（050 的形狀） | **未驗證的假說** |
| 一-9 | 宿主 `scopedStyle` 只數規則開頭的 `:root`／`body` | 改由宿主 0.2.7 修（§9.6） |
| 一-12 | A3-2 的「修訂＋1」分不出 Backspace 與 Delete、Enter 與 Shift+Enter | A3-2 的具名極限：它判的是「被藏的鈕有鍵可以取代」，不是哪個鍵對到哪個動作 |
| 一-15 | A2-3 只量了根目錄的檔案（`dir=/`），子資料夾的關閉網址沒量 | 未量（網址由 `linkToRoute` 用 `resolve()` 的 `dir` 產生） |
| 一-16 | Firefox 的 dirty close 量到的是「離開」不是「留下」（geckodriver 預設接受 `beforeunload` 提示） | 具名極限：Firefox 這格證「有問」，「留下」只在 Chrome 量 |
| 一-18 | `counted_bindings` 沒綁殼層 generation v55 與文件 sha256 | 寫 pin 時一起做（交接第 6 步） |
| 一-19 | A1-1 那一列「從來沒做時的結論」是「—」 | 補：**單元層沒有證據時，109 的修法不得宣稱** |
| 一-20 | 狀態不是 ready／busy 時，工具列 `.click()` 現在什麼都不做 | 讀原始碼：產品路徑網的 `capture_save` 在停下的 session 上，修法前後都拿到空擷取、都等滿 `wait_saves` 的 90 秒；預測網逐格不變，凍 v55 之後實測 |
| 一-21 | A3 的隱藏清單是位置式（`.sep:nth-of-type`），A3-1 不看 `title` 提示文字 | 具名極限 |

## 9.6 不支援 `@scope` 的瀏覽器（審核一-8、一-9；2026-10-06，宿主改動之前寫）

只追加。接在 §10 之後寫，編號接 §9.5 的「（8）另寫」。

- **量測（已觀察，宿主 0.2.6）**：Firefox 157 關掉 `layout.css.at-scope.enabled` 代替沒有 `@scope` 的瀏覽器（Firefox ESR 140
  沒裝）。`CSSScopeRule` 是 `undefined`；`#notice`、`#expired`、`#sink` 都看得見；A3-1 的清單多 8 段不該看到的文字。正向對照
  （同一支探針、偏好開著）：`function`、上述元素全看不見、清單乾淨。證據 `findings/evidence/m3-production-ui/no-scope/`，探針
  `wasm_sdk_probe/tools/probe_m3_no_scope.py`。
- **修法（宿主 0.2.7）**：模板在限縮的那份之後多印一份**未限縮**的產品樣式 `<style id="litecore-unscoped" media="not all">`；
  宿主 JS 一開始看 `typeof CSSScopeRule`，沒有就把它打開（`media="all"`），並把 `scope`（`scoped`／`unscoped-fallback`）寫進
  `data-litecore`。**代價照實寫**：沒有 `@scope` 的瀏覽器回到 110 的樣子（Nextcloud 頂欄被蓋），但編輯器能用、不露出內部元件。
  一-9 同版修：`scopedStyle` 先數**所有**出現位置（不只規則開頭），不是恰好一次就拒絕。
- **判準 A2-4**（一次量測，Firefox，同一支探針，宿主 0.2.7）：偏好關掉時 `hostScope == "unscoped-fallback"`、`#notice`／`#expired`／
  `#sink` 都看不見、A3-1 清單 0 控制項 0 文字；偏好開著時 `hostScope == "scoped"`、未限縮那份的 `media` 仍是 `not all`（不得兩份
  同時生效）。**從來沒做時的結論**：不支援 `@scope` 的瀏覽器上頁面露出內部元件，登錄為具名極限，110 的修法只對支援的瀏覽器宣稱。
- **預測**：關掉→fallback、清單乾淨；開著→scoped、`not all`。出貨頁面恰好一個 `:root {`、一個 `body {`，所以 0.2.7 的
  `scopedStyle` 照樣放行（不會 500）。
- **R 與綁定改綁宿主 0.2.7**（§4 的 R 列與綁定原寫 0.2.6；本輪還沒有任何計數執行，所以沒有計數要歸零）。

## 11. 計數綁定（2026-10-06，寫在任何計數執行之前）

只追加。§4 最後一段的綁定，加上審核一-18 要的兩項，全部已寫進 runner 的常數（`counted_bindings` 與各 runner 的拒絕條件）：

| 綁定 | 值 |
| --- | --- |
| 頁面 `e2-editor-app.js` | `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f` |
| session `narrow-editor-v2-session.js` | `3f5f754bf0495ff2001756014c76f43d8cb0b1f3b7233f0f710e1a635e782c5e` |
| 宿主 | 0.2.7，`0488586` |
| 引擎包 buildId | `fabdb50ecd038802` |
| 殼層 generation | v55，`2470765ae19ced019b423b55e856ef8d60759ee878d56ff835e6e9387b62167c`（runner 跑凍結工具的問答模式，exit 0 且 digest 相同才算） |
| 擁有者的文件 | `7b336879547df057ae6d38e907f221b40c90c37cd65d2df5afceceb91941657e`（563,149 位元組，不進 repo） |
| `check_m3_production_ui.py` | `d23043dc96beda6f61f6f8ec599a60a5dd548f486a8666e49c3196d8ce7cc587`（每份報告自帶 `runnerSha256`；與此不同的報告不算進計數） |

六支既有 M3 runner 同步改綁：`check_m3_locks` 的 `PAGE_SHA256`（`versions`、`same_second` 由它匯入）、`check_m3_page_honesty` 的頁面／session／宿主、
`check_m3_versions` 的宿主 commit、`check_m3_same_second` 的宿主版本、`check_m3_assets` 的頁面與 buildId；`check_m3_host_entry` 不寫死，逐檔比對服務中的產品檔案與 `dist/`。

## 12. locks 計數紅一格之後（2026-10-06，任何重跑之前寫）

只追加。宿主 0.2.7 的計數鏈（2026-10-06 01:35–05:01 UTC）裡，本規格自己的臂 22/22 全過、合併紅案 30/30，其餘五支 runner
全過、紅案全紅；**locks 是 `LOCKS DO NOT LAND`**（`chrome:foreign-lock` 2/3）——一次 Files 頁 60 秒沒畫出任何一列，產品頁沒有被請求，
登錄為 **finding 112**。擁有者交 fable 裁決，裁決是 A（有界限），全文與理由在 finding 112 的「裁決」段，條件寫進
`findings/evidence/m3-locks/README.md` 的規則 5。本節只記下對本規格的效果：

- **判準不動**：R 列的 locks 格仍是「一輪完整計數 52/52、紅案全紅」。10-06 那份報告維持 `LOCKS DO NOT LAND`，不改、不併、不排除
  任何一臂。
- **允許一次重跑**（規則 5），條件：runner 只改儀器（逾時時存下瀏覽器看到的東西、每臂記 `filesRowSeconds`），判分不動並以既存報告
  證明輸出相同；擷取先自己紅一次；新的 runner sha256 寫在本節之後（§12.1）；重跑綁定同 §11。
- **結果對應現在寫死**：重跑綠＝R 的 locks 格在 0.2.7 成立，109、110 才能標已修；任何一臂紅＝R 不成立、不跑第三次，改走專用探針，
  交擁有者。**重跑若永遠沒做**：R 不成立，109、110 維持已確認／未修，「既有判定仍只綁 0.2.5」照 §4。
- **在那之前**，109、110 只追加一行現況：修法已在宿主 0.2.7 上計數通過本規格的 A 列，R 未過（finding 112）。
- 順帶的影響：`check_m3_same_second.py` 與 `probe_m3_save_throw.py` 從 `check_m3_locks` 匯入 `open_from_files`，改動之後它們的報告也會
  多帶那兩個欄位；兩者自己的檔案雜湊不變，same_second 已計數的報告照舊有效（規則 5 之 5）。

### 12.1 新的 locks runner pin（2026-10-06，重跑之前）

| 綁定 | 值 |
| --- | --- |
| `check_m3_locks.py` | `1d3099a21576171237e03e089b0edf05fdb903f90ae8cccc8c8b7df7f5317225`（取代 `6e6b2fa4…`；只加儀器，見 `findings/evidence/112/README.md`） |

判分等價：舊新兩版對 10-06 與 10-02 兩份 locks 報告的 `--score`、`--red-cases` 輸出逐位元相同。擷取已紅一次（故意給錯列名，Chrome、Firefox 各一，
`findings/evidence/112/capture-red/`）。其餘綁定照 §11。

### 12.2 重跑的結果（2026-10-06）

`findings/evidence/m3-locks/runs/2026-10-06T053046+0000.json`：**`LOCKS LAND`**，52/52、`problems=[]`、紅案 99／0、`runnerSha256` 是 §12.1 的 pin、
52 臂都帶 `filesRowSeconds`、擷取一次都沒觸發。照 §12 寫死的對應：**R 的 locks 格在 0.2.7 成立**，10-06 第一份照舊是 `LOCKS DO NOT LAND`。
**R 成立**：六支 M3 判定在頁面 `e97d6e03…`、宿主 0.2.7 上都計數過，產品路徑網 v55 與 v54 逐格相同，`make test-e2-c-static` 結束碼 0。
109、110 依 §4 改標已修；111、112 仍開著。逐判準的讀法在 `findings/evidence/m3-production-ui/RESULT.md`。

## 13. R 改綁到 v19（2026-10-09，任何 0.2.8 的計數執行之前）

只追加。逼出它的是 cutover（`6e9ec27e`，產品頁面改指 v19）與宿主 0.2.8（`4140e00`，打包 v19）：B-del、B-bs 兩個位置在 v19 上
**不再是拒絕**（`SPEC-M3-paragraph-merge.md` §4.4），所以 §4 的 A1-2 在 0.2.8 上照字面會紅，而那個紅說的是「修好了」。本節取代
§4 的 A1-2、A1-3 在 v19 上的寫法、§9.3 A1-5 的位置、以及 merge 規格 §10.2 的 R 列的比較方式；其餘判準（B-ctl、A2-*、A3-*）不動。

### 13.1 事實（全部量過，除非另標）

- **原生 R-host 一輪**（預測先 commit：`68716eba`；結果 `c923fd53`，`findings/evidence/merge-native/PREDICTION-R-host.md`）：擁有者文件上，
  B-del 的位置就是 R0c 的 E02（標題「一、序言」尾按 Delete）：Writer 併段，鍵後文件與 R0c 逐位元組相同（跨 session 穩定）。
  B-bs 的位置（內文第一段段首按 Backspace）原生**從來沒量過**：Writer 第一下是 `Apply attributes`（拿掉首行縮排、文字不變），
  第二下 `Delete paragraph`，**按兩下之後的文件與 E02 逐位元組相同**。文件開頭（標題）與結尾（一行的項目符號）在 v19 的 E 形上
  都是 `nothing-selected`（不按鍵）；Writer 自己的鍵在開頭切換編號、在結尾什麼都不做。這份文件沒有表格（`content.xml` 裡 0 個 `table:table`），所以 v19 上它只剩兩端會拒絕（**推論**：merge 規格的拒絕形狀只有兩端、表格、儲存格尾）。
- 這份文件上**沒有任何段首 Backspace 第一下就併段**（round E、R0c、R-host 三輪一致）：縮排的內文先拿掉縮排，標題與清單先切換編號。
- **v19 上這份文件的 E02 不等於原生**：併段的文字相同，但化約後的 `content.xml` 有 4／15 個分頁點落在別處（finding 115，X6 的 O3
  在 v19 上照舊）。
- **109 的三個點是 v8 的版面**：v8 的文件約 257,000 twips 高，v19 是 12474 × 308480（finding 114 修好之後 CJK 行變高）。同一個比例在
  v19 上落到別的行（例如舊的標題尾 y 0.00728 在 v19 是 2246 twips，落在標題與內文之間）。v19 的游標在這份文件上等於原生（X6，11 格
  x、y 逐 twip 相同），所以原生游標換算的比例就是 v19 上的點擊位置。
- **宿主頁面看不到 `verified-key-undo`**：完成的名字與 `keyUndo.comment` 只有 standalone 頁面加了觀察器才看得到（merge runner）。
  宿主上看得到的是世代、修訂、狀態、`上次操作` 的文字（成功是 `<名稱> N ms`，失敗是 `<名稱> 失敗`）、時間軸、伺服器上的檔案。
- **有打字的文件不能跨 session 比位元組**（merge 規格 §12，rsid）。A1-2 的形狀是「先打字（未存）再按交界的鍵」——那正是 109 的形狀，
  不能拿掉。
- **讀原始碼**：v19 offers `move-line-home`／`move-line-end`（manifest），頁面把 Home／End 接到它們（`e2-editor-app.js` `KEY_ACTIONS`）。

### 13.2 臂（v19；位置是 v19 文件的比例，原生游標換算，規則同 merge runner：Delete 的位置 x−40 twips、Backspace x＋40、y 取行中）

| 臂 | 做什麼 | 參考 |
| --- | --- | --- |
| **K-del** | 在 `IN_TEXT` 用真鍵打標記 → 點標題尾 → Delete | R-host `r1-E02-key.odt` |
| **K-bs** | 在 `IN_TEXT` 打標記 → 點內文第一段段首 → Backspace → 等 → Backspace | R-host `r1-Q01-key2.odt` |
| **R-bs** | 在 `IN_TEXT` 打標記 → 點第一行 → Home → Backspace（文件開頭，拒絕） | 上傳的原文 |
| **R-del** | 點最後一行 → End → **在那裡**打標記 → Delete（文件結尾，拒絕） | 上傳的原文 |
| **B-3x** | 三次都在文件開頭：M1 照 R-bs；重開後**不點擊**打 M2（落在文件開頭）→ 點第一行 → Home → Backspace；M3 同 M2 | —（§9.3 照舊） |

每一臂之後「等」＝狀態回到 ready、佇列 0、持續 0.5 秒，再多等 1 秒（同 0.2.7 的 B 臂）。之後按儲存、等宿主的存檔 `settled`。

| 位置 | 比例 (x, y) | 來源（twips：x, y, 高） |
| --- | --- | --- |
| 標題尾 | (0.225910, 0.006219) | E02 (2858, 1658, 521)；X6 在 v19 上點過、`keyed: false` |
| 內文第一段段首 | (0.155363, 0.008270) | Q01 (1898, 2377, 348) |
| 第一行（＋Home） | (0.116883, 0.006219) | Q02 (1418, 1658, 521) |
| 最後一行（＋End） | (0.836781, 0.990622) | Q03 (10478, 305449, 276) |
| `IN_TEXT` | (0.5, 0.010373) | y 3200：內文第一段第一行頂是 2377，以 348 的行距算是第三行（**推論**：209 個字、每行約 40 字，這段五行以上；落在這段的哪一行都可以） |

**為什麼 R-del 在結尾打標記**：在 `IN_TEXT` 打三個字可能讓第一段多一行，之後每一頁往下推，最後一行的 y 就不是量過的那個；點錯一行再 End
會落在上一個項目的結尾，Delete 變成兩個項目符號併段（不是拒絕）——紅在位置上，不是紅在產品上。先點、先 End、再打字，結尾的位置
就不會被移動。**B-3x 三次都在開頭**是同樣的理由：重開之後標記打在文件開頭，那一行多三個字不換行，開頭的位置不動。

**為什麼兩端都要 Home／End**：B-3x 的第二、三次之前文件開頭已經有標記，點擊落在標記的哪一邊看字寬；Home 不看。Home 在帶編號的
段落可能停在標號**前面**（merge runner 量過 C11），但文件開頭往後選不到任何東西，兩邊都是 `nothing-selected`（**推論**，計數前的
shakedown 會量到）。

### 13.3 判準（取代 §4 的 A1-2、A1-3 在 v19 上的寫法）

段落文字序列＝`tools/odt_paragraphs.py` 的 `paragraph_texts`（merge 規格 §12 的比較器，它自己的紅案是 `--self-test`）；伺服器檔案的
序列先**拿掉標記**再比。報告只帶序列的 sha256、段數與第一個不同的段號，不帶文字。兩個參考的序列雜湊寫成 runner 常數（原文
`d646dda7…`，211 段；K 參考 `1f53faf4…`，210 段，E02 與 Q01 兩下的三輪全同）。

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **A1-2′ K** | K-del、K-bs 每瀏覽器各 **3/3**：世代從頭到尾是 1（沒有重開）；時間軸**每一筆**都是 ready／busy（沒有停下過）；每一下之後 `上次操作` 不是「失敗」、修訂往前走；存檔落地、伺服器檔案恰好一個標記；拿掉標記之後的段落文字序列＝K 參考。**非空洞**：K 參考≠原文（runner 常數，判分時檢查） | 逐實例（每一臂、每一下） | v19 在宿主上不得宣稱「交界的 Delete／Backspace 是 Writer 的鍵」；只能說 standalone（X7、X6） |
| **A1-2′ R** | R-bs、R-del 每瀏覽器各 **3/3**：世代 1→2（拒絕真的發生、重開真的發生）；伺服器檔案恰好一個標記；拿掉標記之後的段落文字序列＝原文（拒絕沒有改到文件） | 逐實例 | 109 的修法在 v19 上不得宣稱（v19 的拒絕只剩兩端） |
| **A1-3′** | R 臂與 B-3x：每一臂至少一筆停下的樣本，每一筆停下的樣本裡工具列每一顆按鈕都停用（同 §4 A1-3）。K 臂由 A1-2′ K 的「沒有停下過」取代 | 逐實例（每一筆樣本） | 同 §4 |
| **A1-5** | §9.3 照舊，位置照 13.2 | 逐實例 | 同 §9.3 |
| **紅一次（K）** | 同一支 runner、非計數，把開發實例的 `engine/` 暫時換回封存的 0.2.7 引擎包（v8，`build/archive/host-0.2.7-engine-fabdb50ecd038802/`），Chrome 跑 K-del、K-bs、R-bs、R-del 各一次：**K 兩臂必須紅、而且紅在世代 1→2**（v8 在這兩個位置拒絕並重開）；R 兩臂必須綠（正向對照：兩端在 v8 上也是拒絕）。跑完換回，`buildId` 回到 `63656ee4…` 才往下走。K 臂若紅在別的原因（世代沒變），這一次不算紅案，照實記下 | 先紅一次 | runner 不得用來宣告 A1-2′ K |
| **突變** | `MUTATIONS` 改以新臂為準，每一條新條款至少一條（K 重開、K 停下、K 某一下失敗、K 某一下沒動、K 序列不同、K 沒有標記、R 沒重開、R 序列不同、R 沒有標記、A1-3′ 兩條）；B-ctl、S、P、B-3x 的照舊。計數報告合併後 `--red-cases` 全紅 | 工具封閉（每條條款） | 同上 |

**撤回（照 `CLAUDE.md` 第 4 節）**：merge 規格 §10.2 的 R 列「宿主上的併段臂比較伺服器上的 `content.xml`（化約後）＝原生鍵臂」**不成立**，
兩個獨立的理由：（1）A1-2 的形狀先打字，跨 session 不能比位元組（§12，那一節更正了 10.2 的三格，漏了 R 這一格）；（2）就算不打字，
E02 在 v19 引擎上化約後也不等於原生（finding 115）。改成上表的段落文字序列。**因此失去的**：宿主上的格式等同（縮排、樣式、分頁點）。
它由別處負責：standalone v19 上 E02 除了位元組之外每一條都過、E10（拿掉縮排）連位元組都過（X6）；合成文件的計數 M2（X7）。
登錄為具名極限：**宿主上的併段，只驗到文字落在哪一段的哪裡**。

**K-bs 為什麼按兩下**：這份文件上段首 Backspace 第一下從不併段（13.1）。只按一下，文字序列與原文相同，「Writer 拿掉了縮排」與「什麼都
沒發生」在文字上分不出來；按兩下，第二下的併段讓序列改變，而且第一下若是直接併段（B≠Writer），第二下會刪掉「言」，序列也不同——
兩種錯都會紅。第一下的「修訂往前走」另外證明它做了事。

### 13.4 R 的其餘格

| 格 | 怎麼滿足 | 從來沒做時 |
| --- | --- | --- |
| 六支 M3 runner | 改綁之後在 0.2.8 上重新計數全過、紅案全紅（PAGE HONEST、LOCKS LAND、VERSIONS CORRECT、ASSETS DELIVERED、HOST_ENTRY LANDS、SAME-SECOND SAVES KEPT） | 0.2.8 不得稱為已計數；既有判定只綁 0.2.7 |
| 產品路徑網（merge 規格 M2-5） | **X5 算數，不重跑**：X5（`findings/evidence/v19/x5-product-path/`，§36 判過）量的就是這一頁——頁面 `e00ab76a…`，殼層的 `servedShell` 雜湊等於後來凍結的 v57（`1aed21b1…`，cutover 交接已核對六份報告）。產品路徑網跑在 standalone 頁面上，宿主不在它的路徑裡；宿主送出的頁面位元組由綁定保證 | — |
| `make test-e2-c-static` | 結束碼 0 | 同第一列 |
| 宿主上的併段＝原生鍵臂 | 由 13.3 的 A1-2′ K（文字序列）取代 | 同 A1-2′ K |

**不重跑的紅案**：§4 的 A1-2 紅案（0.2.5 修法前）與 §9.3 的 A1-5 紅案（0.2.6 修法前）。理由：兩者證明的是「這支 runner 看得到 109／B1」，
R 臂與 B-3x 的判分在這兩件事上與當時同一段程式碼（世代、標記、`data-limit`、救援的存檔），109／B1 的修法（頁面）在 cutover 時只改了
`PINNED_WASM_SHA256` 與 `workerUrl` 兩行。新加的文字序列條款由突變與上面的「紅一次（K）」負責。

### 13.5 綁定（寫進 runner 常數，在任何計數執行之前）

頁面 `e00ab76a550dc12fda5dee1849d9cfb73343b9cfab9c8e9436a8bd035a0a4be8`、session `ee3e53a24fb20a255609c8c684ec597ff21fa938ad55b46fcea4dff04a7cdb65`、
宿主 0.2.8 `4140e00`、殼層 generation v57 `1aed21b1fdcc5d4242f71c06b1a3ea6623927a198919706894a2a72670e1ec88`、文件 `7b336879…`（同 §11）、
引擎包 buildId `63656ee4aa7e4059`（同 0.2.7：`counted_bindings` 不比它，RESULT 從報告的 `static.buildId` 照實讀；§34 不加守衛）、
兩個序列雜湊（13.3），以及改完之後的 `check_m3_production_ui.py` sha256（另起一行追加）。六支既有 runner 的 pin 同步：`check_m3_locks` 的
`PAGE_SHA256`、`check_m3_page_honesty` 的頁面／session／宿主、`check_m3_versions` 的宿主 commit、`check_m3_same_second` 的宿主版本、
`check_m3_assets` 的頁面與 `BUILD_ID`，以及它寫死 v8 與 `cjk-r5` 的地方（K1-3 的「舊的靜態 dist」改指 v19 的 wasm、K1-6 的 manifest 路徑、
Z2-2 與 Z2 D′ 的 CJK 包改成 `cjk-sub-e10.06976180177c8bd2.data`）——這些是把既有條款指到現在出貨的檔案，不是新條款。

### 13.6 預測（寫在任何 v19 宿主執行之前）

- K-del、K-bs：兩個瀏覽器 3/3；每一下 100–300 ms（standalone 上 E02 142 ms、E10 117 ms，宿主不在這條路上）、修訂各＋1；世代全程 1。
- R-bs、R-del：3/3；按鍵後約 250 ms 拒絕（`nothing-selected`），之後與 0.2.7 的 B 臂同一條路（檢查點約 0.9 秒、重開，第一筆停下的樣本到
  ready 1–2 秒）；文字序列＝原文。
- B-3x：2/2，數字與 0.2.7 相近；三次拒絕都在開頭。
- B-ctl、S、P：與 0.2.7 相同（P 的 `IN_TEXT` 換了位置，那四個鍵仍在段中）。
- 紅一次（K）：K-del、K-bs 紅在世代 1→2，伺服器的序列＝原文（v8 的拒絕保住了標記、沒有併段）；R-bs、R-del 綠。
- 六支既有 runner：結果與 0.2.7 相同（它們不碰段落交界；ASSETS 的數字照 0.2.8 的包：wasm gzip 40.88 MB）。
- 若 Home 在文件開頭讓 Backspace **不**拒絕（推論錯）：R-bs 與 B-3x 在 shakedown 紅在世代沒變；那時改成只點擊、不按 Home，並以追加段寫明。

### 13.7 shakedown 與紅一次（2026-10-09，非計數；`findings/evidence/m3-production-ui/v19-shakedown/`）

- **runner pin（§13.5 的最後一項）**：`check_m3_production_ui.py` `3e19651098fa992600c7b0a84a9fd0ee04ab36ea6dd3d3d6a37b3bdd8f21b38f`（`c823b955`）。
  與這個值不同的報告不算進計數。六支既有 runner 的 pin 照 §13.5 改綁（本節同一個 commit），`make test-e2-c-static` 結束碼 0。
- **shakedown**：兩個瀏覽器 16 臂全過，合併突變 40/40。各臂為了對的理由過（README 逐臂列出）：K 兩臂世代全程 1、每一下 146–177 ms、序列＝Writer 的；
  R 兩臂與 B-3x 拒絕並重開、序列＝原文。
- **紅一次（K）成立**：v8 引擎上 K-del、K-bs 都紅在世代 1→2（v8 拒絕、重開、序列＝原文）。**正向對照一半**：R-del 綠；R-bs 沒走到它的鍵——
  v8 上 Home 在文件開頭 30 秒逾時（`recoverable-error`，檢查點 r3），是 finding 096 的形狀（文件邊界上的移動打死 session），不是「開頭不拒絕」。
  不重跑：正向對照要表明的是兩端在 v8 上也是拒絕，結尾已表明；開頭在 v19 上八次 Home 全都完成並拒絕。§13.3 沒有事先寫這種情況，照實記下。
- **觀察（不判）**：v19 上同一個 Home 要 717–981 ms（8/8 完成），v8 上卡 30 秒（1/1）。096 的線索，登錄，不在本輪。
- §13.6 的預測：K、R、B-3x、B-ctl、S、P 全中（shakedown，非計數）；紅一次的 R-bs 那一格**沒中**（預測綠，實際紅在 v8 的 Home）。
- **更正（取代本節第一點的雜湊）**：上面那個 pin 的後 48 個字元是我手打的，不是工具輸出——錯的。正確值（`sha256sum` 直接輸出）：
  `3e19651098fa9926581e4cc1eea55bed73c8eda06895783835105e615ea4aead`。報告自帶的 `runnerSha256` 一直是這個值（shakedown 三份與紅一次那份都是）。
- **更正（取代上面「觀察」那一點的解讀）**：v19 的 Home 不卡，是 finding 096 的 A 半（引擎 250 ms 讀回期限，原始碼無條件編入，v14 起每顆引擎都有、凍結的 v8 沒有）；
  那 0.7–1.0 秒是 096 的 C 半（有未存修改時、移動之前先存檢查點，這份文件約 0.7 秒）加約 0.26 秒的移動，時間軸逐筆看得到。不是 117 的輪詢。
  所以 cutover 之後出貨的產品帶著 096 的 A 半；本輪是它的一個實例（v19 8/8、v8 1/1 卡住），不是 096 原本那個方向鍵形狀的量測。

### 13.8 R 的結果（2026-10-09；`findings/evidence/m3-production-ui/RESULT-0.2.8.md`）

**R 在宿主 0.2.8 上成立。**計數鏈 2026-10-08 16:39–20:11 UTC（六支 shakedown 全乾淨之後才計數）：本規格的臂 A1-2′ K 12/12、A1-2′ R 12/12、
B-ctl／S／P 6/6、A1-5 4/4，合併突變 40/40；六支 M3 runner 全過（PAGE HONEST、LOCKS LAND 一輪就過、VERSIONS CORRECT、ASSETS DELIVERED、
HOST_ENTRY LANDS、SAME-SECOND SAVES KEPT），各自的紅案全紅；產品路徑網由 X5 滿足（13.4，跑之前就決定）；`make test-e2-c-static` 結束碼 0。
§13.6 的預測除了紅一次的 R-bs 正向對照（13.7）之外全中。

## 14. finding 119 與 111 的修法（2026-10-09，任何實作與執行之前；fable 依擁有者授權裁決）

只追加。裁決原文：`findings/evidence/fast-delete-recovery/ruling/fable-ruling.md`（119＝D：先殼層、引擎根因登錄；111＝同一次發佈出修法）。
逼出它的量測：119 的兩次重現（`findings/evidence/fast-delete-recovery/chrome-same-page-1.json` 第 41 次、`findings/evidence/111/browser/owner-chrome.json`
第 6 輪）與 111 的瀏覽器量測（`findings/evidence/111/PREDICTION.md`）。

### 14.1 修法

- **119（殼層＋頁面）**：`NarrowEditorV2Session.action()` 對 `delete-backward`／`delete-forward` 收到 `EDITOR_STATE_UNAVAILABLE`、而且沒有 `formatBarrier` 細節時：
  比照 109 先存檢查點（`_checkpointBeforeBoundaryRestart`，失敗記進 `checkpointError`），自己把佇列擋成 `restart-required`，把 `error.recovery` 設成
  `restart` 再丟出。頁面的 `run()` 把這個情形也送進既有的 `reopenAfterBoundaryRefusal`（世代上限、`restartKeepsContent`、焦點都照舊），句首寫
  「這一下刪除沒有完成」，結尾一律用「這一鍵可能生效了，也可能沒有」那一句——**不宣稱「文件沒有被改動」**（引擎有一個出口理論上在送出之後）。
  另：`onNoticeAction` 的回復完成後把焦點還給輸入槽。範圍**不看**錯誤訊息文字。
- **111（殼層）**：非打字的操作在轉接器還有沒交出去的字時（公開的 `input.state.queueDepth > 0`），以 `input.state.requestCount` 為屏障暫緩；`commitText`
  的覆寫在排第 k 個字之前放行屏障小於 k 的、之後放行等於 k 的；轉接器 `idle()` 收尾被取消的字。**世代守衛**：暫緩時記下 session 的世代，放行時世代已變就以
  `STALE_EDITOR_GENERATION` 拒絕、不執行。
- 不動：`editor-shell/editor-session.js`、`input/input-adapter.js`（E1-C）、引擎；不連結。兩個修法分兩個 commit。

### 14.2 判準

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **F119-U** | 單元：U1 有未存修改、假引擎讓 `delete-backward` 以 `EDITOR_STATE_UNAVAILABLE`（無細節）拒絕 → 存了引擎當下內容的檢查點、狀態 `restart-required`、`restartKeepsContent()` 真、`error.recovery === "restart"`、輸入被擋、`restart()` 打開檢查點位元組；U2 乾淨文件 → 不存檔、`restart-required`、`restartKeepsContent()` 真；U3 檢查點存不出來 → `checkpointError`、`restartKeepsContent()` 假、呼叫端拿到引擎的錯誤；U4 對照：同代碼在非刪除動作上照舊（rollback／`recoverable-error`）；U5 `delete-forward`；U6 頁面：這個錯誤走到自動重開、句首不含「沒有被改動」、`onNoticeAction` 回復後聚焦輸入槽。紅案各紅一次：拿掉檢查點（U1）、擋成 `recoverable-error`（U1）、拿掉動作範圍（U4）、拿掉聚焦（U6） | 逐實例（單元） | 119 不得宣稱已修 |
| **F111-U** | 單元：原型五條＋U7 暫緩的操作跨過一次擋住＋重開會被拒絕、不在新世代執行（守衛之前紅）＋U8「X 送出中、Y 在轉接器、存檔」的順序是 X、Y、存檔。既有 155 條全過 | 逐實例（單元） | 111 不得宣稱已修 |
| **F119-B** | 瀏覽器（候選 `dist/`、Chrome）：`probe_fast_delete_recovery.py --same-page` 改成讀自動重開（不按通知）：失敗的刪除之後 10 秒內 `ready`、世代＋1、工具列可用、`#notice` 隱藏；存檔 → 標題段含 X（與 Y）；不點擊打 `Q` → 修訂前進。預算 400 次、自然出現 3 次就停。**判定規則（現在寫死）**：自然出現 ≥2 次而且每次都綠 → 瀏覽器那一半成立；0–1 次 → 自然路徑登錄為「沒有實例可量」（附次數），瀏覽器那一半改由**注入臂**負責：探針讓 `editor.action` 以那個錯誤拒絕（真引擎、擁有者文件），每個瀏覽器 3/3、同樣的觀測。注入臂兩種結果都要跑（它是決定性的正向對照）。讀法的紅案：既有的 `chrome-same-page-1.json` 第 41 次（holdsX 假、Q 0→0）必須讀成 FAIL | 逐實例＋先紅一次 | 同 F119-U |
| **F111-B** | 瀏覽器（候選 `dist/`）：`probe_111_overtake.py --document boundaries` 與 `--document owner`，間隔 0、10，Backspace 與 Enter 各 10 次，兩個瀏覽器：0 插隊、0 `other`、0 `no-save`。讀法的紅案：既有的 `browser/firefox.json` 與 `owner-firefox.json`（0 ms 9–10/10 插隊）必須讀成 FAIL | 逐實例＋先紅一次 | 同 F111-U |
| **R′** | 發佈順序照裁決：兩個 commit → `make test-e2-c-static`、E1-C 完好 → `make e2-c-assets`（確認 cutover 的兩個 pin 沒動）→ 兩支瀏覽器探針 → **最後**凍殼層 v58（絕不覆寫 v57）→ 宿主 0.2.9 → 依 §13.5 的形狀改綁（只動 pin 行）→ 七支 runner 各自紅案、計數鏈、產品路徑網（M2-5，新頁面）、`make test-e2-c-static` | 既有協定 | 0.2.9 不得稱為已計數；119、111 維持未修 |

### 14.3 預測（寫在執行之前）

- 單元：F119-U、F111-U 全過；四個紅案與 U7 在修法前紅。
- F111-B：兩份文件、兩個瀏覽器、兩個間隔都 0 插隊；Backspace 結果「…X」、Enter 結果「…XY」＋空段。
- F119-B：同頁 400 次內自然出現 2–3 次（目前約 180 次 2 次；111 的修法讓刪除排在 Y 之後，頻率**不預測**），每次都在 10 秒內自動重開、X 與 Y 都在、Q 打得進去；
  注入臂兩個瀏覽器 3/3。
- R′：與 §13 相同的結果；產品路徑網逐格同 v8（§23 規則）。

### 14.4 登錄（不在本輪）

- **C（引擎根因）**：先量（引擎端時間戳）barrier 送出單位選取到 `LOK_CALLBACK_TEXT_SELECTION` 之間的時間，區辨 callback flush 的延遲（040 的家族）與長壽 Worker 的
  累積負擔，再在「插入的 callback 到齊才 arm」與「選取可讀但沒公告時重新 arm」之間選。
- 具名極限：每次自動重開用掉一個 Worker 世代（B1 上限，第三次起走救援）；暫緩的操作在轉接器佇列非空的那幾毫秒不算進 `pending`。

### 14.5 實作中的讀法（2026-10-09，119 的 commit 時寫）

裁決的發佈步驟 1 要每個 commit 之後 `make test-e2-c-static` 結束碼 0，步驟 4 又要最後才凍 v58。兩者在一格上衝突：`test_the_real_manifest_matches_the_real_tree`
（殼層 generation 的守衛）在殼層檔案改了而 v58 還沒凍的時候**必然**紅——那正是它的用途。讀法：步驟 1 的「結束碼 0」在凍結之前指**這一條以外**全過
（119 的 commit：node 162/162、python 107/108，唯一的紅就是這一條，E1-C 完好），凍 v58 之後才要求整體結束碼 0。不是放寬：凍結之後的那一次仍是 R′ 的格子。

### 14.6 綁定（R′；2026-10-09，寫在任何 0.2.9 計數執行之前，值全由程式從檔案算出）

| 綁定 | 值 |
| --- | --- |
| 頁面 `e2-editor-app.js` | `537d62d73b8a38d56210fc1df3bf332155b0194a1304ab6b946d657cfd53eb5d` |
| session `narrow-editor-v2-session.js` | `62a2a20e4c66f630d77caf5bb75973e28aa58b0d8c7bf4cb0e35fa44b6a6fc5c` |
| 宿主 | 0.2.9，`069de55` |
| 引擎包 buildId | `7bf6dbd6142388f1`（同 §13.5：RESULT 從報告的 `static.buildId` 照實讀） |
| 殼層 generation | v58，`a6f9331a4292859a2509a609ded6f82ea6e0fee02af72b42b4b9686e92db234c` |
| 擁有者的文件 | 同 §11 |
| `check_m3_production_ui.py` | `fc4b2298b146ff453b4f1cf2ce3ed8a5f9d44e9701098ec59d59555286a16e64`（只動了 pin 行） |
| `run_e2_c_product_path.py` | `7468abcdaa6a0c1c59a4096a01df25bd3af7768b7299336ba390cad80c26e1b9`（`rollback` 突變重錨，fable 第二次裁決；不是計數 runner 的 pin，記在這裡供產品路徑網對照） |

六支既有 runner 的 pin 同步改綁（只動 pin 行）。改綁之後 `make test-e2-c-static` 結束碼 0。

### 14.7 結果（2026-10-09；`findings/evidence/m3-production-ui/RESULT-0.2.9.md`）

**R′ 在宿主 0.2.9 上成立。**計數前：F119-U、F111-U 全過且紅案各紅；F111-B 160/160；F119-B 由注入臂兩個瀏覽器 3/3 負責，自然路徑同頁 400 次 0 失敗，
照事先寫好的規則登錄「沒有實例可量」。計數鏈（2026-10-08 23:20 – 2026-10-09 04:17 UTC，六支 shakedown 乾淨之後）：本規格的臂 K 12/12、R 12/12、
B-ctl／S／P 6/6、B-3x 4/4、突變 40/40；六支 M3 runner 全過、紅案全紅；產品路徑網 P1–P3 HIT、0 紅格、兩臂 84 格完全相同，新舊頁面的 v19 沒有任何退步；
`make test-e2-c-static` 結束碼 0。§14.3 的預測除了「自然路徑 400 次內出現 2–3 次」與 P4「有幾格不同」之外全中。finding 119、111 改標已修（119 的自然路徑
寫明沒有實例可量，引擎根因 C 仍在 relink 佇列）。因執行而修的檢查 1（`rollback` 突變重錨），因審核而修 0。
- 更正（取代上一段的「04:17 UTC」，那是沒核對就寫的）：計數鏈在 **04:11 UTC** 結束（`runs-0.2.9/chain-2026-10-09b.txt` 的 `DONE`）。

## 15. finding 122、121、120 的修法（2026-10-10，任何實作與驗收執行之前；fable 依擁有者明說的要求裁決）

只追加。裁決原文：`findings/evidence/typing-latency/ruling/fable-ruling.md`（122＝B′，加上參考 Collabora Online 之後的兩點修正）。逼出它的：擁有者手測 0.2.9 回報的兩件事
（`findings/121-*.md`、`findings/122-*.md`）與先前登錄的 120。

### 15.1 修法（只動頁面 `web/e2-editor-app.js`；不動 worker、不換 profile、不連結；三個 commit）

- **122（B′）**：`renderDocument` 把整張畫布切成約 2048 裝置像素的條（像素邊界推出 twips，沿用 062 的條迴圈），**先畫游標所在／視窗內的條，其餘依離視窗的距離由近而遠**；
  每一條一回來就貼上；兩條之間若有新的 `document-invalidated`（`renderAgain`），就中斷這一輪、從視窗內的條重來。**任何一條在新圖到之前都保留舊圖，絕不清空**；
  頁面安靜下來時整張畫布是最新的。不加節流或去抖常數。118（`documentSizeChanged` → 重新排版＋整輪）與 062（每一條仍檢查 `TILE_NOT_PAINTED`）照舊。
- **121**：`beforeinput` 的刪除在選取範圍不是游標、而且 profile 提供 `delete-selection` 時改送 `delete-selection`（兩種 inputType；與剪下同一個判斷）；其餘照舊。
- **120**：`openDocument` 在 `session.attachInput(el.sink)` 之後把 `el.sink.disabled` 同步成新轉接器的 `state.blocked`。

### 15.2 判準

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **儀器** | `tools/probe_typing_latency.py` 只認「新的一張圖」貼在游標那一行、而且它的繪圖回覆帶著該字的修訂號或更新的（`45576249`）。紅案已在現行頁面讀出：Chrome 中位數 146 ms、Firefox 187 ms、快打最慢 904 ms（不是舊量法的約 4 ms 差）。驗收前另加「最後一鍵之後整張畫布全部換成新圖的時間」 | 先紅一次（已做） | 不得用舊的「畫面出現」欄位驗收 |
| **122-U** | 單元（頁面函式抽出編譯）：B1 條剛好鋪滿畫布（像素邊界、無縫無疊；22,256 px → 11 條）；B2 視窗內的條先畫，其餘由近而遠；B3 兩條之間來了失效就中斷、下一輪從視窗內開始；B4 每條一回來就貼、`lastTiles` 對 `paint()` 一直是一致的整組；B5 任一條 `documentSizeChanged` → 重新排版＋整輪；B6 每條 `TILE_NOT_PAINTED` 照樣丟出；B7 沒有任何一條在新圖到之前被清空。紅案各紅一次：照文件順序畫（B2）、條之間不看 `renderAgain`（B3）、整輪結束才貼（B4） | 逐實例（單元） | 122 不得宣稱已修 |
| **121-U／120-U** | 121：非游標選取＋有提供 → `delete-selection`；游標 → `delete-backward`／`-forward`；沒提供 → 今天的動作。120：`attachInput` 之後輸入槽的 `disabled` 等於新轉接器的 `state.blocked`。紅案：拿掉 offer 檢查、拿掉那一行，各紅一次 | 逐實例（單元） | 121、120 不得宣稱已修 |
| **122-B** | 候選 `dist/`、兩個瀏覽器、修好的儀器、擁有者文件：間隔 80 ms × 20 字——按鍵到提交最慢 < 80 ms、不累積（提交間隔約等於按鍵間隔）、新字上螢幕中位數 < 70 ms（Chrome）／< 90 ms（Firefox）、最慢 < 150 ms；間隔 200 ms × 10 字——上螢幕中位數 < 70／< 90 ms；最後一鍵之後 200 ms 內整張畫布換成新圖；`boundaries.odt` 間隔 200 ms 的按鍵到提交中位數 ≤ 10 ms（今天 6.3）。紅案＝`v58-*-fixed-instrument.json` 三份 | 逐實例（每個字）＋先紅一次 | 122 不得宣稱已修 |
| **121-B／120-B** | `findings/evidence/121/select_delete_probe.py` 兩個瀏覽器、Backspace 與 Delete、`range-single` → 選取的字被刪、`ready`、世代 1（今天的報告是紅案）；`findings/evidence/120/sink_probe.py` 殘留組 → `Q` 打得進去（今天的 `sink-*.json` 是紅案） | 逐實例＋先紅一次 | 121、120 不得宣稱已修 |
| **R‴** | 發佈順序同 §14：三個 commit → `make test-e2-c-static`（凍結前照 §14.5 讀）與 E1-C 完好 → `make e2-c-assets`（cutover 的兩個 pin 不動）→ 上面三組瀏覽器判準 → **最後**凍殼層 v59（絕不動 v58）→ 宿主 0.2.10 → 七支 runner 改綁（只動 pin 行）→ 各自紅案、計數鏈、產品路徑網（M2-5，新頁面）、靜態結束碼 0 | 既有協定 | 0.2.10 不得稱為已計數 |

不得：改 worker 或任何 profile 檔；讓畫布只畫視窗、或安靜之後留著舊的條；加節流或去抖常數；動產品路徑 runner 的像素判讀器或任何檢查（pin 行除外）；122 在兩個瀏覽器的
「80 ms 不累積」與「200 ms 上螢幕」兩格都綠之前標已修；v59 放進 122／121／120 以外的東西。

### 15.3 預測（寫在任何驗收執行之前）

- 122-B：視窗內那一條約是整份的 1/11，重畫約 8–15 ms，所以新字上螢幕約為提交（Chrome 約 35 ms、Firefox 約 43 ms）加 10–20 ms：Chrome 中位數 45–60 ms、Firefox 60–80 ms；
  80 ms 間隔不再累積、最慢 < 120 ms；最後一鍵之後整張畫布在 100–180 ms 內換新。若視窗內那一條在擁有者文件上超過 40 ms，觸發 C（§15.4）。
- 121-B、120-B：照修法預期全綠。產品路徑網 0 紅格（讀整張畫布的檢查在頁面安靜之後讀，B′ 那時整張是新的）。

### 15.4 登錄

- **C**（worker 轉送失效矩形與 `documentChangeSequence`，頁面只重畫被碰到的條；Collabora Online 的形狀）：relink 佇列 `queue-f122-forward-the-invalidated-rectangle`，觸發條件見上。
- **參考 Collabora Online（先例，只引用做法、不抄程式碼，MPL-2.0）**：失效轉送與合併 `cool-26-04/kit/ChildSession.cpp:3827–3889`、`kit/KitQueue.cpp:160–262`；
  保留舊圖 `browser/src/app/BitmapTileManager.ts:2288–2309`；依離視窗遠近 `:1147–1178`。不借：差分、PNG／zstd、跨縮放快取、5 秒冷卻、預抓、`EMPTY`、分割窗格。

### 15.5 122-B 第一次驗收（2026-10-10，候選 `dist/` 頁面 `b10f6017…`；數字讀自 `findings/evidence/typing-latency/v59-candidate-*.json` 的 `summary`）

- **Chrome 每一格都過**：80 ms × 20 字提交最慢 63.9 ms、上螢幕中位數 62.3／最慢 89.2 ms、整張換新 187.9 ms；200 ms × 10 字上螢幕中位數 50.9 ms、整張 158.8 ms；`boundaries` 提交中位數 6.3 ms。
- **Firefox 三格沒過**：80 ms 提交最慢 93.4 ms（判準 < 80）；200 ms 上螢幕中位數 99.8 ms（判準 < 90）；整張換新 267.5／280.0 ms（判準 ≤ 200）。其餘（80 ms 不累積、上螢幕中位數 79.8、最慢 101.1／147.6 < 150、`boundaries` 8.1 ms）都過。
- **預測對帳**（§15.3）：Chrome 上螢幕 45–60 → 50.9 中、62.3 略高；Firefox 60–80 → 79.8 中、99.8 沒中；80 ms 最慢 < 120 → 兩邊都中；整張 100–180 → Chrome 158.8 中、187.9 沒中，Firefox 都沒中。視窗內那一條的重畫（上螢幕減提交）約 8–18 ms，沒到 40 ms，**C 的觸發條件沒成立**。
- 依 §15.2 末段，122 在 Firefox 兩格（80 ms 與 200 ms 上螢幕）都綠之前不得標已修；**v59 不凍**。Firefox 為什麼慢（逐條時間軸的讀法）寫在 `findings/evidence/typing-latency/README.md` 末節；怎麼處置送 fable 裁決（判準不自行放寬）。

### 15.6 Firefox 三格之後（2026-10-10，fable 第三次裁決＝A＋B、整張換新改 (ii)；寫在任何 A＋B 的實作與執行之前）

裁決原文：`findings/evidence/typing-latency/ruling/fable-ruling.md` 末節（Third ruling）；簡報 `brief-2-firefox-misses.md`。

- **A**：輸入槽的 `beforeinput`（會送到引擎的輸入類型；組字中的更新除外）**只在 `rendering` 為真時**設 `renderAgain`——進行中的那一條是舊一輪的最後一條，下一輪從視窗內那一條開始，而且排在插入之後。不 `preventDefault`、不碰輸入轉接器（E1-C 綁定）。
- **B**：`RENDER_BAND_HEIGHT = Math.floor(MAX_TILE_HEIGHT / 32)`（約 1023 列；仍由上限推出，one-tile 突變照樣咬得到）。
- **整張換新那格改寫成 (ii)（逐實例）**：最後一鍵之後，下一輪不被中斷地跑完，而且每一條貼上的圖都帶著最後一個字的修訂號（`allCurrentAfterLastKeyMs` 不是 `None`，在探針的安靜窗內）；時間**照實記、每個瀏覽器各記一個具名數字並附預測，不當門檻**。理由：200 ms 是從 Chrome 一條到底的重畫推出來的；Firefox 在這個視窗大小安靜地畫完一輪就要 11 × 18–20 ms，B′ 之下怎麼排都過不了（簡報 F4）。這格真正守的是第一次裁決的「安靜之後沒有舊的條」，那是逐實例的性質，(ii) 驗的就是它。§15.2 的 200 ms 由本節取代。
- **兩個延遲數字不動**：Firefox 80 ms 提交最慢 < 80、200 ms 上螢幕中位數 < 90；其餘 §15.2 各格照舊。若 Firefox 提交最慢仍 ≥ 80 而且不累積：停手，帶著在候選頁面上量到的「只有插入」的底線寫第三份簡報，**不得自行改寫該格**。
- **視窗干擾（登錄）**：兩個瀏覽器畫的畫布不一樣大（Firefox 22,257 列、Chrome 17,929 列，同條高下 Firefox 每條多約 24% 像素），所以「Firefox 每條比較慢」有一部分是視窗。探針若一行就能把視窗設成一樣就設；否則每個數字旁邊記兩個畫布的寬 × 高。
- **單元**：B1 改成新條數（22,256 px → 22 條，邊界剛好）；**B8** 畫的途中來了 `beforeinput` → 進行中那一條之後結束、下一輪從視窗內開始；**B8-對照** 閒置時的 `beforeinput` 什麼都不設、不起新的一輪；B2–B7 不變。紅案各紅一次：條高改回 /16（B1）、拿掉 `rendering` 守衛（B8-對照）、拿掉監聽（B8）。
- **驗收**：122-B 在新的候選 `dist/` 上**整組重跑**（兩個瀏覽器、六份報告；頁面位元組變了，每格重新綁到新的 sha，Chrome 不能沿用上一輪）。探針用 `dbad93c0…` 或視窗一致的版本（後者的紅案要仍把 `v58-*` 基準讀成不過）。不得與其他 headless 瀏覽器工作同時跑。
- **凍 v59 的條件**：Chrome 每格；Firefox 80 ms 不累積且提交最慢 < 80、200 ms 上螢幕中位數 < 90、兩種間隔最慢 < 150；兩個瀏覽器 (ii) 都成立；`boundaries` 不變。之後照 §15.2 的 R‴ 順序。
- **不得**：B 推出的常數以外再加任何常數；A 呼叫 `preventDefault` 或碰轉接器；在沒有進行中的一輪時設 `renderAgain`；改寫延遲數字；Firefox 三格部分綠就凍。
- **預測**（A＋B）：Firefox 提交最慢 65–78 ms、上螢幕中位數 55–68 ms；Chrome 提交最慢 45–55 ms、上螢幕中位數 45–55 ms；整輪（記錄、不當門檻）Firefox 230–300 ms、Chrome 160–230 ms。

### 15.7 A＋B 的驗收（2026-10-10，候選頁面 `18c8afbe…`，commit `4353dcee`；停手規則成立）

只追加；數字讀自 `findings/evidence/typing-latency/v59-candidate2-*.json` 的 `summary`，讀法與表格在該目錄 `README.md` 末節（Second acceptance, A+B）。

- **Chrome 每格都過**（畫布 17,929 列）：80 ms 提交最慢 54.8、上螢幕中位數 36.7／最慢 59.2；200 ms 上螢幕中位數 46.0；(ii) 216.1／177.7 ms；`boundaries` 提交中位數 6.2。
- **Firefox 只差一格**（畫布 22,257 列）：80 ms **提交最慢 82.6 ms（判準 < 80；20 鍵裡 1 鍵 ≥ 80）**、不累積；上螢幕中位數 49.2（80 ms）／51.1（200 ms）、最慢 72.3／72.9；(ii) 359.8／336.0 ms；`boundaries` 8.3。
- **預測對帳**：Firefox 提交最慢 65–78 → 82.6 沒中（偏高）；Firefox 上螢幕 55–68 → 49.2、51.1 沒中（偏低）；Chrome 提交最慢 45–55 → 兩格中；Chrome 上螢幕 45–55 → 36.7 沒中（偏低）、46.0 中；整輪 Firefox 230–300 → 359.8、336.0 沒中（偏高）；Chrome 160–230 → 兩格中。
- **停手規則成立**（§15.6：Firefox 提交最慢仍 ≥ 80 而且不累積）：v59 不凍、該格不自行改寫；第三份簡報 `findings/evidence/typing-latency/ruling/brief-3-firefox-commit-floor.md` 送 fable。
- **候選頁面上的「只有插入」底線**（間隔 600 ms、沒有進行中的一輪；同一個 session 換 `dist/` 頁面位元組當對照，跑完還原並核對）：Firefox 提交中位數 v58 頁面 42.7、B′ 頁面 54.1、A＋B 頁面 57.6 ms。**裁決用的 43 ms 是 v58 頁面的底線；分條重畫把閒置底線抬高約 11–15 ms。**其中約 5 ms 是探針自己每次 `putImageData` 都寫一次 dataset 的開銷（診斷臂，不是 122-B 的儀器，`diagnostic-shim-overhead/`）；拿掉之後 80 ms 提交最慢仍 84.9。
- **逐鍵時間軸**：打字時每一鍵的可視條畫兩次——A 重起的那一輪先畫（已帶新修訂號，字在 +48–60 ms 上螢幕），`document-invalidated` 在它進行中到達又結束那一輪、再畫一次；頁面的修訂號在第二次之前 0.5 ms 才變（+73–83 ms）。這是頁面側時間戳的讀法，Worker 的佇列順序沒有量。
- 121-B／120-B 這一輪**不重跑**：裁決若再動頁面，頁面位元組還會變，到時再跑一次才綁得到最終的 sha。

### 15.8 提交那一格改寫（2026-10-10，fable 第四次裁決＝R；寫在判讀工具寫出與執行之前）

裁決原文：`findings/evidence/typing-latency/ruling/fable-ruling.md` 末節（Fourth ruling）；簡報 `brief-3-firefox-commit-floor.md`。擁有者在本 session 把第二部分（錨點）明說交 fable。

- **改寫的格**（取代 §15.6 的「80 ms 提交最慢 < 80」，兩個瀏覽器都適用；其他數字一個不動）：間隔 80 ms × 20 字，每個瀏覽器，讀綁定報告的 `rows[].revisionMs`——
  **(a)** 每一鍵 `revisionMs` < 2 × 間隔（＝160 ms）：沒有任何一鍵落後兩鍵（**逐實例**）；
  **(b)** 全輪 `revisionMs` 中位數 < 間隔（＝80 ms）：引擎跟得上按鍵（**工具封閉的彙總**，由判讀工具算，不靠人讀）。唯一的常數是該輪自己的間隔。
- **「不累積」改成 (a)＋(b)**。每鍵積壓 b_i = max(0, revisionMs[i−1] − (key_i − key_{i−1})) 與頭五／尾五中位數**照實記錄**、每個瀏覽器附預測、**不當門檻**（以前那是人眼讀的，§2 的缺陷）。
- **理由**：80 是「底線＋兩個半條」推出來的，用的是 v58 的 43 ms 底線；候選頁面自己的閒置底線是 57.6／74.4 ms（§15.7），推導的前提沒了，所以撤掉數字，而不是做 A′ 去保它（本文件開頭的驗收判準形式第 4 條）。使用者看得到的那格（字上螢幕）兩個瀏覽器都過而且有餘裕。
- **從來沒量時的結論**：122 不得標已修；v59 不凍。
- **預測**（讀既有報告）：Firefox (a) 82.6 < 160、(b) 65.3 < 80；Chrome 54.8／45.2——兩個瀏覽器都過。咬人的地方在判讀工具的紅案，不在這些數字。積壓 b_i：兩個瀏覽器每一鍵都是 0（提交都在下一鍵之前回來）；頭五／尾五中位數 Firefox 65.3／65.2、Chrome 46.3／44.1。
- **判讀工具**（`findings/evidence/typing-latency/judge.py`，只讀既有 JSON、不開瀏覽器）：每個瀏覽器綁 `page` = `18c8afbe…`、`runner` = `dbad93c0…`（診斷臂不能計數）；在兩份間隔 80 的報告上判 (a)、(b)，並從 `summary` 重判 §15.6 其餘每一格（兩種間隔的上螢幕中位數／最慢、(ii) 不是 None、`boundaries`）；印出 b_i 與頭五／尾五中位數；兩個瀏覽器都過才結束碼 0。**紅案各紅一次**：`v58-chrome-owner-gap80-fixed-instrument.json` → (a)、(b) 都不過；Firefox 候選報告每一鍵 +80 → 只有 (b) 不過；把一鍵設成 160 → 只有 (a) 不過；`runner` 是診斷臂的報告 → 拒絕。依 §34（`SPEC-M3-paragraph-merge.md`），這支新判讀工具在第一次計數使用前做一次雙席審核，之後不再審。
- **不重跑 122-B**：頁面位元組不為 122 再動，六份 `v59-candidate2-*.json` 就是證據；凍結前若頁面任何位元組變了，第三次裁決的條件 3（兩個瀏覽器整組重跑）照舊。
- **之後**：121-B／120-B 在最終頁面位元組上補跑（§15.7 延後的），然後照 §15.2 的 R‴；第二部分的錨點改在 `make test-e2-c-static` 之前。
- **不得**：v59 放 A′ 或任何 `paint()` 的改動；動探針 `dbad93c0` 的記錄方式；改寫其他任何數字；任一個瀏覽器 (a) 或 (b) 不過就凍。
- **錨點（第二部分）**：`ignore-a-document-that-grew` 只換 `find`／`replace` 兩個字串成 `      if (tile.documentSizeChanged) { documentResized = true; break; }`／`      if (false) { documentResized = true; break; }`；任何計數的產品路徑執行之前，在一個瀏覽器上跑這一條突變一次，`the-canvas-follows-a-document-that-grew` 必須紅，報告放在證人旁邊。§34.4 計「因執行而修 1」。
- **登錄（下一次改頁面時，不進 v59）**：**R1 A′**——先量可採性：探針的 Worker 包裝記下 `document-invalidated` 的修訂號；只有「插入之後的每一個失效都帶該插入遞增之後的修訂號」才可採，出現一個改前的值就放棄 A′、不補丁。單元：已涵蓋→繼續；未涵蓋→重來；這一輪還沒貼任何條→重來；`beforeinput`→一律重來。紅案：拿掉比較（今天的行為）、永不重來。預測：上螢幕 ±5、提交 ±5、Worker 每鍵 −10–13 ms（Firefox）。**R2**——`updateState()` → `paint()` 每次狀態更新都把整張畫布重貼一次、每鍵約六次（兩個頁面都這樣），是 finding 候選；設計之前先量每鍵貼了多少位元組（v58 對 A＋B）。

### 15.9 判讀工具的雙席審核與處置（2026-10-10，§34.3 的那一次；寫在計數判讀之前）

審核原文：`findings/evidence/typing-latency/review/opus-review-judge.md`、`codex-review-judge.md`（題目 `review-prompt.md`）。**因審核而修的檢查：0**——兩席的意見都沒有已 commit 的誠實執行報告當證人，照 §34.4（`SPEC-M3-paragraph-merge.md`）只登錄、不改程式。

- **更正 §15.8**（取代該節紅案那句的「Firefox 候選報告每一鍵 +80 → 只有 (b) 不過」，那是照抄裁決、沒先算）：照做實際是 (a)、(b) 都不過（最慢那鍵 82.6＋80＝162.6 ≥ 160）。照原文跑過並記下實際結果；「只有 (b)」另由 Chrome 每鍵 +80（最慢 134.8、中位數 125.2）與 Firefox 每鍵 +15（97.6、80.3）隔出（`judge-red-cases.txt`）。兩席都認為這樣處理是對的。
- **codex 的 BLOCKING（登錄）**：判讀工具在 `owner-gap200` 也要求「每一鍵都有提交時間」，而該格沒有提交的判準；探針的提交比對要求修訂號**剛好相等**（`probe_typing_latency.py:169`），上螢幕只要求「大於等於」，所以頁面若哪一次狀態更新跳過一個修訂號，該鍵會是 `revisionMs: None`，判讀工具判 FAIL 而規格會判過。這是構造的情境、沒有證人；方向是**只會多判 FAIL、不會多判 PASS**。若真的發生，那份報告就是 §34.1(b) 的證人：修判讀器、拿它當紅案、重判、不重跑。
- **opus 的登錄**（沒有 BLOCKING）：
  - 每鍵、`boundaries` 兩類閘門原本沒有紅案；opus 的突變副本補上了（`review/opus-mutations/`，主 session 自己重跑判讀工具的輸出在 `judge-on-opus-mutations.txt`：漏一鍵→只有「每鍵提交／上螢幕」紅；崩潰只剩表頭→每鍵＋(ii) 紅；`boundaries` 10.0 過、10.1 不過；上中位數 81 → (b) 紅）。
  - 探針崩潰只剩表頭時判讀工具給 FAIL（結束碼 1）而不是拒絕（2）；§34.1(a) 把崩潰導向「重跑那一步」。讀法：結束碼 1 而每鍵是「0 of N」時，先當崩潰處理。
  - **間隔的前提**：探針的 `--gap` 是「放開到下一次按下」（`probe_111_overtake.py`），實測按下到按下的中位數「80」＝98.1（Chrome）／108.6 ms（Firefox），「200」＝217.1／231.6。以名目 80 推出的門檻比格子本身的意思更嚴，所以沒有假的 PASS；但這一輪比真正 80 ms 的打字輕，裁決說的利用率約 0.8 實際約 0.60／0.46。
  - 具名極限：`page` 只雜湊 `dist/e2-editor-app.js`（其他 `dist/` 檔案與 `e2-editor.html` 過期看不見，094 那一類）；擁有者的文件沒有雜湊，唯一的指紋是畫布高度（Chrome 17,929、Firefox 22,257，兩個瀏覽器各自的 owner 報告之間一致）。
- **從來沒做時**：判讀工具照現狀計數使用。

### 15.10 122-B 計數判讀與凍 v59（2026-10-10）

- **122-B 成立**：審核過的判讀工具讀六份 `v59-candidate2-*.json`，兩個瀏覽器每一格都過、結束碼 0（`findings/evidence/typing-latency/judge-output.txt`）。§15.8 的預測全中：Firefox (a) 82.6、(b) 65.3，Chrome 54.8／45.2；積壓 b_i 兩個瀏覽器每一鍵 0；頭五／尾五 65.3／65.2、46.3／44.1（這些預測是讀既有報告後寫的，不是盲測）。
- 121-B、120-B 在同一份位元組 `18c8afbe…` 上重跑過（`5293628a`）。
- **殼層 generation v59 凍結**：`ad65480a97353cc8b1a4c98672ba2bdb437503d072b30c6bea4da57ee5acb337`，與 v58 只差 `web/e2-editor-app.js`（`18c8afbe…`），排除清單相同。凍結後 `make test-e2-c-static` 結束碼 0、E1-C 完好。之後照 §15.2 的 R‴：宿主 0.2.10 → 七支 runner 改綁 → 紅案、計數鏈、產品路徑網（先跑一次重錨的突變）。

### 15.11 綁定（R‴；2026-10-10，寫在任何 0.2.10 計數執行之前，值全由程式從檔案算出）

| 綁定 | 值 |
| --- | --- |
| 頁面 `e2-editor-app.js` | `18c8afbe29e8a5472a7a5eb0fdfae8f94a3e7a95147972c83e192fc69ebeef1a` |
| session `narrow-editor-v2-session.js` | `62a2a20e4c66f630d77caf5bb75973e28aa58b0d8c7bf4cb0e35fa44b6a6fc5c`（與 v58 相同，pin 不動） |
| 宿主 | 0.2.10，`d87960d` |
| 引擎包 buildId | `bebc7e83f573d1a8`（與 0.2.9 的引擎包只差頁面；0.2.9 的封存在 `build/archive/host-0.2.9-engine-7bf6dbd6142388f1/`） |
| 殼層 generation | v59，`ad65480a97353cc8b1a4c98672ba2bdb437503d072b30c6bea4da57ee5acb337` |
| 擁有者的文件 | 同 §11 |
| `check_m3_production_ui.py` | `5bce52d0b1426a784b002715ff2a800f4966cde1e962b7ecab25707c94d08361`（只動了 pin 行） |
| `run_e2_c_product_path.py` | `a6e318966d50cf141437dd5655bc559dca66b62deb06551e6badc9e6b5450dce`（`ignore-a-document-that-grew` 突變重錨，fable 第四次裁決第二部分；不是計數 runner 的 pin，記在這裡供產品路徑網對照） |
| 122-B 判讀工具 `judge.py` | `f02845ac5aa8cb599459ed97efcb222d9b77217c13de6bb106e6e740a84e173c`（§15.9 審核過、§15.10 計數判讀用的就是這一份） |

六支既有 runner 的 pin 同步改綁（只動 pin 行，共 12 行）；host_entry 沒有 pin。產品路徑網：v19 臂＝dist 照原樣（頁面 `18c8afbe…`），v8 臂＝同一份頁面改指 v8，改指後的 sha256 用 runner 自己的 `repointed_page()` 算出＝`d446cbfd826b1beab80b761439aa3d80b1b76ddc35a8721efb78aab436e187e6`（同一個方法對 0.2.9 的頁面算得出當時的 `4d3f3bd6…`）。

### 15.12 結果（2026-10-10；`findings/evidence/m3-production-ui/RESULT-0.2.10.md`）

**R‴ 在宿主 0.2.10 上成立。**計數前：122-U、121-U、120-U 全過且紅案各紅；122-B 由審核過的判讀工具判兩個瀏覽器 PASS（提交那格用 §15.8 的改寫）；121-B、120-B 在最終位元組上重跑過。重錨後的 `ignore-a-document-that-grew` 突變跑一次、該格紅。計數鏈（2026-10-09 18:24 – 23:20 UTC，六支 shakedown 乾淨之後）：本規格的臂 K／R 24/24、B-ctl／S／P 6/6、B-3x 4/4、突變 40/40；六支 M3 runner 全過、紅案全紅（154／99／68／156／23／70，與 0.2.9 相同）；產品路徑網 P1–P3 HIT、0 紅格，兩臂只差一格（Firefox `clear-format-removes-every-inline-format`，v8 3 NE、v19 1 PASS＋2 NE），新舊頁面的 v19 沒有任何退步；`make test-e2-c-static` 結束碼 0。finding 122、121、120 改標已修。因執行而修的檢查 1（`ignore-a-document-that-grew` 錨點），因審核而修 0。

### 15.13 擁有者手測（2026-10-10，只追加）

擁有者在宿主 0.2.10 上用 Chrome、Firefox 手測三項（快打；反白後 Backspace、反白後 Delete；跨段落反白後刪除），回報「全部通過」。測之前核對過服務出去的頁面是 `18c8afbe…`、引擎資產網址帶 buildId `bebc7e83…`。事先講明沒涵蓋的：按住刪除鍵不放（自動重複）從來沒量過。記錄在 `findings/evidence/m3-production-ui/RESULT-0.2.10.md` 末節。

### 15.14 R1、R2、C 的量測（2026-10-10，只追加；診斷，不計數、不動產品位元組）

擁有者選先量 R2。證據：`findings/evidence/typing-latency/r2-blit-bytes/`（README 有預測、結果與逐條對照；包裝程式 `blit_bytes_probe.py` 只在記憶體與 mirror 裡改，`dist/` 不動）。

- **R2 量到了**：擁有者文件上每打一個字，兩個頁面都把整張畫布重貼 6 次（Chrome 52 MB／張、Firefox 80 MB／張），花在 `putImageData` 裡 Chrome 約 20 ms、Firefox 32 ms（v58）／42–46 ms（A＋B）。其中 5 次在提交路徑上：3 次在插入送給 Worker **之前**（session 寫 pending、busy、pending 各一次，每次同步呼叫 `paint()`），2 次在修訂號顯示之前。
- **Firefox 上 A＋B 閒置底線的上升**主要是 R2 乘上條數：同樣的位元組分成 22 次呼叫比 1 次貴約 14 ms／鍵（預測說不會，沒中）。Chrome 沒有這個代價、也沒有上升。
- **拿掉 R2 的上界**（對照臂：重貼照計但不交給原生呼叫，與同一時段的基準成對）：提交中位數 Chrome −19／−16 ms、Firefox −24／−22 ms（間隔 600／80），字上螢幕 −10～−25 ms，約為現值的三到五成。
- **R1（A′）可採**：140 鍵、8 輪，每個修訂號剛好一則 `document-invalidated`，沒有任何一則帶插入前的值。
- **C 的前提在打字時不成立**：全程沒有任何 `INVALIDATE_TILES`（LOK id 0），失效通知全是游標失效（id 1）；Worker 能轉送的矩形只有游標的。是這個 build 從不發、還是只有打字時不發，沒量。
- **未量的放大條件**：畫布寬度乘 `devicePixelRatio`，比例 2 的螢幕上每次重貼是四倍位元組；以上全在比例 1。
- **另記**：Firefox 每個新 `ImageData` 第一次貼上約 5 ms、與大小無關（Chrome 0.18 ms），大多落在背景補畫，不在提交路徑上。
- **從來沒處理時的結論**：0.2.10 照現狀出貨（擁有者手測已過）；R2 是每一鍵最大的剩餘主執行緒成本，修不修、何時修交擁有者。

### 15.15 高解析度螢幕上的 R2（2026-10-10，只追加；診斷，不計數）

接 §15.14。同一支包裝程式加了 `--dpr` 與 `--window`（`findings/evidence/typing-latency/r2-blit-bytes/` README 的後三節，每節預測都寫在執行之前）。

- **devicePixelRatio 2、窄視窗**（Chrome 1450 × 35,858、Firefox 1238 × 30,616）：每鍵重貼 Chrome 73.5、Firefox 83.5 ms；間隔 80 的提交中位數 106.7／105.6 ms（超過間隔），跳過重貼 34.5／59.8。字上螢幕中位數仍 < 70。
- **devicePixelRatio 2、寬到頁面的 900 px 上限**（兩個瀏覽器都是 1800 × 44,514、每張 321 MB）：Chrome 間隔 80 的字上螢幕中位數 **368.5 ms、最慢 595.8**——finding 122 的症狀在這個組態回來了；跳過重貼則 47.0。Firefox 間隔 80 提交 208.1、上螢幕 90.5，跳過重貼後提交仍 158.8：Worker 在插入到達時正在畫背景的條（插入完成的失效在按鍵後 86 ms 才到），而 Firefox 每條新圖第一次貼上在這個寬度約 22 ms。這兩項來自「每改一次就重畫整份文件」，不是 R2。
- **Firefox 畫得出高過 32,767 列的畫布**（44,514 列，三條墨帶都有）。預測說會空白，沒中；沒有 062 同類的缺陷。
- **讀法**：拿掉 R2 在 Chrome 的每一種組態都夠；Firefox 在高解析度＋寬視窗還要不重畫整份文件（Collabora 的做法是畫布只有視窗大、只畫看得到的圖塊，`cool-26-04/browser/src/canvas/CanvasSectionContainer.ts:1518–1543`、`canvas/sections/TilesSection.ts:826–837`）。真實螢幕的比例與視窗寬度沒有量過擁有者的機器。

## 16. 下一次頁面發佈：P（`paint()` 只補變動的格）＋ finding 123（2026-10-10，任何實作與驗收執行之前）

只追加。依據：fable 第五次裁決（`findings/evidence/typing-latency/ruling/fable-ruling.md`「Fifth ruling」與其補充；擁有者說「發給fable裁決」）、量測 `findings/evidence/typing-latency/r2-blit-bytes/`（§15.14、§15.15）、finding 123。擁有者 2026-10-10 裁示：「123 一起放進 A，開始寫規格」。裁決的「A」在本節叫 **P**（§15.6 已經有一個 A），裁決的 A1–A4＝本節 P1–P4。C′（視窗大小的畫布）是**下一個**獨立的規格與發佈，不在本節。

### 16.1 修法（只動頁面 `web/e2-editor-app.js`；不動 worker、不換 profile、不連結；兩個 commit）

- **123**：`renderBands` 在最後一段不足半條（`RENDER_BAND_HEIGHT / 2`，由條高推出、不是新常數）時，把它併進前一條：最後一條介於半條與一條半之間，其餘條高不變。整張畫布不到半條時就是一條。062 的 `tileWasPainted` 守衛原樣保留。
- **P**：`paint()` 記住畫布上現在畫著的覆蓋層（游標矩形、選取矩形、是否 collapsed，連同畫布與文件尺寸）。
  - 新的覆蓋層與它**相同**：一個像素都不貼，直接返回。session 寫 pending、busy、pending、ready 這幾次都落在這裡。
  - **不同**：把舊、新覆蓋層的每個矩形各擴到整數像素再外擴 1 px，從條快取（`lastTiles`）以 dirty-rect 形式的 `putImageData` 補回底圖；還沒畫過的條改用 `clearRect`，因為那裡本來就是透明。接著把覆蓋層畫在這些矩形的 clip 之內，選取的 multiply 不會疊兩次。
  - `layoutCanvas` 清掉畫布時，「畫著的覆蓋層」一起清掉；`paintBand` 照舊在條內重畫覆蓋層，並把「畫著的覆蓋層」記成目前的那一個。
  - 不延後、不合併：`paint()` 仍在 `updateState()` 裡同步執行。不加節流、去抖或合併常數，不用 `requestAnimationFrame`。

### 16.2 判準

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **123-U** | 單元（頁面函式抽出編譯，同 122-U）：對每一個畫布高度 1 ≤ total ≤ 5 × `RENDER_BAND_HEIGHT`（全部列舉），條剛好鋪滿（無縫無疊），除最後一條外每條都是 `RENDER_BAND_HEIGHT`，最後一條 ≥ min(total, ⌈半條⌉) 且 ≤ 一條半；35,858 → 35 條、最後一條 1,076 列。B1（22,256 → 22 條、最後 773 列）照舊成立。紅案：拿掉併段（35,858 會切出 53 列的最後一條）→ 紅 | 工具封閉的列舉（高度由測試生成） | 123 不得標已修 |
| **P-U** | 單元：**P-U1** 覆蓋層沒變時 `paint()` 零次 `putImageData`、零次 `clearRect`；**P-U2** 游標由 y1 移到 y2：只有 dirty-rect 補回，涵蓋舊、新游標擴張後的矩形，然後在 clip 內畫游標；沒有整條的貼上；**P-U3** 選取變動：補回涵蓋舊、新每一個選取矩形；**P-U4** `layoutCanvas` 之後第一次 `paint()` 不從舊的條補回；**P-U5** 補回落在還沒畫過的條時用 `clearRect`。紅案各紅一次：`paint()` 改回每條整貼（P-U1）、拿掉舊矩形的補回（P-U2）、拿掉 layout 的重設（P-U4） | 逐實例（單元） | P 不得宣稱完成 |
| **P1**（裁決 A1） | 比例 1、擁有者文件、間隔 600 × 10，兩個瀏覽器：**每一鍵**送進 `putImageData` 的位元組，扣掉新條第一次貼上，≤ 畫布位元組的 2%。儀器＝`blit_bytes_probe.py`，先改成 dirty-rect 形式只計 dirtyW × dirtyH × 4（今天它把整張來源圖都算進去，會把 P 的補回誤算成整條）。判讀＝新判讀工具 `judge_p.py`（§34.3 的一次雙席審核在第一次計數使用之前） | 逐實例（每一鍵） | P 不得宣稱完成；0.2.10 照舊 |
| **123-B** | 兩個瀏覽器、`--dpr 2 --window 800x1000`、擁有者文件（推算畫布 1450 × 35,858，出貨頁面的最後一條 53 列）、間隔 600 × 3：整輪沒有任何含 `TILE_NOT_PAINTED` 的 toast；最後一條在最後一鍵之後有一次新圖貼上；`allCurrentAfterLastKeyMs` 不是 `None`。判讀＝`judge_p.py` | 逐實例＋先紅一次 | 123 不得標已修 |
| **P2**（裁決 A2） | §15.8 (a)(b) 與 §15.6 的上螢幕各格，比例 1、兩個瀏覽器、計數探針 `dbad93c0…` 原樣，六份報告（擁有者間隔 80 × 20、間隔 200 × 10、`boundaries` 間隔 200 × 10）。判讀＝`judge.py` 的副本，**只改頁面常數**與預設檔名 | 工具封閉（既有判讀工具） | v60 不凍 |
| **P3**（裁決 A3） | **記錄、不當門檻**，每格附預測：比例 1.5 寬（`--dpr 1.5 --window 1400x1000`）、比例 2 窄（`--dpr 2`）、比例 2 寬（`--dpr 2 --window 1400x1000`），兩個瀏覽器，間隔 80 × 20 | 記錄 | 結果寫成 P 頁面的具名限制 |
| **P4**（裁決 A4） | 產品路徑網照 M2-5（新頁面，突變全紅之後才計數），不動任何判讀器；121-B、120-B 在最終位元組上重跑 | 既有協定 | v60 不凍 |
| **R⁗** | 發佈順序同 §15.2 的 R‴：`make test-e2-c-static`、E1-C 完好、`make e2-c-assets`、上面各格，**最後**凍殼層 v60（絕不動 v59）→ 宿主 0.2.11 → 改綁（只動 pin 行）→ 紅案、計數鏈、產品路徑網、靜態結束碼 0 | 既有協定 | 0.2.11 不得稱為已計數 |

### 16.3 紅案（先算好；在 `dist/` 仍是出貨頁面 `18c8afbe…`、任何實作之前執行）

- **P1**：改好的儀器跑出貨頁面，比例 1、擁有者、間隔 600 × 10，兩個瀏覽器 → 每一鍵 6.0 張畫布＝600%（`r2-current-*` 那幾列，那時的儀器在出貨頁面上沒有 dirty-rect 呼叫，算法相同）→ **FAIL**。
- **123-B**：出貨頁面、`--dpr 2 --window 800x1000`、兩個瀏覽器 → 有 `TILE_NOT_PAINTED` toast、`allCurrent` 為 `None` → **FAIL**。Firefox 能不能重現，取決於 `--window 800x1000` 在 Firefox 是否也得到 725 CSS px 寬的畫布。不能的話，照實記下，換一個能讓最後一條短於約兩倍間隙的寬度，**在任何實作之前**重新指定。
- **P2**：`judge.py` 副本讀 `v58-chrome-owner-gap80-fixed-instrument.json` → (a)(b) FAIL（同第四次裁決的紅案）；讀出貨頁面的 `v59-candidate2-*` → 頁面綁定不符 → REFUSED。
- **`judge_p.py` 自己的紅案**：同一份報告改一鍵的位元組到 3% → 只有 P1 紅；加一則 `TILE_NOT_PAINTED` toast → 只有 123-B 紅；`runner` 換成別的雜湊 → REFUSED。

### 16.4 預測（寫在任何執行之前）

- **P1**：P 頁面上每一鍵只有一次覆蓋層變動（插入回覆帶來新的游標），補回兩個約 3 × 18 px 的矩形，約 0.4 KB，畫布的 0.001% 等級。兩個瀏覽器都過。
- **123-B**：P 頁面兩個瀏覽器都沒有 toast，最後一條 1,076 列有新圖貼上，`allCurrent` 有數字（Chrome 約 400–750 ms，跟 §15.15 的比例 2 窄那幾列同級）。
- **P2**（裁決的預測，Firefox 依 §15.15 後的補回量測加約 6 ms）：
  - Chrome：間隔 80 提交中位數 22–32、最慢 < 45，上螢幕中位數 22–32；間隔 200 上螢幕 25–40；`boundaries` 4–8。
  - Firefox：間隔 80 提交中位數 40–52、最慢 < 80，上螢幕 32–46；間隔 200 上螢幕 35–50；`boundaries` 6–10。
  - (ii) 記錄：Chrome 150–220、Firefox 280–360 ms。
  - 每格都過。
- **P3**（跳過重貼那一臂是 P 的上界，再加上 Firefox 每 task 一次的補回成本）：

  | 組態 | Chrome 提交中位數 | Firefox 提交中位數 |
  | --- | --- | --- |
  | 比例 1.5 寬 | 35–50 | 105–135，過不了 (b) |
  | 比例 2 窄 | 34–45 | 65–90 |
  | 比例 2 寬 | 47–65 | 170–220，過不了 (a)(b) |

  Firefox 在比例 ≥ 1.5 寬時過不了，這是 P 頁面的具名限制，由 C′ 關閉。
- **P4**：0 紅格。讀游標／反白墨跡的檢查在頁面安靜之後讀，P 之後畫布上的內容與今天相同。

### 16.5 不得

- P 與 C′ 放在同一次頁面發佈；v60 放 P 與 123 以外的東西。
- 改 worker 或任何 profile 檔；加節流、去抖、合併常數；`paint()` 延後到別的 task。
- 把游標或反白移出畫布（DOM 覆蓋層留給 C′ 的規格，連同它帶進來的檢查變動一起裁）。
- 動產品路徑 runner 的判讀器或任何檢查（pin 行除外）；改寫比例 1 的數字；`judge.py` 副本改頁面常數與預設檔名以外的任何東西。

### 16.6 登錄

- **具名限制（P 頁面）**：
  - Firefox 在比例 ≥ 1.5 寬時過不了 §15.8：大畫布每個 task 第一次貼上要付整張的成本，補一小塊也一樣。
  - 062 的 65,535 列上限：約 65 頁（比例 1）、43 頁（1.5）、33 頁（2，寬）以上的文件整份空白。
  - 按住刪除鍵不放沒量過。

  三者都由 C′ 處理，或在 C′ 的規格裡重新判定。
- **R1（A′）出局**（裁決）。**H9**（打字時沒有 `INVALIDATE_TILES`）在 C′ 之後再解釋，候選解釋是 040 那種永不閒置的 build；C′ 的設計假設永遠不會有失效矩形。
- **§34.4**：`blit_bytes_probe.py` 改成計 dirty-rect 位元組，是一支還沒被任何判準用過的儀器在第一次使用前的準備，不是因執行或審核而修。`judge_p.py` 是新的判讀工具，在第一次計數使用前做那一次雙席審核。這一段開始時兩個數字都是 0。

### 16.7 更正（2026-10-10，只追加；任何執行之前）

取代 §16.3 裡「P2」那一點的執行時機：`judge.py` 的副本綁的是**候選頁面**的雜湊，實作之前那個雜湊不存在，所以 P2 的兩個紅案（`v58-chrome-owner-gap80-fixed-instrument.json` → FAIL；`v59-candidate2-*` → REFUSED）在副本做出來的那一步（`make e2-c-assets` 之後）跑，**排在任何 P2 計數判讀之前**。§16.3 其餘三點（P1、123-B、`judge_p.py` 自己的紅案）照原文，在任何實作之前。

### 16.8 出貨頁面上的紅案與 123-B 視窗的重新指定（2026-10-10，只追加；任何實作之前）

依 §16.3 在出貨頁面（`dist/` 仍是 `18c8afbe…`）上跑了 P1 與 123-B 的紅案（`findings/evidence/typing-latency/p-release/`，README 有預測與結果；判讀＝`judge_p.py --page 18c8afbe… --prefix shipped`）。

- **P1 兩個瀏覽器都 FAIL**（預測中）：Chrome 每一鍵 6.0 張畫布（600%），Firefox 第一鍵 11.0、其餘 6.0；dirty-rect 與 `clearRect` 都是 0 次。
- **123-B 的 Chrome FAIL**（預測中），但畫布不是 §16.2 推算的 1450 × 35,858：`--window 800x1000` 下 Chrome 的畫布是 **1490 × 36,847**，最後一條 **19 列**（y 36,828，整條落在最後一頁下方的透明間隙裡）；1450 是 Chrome 800 × 600 **預設**視窗的值。兩則 `TILE_NOT_PAINTED` toast、`allCurrent` 為 `None`、最後一條從未被貼上——三格全紅。
- **123-B 的 Firefox 在 800x1000 不重現**：畫布 1496 × 36,996、最後一條 168 列，沒有 toast。§16.3 預先寫好的處方適用。

**重新指定（取代 §16.2 123-B 那一列的視窗與推算畫布）**：Chrome `--window 800x1000`、Firefox `--window 797x1000`。依量到的差值（Chrome 的桌面＝CSS 視窗 − 15、Firefox − 12），兩個瀏覽器都得到 745 CSS px 寬、**1490 × 36,847** 的畫布，出貨頁面的最後一條 19 列。其餘（比例 2、擁有者文件、間隔 600 × 3、三格判準）不變。`judge_p.py` 的 123-B 視窗改成按瀏覽器綁定。Firefox 在 797 寬的紅案在任何實作之前重跑。

**§16.4 的 123-B 預測隨之改寫**：P 頁面上最後一條是 1023 + 19 = **1,042 列**（y 35,805），兩個瀏覽器都沒有 toast，最後一條在最後一鍵之後有新圖貼上，`allCurrent` 有數字（Chrome 約 400–750 ms、Firefox 約 900–1,400 ms；Firefox 那一側依出貨頁面 800 寬的 1,237.3 ms）。

**§34.4**：`judge_p.py` 的這一處改動是被一次執行逼出來的（雖然處方在 §16.3 事先寫好），記為「因執行而修 1」。它仍在雙席審核與第一次計數使用之前。

### 16.9 `judge_p.py` 的雙席審核與處置（2026-10-10，§34.3 的那一次；寫在任何計數判讀之前）

審核原文：`findings/evidence/typing-latency/review/opus-review-judge-p.md`、`codex-review-judge-p.md`（題目 `review-prompt-judge-p.md`）。審核期間 P 已 commit（`706e8565`），opus 拿真的 `paint()` 對過判讀工具的前提。**因審核而修的檢查：0**——兩席的意見都沒有已 commit 的誠實執行報告當證人，照 §34.4 只登錄。

- **codex 的三條 BLOCKING（登錄，都是構造的產品退步，不是誠實執行的誤判）**：
  - 明寫 `--dpr 1` 的 P1 執行會被拒絕（綁定要求 `dprRequested` 為 `None`）。方向只會多拒絕；P1 的執行照 §16.2 不帶 `--dpr`。
  - 「第一次貼上的 ImageData」比「新條第一次貼上」寬：頁面若把補回包成一張新的 ImageData，那些位元組會被當成新條而不計。**實際的 P 頁面不這樣做**（補回用的是 `lastTiles` 裡、`paintBand` 已整貼過的同一個物件，opus 逐行對過），而且 P-U 的逐像素模型要求每個像素的底圖就是該條快取的那張圖，換成別的物件會紅。
  - `paintBand` 若誤用 dirty-rect，探針仍以整條列數記覆蓋。同上，P-U 的逐像素模型擋得住（未補到的像素底圖不對）。
- **opus（沒有 BLOCKING）**：
  - **N2**：123-B 綁了要求的視窗，沒綁得到的畫布；Firefox 版本漂移若讓 797 寬不再得到 1490 × 36,847，紅案會靜靜失去鑑別力。它的證人是手動改標籤的報告（M2），不是誠實執行，所以只登錄；**讀法**：計數判讀時把兩個瀏覽器 123-B 的畫布尺寸照實寫進結果，不是 1490 × 36,847 就先停手回報。
  - **N1** 同 codex 第二條；**N3**「最後一條在最後一鍵之後被貼上」被 `allCurrent` 不是 `None` 蘊含（多餘、無害）。
  - 123-B「每一鍵都打了」那格沒有紅案（讀的是 `raw.keys`，與 K7 的 `r2.keys` 不同欄）；opus 的 M3 補上了，只紅那一格。
  - 文件：README 第 3 行的 123-B 視窗已改成按瀏覽器寫；判讀工具的雜湊與綁定的 `--page` 在計數判讀時一起記下。
- **兩席都認為** §16.8 的重新指定與按瀏覽器綁定成立，「因執行而修 1」的記法正確。
- **從來沒做時**：判讀工具照現狀計數使用。

### 16.10 候選頁面的驗收（2026-10-10，候選 `dist/` 頁面 `36c2b18b…`，commit `db9a0052`（123）、`706e8565`（P）；只追加）

數字與表格在 `findings/evidence/typing-latency/p-release/README.md`（Results on the candidate page）。

- **123-U、P-U**：單元 189/189；§16.2 的紅案各紅一次（R-123 只紅 123-U；R-P1 紅 P-U1；R-P2 紅 P-U2；R-P4 只紅 P-U4）。額外的「拿掉 clip」是等價突變（P 畫的每個矩形都已先補回），照實記為綠。
- **P1 成立**（審核過的 `judge_p.py`，結束碼 0）：每一鍵補回 640／736 位元組（Chrome／Firefox），約畫布的 0.001%；出貨頁面是 600%。
- **123-B 成立**：兩個瀏覽器畫布都是 1490 × 36,847（§16.9 N2 的讀法成立），沒有 `TILE_NOT_PAINTED`，最後一條 1,042 列在最後一鍵之後貼上，`allCurrent` 700.9／1,047.3 ms。
- **P2 成立**（`judge_p2.py`，結束碼 0）：間隔 80 提交中位數 Chrome 26.1、Firefox 36.2 ms（出貨頁面 45.2／65.3），字上螢幕 25.3／29.7 ms。Chrome 間隔 80 那份第一次與靜態測試的編譯重疊，在讀數之前就決定不計、單獨重跑。
- **P3（記錄）**：Firefox 比例 1.5 寬的提交中位數 60.9 ms、最慢 77.3——**§15.8 的 (a)(b) 都過**（預測 105–135、過不了）；比例 2 寬 84.5／108.5——只有 (b) 沒過（預測 170–220、兩格都過不了）。Chrome 三種組態的提交中位數 34.9–43.9 ms。
- **121-B／120-B**：在 `36c2b18b…` 上重跑，與 v59 的報告逐欄相同（只差延遲字串）。
- **§16.6 具名限制的改寫（取代該節第一點）**：Firefox 在**比例 2、寬到 900 px 上限**時，間隔 80 的提交中位數 84.5 ms，過不了 §15.8 (b)（一次量測，包裝程式）；比例 1.5 寬已過。其餘兩點（062 的 65,535 列上限、按住刪除鍵沒量過）不變，仍交 C′。
- **之後**：照 R⁗——`make test-e2-c-static`、E1-C 完好、凍殼層 v60、宿主 0.2.11、改綁、紅案、計數鏈、產品路徑網。
- **殼層 generation v60 凍結**（2026-10-10）：`784a1d93fd8e7d18482c92140d5b08ffcdb8a3879c6d882dc4603613e9f657af`，與 v59 只差 `web/e2-editor-app.js`（`36c2b18b…`），排除清單相同（承自 v40）。凍結前 `make test-e2-c-static` 只紅在 generation 守衛（`release-0.2.11/test-e2-c-static-before-freeze.txt`），凍結後結束碼 0（node 189＋5、python 108）、E1-C 完好。v59 沒有被動到。

### 16.11 綁定（R⁗；2026-10-10，寫在任何 0.2.11 計數執行之前，值全由程式從檔案算出）

| 綁定 | 值 |
| --- | --- |
| 頁面 `e2-editor-app.js` | `36c2b18baa8340c559cc445a5e7ef6f87957356aa94f54b863d0189328591a44` |
| session `narrow-editor-v2-session.js` | `62a2a20e4c66f630d77caf5bb75973e28aa58b0d8c7bf4cb0e35fa44b6a6fc5c`（與 v59 相同，pin 不動） |
| 宿主 | 0.2.11，`6b53c2e` |
| 引擎包 buildId | `b99f4b138839ff04`（與 0.2.10 的引擎包只差頁面；0.2.10 的封存在 `build/archive/host-0.2.10-engine-bebc7e83f573d1a8/`，逐位元組核對過） |
| 殼層 generation | v60，`784a1d93fd8e7d18482c92140d5b08ffcdb8a3879c6d882dc4603613e9f657af` |
| 擁有者的文件 | 同 §11 |
| `check_m3_production_ui.py` | `d799fa9d6e9632ed6f99bb39dc8b6b1cce22fb7558da240a71c2c164057549a5`（只動了 pin 行） |
| `run_e2_c_product_path.py` | `a6e318966d50cf141437dd5655bc559dca66b62deb06551e6badc9e6b5450dce`（與 0.2.10 相同，沒動） |
| P1／123-B 判讀工具 `judge_p.py` | `1461fc0344858a6db29ad544a043f1f046093064acd15786a7a6ce2518d33c41`（§16.9 審核過、§16.10 計數判讀用的就是這一份） |
| P2 判讀工具 `judge_p2.py` | `1faea9d997f0be9f33ca07ef1070c91ed9bbd8a69ffb035fff9efa72c4997a22` |

六支既有 runner 的 pin 同步改綁（只動 pin 行，共 12 行）；host_entry 沒有 pin。改綁後 `make test-e2-c-static` 結束碼 0（`findings/evidence/release-0.2.11/test-e2-c-static-after-repin.txt`）。產品路徑網：v19 臂＝dist 照原樣（頁面 `36c2b18b…`），v8 臂＝同一份頁面改指 v8，改指後的 sha256 用 runner 自己的 `repointed_page()` 算出＝`bd29eccaeab42ab0dc3bc20d5484b7a07d448e14eb92bb1a63ae43acf17747fe`（同一個方法對 0.2.10 的頁面算得出當時的 `d446cbfd…`）。預測與判讀副本在 `findings/evidence/release-0.2.11/product-path/`；P 移動了錨點所在位置的兩個突變（`caret`、`caret-ignores-x`）在任何計數執行之前各跑一次（Chrome），各自那一格必須紅。

### 16.12 結果（2026-10-10；`findings/evidence/m3-production-ui/RESULT-0.2.11.md`）

**R⁗ 在宿主 0.2.11 上成立。**計數前（§16.10）：123-U、P-U 全過且紅案各紅；P1、123-B 由審核過的 `judge_p.py` 判兩個瀏覽器 PASS，123-B 兩個瀏覽器的畫布都是 1490 × 36,847（§16.9 N2 的讀法成立）；P2 由 `judge_p2.py` 判 PASS；P3 已記錄；121-B、120-B 在最終位元組上重跑過。P 移動錨點的兩個突變各跑一次：`caret` 咬到；`caret-ignores-x` 那格是 NE，在出貨 v59 頁面上的對照完全相同，歸給判讀器（登錄，不修）。計數鏈（2026-10-10 01:57 – 06:47 UTC，六支 shakedown 乾淨之後）：本規格的臂 K／R 24/24、B-ctl／S／P 6/6、B-3x 4/4、突變 40/40；六支 M3 runner 全過、紅案全紅（154／99／68／156／23／70，與 0.2.10 相同）；產品路徑網的判讀工具先在 scratch 副本上紅過一次，判定 P1–P3 HIT、0 紅格，兩臂沒有任何一格不同；新舊頁面的 v19 沒有任何退步（只差 Firefox `clear-format-removes-every-inline-format`，舊 1 PASS＋2 NE、新 3 NE，只有 NE 的差別）；計數之後 `make test-e2-c-static` 結束碼 0。finding 123 改標已修。P 頁面的三條具名限制（§16.10 改寫後的 §16.6）照舊，交 C′。因執行而修的檢查 1（§16.8），因審核而修 0；計數鏈本身 0。

### 16.13 擁有者手測（2026-10-10，只追加）

擁有者在宿主 0.2.11 上手測，回報「已手動測試，目前看起來正常」。測之前核對過宿主 app 裡的 `e2-editor-app.js.gz` 與 `.zst` 解壓後都是 `36c2b18b…`、`info.xml` 是 0.2.11。同一次手測另回報兩件事，另立 finding（都不是本次發佈的退步，P 沒有碰那兩條路）：(1) 長文件裡用「下」方向鍵把游標往下移，畫面不跟著捲動；(2) 用方向鍵移動游標時狀態膠囊一直閃「處理中」，但內容沒有變更。記錄在 `RESULT-0.2.11.md` 末節。
