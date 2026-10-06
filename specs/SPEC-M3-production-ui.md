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
