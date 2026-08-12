# wedge-split — finding 037 的三選一收斂

callback 串流把卡點框在 barrier 讀取那一步的三個操作裡，其中 containment 檢查是純算術，
剩兩個 LOK 呼叫。**串流分不開它們**——兩個進去之前都不發訊號。

所以這裡繞開 barrier：用產品既有的 `editorDiscoverySelect`（滑鼠拖曳）把**同一個選取**擺好，
再一個一個單獨叫，每步各自計時、各自記狀態。`PC-PLAIN` 跑完全相同的順序當對照，
**在兩列都掛的步驟是探針的性質，不是圖片的性質**。

profile 與 wedge-trace 相同（wasm 就是 `ee185b3d…`，見 `ARTIFACT.sha256`），
所以這批量測與被解釋的那一輪綁在同一份 artifact 上。

`result.json` 的 `wedgeSplit[].steps`：`locate` → `drag-select` → `selection-rectangles`
→ `get-selection-text` → `selection-reset`，最後 `liveness` 是三段活性梯。

要看的一列是 `selection-rectangles`：拖曳做出來的端點必須與 wedge-trace 串流裡
barrier 那個選取相同（`1418 → 5798 @ y8465`），否則兩邊比的是不同的輸入。
