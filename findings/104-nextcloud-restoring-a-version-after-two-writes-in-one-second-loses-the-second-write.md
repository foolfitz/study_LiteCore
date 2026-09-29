# 104 — Nextcloud 在同一秒內寫入兩次之後，還原任何舊版本會讓第二次寫入的內容從檔案與版本歷史裡一起消失

| | |
|---|---|
| **狀態** | 已確認（HTTP 實測兩輪：同秒 5/5 遺失、跨秒 5/5 保住；2026-09-29 經真的頁面重現，六趟全遺失）／上游未回報（送出擱置中）／**宿主自己連按的那條路已在宿主 0.2.2 關上**（`SAME-SECOND SAVES KEPT`） |
| **上游** | nextcloud/server，`apps/files_versions`（`lib/Storage.php` `rollback()`、版本檔以 mtime 秒數命名） |
| **發現日** | 2026-09-28 |
| **嚴重度** | 一般偏高（**永久的資料遺失**：被丟掉的內容哪裡都找不到；但需要「同一秒兩次寫入」加上「之後有人還原」兩個條件） |
| **可重現** | 同秒的試次 100%；要讓兩次寫入落在同一秒，自然發生的機率取決於寫入間隔 |
| **是否上游** | 是：NC 34.0.2 正式版 tarball、`files_versions` 1.27.0、本機儲存，零設定 |

## 現象

一份檔案先有內容 F。在同一秒內寫入 A、再寫入 B（兩次都 204；檔案現在是 B）。接著從 Files 的版本分頁還原 F
（或任何更舊的版本）：還原成功，檔案變回 F——**B 不在檔案裡，也不在版本清單裡的任何一格**。
兩次寫入隔 1.5 秒的對照組，還原之後 A 與 B 都在版本清單裡。

還原之前就有一個看得到的徵兆：版本清單裡 revision 等於目前 mtime 的那一格，GET 時 `Content-Length` 是 B 的大小，
送出的卻是 A 的位元組（本次 A 比 B 短 1 位元組，用戶端收到 `IncompleteRead`：1355 of 1356）。

## 重現步驟

1. 上傳 F。等 2 秒以上。
2. 同一秒內：`PUT` A，再 `PUT` B（兩次的回應 ETag 會相同，見 [103](103-nextcloud-a-second-write-in-the-same-second-keeps-the-etag-so-if-match-lets-an-overwrite-through.md)）。
3. `PROPFIND` `/remote.php/dav/versions/<user>/versions/<fileid>`，取最舊那一格的 revision。
4. `MOVE` 那一格到 `/remote.php/dav/versions/<user>/restore/target`（Files 版本分頁送的就是這個請求，讀自出貨的 source map）。
5. 讀檔案、讀版本清單、GET 每一格。

**預期**：還原之前的內容 B 被存成一個版本（沒有同秒寫入時就是這樣）。
**實際**：201；檔案＝F；清單裡沒有任何一格是 B。

探針：`wasm_sdk_probe/tools/probe_m3_versions.py --only V8`（三次同秒、兩次隔 1.5 秒）。

## 證據

- `evidence/m3-versions/versions-2026-09-28T151353Z.json`，`facts.V8`：
  - 同秒（`sameEtag: true`）3/3：`secondInFile: false`、`secondInHistory: false`；還原前那一格 `GET 200 incomplete: 1355 of 1356 bytes`。
  - 隔 1.5 秒（`sameEtag: false`）2/2：`secondInHistory: true`、`firstInHistory: true`。
- `evidence/m3-versions/versions-2026-09-28T151613Z.json`，`facts.V8`：同秒 2/2 遺失；本來要同秒的第三次自然跨過了秒界
  （`sameEtag: false`，兩格 revision 差 1），A、B 都保住——天然的對照；隔 1.5 秒 2/2 保住。兩輪合計同秒 5/5 遺失、跨秒 5/5 保住。

## 分析（讀原始碼）

- 版本檔以檔案的 mtime（秒）命名：`files_versions/<path>.v<mtime>`。寫入 B 時，`write_hook` → `Storage::store()`
  把**當時的**檔案（A，mtime T）複製成 `.vT`；B 寫完之後 mtime 仍是 T，`post_write_hook` 因為 mtime 沒變而不建新的
  版本列，只更新既有那一列（大小等中繼資料改成 B 的）。所以 `.vT` 裝的是 A，那一列的中繼資料卻是 B——就是上面
  `Content-Length` 對不上的原因（`Listener/FileEventsListener.php:303-377`）。
- 還原時，`Storage::rollback()`（`lib/Storage.php:348-405`）先保存還原前的內容，但**只有在 `.v<目前 mtime>` 不存在時才
  複製**（369-373 行）。同秒寫入之後 `.vT` 已經存在（裝著 A），於是 B 沒有被保存，接著版本檔被搬進原位，B 就沒了。
- 修法方向（推論，未驗證）：`rollback()` 在 `.v<mtime>` 已存在時也應該保存目前的內容（例如用別的名字），或
  `store()`／`post_write_hook` 不該讓同一秒的兩次寫入共用一個版本檔名。

## 對我們產品的影響

`litecore` 宿主本身不會觸發還原；觸發的是使用者（或有寫入權的人）在 Files 的版本分頁按「還原」，而那個請求會
穿過我們的 token 鎖（`evidence/m3-versions` V3、V4）。要掉資料，還需要檔案最後兩次寫入落在同一秒：

- 使用者在頁面上一秒內存兩次（頁面會排隊，兩次存檔各約一百毫秒；按得夠快就會發生）；或
- 宿主的一次存檔與別人一次繞過鎖的寫入落在同一秒（見 103）。

之後任何人還原任何舊版本，較晚那一次寫入就永久遺失。宿主這一側可以不讓自己的兩次存檔落在同一秒（存檔之間至少
隔一秒），但擋不住別人的寫入；~~**沒有做**，登錄在 `specs/SPEC-M3-versions.md` §5。~~ 更正（2026-09-29）：依下方裁決做了，
宿主 0.2.2——第一種路徑（使用者自己連按）在宿主這一側關上；第二種（別人的寫入落在宿主那一秒）仍擋不住，見 103。

## 裁決（2026-09-29，fable 代擁有者，擁有者不在時授權）

裁決全文與條件：`evidence/m3-same-second/ruling-2026-09-29-fable-d.md`。裁決是 **D**：只改宿主，先量再修。
fable 寫給擁有者的理由（原文照錄）：

> 這一輪剩下的選項裡，只有 D 是「產品自己的路就走得到、而且會永久掉資料」的缺陷：使用者連按兩次存檔（或按住 Ctrl+S——頁面沒有過濾鍵盤重複，按住就是一連串存檔）→ 每次 PUT 只要 74 ms，兩次落在同一秒 → 之後任何人從 Files 還原任何舊版本，較晚那次存檔就從檔案和版本歷史裡一起消失（104，實測 5/5）。上游修不了（送出擱置中），頁面不能動（換身分就要重跑全部計數執行），宿主是唯一能動的地方，而宿主的四張回歸網都在。其他選項都該等你回來選：A 要你出面、C 作廢所有計數判定、H 會讓你另外兩個 ddev 專案短暫 404、G 是省流量不是修缺陷、F 沒有資料遺失也還沒有修法設計。D 做完的樣子是宿主 0.2.2＋一支先紅過的新臂＋四支既有 runner 在 0.2.2 上重新全綠；`INSTALLS ELSEWHERE` 仍然只是 0.2.1 的事實，0.2.2 要不要再跑安裝窗留給你。我要求先量「頁面真的能讓兩次存檔落在同一秒」再動手：現有每一筆計數執行的兩次存檔都隔了 ≥1.18 秒，那是 harness 的路，不是使用者的路，沒有人真的量過。

**做了什麼、結果**：

- 條件 1（先量）：經過真的頁面，按鈕＋Ctrl+S 不等待連按，Chrome 12 對裡 5 對、Firefox 6 對落在同一個 ETag，每一對
  都少一格版本；按住 Ctrl+S 一秒送出 30 個 PUT。「約一半」後來查明是探針固定節奏造成的相位漂移，不是機率
  （`evidence/m3-same-second/README.md`）。
- 判準先寫（`specs/SPEC-M3-versions.md` §4 R2），在 0.2.1 上先紅：控制相位之後，六趟裡每一趟十對有 8–9 對同秒，
  還原之後較晚那次存檔（S23）每一趟都找不到——**這張 finding 經過真的頁面、端到端重現了**。
- 宿主 0.2.2（`litecore` `695d9ad`）：對同一個檔案的 PUT，在前一次的回應收到之後至少 1.1 秒才送；不是連著的存檔不等。
- 計數執行 **`SAME-SECOND SAVES KEPT`**（`evidence/m3-same-second/runs/2026-09-29T035833+0000.json`）：R2 Chrome 3/3、
  Firefox 3/3，連按的每一次存檔都留在版本裡、還原之後較晚那次也在；紅案 70/70。代價：連著的第二次存檔從約 45 ms 變成
  約 1.1 秒。
- 按住 Ctrl+S 仍然每一次鍵盤重複都存一次（頁面的缺陷，另立 finding 106，宿主不補）。

**上游的缺陷本身沒有變**：別的用戶端一秒內寫兩次、之後有人還原，照樣會丟。

## 還缺什麼才能送

- [ ] 在 nextcloud/server master 確認 `rollback()` 仍是這個條件
- [ ] 查 GitHub issues 有沒有重複（「restore version lost」「same second」一類）
- [ ] 用 Files 的 UI 走一次（目前只用 DAV 送同一個請求）
- [ ] 與 103 分開送：根因不同（這張是版本檔名衝突，103 是快取沿用 ETag），但重現都需要同秒寫入
- 送出擱置中（2026-08-15 起的規矩）。

## 時間軸

- 2026-09-28：版本那一步的對抗性審核（`evidence/m3-versions/review-2026-09-28-opus.md` 第 2 項）從 `rollback()` 的條件
  與 V2 的量測推出「同秒寫入之後還原會丟掉第二次寫入」。加 V8 直接量：3/3 成立，並多量到還原前那一格的
  `Content-Length` 與內容對不上。
- 2026-09-29：fable 代擁有者裁決 D（先量再修）。條件 1 量到頁面連按就會同秒；R2 控相位後在 0.2.1 上經真的頁面端到端重現
  （六趟全遺失）；宿主 0.2.2 讓自己的 PUT 至少隔 1.1 秒，計數執行 `SAME-SECOND SAVES KEPT`。
