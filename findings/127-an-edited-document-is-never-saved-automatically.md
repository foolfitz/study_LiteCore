# 127 — 編輯中的文件從不自動儲存（richdocuments＋Collabora Online 會）

| | |
|---|---|
| **狀態** | **已確認、未修**（登錄；規格與實作排在 0.2.12 計數之後） |
| **所在** | 我們的產品頁 `wasm_sdk_probe/web/e2-editor-app.js`（`8909564e…`）與宿主 `litecore`（0.2.12 `b245ae7`）`js/litecore-editor.js`：兩邊都沒有任何依時間或閒置觸發的存檔。宿主的兩個 `setInterval` 一個只更新「未儲存」標記（:155，每 500 ms 讀 `pageUnsaved()`），一個續租鎖（:219） |
| **發現日** | 2026-10-11（擁有者比較 richdocuments＋Collabora Online 時發現並回報；主 session 當天讀原始碼確認） |
| **嚴重度** | **高（資料遺失的範圍）**：不是單一缺陷，而是把每一種會丟掉「上次存檔之後的修改」的事件（工作階段死掉、分頁或瀏覽器當掉、斷電、關機）的損失從「最多幾十秒」放大成「從上次手動存檔到現在的全部」。109 那一類（工作階段死掉、未存內容全失）就是這個範圍的實例 |
| **可重現** | 100%（依構造：沒有觸發點） |
| **是否上游** | 否，我們的產品 |

## 現象

在 litecore 裡編輯一份文件，不按儲存：不論編輯多久、停多久，伺服器上的檔案都不變，直到使用者自己按儲存。~~（或離頁時宿主的 K2 先存）~~——**更正（2026-10-12）**：宿主沒有「離頁前先存」；K2 是 runner `check_m3_assets.py` 在每次離頁前按儲存（`save_before_leaving`，SPEC-M3-page-honesty §7.8 的裁決 A′），不是產品行為。宿主離頁時只做兩件事：有未存內容就問、否則放鎖。在 richdocuments＋Collabora Online 裡做同樣的事，文件會自己存回去。

## 對照：Collabora Online 怎麼做（讀原始碼，`cool-26-04/coolwsd.xml.in:69-73`，co-26.04）

- `idlesave_duration_secs` 預設 **30**：文件有修改、閒置 30 秒就存。
- `autosave_duration_secs` 預設 **300**：文件有修改，每 5 分鐘存一次（不管是否閒置）。
- `background_autosave` 預設 **true**：自動存檔在 **fork 出來的背景行程**裡做，不擋編輯。
- `always_save_on_exit` 預設 false（最後一位編輯者離開時，即使先前略過也一定存並上傳）。

## 不能直接照抄的地方（設計前要先定、要先量）

1. **我們的存檔會擋住編輯。**Collabora 在背景行程存；我們的存檔在編輯用的同一個 Worker 裡序列化文件。擁有者文件存一次 517–724 ms（規格 §17.18 的登錄量測），期間鍵盤輸入要等；超過 700 ms 還會亮「處理中」（125 的門檻）。所以「每 5 分鐘不管閒不閒置都存」在我們這裡等於每 5 分鐘卡一下——只用閒置觸發、或另外處理「一直在打字」的情況，要先決定。
2. ~~**Nextcloud 的版本**：閒置 30 秒存一次會產生多少版本~~——**不成立，已撤回**（擁有者指出，2026-10-11 讀原始碼查明）。每次覆寫確實先產生一個版本（`files_versions` 的 `FileEventsListener::write_hook` → `Storage::store` → `createVersion`），但每產生一個就排一次清理（`Versions/LegacyVersionsBackend.php:160` `scheduleExpire`，經 `CronBus` 進背景工作），而預設 `versions_retention_obligation = auto` 的清理**按時間疏化**（`Storage.php:65-75`）：10 秒內每 2 秒留一個、1 分鐘內每 10 秒、1 小時內每分鐘、1 天內每小時、30 天內每天、之後每週。有命名（label）的版本永不自動清掉（`Storage.php:941`）。所以版本數由時間框住，不隨存檔次數增長。richdocuments v8.8.0 對 Collabora 的自動存檔也沒有任何版本上的特別處理（`lib/Controller/WopiController.php` 沒有 autosave 分支），兩者走同一套。出處：litecore 實例的 core（NC 34.0.2，`~/Projects/Nextcloud_Apps/litecore/nextcloud/`），與 `~/OSSII/ncdev_env/upstream/nextcloud-v31.0.14/` 相同。此實例沒有設定 `versions_retention_obligation`（`occ config:system:get` 回 1＝未設定），即預設 `auto`。**不是設計問題，不列入規格。**
3. **衝突與鎖**：自動存檔走既有的存檔路徑（token 鎖、`If-Match`、宿主 0.2.2 起的 ≥ 1.1 秒間隔與存檔前讀回比對，103／104／108）。別人改過檔案時，自動存檔絕不能蓋掉，要跟手動存檔一樣報衝突——而且自動存檔撞到衝突時使用者沒在看，要怎麼告訴他要定。
4. **唯讀模式**（擁有者裁示：只能看）不自動存。
5. **離頁誠實化**（107、K2、§7 的 `watchUnsaved`）：自動存檔縮短「未儲存」的窗口，但不消滅它，離頁的判準照舊要成立。
6. **「有修改」的定義**：頁面已有的未儲存判斷（`pageUnsaved()`）~~／revision 自上次存檔後是否前進~~。**更正（2026-10-12，讀原始碼）**：不是 revision——`hasUnsavedEdits()` 是 `dirty || pending > 0`（`narrow-editor-v2-session.js:630-633`，註解明寫不用 revision，因為每個 Worker 的 revision 從 0 起算，099 那一類），頁面再加上「存檔已要求、宿主還沒落定」（`savesUnsettled > 0`，`e2-editor-app.js:87-89`）。
7. **工作階段死掉之後**（109、111、119 的路徑）：自動存檔是減少損失的主要手段；與既有的檢查點（瀏覽器內）是兩回事，要寫清楚各自保證什麼。

## 處置

**時機（2026-10-11 主 session 的建議，待擁有者確認）**：不進 0.2.12（計數鏈正在跑，動頁面或宿主會讓計數作廢）；0.2.12 計數完成、擁有者手測過之後，當**下一個發佈的主題**——它是資料遺失這一族（107／108／109）的防線，優先於其他已登錄的項目（含 §17.21 那一次 runner 開啟，那件事只在下一次普查之前需要）。先寫規格（上面 1、3–7 的決定與要先量的事、判準、紅案、預測），設計取捨可交 fable 裁決。

## 修訂紀錄

| 日期 | 修訂 |
|---|---|
| 2026-10-11 | 建立（擁有者回報；主 session 讀頁面、宿主、COOL 原始碼確認） |
| 2026-10-11 | 撤回第 2 點「版本數會累積」：擁有者指出 Nextcloud 版本不是這種機制；讀 NC 34.0.2 `files_versions` 原始碼查明為按時間疏化（見第 2 點）。原文是未查證的推測 |
| 2026-10-12 | 更正兩處（寫 0.2.13 規格時的存檔路徑普查，主 session 讀原始碼確認）：「離頁時宿主的 K2 先存」不成立（K2 是 runner）；「有修改」的定義不是 revision，是 `dirty \|\| pending > 0` 加上頁面的 `savesUnsettled`。另記：存成副本之後宿主不更新 ETag（`litecore-editor.js:519-556`），之後每一次存檔都會再撞同一個衝突、再多一份副本——自動儲存的硬限制 |
