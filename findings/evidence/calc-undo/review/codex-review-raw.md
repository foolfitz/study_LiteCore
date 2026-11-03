找到 **6 個缺陷**。第 1 項會直接阻止 v4 連結成功。全程未修改檔案、未建置。

1. **[P1] undo／redo 的 C API 被 v4 的巨集排除了。**  
   [sdk_api.cpp:251](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/sdk_api.cpp:251) 的 `#ifndef OXSDK_READER_PROFILE` 包住 [undo／redo 定義](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/sdk_api.cpp:273)，但 [v4 定義](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/Makefile:5828)包含 `OXSDK_READER_PROFILE`。[exports.txt 規則](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/Makefile:5854)因此要求匯出不存在的符號，連結會失敗。  
   **修法：**僅將這兩個函式改為在 `!OXSDK_READER_PROFILE || OXSDK_ODS_UNDO` 下編入；連結前檢查實際符號定義，不能只檢查 exports 清單。

2. **[P1] walk 沒有隔離其他命令，正確的 undo 可以被判成結果未知。**  
   回呼透過 [submit](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:3563)把 verify 加到[佇列尾端](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:2822)，但 [handleCell](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:7545)完全沒有 walk 的 BUSY gate。並行送出 undo 與相同 `expectedRevision` 的 cellInput，後者可以在 verify 前通過 revision 檢查、增加 undo 並清空 redo，使正確 undo 被報成 `MUTATION_OUTCOME_UNKNOWN`。即使只是 cellRead，也會[改變引擎游標](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/calc_cell_bridge.cpp:371)，污染 `cursor.moved`。  
   Close／Open 也沒有隔離，而 [verify](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:5420)忽略傳入命令的身分，可能讀另一份文件並推進其 revision。  
   **修法：**從派送到驗證結束維持交易閘門，拒絕或延後會改堆疊、游標或文件生命週期的命令；verify 同時驗證 handle 與交易序號。已確認可造成誤報失敗，未找到公開 Calc 命令可造成誤報成功的具體序列。

3. **[P1] 排隊期間新增的草稿會被 undo／redo 靜默丟掉。**  
   [undo／redo](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/spreadsheet-shell/calc-editor-session.js:309)在呼叫當下檢查草稿；真正執行的 [_walk](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/spreadsheet-shell/calc-editor-session.js:321)卻直接清掉 `_editing`。頁面在 saving 時仍[允許復原與輸入](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:154)。  
   **已用記憶體內 fixture 重現：**host save 等待中 → 按 undo → 輸入新草稿 → save 完成；結果送出 `engine.undo`，草稿被舊內容覆蓋。  
   **修法：**在 `_enqueue` 工作真正開始時重新套用草稿規則；undo 只取消草稿，redo 拒絕，不派送引擎。

4. **[P1] 頁面仍固定載入 v3，連結 v4 不會啟用復原。**  
   [ods-editor-app.js:5](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:5)仍指向 `ods-editor-v3/sdk-worker.js`；[按鈕顯示](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:164)和[快捷鍵](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:607)都受 `undoSupported` 控制。這三個 commit 的連結／組裝規則沒有改寫頁面 URL，因此正常開頁仍沒有文件復原，CU-1／CU-2 無法通過。  
   **修法：**驗收頁面明確指向 v4 的開發產物；正式發布時切到凍結的 v4 profile。

5. **[P2] undo 跨工作表繞過頁面的視圖保存流程。**  
   session 在 [_walk:345](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/spreadsheet-shell/calc-editor-session.js:345)直接呼叫 `viewer.showPart`，沒有經過頁面的 [showSheet](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:259)。因此沒有保存離開工作表的最新 `sheetViews`、設定 `sheetSwitching`，也沒有套用目的表的 `pendingView`。  
   **情境：**在 A 表捲到新位置，undo 跳到 B，再點回 A；A 恢復較舊的位置或原點。切換期間還可能用舊格子的幾何資訊開始畫 B。  
   **修法：**讓 undo 引發的跨表切換也走共同的視圖保存／恢復流程，恢復後再 reveal 被還原的格子。

6. **[P2] 沒有命令結果回呼時，walk 永遠不會收尾。**  
   [startOdsUndoWalk](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:5406)設為 active 後，只能靠匹配回呼推進；沒有 deadline。LOK 的[派送失敗路徑](/home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-8/desktop/source/lib/init.cxx:5523)只設定錯誤訊息，沒有補完成回呼。此時引擎持續保留 active／asynchronous 狀態，[cancel 也拒絕取消](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:9022)。SDK 雖會 timeout，頁面會進 uncertain，後續 undo 仍 BUSY。原生量測只證明正常派送會收到回呼。  
   **修法：**加入有交易序號的 deadline，逾時於引擎迴圈回報結果未知並清理狀態；也檢查派送後的 LOK 錯誤。

已檢查、未發現問題的部分：

- **初始發布與鎖順序：**[先寫 walk](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:5416)，再由 [release store](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:5315)發布，回呼以 acquire 讀取；結果即使在 `postUnoCommand` 內到達也不會讀到尚未寫入的 walk。`submit()` 延後讀取的方式符合 [queueFormatBarrierStep](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:5844)。鎖範圍檢查通過。
- **不同命令的結果：**[commandName 比對](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:3556)會忽略不同名稱的命令結果，不會直接完成這次 walk。
- **成功完成的 revision：**[advance → emit → finish](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:5431)與既有非同步完成一致；worker 保留 revision，SDK 的 [undo／redo](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/sdk/document-sdk.js:617)會採用它。問題在第 2 項的命令插入窗口。
- **能力位元：**依目前 core 的 `HAVE_FEATURE_DBCONNECTIVITY=1`，runtime 與新 manifest 都是 **1046835**。v4 規則使用獨立 build 目錄；未發現會重建或改寫凍結 v3 產物的相依路徑。
- **bridge 與 worker：**粗體／斜體的單次 `setPropertyValues` 符合原生量測；兩個 worker hunk 均只匹配一次，counts、cursor 與 revision 都有轉送。
- **一般草稿／空堆疊路徑：**沒有排隊時，頁面的 `pendingEntry` 與 session 草稿規則一致；公式列保留文字復原，空堆疊維持 ready。既有 session 測試通過。
- **save／paint：**save 不改堆疊有 NU-2 證據；paint 路徑未見增加 undo 的寫入。頁面 autosave 經 session chain 串行化。