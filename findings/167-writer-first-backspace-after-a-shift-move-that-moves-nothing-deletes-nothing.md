# 167：Shift+方向鍵沒有移動時，Writer 吃掉接下來的第一個 Backspace／Delete

| | |
|---|---|
| **狀態** | 已確認（native LOK 26.8 量測＋讀碼）／桌面版**未量** |
| **Bugzilla** | — |
| **發現日** | 2026-10-27 |
| **嚴重度** | 小（使用者可見：按了 Backspace 沒反應；再按一次才刪） |
| **可重現** | 100%（native 49/49 個「空 mark」格，連送與每鍵 settle 結果相同） |
| **是否上游** | **未確認**——程式碼路徑是 Writer 共用的按鍵處理，桌面版很可能同樣；送出前要在桌面 Writer 重現 |

## 現象

游標已經在行尾（或文件尾、儲存格尾、空段落），按 Shift+End——畫面上什麼都沒變，沒有選取、游標沒動。接著按 Backspace：**什麼都沒刪**。再按一次 Backspace 才刪掉一個字。Delete、以及 Shift+Home／Shift+Left／Shift+Right 在「不會移動」的位置上都一樣；把一個字元的選取用 Shift+Left 縮回原點（`range-one`）之後也一樣。

## 重現步驟（native LOK）

1. 開 `findings/evidence/link-batch/extend-signatures/run-20261013T095104Z/fixture-as-run.fodt`，游標點到表格 A1 文字 `A1 cell text` 的尾端。
2. `postKeyEvent` Shift+End（KEYINPUT／KEYUP）。
3. `postKeyEvent` Backspace（KEYINPUT／KEYUP），存檔。

**預期**：`A1 cell tex`。
**實際**：`A1 cell text`（沒刪）。連按兩次 Backspace 才得到 `A1 cell tex`。

## 證據

- `evidence/link-batch-v23/feature-protocol/s5-native/run-01/`（連送）與 `diag-settled-01/`（每個按鍵都 settle 後才送下一個，66 格）：**66/66 結果相同**，所以不是時序問題（與 finding 166 不同）。
- 每格「Shift 之後」的 Writer 狀態：`selectionType 0`、`getTextSelection ""`、`TEXT_SELECTION ""`——LOK 對外沒有任何東西顯示有選取。診斷 66 格中這種「空 mark」狀態有 49 格；完整 336 格的見證在 `s5-native/empty-mark-witness-01/`（裁決 4 條件 1）。
- 產品比對：`s5-prep-04/`（兩瀏覽器 10/12 FAIL，產品每格比 Writer 多刪一個字）、`s5-counted-01/` 的停止格。

## 分析（讀碼）

- `SwCursorShell::IsSelection()` = `IsTableMode() || m_pCurrentCursor->HasMark() || 多游標`（`libreoffice-26-8/sw/inc/crsrsh.hxx:951-955`）：**只要有 mark 就算有選取，即使 mark 與 point 在同一位置**。
- Shift+方向鍵即使沒有移動也會設 mark。
- `SwWrtShell::DelLeft`（`sw/source/uibase/wrtsh/delete.cxx:167-191`）先走「有選取就刪掉選取」分支：刪除空範圍、`EnterStdMode()` 清掉 mark、`return`。`DelRight` 有同一個分支（`:308`）。所以第一鍵只清掉了看不見的空選取。

上面是讀碼推導，與量測一致，但沒有在除錯器裡逐步確認。

## 對本樹的影響

fable 裁決 4（`evidence/link-batch-v23/feature-protocol/s5-silent-shift-deletion-ruling/RULING.md`）：這個行為**不是** S5 要對齊的目標；空 mark 格（逐格由 native 見證決定）改比 settled-WASM，並逐格標記。產品維持「第一次 Backspace 就刪一個字」。

## 還缺什麼才能送

- [ ] 桌面 Writer 26.8（非 LOK、非 svp）手動重現：行尾 Shift+End 後按 Backspace
- [ ] 確認是否為刻意行為（「Shift 選取模式」的設計）——查 Bugzilla 與 sw 的 git log
- [ ] 搜尋 Bugzilla 有無重複
- [ ] 上游送出目前擱置（2026-08-15 起），重啟時先重查

## 時間軸

- 2026-10-27 08:05：`s5-counted-01` 停在 Chrome `shift-End@cell-end/backspace`（產品 `A1 cell tex`，native `A1 cell text`）。
- 2026-10-27 08:35：`diag-settled-01` 66/66 settled 與連送相同。
- 2026-10-27：fable 裁決 4。
