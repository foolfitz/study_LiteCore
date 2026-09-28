# 100 — files_lock 的 OCS 上鎖端點在檔案已被別人鎖住時回 500，不是 423

| | |
|---|---|
| **狀態** | 已確認（原始碼＋兩輪實測）／上游未回報（送出擱置中） |
| **上游** | nextcloud/files_lock（GitHub），不是 LibreOffice Bugzilla |
| **發現日** | 2026-09-28 |
| **嚴重度** | 一般 |
| **可重現** | 100%（兩輪、兩個情境各一次） |
| **是否上游** | 是：NC 34.0.2 正式版 tarball 內附、預設啟用的 `files_lock` 34.0.1，零設定 |

## 現象

檔案已被另一個使用者鎖住時，`PUT /ocs/v2.php/apps/files_lock/lock/{fileId}` 回
**HTTP 500**，OCS statuscode 996、訊息 `Internal Server Error`，**不是** 423。
呼叫端因此分不出「被別人鎖住」和「伺服器壞了」。同一個情況走 DAV `LOCK`＋`X-User-Lock: 1`
則正確回 423，而且本文帶著鎖的屬性。

## 重現步驟

1. 使用者 B 對使用者 A 分享的檔案取得使用者鎖（OCS lock，lockType 0）→ 200。
2. 使用者 A 對同一個檔案 `PUT /ocs/v2.php/apps/files_lock/lock/{fileId}`（`lockType=0`）。

**預期**：423，本文是鎖的資訊，訊息「File is currently locked by B」。
**實際**：500。`nextcloud.log`：
`OCA\FilesLock\Model\FileLock::import(): Argument #1 ($data) must be of type array, OCA\FilesLock\Model\FileLock given`。

## 證據

- `evidence/m3-locks/semantics-2026-09-28T101145Z.json`、`…101329Z.json`：步驟
  `L1 ocs other lock` 與 `L4 our lock` 都是 500；同一個情境下的 `L1 dav other lock`
  與 `L4 our X-User-Lock LOCK` 都是 423。
- `evidence/m3-locks/superseded/semantics-2026-09-28T100954Z.json`：同樣兩格 500（那一輪
  的探針有別的缺陷，但這兩格不經過它）。

## 分析

`apps/files_lock/lib/Controller/LockController.php`（34.0.1，隨 NC 34.0.2 tarball 出貨）：

- `locking()` 在 `catch (OwnerLockedException $e)` 回 `new DataResponse($e->getLock(), Http::STATUS_LOCKED)`：
  data 是 `FileLock` **物件**。
- `buildOCSResponse()` 碰到 423 就 `$lock = new FileLock(); $lock->import($data->getData());`，
  而 `FileLock::import(array $data)` 只收 array → TypeError → 500。
- `unlocking()` 的 423 分支傳的是 `$lock->jsonSerialize()`（array），所以解鎖那條路沒有這個問題。
  兩個分支傳的東西不一致，這就是缺陷本身。

**對我們的影響**：`litecore` 宿主要上使用者鎖時，改走 DAV `LOCK`＋`X-User-Lock`，不要走 OCS。

## 還缺什麼才能送

- [ ] 在 files_lock 的 main 分支確認還沒修（這裡只讀了 34.0.1）
- [ ] 查 GitHub issues 有沒有重複
- 送出擱置中（2026-08-15 起的規矩）；重啟時先做上面兩項。

## 時間軸

- 2026-09-28：M3 鎖與權限第 0 步的伺服器語意探針量到；讀原始碼定位。
