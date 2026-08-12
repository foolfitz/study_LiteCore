# 交接 — 2026-08-12（finding 035 已關閉，037 已開）

接手前先讀這一份。上一份是 [`260811-handoff.md`](260811-handoff.md)。

## 現在的狀態

| | |
|---|---|
| 分支 | `main`，工作樹乾淨，最新 `80fefb8` |
| 出貨引擎 | **`ee185b3d5972cac761acbcbc19cbafe916962788822e7cbae87bfe771d62a566`** |
| A3／A4／A5 | **全部 PASS 且綁在 `ee185b3d`**（`validate_e2_a.py` 發的） |
| 測試 | `wasm_sdk_probe` 底下 `python3 -m unittest tests.test_e2_profile` → 49 過 |

**三份 artifact 都有存檔**（`wasm_sdk_probe/build/archive/`，gitignore，各約 111 MB）：

```
ee185b3d…  e2-format-discovery-ee185b3d   ← 現行，判定綁在這裡
38168306…  e2-format-discovery-38168306   ← 034 修法後、035 修法前
bd102b4a…  e2-format-discovery-bd102b4a   ← 034 修法前
```

這次不會再有 `25761ff0` 那種「只能引用不能重現」的情形。

## 動手之前必讀的三個陷阱

1. **重編就換 artifact，判定就得全部重掃。** `probe.wasm` 的 hash 不是原始碼的函數
   （finding 036）。動引擎前**先**把現行 profile 四件複製到 `build/archive/<name>/`。
   **sweep 與判定之間絕不重編。**
2. **要診斷就開自己的 profile。** 想在引擎裡加 log 來追 037，**絕不能改
   `e2-format-discovery`**——那會把剛綁好的 A3／A4／A5 全部解綁（finding 027）。
   Makefile 已有多個 profile 的樣板（`e2-scheduler-attribution` 等），照那個模式加。
3. **fixture 的共用區塊會炸掉所有既有證據。** `create_e1_corpus.py` 的 `NAMESPACES`、
   `STYLES_XML`、`MANIFEST_XML` 與 automatic-styles 是**所有 fixture 共用**的。
   新 fixture 必須自帶 namespace／樣式／manifest 項目（`paragraph-content` 是現成範例），
   且既有六份重生成後要位元組完全相同——用 `git show HEAD:<path> | sha256sum` 對，
   不要用工具自己回報的數字。

## 這一輪做完的事

**finding 035（後置條件對含格式或中日韓文字的段落一律 fail closed）已修並關閉。**

- 修法不是「把行內標籤加進集合」，而是**結構深度掃描**：結構標籤在任何深度都辨識與計數，
  **只有非結構標籤依深度分流**（深度 ≥1 忽略、深度 0 fail closed）。
  反過來寫會把 `li` 與清單內的 `<p>` 一起忽略，拆掉 034 多段防護的一半。
  **有測試專門攔這個變異。**
- 結構集合 `p`／`h1`–`h6`／`pre`／`blockquote`／`ul`／`ol`／`li`，每一個都是**實測在 body 層
  出現才收**。**進集合就必須計入 `blockCount`，兩者不可拆。**
- `unknownTag` 提前判，拆成三個通道：`footnote-apparatus-readback`／
  `unknown-structural-tag`／`malformed-readback-nesting`，全部排在 `multiBlock` 與
  containment **之前**（中止時計數已被截斷）。失敗碼一律 `MUTATION_OUTCOME_UNKNOWN`。
- 一次 build、44 輪重掃（A3 18 輪／90 派送、A4 18 輪／270 派送、A5 8 輪／42 case、零失敗）。
- SPEC v13、矩陣 `paragraphContentCoverage` 由 3 欄擴為 15 欄。

**兩個明列的收窄，寫進 SPEC 2.10 了：**

- **ODF outline level 7–10 讀回 `<p>`**，所以 level ≥7 的標題與內文段落無法區分。
  今天無害（封閉動作集只有一級標題），**一旦出現「套用第 N 級標題」，N ≥ 7 無法驗證**。
- **帶註腳／尾註的段落設計上拒絕**（註腳本文是第二個 body 層區塊）。要改成放行，
  入口是量註腳邊界，不是重新論證。

## 還開著的（task #29 = finding 037）

**含行內圖片的段落會卡死 document handle。** 動作死於用戶端 20 s 逾時而**不是**引擎 5 s 的
`stage-deadline:*`，之後每個操作都逾時；文件本身仍關得掉。**兩個 build 都重現，是既存缺陷。**

已縮小的範圍：原生重放 barrier 六個階段、六個錨點一起跑，**每階段都 ≤10 ms 含圖片那列**
（COMPLEX 選取讀回 798 bytes、還原 10 ms 清空、handle 可用）——**所以不是 LOK 對 COMPLEX
選取做了什麼**，問題在 WASM 引擎的階段機器或事件推進。

**下一步**：診斷用 WASM profile（**自己的 profile**），`stage` 在武裝與逾時各印一次，
加上「引擎迴圈還在轉嗎」。**5 秒 deadline 完全沒作用本身是線索**——迴圈沒轉就沒有東西去
武裝或檢查 deadline，那樣卡點在 barrier 之上而不是裡面。

未做：其餘四個封閉動作、Firefox、上游重複單。

## 方法論：這一輪我出的三個錯

**沒有一個是自己發現的**，三次結論碰巧都對，但那是因為每次剛好有別的東西擋著。

1. 驅動腳本的 stdout 擷取器**靜默失敗**，留下判定欄全空的記錄 → 被空欄位的顯眼度抓到。
2. A5 的彙總判準用「status 是 `rejected` 或 `completed`」，而 A5 本來就有些案例預期
   rejected、有些預期 completed——**在兩種答案上都會通過** → 被 `validate_e2_a.py` 抓到。
3. handle 可用性訊號用「再搜同一個錨點」，**在控制組上也會亮** → 被控制組抓到。

**控制組與驗證器不是流程裝飾**，它們是這一輪唯一沒讓錯誤進到記錄裡的原因。
另外：**別在會改變狀態的指令後面加 `2>/dev/null`**——這一輪有一個 `cp` 因為唯讀權限
靜靜失敗，而我把 stderr 丟掉了。

## 外包

- **codex**：機械性、驗收條件可機器檢查的步驟可以丟（fixture 產生、掃描腳本、
  照既有檔案擴充）。**它的結論要自己跑變異控制覆核。** 這一輪它成功一次、
  三十分鐘靜默失敗一次（什麼都沒改）。指令要自帶驗收條件與禁區。
- **fable**：設計取捨、結論成不成立這類判斷題，先問使用者要不要叫。
  這一輪它抓到我一個致命錯誤（規則 2）並裁決了註腳那一刀。
