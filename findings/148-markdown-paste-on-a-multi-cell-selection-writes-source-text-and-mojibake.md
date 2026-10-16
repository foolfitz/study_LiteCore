# 148 — 在跨儲存格的選取上貼上 Markdown：每一格都被附加，第二格寫進的是原文與亂碼

| | |
|---|---|
| **狀態** | 待驗證（原生已觀察 3/3；機制未追） |
| **Bugzilla** | tdf#______（送出後回填） |
| **發現日** | 2026-10-16 |
| **嚴重度** | 一般（會寫進看不懂的文字；一次 Undo 可以還原） |
| **可重現** | 100%（原生 3/3，五個語料項） |
| **是否上游** | **未確認**：在沒有本地修改的原生 LOK build（`671c848b`）上重現；還沒在桌面 LibreOffice 的「選擇性貼上 → Markdown」上試 |

## 現象

選取從 A1 跨到 B1（`getSelectionType` = 1，選取文字 `'A1 text\tB1 text\n'`），用 `paste(doc, "text/markdown;charset=utf-8", …)` 貼上。結果選取沒有被取代，**每一個被選的儲存格都在原有文字之後被附加**：第一格得到轉好的 Markdown；第二格得到的是 Markdown **原文**，換行變成 U+00A0；M2 的粗體不見，M8（中文）變成亂碼（例如 `'B1 text# jL�\xa0\xa0�|…'`）。一次 Undo 可以還原。

## 對我們的影響

v21 的「貼上為 Markdown」只在收合的游標上送出（`specs/SPEC-M3-link-batch-v21.md` §9.14），不會走到這條路。

## 證據

- `findings/evidence/link-batch-v21/native/markdown-paste/round-2/out/T1-P11-M1`、`-M2`、`-M4`、`-M5`、`-M8`；表格在 `findings/evidence/link-batch-v21/native/markdown-paste/round-2/out/RESULTS.md` 的 `### T1-P11-M8`。

## 分析

**機制未追（NOT VERIFIED）。**第二格看起來是用別的解碼路徑把同一份位元組當純文字貼上（亂碼的樣子像是 UTF-8 位元組被當成另一種編碼）。

## 還缺什麼才能送

- [ ] 桌面 LibreOffice 26.8 上「選擇性貼上 → Markdown」到跨儲存格的選取，重現並截圖
- [ ] 追到機制
- [ ] 查 Bugzilla 有沒有重複
- [ ] 上游送出擱置中

## 時間軸

- 2026-10-16：v21 計畫的原生 Markdown 補量（round 2，T1 P11）看到。
