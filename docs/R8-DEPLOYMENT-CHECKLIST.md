# R8 部署檢查表

本檢查表適用於 `writer-review` 的 immutable release graph。SHA-256 用來驗證內容身分；來源可信度仍由受信任
HTTPS、部署權限與供應鏈負責。

## 上線前

- 固定單一 release manifest；確認 release ID、core commit、SDK profile、必需 artifact 與字型 pack 完整。
- entry、manifest、Service Worker 使用可重新驗證的更新策略；content-addressed artifact 才使用 immutable cache。
- JS、Worker、WASM、data、metadata 的 media type、`nosniff`、COOP、COEP、CORP 與 CORS 通過。
- application origin 不把 cookie／Authorization 送到 artifact origin；URL 不得含 credential、path traversal 或未知 scheme。
- 完成 Chrome／Firefox 的 T0、T1；T2 只有在已授權 HTTPS 環境存在時才執行與宣稱。
- last-known-good 至少保留一版；candidate 不得覆蓋唯一 known-good。
- 確認 user document、clipboard、協作 token、presence 與 sidecar 不進公開 CacheStorage。

## 逐步發佈

1. 上傳完整的新 release graph，但不切換 current。
2. 下載並驗證 manifest、每個必需 artifact 的 bytes／media／encoding／SHA-256。
3. 將 candidate 標為 ready；失敗時保留 current 與 last-known-good。
4. 啟用新 client，執行 open／render／search 的 bounded health check。
5. health 通過後才提交 last-known-good；舊 client 繼續 pin 舊 release。
6. 顯示明確更新提示；使用者 reload／新 session 後才採用新 generation，不熱換既有 Worker。
7. 依 retention policy 回收無 client pin 的 retiring／failed cache。

## Rollback

- 先確認目標 release 的完整 cache 與 hash，再原子切換 current。
- rollback 後執行 runtime health，並測一次 server-down offline open／render／search。
- rollback target 損壞時回 typed terminal action，不拼湊不同 release，也不形成 reload loop。
- 未儲存 mutation 不自動重送；依 Finding 012 bounded recovery 語意提示使用者。

## T2 額外證據

- 記錄授權 URL、region、TLS、proxy/CDN、compression、cache topology 與實際 browser version。
- 各瀏覽器至少三次 cold／warm／update；保留 header、encoded bytes、timing 與失敗樣本。
- 未提供 T2 時判定 `PARTIAL_GO_LOCAL_DELIVERY`，不得寫成 production CDN SLA。
