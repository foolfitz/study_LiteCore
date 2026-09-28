# 101 — files_lock 的 token 鎖續約不會延長鎖：不管續約幾次，都在上鎖後 Timeout 秒到期

| | |
|---|---|
| **狀態** | 已確認（原始碼＋一次端到端實測＋HTTP 最小重現附對照組）／上游未回報（送出擱置中） |
| **上游** | nextcloud/files_lock（GitHub） |
| **發現日** | 2026-09-28 |
| **嚴重度** | 一般（鎖在用戶端看來還在，其實已失效；資料不會掉，因為我們的寫入一律帶 `If-Match`） |
| **可重現** | 1/1 端到端（Firefox K3）＋1/1 HTTP 最小重現（L8），原始碼路徑確定 |
| **是否上游** | 是：NC 34.0.2 tarball 內附、預設啟用的 files_lock 34.0.1，零設定 |

## 現象

RFC 4918 的 `LOCK` 續約（`If: (<token>)`、沒有本文、`Timeout: Second-300`）回 200，
但鎖的到期時間**沒有往後延**。上鎖 300 秒後，鎖一定會消失，不管中間續約過幾次。
之後持有者的續約會得到 400。

RFC 4918 §9.10.2 的規定是：續約會把逾時重新設定，從續約的那一刻起算。

## 證據

- `evidence/m3-locks/shakedown/2026-09-28T112341+0000.json` 的 Firefox `heartbeat` 臂：宿主每 60 秒續約一次，
  結果是 `refreshes [200, 200, 200, 200, 400]`。第 330 秒伺服器上的 `nc:lock` 已經是空的。
  這正是審核者事先從原始碼推出來的預測。
- `evidence/m3-locks/semantics-2026-09-28T101717Z.json`（L6）：續約前後的 `lock-time` 與
  `timeout` 都沒變。當時的續約緊接在上鎖之後，所以這組數據跟兩種解讀都相容，分不出來。
- `evidence/m3-locks/semantics-2026-09-28T130648Z.json`（L8，最小重現）：A 以 `Second-20` 上鎖，
  第 10.3 秒用 `Second-20` 續約（200），第 22.32 秒不帶 token 的 PUT 回 **204**，`nc:lock` 已空。
  對照組 B 在第 10.59 秒照宿主的修法用 `Second-30` 續約，第 23.2 秒同樣的 PUT 回 **423**，鎖還在。
  有 B 才能說 A 的 204 是「鎖沒了」，不是「那個 PUT 本來就擋不住」。

## 分析

- `apps/files_lock/lib/DAV/LockBackend.php` `lock()`：續約走 Sabre `Locks/Plugin::httpLock` 的
  refresh 分支，最後呼叫 `$lock->setTimeout($lockInfo->timeout)`，也就是請求裡的秒數，再 `update()`。
- `lib/Db/LocksRequest.php` `update()`：寫 `ttl`、`token`、`user_id`、`owner`、`scope`，**從來不寫 `creation`**。
- `lib/Model/FileLock.php` `getETA()`：`creation + ttl − now`。
- 所以一次「Timeout 300 的續約」只會把 ttl 設回 300，到期時間永遠停在 `creation + 300`。
- 另外，管理者如果設了 `lock_timeout`，`Cron/Unlock` 會按 `creation` 的年齡刪鎖，同樣不看續約。

**我們的對策**（`litecore` 宿主）：續約時送 `Timeout: Second-(自上鎖以來的秒數 + 300)`。
這樣 `ttl` 會長到讓 `creation + ttl ≈ 現在 + 300`。

## 還缺什麼才能送

- [ ] 在 files_lock main 分支確認還沒修
- [ ] 查 GitHub issues 有沒有重複
- [x] 一個只用 HTTP 的最小重現：`Timeout: Second-20` 上鎖，第 10 秒續約，第 22 秒不帶 token 做 PUT。
  如果回 204，就證明續約沒有延長鎖。→ 204，附對照組（見證據 L8，2026-09-28）。
- 送出擱置中（2026-08-15 起的規矩）。

## 時間軸

- 2026-09-28：opus 對抗性審核從原始碼指出，並預測 K3 會紅成 `[200,200,200,200,400]`；
  同一天的 shakedown 實測完全符合。
- 2026-09-28（晚）：HTTP 最小重現（L8）成立，附宿主修法當對照組。
