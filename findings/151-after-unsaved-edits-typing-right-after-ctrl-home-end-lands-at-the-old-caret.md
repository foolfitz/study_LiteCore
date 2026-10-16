# 151 — 文件有未存的改動時，按 Ctrl+Home／End 之後接著打的字落在移動前的游標處

| | |
|---|---|
| **狀態** | **已確認（量測），待裁決**（2026-10-17 凌晨；擁有者授權 fable 代為裁決） |
| **影響版本** | v21 未計數候選（頁面 `3d511216…`、殼層原始碼 digest `e0252c0b…`、引擎 `e2-editor-v21` wasm `db3408f5…`）。0.2.24 沒有綁 Ctrl+Home／End，所以這條路徑在出貨版上不存在 |
| **所在** | session `editor-shell-v2/narrow-editor-v2-session.js` `action()`（約 `:1004-1006`）：`BOUNDARY_CAPABLE_MOVES` 裡的移動，在文件有未存改動時先存檢查點（finding 096）。引擎的 `move-document-*` 在 250 ms 內沒等到游標回呼就以快取完成（`verified-move-readback`，規格 §9.1） |
| **發現日** | 2026-10-17，v21 shakedown 的 item 1 smoke（D11b-dirty、D6、D8 (e) 都出現「回覆帶舊游標」）；落點由 `findings/evidence/link-batch-v21/shakedown/diag-dirty-move/` 量出 |
| **嚴重度** | **打的字落錯地方**。發生在最常見的流程：改了內容 → 按 Ctrl+End → 接著打字 |
| **可重現** | 每次。Chrome 3/3、Firefox 3/3（小文件與 60 頁文件都是） |
| **是否上游** | 否（是我們的完成規則加上檢查點的時序） |

## 現象（量測，`diag-dirty-move/` V1–V4，兩個瀏覽器各 3 次）

| 變體 | 情境 | `Q` 落在 | 移動的完成方式 |
|---|---|---|---|
| V1 | plain3：開頭打 `Z`（文件變髒）→ Ctrl+End → 30 ms 後打 `Q` | **移動前的游標處**（存檔為 `ZQAlpha…`），6/6 | `verified-move-readback`，250.5–251.7 ms，回覆游標是舊的 `1564,1418` |
| V2 | 同上，但在移動的**回覆到了之後** 51–54 ms 才打 `Q` | **移動前的游標處**，6/6 | 同上 |
| V3 | 對照：不先打 `Z`（文件是乾淨的，不存檢查點） | 文件結尾，6/6 | `documented-callback-visible-cursor`，34–45 ms |
| V4 | 60 頁文件，開頭打 `Z` → Ctrl+End → `Q` | **移動前的游標處**，6/6；回覆後 500 ms 讀引擎，游標**仍是舊的** | `verified-move-readback` |

請求順序都是：`save`（檢查點）→ `move-document-end` → `insertText`。頁面沒有把任何指令重排。是**核心**在檢查點存檔之後超過 250 ms（大文件超過 750 ms）才執行 Ctrl+End，而引擎已經用快取回報完成，接著送出的 `insertText` 走同步的 `paste`，搶在 `GoToEndOfDoc` 之前執行。這正是規格 §9.1 具名的 **L-142-readback-overtaken**。差別在於它當初被當成「核心偶爾停頓」的罕見情況，實際上**每次在髒文件上按都會發生**，而 D7 的母數（乾淨文件）看不到它。

## 為什麼判準沒有抓到

D7 的母數是 D1 的 38 臂，全是剛開啟、沒改過的文件；D2 的宿主臂也是乾淨文件。所有釘死的判準都可以全綠，而這個缺陷照樣存在。這是「harness 的路不是使用者的路」那一型：使用者幾乎都是在改過內容之後才按 Ctrl+End。

## 候選修法（量測中，`diag-dirty-move/` V7–V9）

- V9：Ctrl+Home／End 不在移動前存檢查點（只在 mirror 套用的 session 補丁）。理由：檢查點保護的是 finding 096 的「送出的鍵在邊界上永遠等不到回呼」，而 22／23 有 250 ms 讀回期限，不會卡死。
- V7：量「任何一次存檔（自動儲存、Ctrl+S）之後多久內」仍會發生，決定修法之後還剩多少殘餘。

## 裁決

（待 fable。）
