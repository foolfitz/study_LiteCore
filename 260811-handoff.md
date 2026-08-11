## 先讀這三份，不要憑摘要動手

1. `findings/034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md`
   ——完整成因、實測矩陣、**修法定案**、空段落的規格層收窄、我自己三個探針自傷的形狀。
2. `HANDOFF-2026-08-08-session-state.md` 最後一節「2026-08-11（續二）」——執行順序與進度表。
3. `findings/033-…md` 的〈順帶暴露的缺口〉——deadline 的規格（三個 awaiting stage、
   `FormatBarrierStageDeadlineMs = 5000`、期限永不判成功、不強制 fresh worker）。

## 任務：把四個改動做進**同一個** build

在 `wasm_sdk_probe/src/probe_engine.cpp`：

1. 段落選取換成**單一派送** `.uno:SelectText`（`kFormatBarrierSelectCommand`／
   `postFormatBarrierParagraphSelection`）。clamp 在 stock core 的 dispatch handler，
   已在 26.8 baseline 核對過（`sw/source/uibase/shells/textsh1.cxx:1975`）。
2. `parseFormatReadback` 加多段防護：第二個 block tag 或第二個 `li` → `multiBlock` → fail closed。
3. containment 檢查：selection 縱向範圍須包含 restore point，否則 typed 失敗。
4. 三個 awaiting stage 的 deadline，照 033 的規格；engineLoop 既有兩個 `wait_until` 分支
   （selection barrier 那個約在 3644 行）是抄寫範本。
5. `appendFormatBarrierDetails` 補 `stage`、`resultSeen`、`failureShape`。
   失敗碼：deadline／containment／`multiBlock` 一律 `MUTATION_OUTCOME_UNKNOWN`；
   `EDITOR_FORMAT_POSTCONDITION_FAILED` 只留給「乾淨讀到單一段落但不在目標狀態」。

## 執行順序（fable 定的）

引擎改動 → 前處理 TU 比對確認隔離（**不是 object bytes**，finding 032）→
鑑別器案例**先在舊 build `25761ff0` 跑出失敗基線** → 新 build 全套 →
重掃 A3–A5 重綁（`tools/run_e2_discovery.py` + `tools/validate_e2_a.py`，約 20 分鐘全自動）→
矩陣加 `caretOffsetCoverage` 軸 + revision 條目、SPEC 10.10、findings README 與 033/034 修訂。

鑑別器案例（fable 指定，含一個**建構的假成功 fixture**：上一段已在目標狀態 + caret offset 0，
現行 build 會「回報成功但驗證的是別段」）。

## 已否決，不要重新提案

- 三命令候選 `GoToEndOfPara` → `GoToStartOfPara` → `EndOfParaSel`：我量過、fable 駁回，
  它在 offset `Len()` 逃逸，而那正是既有測試放游標的位置。
- `sourceSequence` 時序過濾當歸屬：那是收件序號，所有危險回呼都拿到更大的號碼。
- 空段落當實作缺陷去修：它沒有可選取內容，任何游標移動式選取都定址不到，屬規格收窄。

## 可用資產

`tools/e2_a_native_empty_paragraph.cpp`（序列 × 游標 offset 矩陣探針，放不到位會輸出 `skipped`）、
fixture `empty-paragraph`（含文件中段與**末段**兩個空段落）、`run_e2_discovery.py --mode deadline`。

## 紀律（這輪反覆踩到的）

- 檢查要能對兩種答案給出不同結果。我這輪三個自傷全是「與自己名字不符的那一列」抓出來的。
- 引用數字先核對是哪個 build／哪個量測（fable 駁回沿用 250ms 就是這條）。
- 改引擎會讓現有 375 次派送變成別的 artifact 的證據（finding 027），所以**一個 build、一次重掃**。
- 凍結 artifact（`e1-editor-v1` = `835b453d…`）不得受影響。

## fable

同 session 可續問：`SendMessage` to `a38648505b6958a1d`（保留脈絡，比冷啟動便宜很多）。
它這輪第一版判斷被實測否證過一次，所以**發問前先讀 finding 034 對一次事實**，不要憑摘要轉述。
狀態機改動正是現實最容易再次不同意設計的地方，卡住就問它。
