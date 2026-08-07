# Finding 016 人工刪除觀察

狀態：`stopped-finding-017`。第一版自由組合流程已證明容易把caret放錯位置；第二版在同一Worker內
close／open後的第一筆search逾時，隨後搜尋因殘留request回`BUSY`。兩輪原始紀錄分別保留於
`operator-2026-08-04-01.log`與`operator-2026-08-04-02.log`。第三版雖以全新Worker排除timeout，但方向鍵回覆時
selection仍未collapsed，Backspace實際刪除整個搜尋選取；紀錄位於`operator-2026-08-05-03.log`。第四版改用搜尋
矩形click仍無法解除搜尋選取，安全前置條件已阻止mutation，原始紀錄為`operator-2026-08-05-04.log`。第五版改用
既有closed diagnostic `selection-reset-unstable`，並保留mutation前雙重readback；reset後第一個public
`getSelection()`卻回`LOK_ERROR: Flavor text/plain;charset=utf-16 is not supported`。這不是delete失敗，因為尚未
dispatch mutation；空selection readback邊界已另立Finding 017，本人工頁停止迭代，不改變E1的
`STOP_OR_RESCOPE`判定。

## 開啟

伺服器啟動時開啟：

`http://127.0.0.1:8765/e1-manual-delete.html`

若瀏覽器不在同一主機，需由操作員使用既有SSH port forwarding把遠端`127.0.0.1:8765`轉到本機；本研究不自行修改
SSH或防火牆設定。

## 最短測試

1. 等右上角顯示「就緒」。
2. 按「Delete：預期只刪除0」。頁面會刷新並建立全新Worker，再自動載入、以限定的selection reset收至字串
   開頭、確認沒有selection後才刪除；確認綠色結果且畫面為`123456789`。
3. 按「Backspace：預期只刪除9」。頁面會再次刷新並建立另一個全新Worker；確認綠色結果且畫面為
   `012345678`。
4. 按「段首Backspace」：確認第二段與上一段合併，沒有額外遺失字元。
5. 按「段尾Delete」：確認`combining é boundary`與下一段合併，沒有額外遺失字元。
6. 只有需要自由探索時才使用第3區的搜尋、collapse、canvas點擊與單獨Delete／Backspace按鈕。
7. 可用「插入文字」「段落換行」「行內換行」作對照；需要保存時按「儲存 ODT」。

每次delete的log應顯示：

- `placement.selectionText: ""`
- `placement.stateCollapsed: true`
- `placement.method: "selection-reset-unstable"`
- `changed: null`
- `manualVerificationRequired: true`
- `completion: uno-command-result-manual-observation`

請回報每個案例「符合預期／不符合預期」及畫面上的實際結果。不要只回報按鈕沒有報錯。

若任何操作出現`TIMEOUT`或`BUSY`，該Worker視為不可繼續使用；頁面會停用自由操作。按「以全新Worker載入原始
文件」或任一一鍵案例即可建立乾淨Worker，不要在失效Worker上繼續串接搜尋。

若出現`CARET_NOT_COLLAPSED`，代表前置定位驗證已安全攔截；該輪沒有執行delete，請直接回報log，不要改用自由
測試繞過。

r5已命中新的public selection readback阻礙並建立Finding 017。本人工流程停止，不再要求操作員測試或迭代其他未
證實定位技巧；需先完成Finding 017的程式修正與自動測試，才能另開新artifact重驗。
