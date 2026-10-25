# 165：Calc 套用格式先通知新 revision，再取消圖塊，導致舊圖或全白

狀態：產品修法 **4caa253e** 已落地，鏡像 Chrome／Firefox 各三輪通過；宿主發佈結果另追加。這是本樹殼層缺陷，不是引擎未套格式，也不是 Collabora 缺陷。

## 擁有者觀察與證人

2026-10-25，擁有者先確認文字／公式輸入符合預期，再回報雙擊 cell、選取文字、按 B／I／U 後編輯區全白；關閉重開後格式存在。原話在 `evidence/165-calc-format-blank/owner-report.md`。

未修鏡像 `red-01/report.json`：三種格式的 inline／cell 路徑共六個畫面檢查全紅。第一次粗體顯示 28 塊 tile，其中 1 塊與同區域引擎直接 render 不同；後五次 DOM tile 數為 **0**。引擎文字與格式結果全部正確，取消的 render 沒被當 tile error，所以 `tileErrors=0` 並不代表畫面完整。截圖與原始 snapshot 一併留存；證人先於修法 commit。

## 原因與修法

`CalcEditorSession.setFormat()` 在引擎成功後先 `_adopt(result.cell)`，而 `_adopt` 同步 emit。畫面監聽者看到新 document revision 後清掉 DOM 並排圖，但 scheduler 還是舊 revision／快取。隨後才執行 `invalidateRevision()`，清快取、取消剛排的圖塊；最後的 state emit 沒再改 revision，頁面不再補畫。冷快取臂因而留空，快取臂會畫到舊圖。

改成**先 invalidate scheduler，再 adopt／emit**。新增單元測試在每次新 revision 的 state callback 直接檢查 scheduler context，一開始確實紅，修後通過。沒有改引擎、capability、輸入語意、格式作用範圍或共享 viewer scheduler。

## 驗證與原本漏掉的部分

事前判準為 `SPEC-M4-cell-editing-v1.md` §9，F165-view。`green-01/report.json` Chrome／Firefox 各三輪共 **90／90**；36 個格式後 snapshot，**936** 塊實際 DOM tile 逐位元組對比同區域引擎 render，全部相符。單擊選格與雙擊選取文字兩條路都涵蓋 B／I／U，也包含下載、獨立 XML 與重開。

重讀：

```bash
python3 wasm_sdk_probe/tools/read_calc_format_view.py findings/evidence/165-calc-format-blank/green-01
```

同一工具讀 red-01 會拒絕；沒有把空 tile 集合當作 `all([])` 通過。

先前 v1 的 B／I／U 測試只驗模型、存檔、重開，沒有驗格式操作後畫面。那些正向證據仍為真，但不能替代這輪畫面驗證。全白時以引擎狀態與實際繪圖資料分辨成因，沒有靠像素非白數推定模型是否修改。這是新增產品回歸，不是修理既有判讀器；§34.4 +0／+0，累計 47／27。
