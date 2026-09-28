# 102 — files_lock 的 token 鎖不檢查送 token 的是誰：有寫入權的其他使用者拿持有者的 token 就能寫穿鎖

| | |
|---|---|
| **狀態** | 已確認（HTTP 實測 2/2，第二次附讀回）／上游未回報（送出擱置中） |
| **上游** | nextcloud/files_lock（GitHub）；送出管道要先查安全政策，見下 |
| **發現日** | 2026-09-28 |
| **嚴重度** | 一般（鎖的保證對「照規矩來的用戶端」才成立；對方本來就有寫入權，所以不是越權；我們的宿主不掉資料，因為寫入一律帶 `If-Match`） |
| **可重現** | 2/2（`probe_m3_lock_semantics.py --only L7`） |
| **是否上游** | 是：NC 34.0.2 tarball 內附、預設啟用的 files_lock 34.0.1，零設定 |

## 現象

使用者 A（admin）對檔案取 RFC 4918 token 鎖（`LOCK`、`Timeout: Second-300`）。
檔案以可寫入（permissions 3）分享給使用者 B（`lcprobe`）。

- B 不帶 token 的 PUT：**423**（鎖擋住了，這是對照組）。
- B 帶 **A 的** token（`If: (<opaquelocktoken:…>)`）的 PUT：**204**。A 接著 GET 讀回來的是
  **B 的位元組**，ETag 也動了。

B 要拿到 token 不費力，兩條路都量到了：

- B 對 A 的鎖送 OCS 解鎖（`DELETE /ocs/v2.php/apps/files_lock/lock/{fileId}`）被拒絕，
  回 423，**本文裡就帶著 A 的 `token`**。
- B 自己的 PROPFIND `d:lockdiscovery` 回 207，裡面有 A 的 token。另外 files_lock 還把
  token 當成 `nc:lock-token` 屬性提供（`lib/DAV/LockPlugin.php:177-183`）。

RFC 4918 §6.5 本來就把 lock token 當成公開資訊，所以 token 被看到**本身不是缺陷**。
缺陷在 §6.4：修改被鎖住的資源時，伺服器**必須**確認送出請求的已驗證主體就是建立
那把鎖的人，光是送了有效 token 還不夠。這台伺服器沒有做這個檢查。

## 證據

- `evidence/m3-locks/semantics-2026-09-28T130648Z.json`（L7、L8）：`recipientPutNoToken 423`、
  `recipientPutWithHoldersToken 204`、`refusalBodyCarriesToken true`。
- `evidence/m3-locks/semantics-2026-09-28T130750Z.json`（L7 重跑）：B 送的位元組和 fixture 不同，
  `fileHoldsRecipientBytes true`、`recipientLockdiscoveryCarriesToken true`；其餘每個狀態碼與
  `130648Z` 逐格相同。
- 舊證據裡早就有 token 外洩，只是當時沒人看：`semantics-2026-09-28T101329Z.json` 的
  `L5 other (not owner) OCS unlock`，423 本文 `"token":"3f52178b-…"`。

## 分析（讀原始碼；哪一行該做檢查還沒用突變驗證）

- `apps/files_lock/lib/DAV/LockBackend.php` `getLocks()`：只對「自己的 user lock」
  （`TYPE_USER` 且 owner 是目前使用者）回空陣列；token 鎖（`TYPE_TOKEN`）對任何使用者都
  原樣回傳 `toLockInfo()`，連 token 一起。
- files_lock 的 `LockPlugin` 繼承 Sabre 的 `Locks\Plugin`（`initialize()` 最後呼叫
  `parent::initialize`），只拿掉 core `FakeLockerPlugin` 的 listener，**沒有**自己的
  `validateTokens`。
- Sabre `3rdparty/sabre/dav/lib/DAV/Locks/Plugin.php` `validateTokens()`（393 行起）：
  拿請求 `If` 裡的 token 去比對 `getLocks()` 回來的鎖，比的只有
  `$mustLock->token == $checkToken` 這個字串，不看 principal。所以 token 只要對，誰送都算數。
- 以上兩點是讀原始碼讀到的。**推論**：檢查應該補在 `getLocks()`（token 鎖的 owner 與
  目前使用者比對），或是在 `validateTokens` 之後補一道。這一段沒有改原始碼驗證過。

## 對我們產品的影響

- ~~**資料不會掉**~~ **寫穿換了 ETag 時資料不會掉**（2026-09-28 修訂：寫穿若與宿主最後一次存檔落在同一秒，ETag 不會換，宿主的下一次存檔會把它蓋掉，見 [103](103-nextcloud-a-second-write-in-the-same-second-keeps-the-etag-so-if-match-lets-an-overwrite-through.md)；被蓋掉的內容留在版本歷史裡）：`litecore` 宿主的每一次寫入都帶 `If-Match`。被人寫穿之後 ETag 動了，
  宿主下一次存檔拿到 412，token 還在伺服器上，走衝突副本，**不重試**
  （`js/litecore-editor.js` `saveOnce`，約 337–345 行）。如果 token 已經不在，宿主會用
  **同一個舊 ETag** 重試一次，也還是 412，最後同樣走副本。兩條路都不會覆寫對方的位元組。
  宿主也從來不採用不是自己 `LOCK` 拿到的 token（`takeLock`，149–159 行）。
- **打折扣的是鎖的承諾**：「你開著的時候別人寫不進來」只對照規矩來的用戶端成立
  （我們自己的宿主、Nextcloud 的其他 app）。有寫入權的人用自製請求就能寫穿。這要寫進
  規格的「明確不承諾」。
- 宿主「token 還在、PUT 卻 412」這條路徑由 K12 驅動。**寫穿之後鎖還在不在，沒有量**，
  但如上所述，兩種情況宿主的結果都是走副本。

## 還缺什麼才能送

- [ ] 在 files_lock main 分支確認還沒修
- [ ] 查 GitHub issues／安全公告有沒有重複
- [ ] **先決定送出管道**：這是鎖語意的完整性問題，不是越權（B 本來就有寫入權）。但
  Nextcloud 的安全政策可能把「繞過鎖」算進 HackerOne 的範圍。**查清楚之前不要開公開
  issue。**
- [ ] 同樣的檢查對 user lock（`X-User-Lock`、lockType 0）是否也缺：沒量
- 送出擱置中（2026-08-15 起的規矩）。

## 時間軸

- 2026-09-28：補 K12 前提的 HTTP 探針（L7）時，翻到舊證據的 423 本文帶著持有者的 token，
  因此加了「B 拿那個 token 去 PUT」這一臂。第一次 204；第二次改送不同的位元組並讀回，
  確認檔案裡是 B 的位元組。
