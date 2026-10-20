# 157 — 檢視頁把隱藏工作表畫成可點的 tab；引擎的 `set_part` 切不過去，讀回停在前一張可見表

| | |
|---|---|
| **狀態** | **已確認**（Phase E 全語料第一次執行，2026-10-20；core 原始碼讀過）；未修 |
| **Bugzilla** | 不適用（本專案的檢視引擎／頁面；core 的行為與桌面一致） |
| **發現日** | 2026-10-20（`findings/evidence/m4-ods/phase-e/report-2026-10-20T133240Z.json`，`upstream/fdo67682-2.ods`） |
| **嚴重度** | 一般。使用者會看到 12 個點了只得到錯誤的 tab；文件本身的可見表都開得了 |
| **可重現** | 全語料 1 次＋診斷重跑 1 次，同一份檔同 12 張，每次都一樣 |
| **是否上游** | 否。`ScTabControl` 本來就只為可見表插頁（桌面也不能切到隱藏表）；缺的是**我們的引擎沒把「可見」報給頁面** |

## 現象

`fdo67682-2.ods` 有 31 張表，`Table`…`Table_12`（part 12–23）用表樣式 `ta2`：`<style:table-properties table:display="false">`。
檢視引擎 `part_name` 回全部 31 個名字、`parts == 31`；頁面的 session 把 31 個都做成 enabled 的 tab。對 part 12–23 呼叫
`set_part(k)` 之後 `current_part` 讀回都是 **11**（前一張可見表）；session 因此丟 `PART_READBACK_MISMATCH`
（`asked for part 12, the engine reports part 11`），E3／E4a／E5 對這 12 張全紅。Part 24 起（可見）又正常。

## 原因（讀原始碼）

- `ScModelObj::setPart(nPart)` → `pTabView->SelectTabPage(nPart + 1)`（`sc/source/ui/unoobj/docuno.cxx:623-638`）。
- `ScTabControl::UpdateStatus` 只為 `rDoc.IsVisible(i)` 的表 `InsertPage`（`sc/source/ui/view/tabcont.cxx:60-69`）；切到一個沒有頁的 id
  什麼都不做，所以引擎留在原處。
- LOK 有 `getPartInfo(nPart)`，回 JSON `{"visible": 0/1, "protected": …, "rtllayout": …}`（`docuno.cxx:652-670`）——我們的檢視引擎
  **沒有**把它接成查詢，頁面無從得知哪些 tab 該停用。

## 證據

- 全語料報告裡該筆：`state.parts == 31`、part 12–23 的 `sheets[k].error.code == "PART_READBACK_MISMATCH"`、`switch == null`；
  part 11 與 24 的 `switch.readBack` 分別是 11、24〔已觀察〕。
- 原生 oracle（`01-native-oracle/oracle.jsonl`）對這 12 張讀到的文字與 part 11 的相同——同一個機制在原生也發生，oracle 給的「期望」
  本來就不是那張表的〔已觀察，由此推論〕。
- content.xml：`<table:table table:name="Table" table:style-name="ta2">` ×12，`ta2` 的 `table:display="false"`〔已觀察〕。

## 處置

- 規格追加 7 A7.2：runner 從檔案推 `hiddenParts`；E3／E4a 略過、E5 要求「拒絕且讀回不是它」；E2 的 `parts` 計數不變。
- **產品修法**（下一個檢視連結）：引擎加 `part_info(k)`（包 `getPartInfo`）→ worker → SDK → adapter 的 `tabs[].enabled = visible`，
  停用理由寫「隱藏的工作表」。頁面已有 `disabledReason` 的位子。在那之前，使用者會看到可點但會失敗的 tab——登錄為 v1 的具名限制。
