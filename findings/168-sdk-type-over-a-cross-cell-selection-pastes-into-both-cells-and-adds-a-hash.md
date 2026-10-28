# 168：跨儲存格選取後打 x，SDK 在兩格末端貼上文字，第二格多出 #

| | |
|---|---|
| **狀態** | 已確認（產品 Chrome／Firefox 存檔）；尚未修復 |
| **Bugzilla** | — |
| **發現日** | 2026-10-27；2026-10-28 補兩瀏覽器診斷 |
| **嚴重度** | 一般（輸入結果錯誤，阻擋 S5 完整驗收） |
| **可重現** | 已保留 Chrome 兩次、Firefox 一次相同結果；不是完整情境普查 |
| **是否上游** | **未確認**——產品把打字交給 paste，原生參照是鍵盤；尚未直接量原生純文字 paste |

## 現象與重現

在凍結的 `e2-editor-v23`／ABI6／generation 76 開既有 feature fixture，表格 A1 為 `A1 cell text`、B1 為 `B1 cell text`。游標在 A1 文字尾端，按 Shift+Right，再打 `x`。案例為 `shift-Right@cell-end/type`。

- 產品存檔：A1 `A1 cell textx`，B1 `B1 cell textx#`。
- 已綁定且具順序見證的 native run-03 鍵盤參照：A1 空字串，B1 `x`。
- 一般文字對照 `shift-Right@caret-mid/type`：Chrome、Firefox 都通過既有原生參照。

初始存檔與 fixture 一致，公開請求只有一次 `insertText(text='x')`，成功回覆的 `method` 為 `paste`。Shift 延伸的成功 terminal **先於** insert request，因此不能把這筆差異直接歸為 Shift 尚未完成。沒有額外送出 `#`，也沒有在原始文件中找到 `#`。這些紀錄不足以判定記憶體汙染或責任層。

## 證據與驗收狀態

- `evidence/link-batch-v23/feature-protocol/s5-counted-02/`：Chrome 前 401 筆 PASS，第 402 筆是本案 FAIL，隨即按規則停止；Firefox 尚未執行，整輪不計入 S5 完整通過。
- `evidence/link-batch-v23/feature-protocol/s5-prep-07/`：同一凍結計畫，兩個案例各跑兩瀏覽器；一般文字兩筆 PASS，表格兩筆 FAIL。這是新診斷資料，不覆蓋 counted 失敗，也不計入正式驗收。
- `evidence/link-batch-v23/feature-protocol/s5-table-type-diagnostic-01/`：英文報告、可重跑讀取器、存檔段落、完整 insert／extension 請求回覆、native save 雜湊與原始碼定位。
- 已完成的 R1 144/144 PASS 是同一身分上的獨立結論，不因 S5 停止而消失；本案也不受 Astra A 的刪除參照裁決涵蓋。

## 讀碼與尚未證實的解釋

`probe_engine.cpp::handleInsertText` 優先走 LOK `paste(text/plain;charset=utf-8)`；只有 paste 回 false 才送字元按鍵。Writer 的 `SwTransferable::PasteData` 明確在 table mode 略過「刪除既有選取內容」分支，與兩格都保留舊字、末端多出 x 的觀察相符。

第二格的 `#` 有一條可驗證的候選：`PasteFileContent` 把字串建成 UTF-16 stream，先設 UCS2 選項；`SwReader::Read` 對多個 PaM 重用 stream，而 `AsciiReader::Read` 每次返回會 reset 選項為系統字元集，文字 parser 又會把控制字元轉成 `#`。後續 PaM 若以重設後的單位元組字元集解讀 `x\0`，可以得到 `x#`。**這是讀碼推論**；還有文字編碼偵測分支，沒有逐步追蹤確認實際選到哪一條，不能寫成已歸因。

較早的 v21 Markdown paste 原生量測也看過跨格貼上保留舊文字、後續格解碼不同；MIME 與輸入不同，只是旁證。

## 下一步

- 先區分「產品把打字實作成 paste 的語意差異」與「後續儲存格多出 # 的解碼問題」。若補原生 direct-paste／key-input 與編碼對照，需遵守既有建置與量測規則。
- 若採產品修法，準備獨立、可檢視的引擎／核心變更與反例，再由使用者執行必要的建置；凍結 v23 不覆寫，後繼身分另行綁定及驗證。
- 若要縮小驗收宣稱，必須另有明確裁決與事前判準，不能自行把本格改成 settled-WASM 取得綠燈。
- 尚未做桌面 Writer、原生純文字 paste、上游重複單查詢或上游提交。
