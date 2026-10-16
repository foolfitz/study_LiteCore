# 147 — 在 text input 欄位裡貼上會弄亂文字，而且 Undo 還原不回來（純文字貼上也一樣）

| | |
|---|---|
| **狀態** | 待驗證（原生已觀察 3/3；WASM 未量；機制未追） |
| **Bugzilla** | tdf#______（送出後回填） |
| **發現日** | 2026-10-16 |
| **嚴重度** | 嚴重（資料遺失，而且 Undo 救不回） |
| **可重現** | 100%（原生 3/3，Markdown 與 text/plain 兩種 mimetype） |
| **是否上游** | **未確認**：在沒有本地修改的原生 LOK build（`native-lok-26-8`，`671c848b`）上重現；還沒在桌面 LibreOffice 上用一般貼上試 |

## 現象

游標在一個 `text:text-input` 欄位裡（在 `Field` 之後）時，用 LOK `paste()` 貼上一段文字，段落會被弄亂：欄位被複製到一個新段落，`Plain `、` end` 與下一段開頭的 `S` 不見了。接著按一次 Undo，**文件回不到貼上前**，而 Undo 堆疊已經空了。同樣的位元組用 `text/plain;charset=utf-8` 貼（今天產品的 Ctrl+V 就是這條路），貼上本身是對的，但 Undo 一樣會掉字。

## 對我們的影響

**今天出貨的 Ctrl+V（v20）在原生上就受影響**：使用者若把游標放進文件裡的輸入欄位再貼上，Undo 會掉字。WASM 上會不會一樣：未量。v21 的「貼上為 Markdown」也一樣（`specs/SPEC-M3-link-batch-v21.md` §9.14）。

## 證據

- `findings/evidence/link-batch-v21/native/markdown-paste/round-2/README.md`（T2 那一節、預測表第 11 列）、`findings/evidence/link-batch-v21/native/markdown-paste/round-2/out/T2-input-M1`、`T2-input-M2`、`T2-input-plain-M2`（各 3 回，存檔前後與 stdout）。
- Fixture：`findings/evidence/link-batch-v21/native/markdown-paste/round-2/tool/inputs/`（雜湊在 `findings/evidence/link-batch-v21/native/markdown-paste/round-2/SHA256SUMS`）。

## 分析

**機制未追（NOT VERIFIED）。**下一步：讀 `sw/source/uibase/dochdl/swdtflvr.cxx` 在欄位內貼上的路徑，以及 Undo 記錄的範圍。

## 還缺什麼才能送

- [ ] 在桌面 LibreOffice 26.8 用一般的 Ctrl+V 重現（不經 LOK）
- [ ] 追到機制
- [ ] 查 master 與 Bugzilla 有沒有重複
- [ ] 確認 Component
- [ ] 上游送出擱置中（記憶 `upstream-submissions-on-hold`）

## 時間軸

- 2026-10-16：v21 計畫的原生 Markdown 補量（round 2，T2）看到；同一回的純文字對照確認不只 Markdown。
