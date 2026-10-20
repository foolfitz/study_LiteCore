# 163：編輯器宿主離開頁面時送四次 UNLOCK，第一次 204、其餘 500——`files_lock` 對已釋放的鎖丟未捕捉的 `LockNotFoundException`

| | |
|---|---|
| **狀態** | **候選，已觀察、未深究**。不是 Phase H 的判準；不影響任何已過的臂 |
| **影響版本** | 宿主 0.2.28–0.2.31（`js/litecore-editor.js` 這幾版逐位元相同）；更早的版本可能也有，沒有人把 Apache log 對準過編輯器的離開 |
| **所在** | 宿主：`js/litecore-editor.js` 離開路徑——設計上在 `beforeunload` 與 `pagehide` 各送一次 keepalive 的 UNLOCK（檔內註解 285–290 行說明是為了 Firefox 的快取曾吞掉 pagehide 那一次）。伺服器：Nextcloud 34 的 `files_lock` 對不存在的鎖 UNLOCK 時 `OCA\FilesLock\Exceptions\LockNotFoundException` 未捕捉（`apps/files_lock/lib/Db/LocksRequestBuilder.php:96`），回 500 |
| **發現日** | 2026-10-21 06:21：Phase H 第三次跑的正對照（`findings/evidence/m4-ods/phase-h/shakedown/2026-10-20T222047+0000.json` `odtLog`）；`check_m3_host_entry.py` 的每一臂離開時 Nextcloud log 都有同一筆（`ddev occ log:tail`） |
| **嚴重度** | **小**。第一個 UNLOCK 204，鎖確實放掉；之後的 500 只是 log 噪音與多餘的請求。但擁有者的 Nextcloud log 每次離開編輯器都會多 3 筆 level 3 的 uncaught exception |
| **是否上游** | 伺服器那一半是（`files_lock` 應回 409／412 而不是 500，RFC 4918 §9.11）；宿主那一半是我們的（為什麼是 4 次不是 2 次） |

## 量測

- plain 臂的 ODT 正對照，Apache log 同一秒內：`LOCK 200、PROPFIND 207、GET 200`，離開時 `UNLOCK 204、500、500、500`。
- 紅案臂：`LOCK 200、PROPFIND 207、LOCK 423（紅案的第二個 LOCK）、GET 200`，離開時 `UNLOCK 500、204、500`——哪一次成功不固定。
- Nextcloud log（`occ log:tail`）22:25:58、22:26:49、22:27:34 UTC 各兩筆：`webdav` 的「Exception thrown: LockNotFoundException」與「Uncaught exception」。

## 沒查的

- 為什麼是四次：設計是兩次（beforeunload＋pagehide）。候選：runner 的 `navigate()` 讓兩個事件各跑兩次；或 `release()` 被 `visibilitychange` 之類再觸發一次。要讀離開路徑並用瀏覽器的網路紀錄數。
- 真人用瀏覽器離開是幾次（harness 的路 vs 使用者的路）。

## 處置

- 登錄，不改宿主、不改判準。若之後要修：宿主側讓第二次以後的 UNLOCK 不送（記住已釋放），伺服器側對 `files_lock` 回報。
