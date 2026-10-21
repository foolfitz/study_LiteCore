# 163：編輯器宿主離開頁面時送四次 UNLOCK，第一次 204、其餘 500——`files_lock` 對已釋放的鎖丟未捕捉的 `LockNotFoundException`

| | |
|---|---|
| **狀態** | **已確認，成因讀出**（2026-10-21 更新）：四次是宿主的**設計**（兩個事件 × 每次兩份），不是重複觸發；500 是伺服器那一半。不是 Phase H 的判準；不影響任何已過的臂 |
| **影響版本** | 宿主 0.2.28–0.2.31（`js/litecore-editor.js` 這幾版逐位元相同）；更早的版本可能也有，沒有人把 Apache log 對準過編輯器的離開 |
| **所在** | 宿主：`js/litecore-editor.js` 離開路徑——設計上在 `beforeunload` 與 `pagehide` 各送一次 keepalive 的 UNLOCK（檔內註解 285–290 行說明是為了 Firefox 的快取曾吞掉 pagehide 那一次）。伺服器：Nextcloud 34 的 `files_lock` 對不存在的鎖 UNLOCK 時 `OCA\FilesLock\Exceptions\LockNotFoundException` 未捕捉（`apps/files_lock/lib/Db/LocksRequestBuilder.php:96`），回 500 |
| **發現日** | 2026-10-21 06:21：Phase H 第三次跑的正對照（`findings/evidence/m4-ods/phase-h/shakedown/2026-10-20T222047+0000.json` `odtLog`）；`check_m3_host_entry.py` 的每一臂離開時 Nextcloud log 都有同一筆（`ddev occ log:tail`） |
| **嚴重度** | **小**。第一個 UNLOCK 204，鎖確實放掉；之後的 500 只是 log 噪音與多餘的請求。但擁有者的 Nextcloud log 每次離開編輯器都會多 3 筆 level 3 的 uncaught exception |
| **是否上游** | 伺服器那一半是（`files_lock` 應回 409／412 而不是 500，RFC 4918 §9.11）；宿主那一半是我們的（為什麼是 4 次不是 2 次） |

## 量測

- plain 臂的 ODT 正對照，Apache log 同一秒內：`LOCK 200、PROPFIND 207、GET 200`，離開時 `UNLOCK 204、500、500、500`。
- 紅案臂：`LOCK 200、PROPFIND 207、LOCK 423（紅案的第二個 LOCK）、GET 200`，離開時 `UNLOCK 500、204、500`——哪一次成功不固定。
- Nextcloud log（`occ log:tail`）22:25:58、22:26:49、22:27:34 UTC 各兩筆：`webdav` 的「Exception thrown: LockNotFoundException」與「Uncaught exception」。

## 為什麼是四次（2026-10-21 更新：讀程式碼）

上面「設計是兩次」是我讀註解讀錯了：設計是**四次**。

- `release(by)`（宿主 `js/litecore-editor.js:294-310`，0.2.31 `421f4b8`）每被呼叫一次就送**兩份**相同的 keepalive UNLOCK（`for (let copy = 0; copy < 2; copy++)`）；`released` 記住 token 之後，第二次呼叫仍照送兩份〔已觀察〕。
- 呼叫點有兩個：`beforeunload`（沒被詢問留下時，`:335`）與 `pagehide`（`:348`）〔已觀察〕。2 × 2 ＝ 4。
- 兩個「兩份」都是量出來的，不是手滑：`pagehide` 送兩份是 `findings/evidence/m3-locks/unload/README.md` exp10 V3（Chrome 151 headless，單一份 0／4、兩份 4／4）；`beforeunload` 那一組是 Firefox 156 開 HTTP 快取時 `pagehide` 那次只到 6／13（檔內註解 285-293）〔已觀察，皆為既有證據〕。檔內註解本來就寫著「A copy that finds no lock is answered 204 or 500 and releases nothing else」——500 是**預料中的**。
- 紅案臂只看到 3 次：四份裡有一份沒到伺服器，與 exp10 量到的 keepalive 遺失同形〔推論，未另外量〕。哪一次是 204 不固定，也與「先到的那一份放掉鎖」相符。

所以**宿主那一半不是缺陷**：多出來的請求就是那份備援，拿掉任何一份都會退回 105 的處境（下一個開同一檔的人拿到 423、五分鐘存成副本）。

## 沒查的

- 真人用瀏覽器離開時實際到伺服器的是幾份（harness 的路 vs 使用者的路）；exp10 只量過 headless Chrome。
- `files_lock` 對已釋放的 token 回 500 是不是 34.0.2 才有（上游哪一版開始、有沒有已知的單）。上游送出擱置中，只登錄。

## 處置

- 登錄，不改宿主、不改判準。~~若之後要修：宿主側讓第二次以後的 UNLOCK 不送（記住已釋放）~~（2026-10-21 撤回：頁面在送出時拿不到前一份的回應，「記住已釋放」只能記住「送過」，那正是 105 的備援要的東西；這個修法會把 105 帶回來）。
- 唯一乾淨的修法在伺服器：`files_lock` 對找不到的鎖應回 409／412 而不是讓 `LockNotFoundException` 冒成 500。上游候選，送出擱置。
- 對擁有者的影響：每次離開編輯器，Nextcloud log 多 2–3 筆 level 3 的例外。是噪音，不是資料問題。

## 修訂紀錄

| 日期 | 變更 |
| --- | --- |
| 2026-10-21 06:3x | 建立（候選） |
| 2026-10-21 | 讀離開路徑：四次是設計（2 事件 × 2 份，exp10 V3 與 Firefox 快取兩筆既有證據）；狀態改「已確認」；撤回宿主側修法；「沒查的」只留真人路徑與上游版本 |
