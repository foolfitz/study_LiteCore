# 142 — Ctrl+Home（以及 Ctrl+End）不會把游標移到文件開頭／結尾；接著按 Backspace 會刪到游標原本所在處的字

| | |
|---|---|
| **狀態** | **後繼已修：v21／v22 機械驗收成立，0.2.33 的擁有者 Home／End 邊界手測亦符合預期**（2026-10-25）；0.2.33 仍為未計數候選 |
| **影響版本** | 原始問題見於早期 0.2.x，在 0.2.20 的手測診斷首次量到；後繼動作與驗收見下方追加紀錄 |
| **所在** | `web/e2-editor-app.js:2679`：按鍵處理遇到 Ctrl／Cmd 組合鍵就 `return`，頁面不處理；隱藏的輸入 textarea 自己吃掉這個鍵，文件游標不動。引擎沒有「移到文件開頭／結尾」的動作。 |
| **發現日** | 2026-10-14，任務 10-14n 的 `press-after-ctrl-home` 臂（`findings/evidence/host-0.2.20-hand-test/README.md`）：Ctrl+Home 之後按 Backspace，刪掉第一個標題裡的一個字（verified-selection-delete，revision 0→1）——刪的是游標**實際**所在處，不是文件開頭。 |
| **嚴重度** | 中低：引擎刪的是畫面上游標所在的位置，行為本身一致；但使用者以為自己在文件開頭，會刪到不想刪的字。 |
| **可重現** | 每次都重現（Firefox、Chrome）。 |
| **是否上游** | 否 |

## 修法方向（提出，未裁決）

正解要引擎動作（`move-document-start`／`move-document-end`），進下一批連結；紅案＝`press-after-ctrl-home` 臂必須讀成邊界 no-op。連結之前的過渡選項（頁面攔下 Ctrl+Home／End 並提示「尚不支援」，或用既有動作組合模擬）未評估。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-14 | 登錄 |

## 後繼修復與擁有者手測（2026-10-25 補登錄）

前述「引擎沒有動作／修法未裁決」是登錄時的原始狀態。v21 第 1 項已提供文件開頭／結尾動作，0.2.26 的 D2 宿主驗收見 `handoff/HANDOFF-2026-10-17c-d2-pass-host-0226-bound-count-chain-ready.md`；v22 的對應驗收見 `handoff/HANDOFF-2026-10-20-v22-host-0227-installed-all-arms-pass.md`。

在 host **0.2.33／editor v22** 的新手測時段，擁有者對列明的四項結果回覆「A」（A＝「四項都符合預期」），包含 Ctrl+Home 後 Backspace 與 Ctrl+End 後 Delete 都沒有在文件邊界刪字。證據 `findings/evidence/host-0.2.33/f3-hand-2026-10-25/owner-confirmation.md`；該版未計數狀態不因人的回報而改變。
