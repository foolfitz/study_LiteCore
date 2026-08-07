# R8 Operator Runbook

## 正常更新

- `current` 是新 client 使用版，`candidate` 是已下載但尚未提交版，`last-known-good` 是可 rollback 版。
- `ready` 只代表完整 graph 已驗證；仍需 activate 後的 runtime health 才能提交。
- 現有文件 session 不熱換 Worker。請先儲存，再使用「Reload to update」建立新 generation。

## 使用者可採取的動作

- `Retry`：網路／暫時性 cache write 失敗，重跑同一 closed operation。
- `Continue current`：保留目前 known-good，不採用 candidate。
- `Reload to update`：已儲存且 candidate health 通過後，建立新 session。
- `Rollback`：candidate health 或新版本完整性失敗時回 known-good。

## 常見 typed error

| 錯誤 | 操作 |
|---|---|
| `ARTIFACT_*`／`RELEASE_MANIFEST_INVALID` | 停止啟動 candidate；檢查部署 graph，不略過 hash。 |
| `CROSS_ORIGIN_ISOLATION_REQUIRED` | 檢查 COOP／COEP／CORP／CORS；不要關閉 pthread 要求規避。 |
| `CACHE_WRITE_FAILED`／`STORAGE_QUOTA_EXCEEDED` | 保留 known-good，清除未 pin 的 failed／retiring release 後 retry。 |
| `OFFLINE_RELEASE_UNAVAILABLE` | 恢復網路下載完整 release；不可啟動 partial runtime。 |
| `CACHED_ARTIFACT_INVALID` | 在線執行 atomic repair，驗證新 cache 後才切換 cache name。 |
| `ROLLBACK_UNAVAILABLE` | 停止自動 reload，要求恢復網路或重新部署完整 known-good。 |
| `FONT_PACK_RESTART_REQUIRED` | 儲存後 reload；取消則維持目前 fidelity，不靜默換字型。 |
| `WORKER_GENERATION_BUDGET_EXHAUSTED` | 儲存並重新載入整個 Firefox 工作階段。 |

## 離線與損毀

- 已完整驗證的 known-good 可離線 open／render／search；cold profile 沒有 release 時應明確拒絕。
- 單一 cache entry 遺失或 bytes 不符時不得啟動 Worker；恢復網路後執行 repair。
- metadata current 損壞時只可使用已驗證 backup；無有效 backup 就停止，不猜測 current。

## Firefox generation budget

- 長壽 session 優先重用單一 Worker，文件逐一 open／close。
- crash recovery 與更新建立新 generation 必須有界；接近產品 budget 時提早要求 reload，不等待 120 秒 timeout。
- reload 前不重送未儲存 mutation，並拒絕 stale handle。
- 大型回歸／批次工作不要接在已完成大量R8-C session的Firefox生命週期後；先完整結束測試browser，待資源回收後
  以隔離profile開始下一個campaign。這是Finding 014的操作性緩解，不代表根因已修正。

## 證據位置

- R8-C：`findings/evidence/sdk-r8/service-worker/`
- R8-D：`findings/evidence/sdk-r8/production/`
- 最終摘要：`findings/evidence/sdk-r8/summary.json`
