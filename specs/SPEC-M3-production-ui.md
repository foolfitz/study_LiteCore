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
