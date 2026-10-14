# SPEC M3：捲動時跟著卷軸游標的頁碼泡泡

> 2026-10-14 立（草稿）。判準（第 5 節）寫在任何實作與執行之前。證據標記照 `doc-conventions`：**已觀察**＝量過、**讀原始碼**＝沒量、**推論**。
> 起點：任務 10-14q 做完的頁面（0.2.22 候選；寫這份時 `web/e2-editor-app.js` 正在被 144 的任務改，紅案的「今天的位元組」＝v71 凍結時的頁面雜湊，由實作任務填入）。只動頁面；不動引擎、不連結、不換 profile、不改宿主樣板（§7）。完整計數照 `release-count-batched` 併入下一個改引擎的批次。

## 1. 為什麼要有

擁有者 2026-10-14：「我希望『拉著卷軸的游標』旁邊會有一個泡泡顯示當前頁數」。finding 143 的底部狀態列（宿主 0.2.21，Collabora 的樣子）**留著**；泡泡是第二個讀出口，在使用者的眼睛正在看的地方——卷軸旁邊。

**擁有者的決定（2026-10-14）：泡泡「捲動時都出現」→ OK。**拉卷軸、滾輪、鍵盤造成的捲動都顯示，捲動停了就淡出。理由（主 session 提的，擁有者採）：原生捲軸分不出「拉著游標」和「滾輪」——Chrome 對卷軸按下會發 `mousedown`、Firefox 不發（推論，未量），任何靠指標事件的判別都是只對一個瀏覽器成立的規則。主 session 記得 Google Docs 是這個樣子，**未查證**；設計不依賴先例。

## 2. 事實（讀原始碼，2026-10-14；頁面 `2d6c4580…`＝0.2.21）

- **頁碼今天怎麼算**：`#page-status` 的字由 `updatePageStatus()`（`web/e2-editor-app.js:305`）從上一次 `pageRectangles()` 的答案與 `visibleDocRows()` 算出，`onDeskScroll`（`:1152`）每次捲動呼叫它，**不呼叫引擎**（SPEC-M3-link-batch §10.8；10-14n／K4 (f) 量過：18 步滾輪 0 個非 paint 請求）。字串由 `pageStatusText`（`editor-shell-v2/narrow-editor-v2-session.js:253`）給：「第 N 頁，共 M 頁」或「第 N–L 頁，共 M 頁」（U+2013）。
- **捲動的容器是 `#desk`，不是視窗**：`.desk { flex: 1; overflow: auto; }`（`web/e2-editor.html:84`）；`#paper` 是整份文件的高、canvas 是三個畫面高的窗（release C′）。`followCaret`（`:929`）用 `el.desk.scrollTop` 捲——鍵盤移游標造成的捲動也是 `#desk` 的 `scroll` 事件。頁面沒有 `dir`、沒有 RTL 處理、沒有 `prefers-reduced-motion` 處理；唯一的過場是 `#toast` 的 `transition: opacity .18s`（`html:219`）。
- **卷軸長什麼樣（已觀察，K4 的截圖，宿主、1850 寬）**：`#desk` 高 794（Firefox）／780（Chrome），60 頁的 `scrollHeight` 74,182。Firefox 157 是 **overlay 卷軸**：貼在右緣、約 3 px 寬、游標約 35 px 長、沒有箭頭、不佔版面（`offsetWidth − clientWidth` 推論為 0）。Chrome 151 是**傳統卷軸**：上下各有箭頭鈕（約 17 px）、游標約 23 px 長。`scrollTop` 4900 時，游標中心約在視口 y ≈ 230（Firefox）／234（Chrome）——從 2× 裁切目測，±8。**游標的位置沒有任何 DOM API 可讀**；兩個瀏覽器的最短游標長度與箭頭都是瀏覽器的，頁面不知道。
- **宿主**：`templates/editor.php` 把頁面的 `<style>` 包進 `@scope (#litecore-editor-root)`，根元素 `height: 100%` 填滿 Nextcloud 的 `#content`（`overflow: clip`、圓角 16 px）；`#page-status` 在宿主裡是根元素底緣 32 px 的狀態列（143 的修法）。`#toast` 已經用 `position: fixed` 而宿主沒有為它補任何規則。
- **會說話的元素（本頁與宿主）**：`#a11y-para`（`aria-live="polite"`，`html:308`；寫入前先比對，`app.js:421`）、`#toast`（`role="status"`）、宿主 `#litecore-host-bar`（`role="status"`）。捲動不該說話：finding 087／088，`#page-status` 刻意不是 live region。
- **`web/e2-editor.html` 沒有被任何閘門雜湊**（finding 094；v70 bundle 的範圍是 `*.js`）。`layoutCanvas` 因此把樣式寫在 JS 裡。

## 3. 設計

只動 `web/e2-editor-app.js`。元素由頁面建一次（`<div id="scroll-bubble" aria-hidden="true">`，插在 `#desk` 之後），樣式用 CSSOM（`element.style`）寫，**html 零位元組改動**（§2 最後一點；也避開宿主 `@scope` 與 `[hidden]` 那一類覆寫問題，143 踩過）。

- **3.1 說什麼**：`#page-status` 的字到第一個「，」為止——「第 4 頁」或「第 4–5 頁」。純函式 `scrollBubbleText(statusText)`；狀態列 hidden 或字是空的 → `null` → 泡泡不顯示。**兩頁都看得到時**照狀態列寫「第 4–5 頁」：同一個瞬間兩個讀出口不說不同的數字，而且文字判準變成「等於狀態列的頁數部分」，不必再養第二條規則。「共 M 頁」留給狀態列：拉的時候 M 不變，泡泡要短。
- **3.2 放哪裡**：`position: fixed`，每次捲動從 `#desk.getBoundingClientRect()` 算。純函式 `scrollBubblePlace(desk, bubble)`：
  - 垂直：`f = scrollTop / (scrollHeight − clientHeight)`；游標長度模型 `t = max(clientHeight² / scrollHeight, 20)`；箭頭餘裕 `a = scrollbarWidth > 0 ? 17 : 0`（傳統卷軸有箭頭，overlay 沒有；§2 兩個瀏覽器各一個樣本）；中心 `y = desk.top + a + t/2 + f × (clientHeight − 2a − t)`，再夾在 `[desk.top + h/2, desk.bottom − h/2]`（h＝泡泡高）。登錄 **L-bubble-thumb-model**：游標真實長度與箭頭是瀏覽器的，頁面只按比例放；判準量的是**真游標**（§5 N2）。
  - 水平：`scrollbarWidth = desk.offsetWidth − desk.clientWidth`（overlay 是 0）；泡泡右緣 `= desk.right − (max(scrollbarWidth, 12) + 6)`（overlay 的細游標貼著右緣，12 的下限讓泡泡不蓋到它）。**邊由 `desk.clientLeft` 決定**（MDN：RTL 且有直向卷軸時 `clientLeft` 含卷軸寬）——卷軸在左就鏡射到左緣。不看語系。登錄 **L-bubble-rtl-untested**（本頁 zh-TW、沒有 RTL 臂；單元測試覆蓋 `side: "left"`）。
  - 縮放：全部用 CSS px（`getBoundingClientRect`），**推論**縮放不影響；儀器不驅動瀏覽器縮放，由擁有者手測涵蓋。登錄 **L-bubble-zoom-untested**。
  - `scrollHeight ≤ clientHeight`（沒有東西可捲，`f` 無定義）→ `null`，永不顯示。**「一頁就不顯示」不是規則**：一頁的文件在 794 px 高的 desk 裡仍是可捲的（A4 在 900 寬下 1273 px 高），那時泡泡寫「第 1 頁」是對的。
- **3.3 什麼時候**：`#desk` 的每一個 `scroll` 事件（`onDeskScroll` 裡，`updatePageStatus()` 之後）→ 顯示並重設計時器；最後一個事件後 **1,000 ms** 隱藏（`opacity` 0，過場 180 ms 與 `#toast` 同，過場完 `visibility: hidden`）。`matchMedia("(prefers-reduced-motion: reduce)")` 為真 → `transition: none`，立刻顯示、立刻隱藏；**1 秒的停留不是動畫，照舊**。視窗 `resize` → 重放或隱藏。後果（擁有者的決定包含它）：打字把視圖推下去、`followCaret` 捲動時，泡泡也會出現 1 秒。
- **3.4 無障礙**：`aria-hidden="true"`、沒有 `role`、沒有 `aria-live`、`pointer-events: none`、不可聚焦、不碰 `#a11y-para` 與 `#toast`。讀報軟體的使用者有狀態列（瀏覽模式讀得到）；泡泡是視覺的。
- **3.5 不做**：只在拉游標時顯示（§1）；點泡泡跳頁、Collabora 的 badge（143 裁決列為之後）；宿主 CSS（§7，預測不需要）；用引擎（0 個請求的性質不變）。

## 4. 擁有者可推翻的決定

| 題 | 這裡的裁定 | 替代方案 |
|---|---|---|
| 兩頁可見 | 「第 4–5 頁」，與狀態列同 | 只寫第一頁「第 4 頁」（要第二條規則） |
| 要不要「共 M 頁」 | 不要 | 「第 4 頁／60」 |
| 停留時間 | 1,000 ms＋180 ms 淡出 | 擁有者手測後改數字；判準 N4 的 1.5 s 上限隨之改並寫理由 |
| 打字推動視圖也顯示 | 顯示（任何 `scroll` 事件） | 排除頁面自己寫 `scrollTop` 的捲動——但鍵盤捲動在本頁就是那條路，排除了鍵盤 |

**擁有者 2026-10-14 裁示：「OK 照規格走」。**四列都照這裡的裁定：「第 4–5 頁」與狀態列同；不要「共 M 頁」；1,000 ms＋180 ms 淡出，手測後再調；打字推動視圖也顯示。實作任務同日開始（只追加）。

## 5. 判準（寫在任何實作與執行之前）

形式照 AGENTS.md「驗收判準的形式」§1；每條附「若永遠沒做」的預設結論。儀器：10-14n／10-14o 的探針（`findings/evidence/host-0.2.21/probe_10_14o.py`）加泡泡欄位——`read()` 多記 `bubble: {shown, text, rect}` 與 `a11y: #a11y-para.textContent`，`GEOMETRY` 多記 `desk.offsetWidth/clientWidth/clientLeft` 與泡泡的 rect／`transition-duration`／`checkVisibility()`；滾輪臂照 `page-number` 的 18 步（14×700、3×3000、回頂），每步後 0.6 s 讀一次並截圖。**真游標讀法**：截圖欄 x ∈ [desk.right − 12, desk.right − 1]、y ∈ [desk.top, desk.bottom]，欄內與眾數色亮度差 > 40 的最長連續直向區段（≥ 12 px；箭頭的三角形 ≤ 8 px）即游標，取其中心；找不到記 `null`。

| id | 內容（每格、每步、兩個瀏覽器） | 形式 | 紅案 | 若永遠沒做 |
|---|---|---|---|---|
| **U1** | `scrollBubbleText`：「第 4–5 頁，共 60 頁」→「第 4–5 頁」、「第 4 頁，共 60 頁」→「第 4 頁」、`null`／`""` → `null` | 單元（逐案） | 今天的位元組（函式不存在）；突變：回整串 | 不得宣稱已實作 |
| **U2** | `scrollBubblePlace`：`f` 0 與 1 的中心落在 desk 內（夾住）、`scrollHeight ≤ clientHeight` → `null`、`side: "left"` 鏡射、`scrollbarWidth` 0 → 右緣距 18、15 → 距 21 | 單元（逐案） | 今天紅；突變：拿掉夾住（`f`=1 中心掉出 desk）、`t` 下限改 0 | 同上 |
| **U3** | 頁面接線（mock timers，照 `page-held-deletes.test.mjs` 從原始碼編譯）：`scroll` → `data-shown="1"`；連續事件重設計時器；最後事件後 1,000 ms → `"0"`；`matchMedia` reduce 為真 → `transition` 為 `none` | 單元（逐案） | 今天紅；突變：計時器不重設（第二個事件後 1,000 ms 仍 `"1"` 應紅） | 同上 |
| **U4** | `node --test editor-shell-v2/tests/*.test.mjs` 全綠、`check_e1_c_bundle_intact.py` `intact: true`；既有斷言一個不改 | 工具封閉 | — | 不凍 v72 |
| **N1** | 無宿主、`dist/` 鏡像、v20、60 頁 fixture、滾輪臂：每一步讀到 `bubble.shown` 為真且 `bubble.text === scrollBubbleText(#page-status.textContent)`；泡泡顯示 ⇒ `#page-status` 不是 hidden | 逐實例 | 今天的 K4 報告沒有泡泡欄位 → **紅，不是空洞**；合成：泡泡字＝整串 → 紅 | 不凍、不出貨 |
| **N2** | 每一步：\|泡泡中心 y − 真游標中心 y\| ≤ 24 px；泡泡 rect ⊆ desk rect；`bubble.right ≤ desk.right − 16`（不蓋住卷軸欄）且 `≥ desk.right − 60`（在旁邊）。真游標在 ≥ 15/17 步讀得到，否則**儀器紅** | 逐實例（游標＝截圖讀的，不是模型） | 今天紅；合成：rect 下移 40 px → 紅；欄塗平 → 讀出 `null`、不是數字 | 不凍、不出貨 |
| **N3** | 滾輪臂期間 `nonPaintRequests` 為空（`pageRectangles` 0、`editor*` 0；paint 不算——窗移動本來就會要一張） | 逐實例 | 今天綠（143 (f)），保留為回歸網；突變：泡泡改讀 `pageRectangles()` → 紅 | 不凍 |
| **N4** | 由 log：每個 `scroll` 事件後 ≤ 100 ms 有 `shown=1` 的 `st`；臂的最後一個 `scroll` 事件後 ≤ 1,500 ms 有 `shown=0`，且 +2.0 s 讀 `checkVisibility()` 為假 | 逐實例 | 今天紅；合成：+3 s 仍 `shown=1` → 紅 | 不凍 |
| **N5** | 整臂 `focus` 欄位不變（`document.activeElement` 同一個元素）；執行起點與終點用 `[aria-live], [role="status"], [role="alert"]` 列舉的集合相同、每個元素 `textContent` 前後相等，且 log 裡沒有 `toast` 非空或 `a11y` 改變的 `st` | 逐實例，母數由 DOM 查詢封閉 | 合成：`a11y` 改變一筆 → 紅；正向對照：同一次執行先叫一次 `toast()` 看儀器記得到 | 不凍（a11y 退步） |
| **N6** | 3 步滾輪子臂在 reduce 模擬下（Chrome `Emulation.setEmulatedMedia`；Firefox pref `ui.prefersReducedMotion=1`）：泡泡 computed `transition-duration` 為 `0s`，N1／N4 照樣成立；不模擬時 ≤ 0.2 s | 逐實例 | 突變：忽略 `matchMedia` → `0.18s` → 紅 | 不凍 |
| **D1** | **拉游標（擁有者的路）**：Chrome 用 CDP 在截圖讀到的游標中心 `mousePressed`、10 步各 +10 px 間隔 50 ms、`mouseReleased`：`scrollTop` 變大、移動期間 ≥ 1 次讀到 `shown` 且字＝N1 的規則、放開後 ≤ 1.5 s 隱藏。Firefox 用 WebDriver actions 同樣拖；`scrollTop` 沒動就記 **NOT_ESTABLISHED（overlay 的命中區是瀏覽器的）**，滾輪臂為準 | 逐實例 | Chrome 今天紅（沒有泡泡）；拖不動＝儀器問題，要分開記 | Chrome 必過；Firefox 可 NE |
| **K1** | 鍵盤：游標在文件開頭、sink 有焦點、ArrowDown ×40 每 60 ms：≥ 1 個 `scroll` 事件、每個之後泡泡顯示且字照 N1、最後一個後 ≤ 1.5 s 隱藏。**N3 不適用**（移游標本來就是引擎請求） | 逐實例 | 今天紅 | 不凍 |
| **Z1** | 不可捲：空白新文件、視口高 1,500（Chrome `setDeviceMetricsOverride`／Firefox window rect）使 `scrollHeight ≤ clientHeight`：滾輪 ×3 → 0 個 `scroll` 事件、泡泡全程 `shown=0`、狀態列「第 1 頁，共 1 頁」；**正向對照**：縮回 994 高 → 滾輪 → 泡泡「第 1 頁」 | 逐實例 | 合成：`f` 為 NaN 時仍顯示 → 紅 | 不凍 |
| **H1** | 宿主（主 session 裝好帶這份頁面的版本之後，另開任務跑）：N1–N5 在 Files → 開 60 頁 fixture 的路上同樣成立 | 逐實例 | 同 N | 宿主不出這一版 |
| **H2** | 宿主：泡泡 rect ⊆ desk rect ⊆ `#content` rect；泡泡 rect 與 `#page-status` rect 不相交 | 逐實例 | 合成：rect 底 > `#content` 底 → 紅 | 宿主不出這一版 |
| **H3** | `templates/editor.php` 在這一版的 diff 裡沒有 `scroll-bubble`；若實測需要宿主 CSS，本規格**追加**一節寫理由再改 | 工具封閉（git diff） | — | — |

**判讀器要先紅**：落地前拿今天的 K4 報告（無泡泡）跑 N1／N2／N4 要紅；真游標讀法先在 K4 的 `*-mid.png` 上自測——預測讀出中心 Firefox 230 ± 8、Chrome 234 ± 8（§2 目測），對照模型（`a`＝0／17、`t`＝20）給 222／236；兩者差 > 24 就是模型錯了，改模型不改判準。

## 6. 預測（執行前寫下）

- 60 頁、1850 寬：模型誤差 Firefox ≤ 10 px（真游標約 35 對模型 20，差的一半）、Chrome ≤ 6 px（`a` 17 抵掉箭頭）；`a` 猜錯的桌面（傳統卷軸但沒有箭頭，GTK 非 overlay）最多 17 px，仍在 24 之內。兩個瀏覽器 17/17 步 N2 綠。泡泡約 26 px 高、「第 4–5 頁」在 13 px 字下約 80 px 寬。
- 顯示在 `scroll` 事件的同一個 task 裡（< 20 ms）；隱藏在最後事件後 1,000 + 180 ms ≈ 1.2 s。
- N3 與今天相同：0 個非 paint 請求；paint 數與 10-14n 同量級。
- 宿主不需要任何 CSS（`position: fixed` 不受 `#content` 的 `overflow: clip` 裁切——**推論**，由 H2 量）。若 Nextcloud 的某個祖先帶 `transform`／`contain`，fixed 的參考框會變、H2 會紅——那時改成相對 desk 的 `absolute` 定位，追加一節。
- 擁有者手測最可能的回饋：停留太短／太長（§4 第 3 列）、打字時泡泡閃（§4 第 4 列）。

## 7. 動到什麼、不動什麼

- **動**：`web/e2-editor-app.js`（元素、CSSOM 樣式、`scrollBubbleText`／`scrollBubblePlace`、`onDeskScroll` 加一行、`resize` 加一行、`matchMedia`）；`editor-shell-v2/tests/page-scroll-bubble.test.mjs`（新）；儀器與判讀器（`findings/evidence/` 新目錄）。
- **因此要**：`make e2-c-assets` 更新 `dist/` 鏡像；凍殼層 generation **v72**（v71 是 144 的）並重釘頁面（`FINAL_PAGE_SHA256`、`e2/editor-shell-v2-bundle-v72.json`、`tools/build_e2_c_shell_bundle.py`、`tools/run_e2_c_product_path.py`，照 8565d973 的樣子）；宿主升一版（只換引擎套件，`editor.php` 不動，H3）。
- **不動**：引擎、SDK、`editor-shell*/`（E1-C 與 E2-C 綁定）、`web/e2-editor.html`、宿主樣板、`#page-status` 的任何行為。
- **計數**：這一版是未計數候選；132-B／K3 這類回歸網照 §5 的 N3 保證不受影響，完整計數鏈併入下一個改引擎的批次。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-14 | 草稿：為什麼、事實（含 K4 截圖讀到的兩種卷軸）、設計（文字＝狀態列的頁數部分、fixed 定位的比例模型、任何 `scroll` 事件顯示 1 s、reduced-motion、aria-hidden）、擁有者可推翻的四題、判準 U1–U4／N1–N6／D1／K1／Z1／H1–H3 與各自的紅案、預測、觸及範圍。擁有者 2026-10-14 決定「捲動時都出現」寫進 §1 |
| 2026-10-14 | 擁有者「OK 照規格走」記在 §4 之後；U1–U4 落地：`aa50cd20…` 上 8/8 紅 → 頁面 `ccb67a52…` 8/8 綠、三個突變各紅在指定的那一格、套件 372/372、E1-C intact、41 個產品路徑突變錨各出現一次（resize 的錨差點被移動，改成自己的 listener 保住；見 `findings/evidence/scroll-page-bubble/README.md`）。N／D／K／Z 等 `dist/` 鏡像與瀏覽器可用之後跑 |
| 2026-10-14 | N1–N6／D1／K1／Z1 無宿主落地（`findings/evidence/scroll-page-bubble/n-nohost-v20/`，頁面 `ccb67a52…`、v20、headless Firefox 157.0.1 與 Chrome 151，判讀 ALL PASS；判讀器先在 K4 無泡泡報告上紅、游標讀法在 K4 截圖自測 230.0／234.5）。**更正 §2 的推論**（取代「Firefox 157 是 overlay 卷軸…不佔版面（推論為 0）」）：無宿主量到 Firefox 的 `offsetWidth − clientWidth` = 12；K4 截圖裡 6 px 的游標是宿主 CSS `scrollbar-color` 上色的非原生游標（兩個瀏覽器都是 rgb(125,125,125)），坐在 12 px 的欄裡，沒有箭頭。§3.2 的 `a = 17` 因此在 Firefox 是多算的，實測模型誤差 3–7 px，在 24 之內，不改模型（§5「改模型不改判準」的反向：模型沒錯到要改）。**儀器限制 L-bubble-ff-headless-thumb**：headless Firefox 對預設（GTK 主題）卷軸在 WebDriver 截圖裡完全不畫游標（靜止、指標懸停、滾輪後 0.2 s 都是白的；`scrollbar-width: thin` 也不畫），只有 `scrollbar-color` 會畫。Firefox 的 N2／D1 是在儀器對 `#desk` 設 `scrollbar-color: #7d7d7d transparent`（與宿主同一種上色；不改 `offsetWidth − clientWidth`，泡泡的擺放因此不變）之後讀到的；原始 Firefox 執行的 N2 登錄 INSTRUMENT_RED、D1 登錄 NOT_ESTABLISHED（儀器沒有游標可按，與「拖了沒動」是不同的案子），原樣保留。擁有者桌面 Firefox 的 GTK 預設游標本儀器量不到，由 H1（宿主、CSS 上色）與手測涵蓋。Z1 的 Chrome 第一次嘗試在啟動時被環境中斷（視窗誤關），留檔 `probe-chrome-blank.aborted-2328.out`，單獨重跑 |
| 2026-10-15 | 出貨與宿主判準：殼層 **v72 凍結**（`19c19543`）、**宿主 0.2.23（`2ccf1a9`，buildId `c3c22d92…`）**；擁有者手測通過；宿主 H3 過、守衛 132-B 與邊界連按過（任務 10-15a，`ad5ab7e3`）；H1／H2 先因探針沒有宿主模式未跑，補上 `--mode host` 與 H2 條款（紅案先紅）後兩瀏覽器 **ALL PASS**（任務 10-15b，`b1efbe98`；H2 19 處 0 越界、0 壓到狀態列）。「宿主不出這一版」的預設不再適用；主 session 重跑判讀輸出逐字相同。 |
