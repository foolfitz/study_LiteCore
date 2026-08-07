# 015 — Firefox 對部分 Content-Length 不符回應仍可能 resolve fetch

## 狀態

**已確認，R8 交付驗證契約已修正。** 這不是 LibreOffice core 或 Document SDK 缺陷；它否證了「截斷回應必然
使 `fetch()` reject」的我方測試假設。

## 影響

- 交付層若只把 network rejection 視為截斷偵測，會在部分 Firefox 行為下漏判。
- R8-B～R8-D 不得依賴 `fetch()` 是否 reject；每個 artifact 都必須在執行或寫入 active release 前比對
  manifest 宣告的 decoded bytes 與 SHA-256。
- Finding 只影響 fault oracle，不降低資料完整性要求，也不需要修改 LibreOffice core。

## 已觀察

- 同一個 deterministic T0/T1 fault server 回傳完整 22-byte canary，但宣告 `Content-Length: 29` 並關閉連線。
- Chrome 150 在 T0、T1 都以 `TypeError: Failed to fetch` 拒絕該請求。
- Firefox 153.0.1 在 T0、T1 都 resolve response，回傳完整 22 bytes，SHA-256 仍等於 canary。
- Firefox 的 Service Worker、CacheStorage、cross-origin isolation、115 MB WASM cache roundtrip與重啟後驗證在
  同輪皆通過；R8-A false 僅由原先要求 `truncated.rejected === true` 的 fault oracle 造成。

## 推論

- `Content-Length` 與連線結束的處理不能作為跨瀏覽器一致的完整性介面。
- 跨瀏覽器穩定的產品契約應是「reject，或取得的 decoded bytes／hash 與 release manifest 不符時拒絕啟動」。
- 測試 fixture 應真正少傳 body bytes，避免「body其實完整、只有宣告長度較大」造成 fault 定義歧義。

## 修正後已驗證

- fixture改成宣告22 bytes、實際只傳15 bytes後，Chrome T0／T1皆reject且`detected: true`。
- Firefox T0／T1仍resolve 15-byte response，但decoded size與SHA-256 mismatch使`detected: true`。
- 兩browser的fault aggregate、完整T0／T1 discovery與R8-A validator皆通過。

## R8-B完整graph重驗

- Chrome／Firefox在T0／T1、identity／gzip的完整mandatory graph均逐項驗證encoded length、decoded size與
  SHA-256後才啟動Worker。
- partial response、錯誤bytes、size/hash mismatch在兩browser共形成typed拒絕，Worker=0、document mutation=0；
  Firefox不論底層fetch reject或resolve，都沒有繞過bytes/hash oracle。
- R8-B machine evidence：`findings/evidence/sdk-r8/delivery/negative/summary.json`及兩browser case raw JSON。

## 待驗證

1. R8-C寫入candidate CacheStorage前與離線讀回時仍使用相同decoded size/SHA-256邊界。
2. R8-D在環境可用時以Brotli重驗相同完整性邊界。

## 修正策略

- `truncated` fixture宣告完整 canary長度，但只傳送前段內容後關閉連線。
- browser probe接受兩種安全結果：transport rejection，或已resolve response的 bytes／SHA-256 mismatch。
- 不接受「HTTP 200且不驗證內容」作為成功。

## 證據

- `findings/evidence/015/browser-comparison.json`
- `findings/evidence/sdk-r8/discovery/browser/chrome/t0/initial/result.json`
- `findings/evidence/sdk-r8/discovery/browser/chrome/t1/initial/result.json`
- `findings/evidence/sdk-r8/discovery/browser/firefox/t0/initial/result.json`
- `findings/evidence/sdk-r8/discovery/browser/firefox/t1/initial/result.json`

## 環境

- 日期：2026-08-04
- Chrome：150.0.7871.128（headless CDP）
- Firefox：153.0.1 Snap；geckodriver 0.37.0（headless WebDriver）
- topology：T0 loopback same-origin、T1 loopback cross-origin
- R8 release：`writer-review-82cfce600c80ed6e`
- writer-review WASM：`ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6`
- Core：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`

## 是否上游

否。這是 browser observable behavior差異與我方 fault oracle假設，不歸因為 LibreOffice 或 Firefox bug。

## 時間軸

- 2026-08-04：R8-A Chrome／Firefox T0/T1 discovery發現差異並保存原始結果。
- 2026-08-04：修正 fault fixture與完整性判定；Chrome以reject、Firefox以15-byte mismatch安全偵測，T0／T1重驗通過。
- 2026-08-04：R8-B完整release graph、identity/gzip與88項跨browser negative通過，Finding 015產品契約已實作。
