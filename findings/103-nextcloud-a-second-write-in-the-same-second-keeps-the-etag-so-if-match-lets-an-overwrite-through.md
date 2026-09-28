# 103 — Nextcloud 對同一秒內的第二次寫入不換 ETag，所以 `If-Match` 擋不住：帶舊 ETag 的 PUT 會靜默蓋掉別人剛寫的內容

| | |
|---|---|
| **狀態** | 已確認（HTTP 實測三輪，同秒 23/23、跨秒 13/13）／上游未回報（送出擱置中） |
| **上游** | nextcloud/server（`lib/private/Files/Cache/Scanner.php`） |
| **發現日** | 2026-09-28 |
| **嚴重度** | 一般（樂觀並行控制在一秒的窗口內失效＝lost update；被蓋掉的內容仍在版本歷史裡，直到保留政策清掉它；**雙方都拿到 204，沒有人被告知**） |
| **可重現** | 同秒的試次 100%（23/23）；要讓兩次寫入落在同一秒，自然發生的機率取決於寫入間隔 |
| **是否上游** | 是：NC 34.0.2 正式版 tarball，本機儲存（Local），零設定 |

## 現象

A 寫入檔案（204，拿到 ETag `E`）。同一秒內 B 寫入**不同的內容**（204）——B 拿到的 ETag
**還是 `E`**。A 之後帶 `If-Match: E` 再寫：**204**，B 的內容被蓋掉。兩次寫入跨過秒界時，
B 的寫入會換 ETag，A 的條件式寫入是 412（正確）。

## 重現步驟

1. 使用者 A 有一份檔案，並以可寫入（permissions 3）分享給 B。
2. A：`PUT` 內容 X，記下回應的 `ETag` = `E`。
3. 立刻（同一秒內）B：`PUT` 內容 Y（與 X 不同；長度相同或不同都一樣）。
4. A：`PUT` 內容 Z，帶 `If-Match: E`。
5. A：`GET`。

**預期**：第 3 步之後 ETag 不再是 `E`；第 4 步 412；第 5 步讀到 Y。
**實際**：第 3 步回的 ETag 仍是 `E`；第 4 步 204；第 5 步讀到 Z。

探針：`wasm_sdk_probe/tools/probe_m3_versions.py --only V7`（每輪 12 次，靠自然的時間分佈
得到同秒與跨秒兩種試次；每一次都從容器裡 `stat` 檔案，記下 inode／mtime／size）。

## 證據

- `evidence/m3-versions/versions-2026-09-28T142621Z.json`（V7，12 次：同秒 9、跨秒 3）
- `evidence/m3-versions/versions-2026-09-28T143009Z.json`（V7，12 次：同秒 8、跨秒 4）
- `evidence/m3-versions/versions-2026-09-28T143221Z.json`（V7，12 次：同秒 6、跨秒 6；另記被蓋掉的內容在不在版本歷史）

| | 同秒（`stat` mtime 相同） | 跨秒 |
|---|---|---|
| B 的寫入之後 ETag 仍是 `E` | 23/23 | 0/13 |
| A 帶 `If-Match: E` 的 PUT | **204**（23/23） | 412（13/13） |
| 其中 B 比 A 多一個位元組（原本當「同大小」的對照） | 8/8 仍是 204 | — |
| B 的內容事後在版本清單裡 | 6/6（只有第三輪有記） | — |

三輪裡檔案的 inode 從頭到尾沒變（就地寫入），變的只有 mtime（秒）與大小。

## 分析

- `lib/private/Files/Cache/Scanner.php:174-183`：更新檔案快取時，若檔案的 `storage_mtime`
  與快取裡的相同（`$mtimeUnchanged`），就沿用快取裡的 `etag`（`REUSE_ETAG`），不論大小
  是否改變。mtime 的解析度是秒，所以同一秒內的第二次寫入不會產生新的 ETag。這一段是
  讀原始碼；與「大小不同也一樣」的實測一致。
- 一開始讀的是 `Local::calculateEtag`（mtime、inode、device、size 的 md5），因此預測「同秒
  **且**同大小」才會撞。**大小那一半被實測否證**：快取層在更上面就沿用了舊值，
  `calculateEtag` 的結果根本沒被採用。
- 對 `IReliableEtagStorage` 的儲存不沿用（同一段條件）。本機儲存不是。其他後端沒查。
- 上鎖／解鎖不受影響：files_lock 用 `propagateEtag` 另外寫一個新 ETag（實測 LOCK 會換
  ETag 而 mtime 不變）。

**推論（未驗證）**：同步用戶端送 `X-OC-Mtime`（把伺服器端 mtime 設成本機檔的 mtime）。
若它設的值剛好等於目前的 mtime，不必同一秒也會沿用 ETag。沒量。

## 對我們產品的影響

`litecore` 宿主的鎖與權限規格（`specs/SPEC-M3-locks-and-permissions.md`）和 finding 102 都寫著
「寫入一律帶 `If-Match`，所以宿主不掉資料」。**這句話在一秒的窗口內不成立**：

- 宿主持有 token 鎖時，照規矩來的 DAV 用戶端寫不進來（423），所以窗口只對**繞過鎖的寫入**
  開著：拿到持有者 token 的人（finding 102），以及不看 token 鎖的伺服器端寫入（files_lock 的
  儲存層包裝不檢查 token 鎖；「從版本還原」就是一例，但還原會把 mtime 設回被還原那一格的時間，
  實測 ETag 都換了、宿主拿到 412——`evidence/m3-versions` V3、V4；唯一的例外是推論：同一秒存兩次之後
  revision 等於目前 mtime 的那一格，還原它不改 mtime）。
- 宿主**沒有**持有鎖時（上鎖失敗、鎖被解掉、鎖過期），任何人在宿主最後一次存檔的同一秒內
  寫入，宿主下一次存檔都會把它蓋掉。
- 被蓋掉的內容在版本歷史裡找得到（上表），所以不是永久遺失；但沒有任何一方會被告知。

宿主這一側能做的只有縮小窗口（例如存檔前先比對內容），沒辦法關掉它；真正的修法在上游。

## 還缺什麼才能送

- [ ] 在 nextcloud/server master 確認 `Scanner` 仍沿用
- [ ] 查 GitHub issues 有沒有重複（「etag not changed same second」一類）
- [ ] 決定是不是安全問題：這是並行控制失效，不是越權（B 本來就有寫入權）；照 102 的規矩，
  先查 Nextcloud 的安全政策再決定管道
- [ ] `X-OC-Mtime` 那條推論：量或刪
- 送出擱置中（2026-08-15 起的規矩）。

## 時間軸

- 2026-09-28：量版本（路線圖 §5.5「版本正確」）的 V2 臂裡，同一秒內兩次內容不同的 PUT 回了
  同一個 ETag。因為 102 的結論正是「資料安全靠 `If-Match`」，加了 V7 直接量它；原本當對照組的
  「多一個位元組」也一樣被蓋掉，於是把「同大小」從條件裡拿掉，回頭找到 `Scanner` 那一段。
