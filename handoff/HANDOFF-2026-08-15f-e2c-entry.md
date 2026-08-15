# 交接 — 2026-08-15（第六段）：E2-C 進場完成、D0 通過、D1 前置探針改了判準

**接手先讀這一份**，它接續
[`HANDOFF-2026-08-15e-e2b-go.md`](HANDOFF-2026-08-15e-e2b-go.md)（仍然有效，
E2-B 的判定與那六個必讀沒有變）。

## 一句話

**E2-C 規格到 v4，三件進場工作與三件 D0 前置全部完成，`D0` 兩瀏覽器九格全過，
D1 的前置探針量出「收合游標上的 inline 格式不會動到文件位元組」並據此在 D1 執行
之前改了凍結矩陣的八個判準。D1 的正式輪還沒跑。全程零 relink、四顆凍結 artifact
逐位元未動。**

## 狀態

| | |
|---|---|
| **E2-C** | 規格 **v4**（`specs/SPEC-E2-C-paragraph-format-validation.md`），**D0 已過**，D1～D5 未執行，無判定 |
| 進場工作 | **三件全部完成**：2.2 客戶端／2.3 session／2.4 產品頁面 |
| D0 前置 | **三件全部完成**：凍結矩陣 `e2/validation-matrix-v1.json`（75 格）／殼層 bundle `b01d77da…`／`test-docs/e2/`（`list-split` ＋ `d1-anchors`） |
| **D0** | **兩瀏覽器九格全過**，十五個動作**由單一客戶端**在真引擎上到達，兩邊投影逐格相同；分析器 11 個突變全紅 |
| D1 前置探針 | 已跑（兩瀏覽器），矩陣八個 inline 格式格**在執行前**改判準 |
| E2-B | **`GO_TO_E2_C` 不變**，`validate_e2_b.py` 重跑仍是 `problems: none` |
| E1-C | `E1_GO_ODT_EDITOR` 不變，shell bundle `f9b1a52f` 完好 |
| 四顆凍結 artifact | 逐位元未變（`test-e1-c-frozen-guard` 通過） |
| 上游 | **擱置**（使用者裁示，未改變） |

## 量到的兩件事（都自帶對照組）

1. **出貨的 v2 profile 上，E1 的十個動作沒有任何殼層到得了**（0／10，
   兩個殼層各自的理由不同；對照組 v1 殼層在 v1 profile 上 10／10）。
   四路清單檢查看不到它，因為它的 client 側是**兩個殼層的聯集**。
2. **出貨的 `EditorSession` 在 v2 profile 上開不起來**
   （`UNSUPPORTED_OPERATION`，停在 `recoverable-error`；對照組在 v1 上 `ready`）。
   **所以 D1／D2 承諾的 session／queue／checkpoint／rollback／三代上限，
   在 v2 上本來沒有任何實作。**

## 修掉的兩個已出貨缺陷

1. **沒送出去的失敗會叫 host 回滾文件**：`formatFailureDisposition()` 對沒有
   barrier 欄位的錯誤一律 `unknown-rollback`，而客戶端自己丟的
   `INVALID_ARGUMENT` 沒有 barrier ——「呼叫端打錯一個參數」的處置變成
   **從 checkpoint 重開、丟掉自那之後的全部編輯**。三個證得了是派送前的碼
   改判 `refused-no-mutation`，**順序排在 barrier 之後**。
2. **`demo-structure` 每一次點擊都丟 TypeError**：遷到產品 v2 之後仍呼叫
   `client.placeCaretByClick`，而那是**診斷客戶端**的方法。已修，並補了通用檢查
   `product-page-calls.test.mjs`。

## 下一步

**D1 的正式輪**（矩陣裡 28 格 × 3 輪 × 2 瀏覽器），然後 D2 → D3 → D4 → D5。

D1 的 harness 還沒寫。已經備好的材料：

- 語料 `test-docs/e2/d1-anchors.odt`，**每個動作自己的錨點**，四個 inline 格式
  各另有一個「已經套好」的 `-OFF` 錨點。
- 判準在矩陣裡，**inline 格式那八格已按探針結果改寫**：派送 → 提交專屬標記 →
  標記所在 span 必須帶／不帶那個屬性。
- 可重用的東西：`tools/run_e2_c_d0.py`（已參數化 `--page`／`--namespace`，
  預設仍是 D0 的，所以 D0 照樣重現）、`web/e2-c-d0-app.js` 的錨點掃描與存檔
  base64 傳遞、`tools/analyze_e2_c_d0.py` 的 `--self-test` 形狀。
- **錨點掃描一定要在丟棄用的文件上做**，不能在要量的那份上做（掃描本身會選取）。

## 動手之前必讀（在 e 版那六條之外，本段新增）

1. **一個殼層不是一個產品。** 本段最大的錯就是這個：客戶端能送出動作 ≠ 產品修好了。
   收尾前問三件事——**有沒有 session？有沒有頁面？頁面上做得到那個手勢嗎？**
2. **`inventory_corpus_axes.py` 的預設 `--output` 是 E1 的證據**
   （`findings/evidence/sdk-e1/baseline/content-axes.json`），而 E1-C 的判定證據裡
   **逐字收著這支工具的 stdout**。E2 一律明寫 `--suites e2/…` 與 `--output`。
3. **`NarrowEditorV2Session` 依賴基底類別的 `this.editor` 指派。**
   那是刻意的（見檔頭），釘住它的是 `clientReplacements` 計數器。
   若哪天 `editor-shell/editor-session.js` 真的被改，**那個計數器會留在 0**，
   測試會說話——**不要把那個測試改掉**。
4. **`e2-editor.html` 釘死在 `572035ac…`**，換 build 會拒絕啟動。
5. **產品頁面不設 `__probe_metrics`。** 那是 harness 頁面的慣例，
   `ChromeSession.navigate` 等的就是它；產品頁面要用
   `tools/run_e2_c_page_smoke.py` 裡的 `navigate()`（等 `readyState`）。
6. **別用 `pkill -f` 停自己起的伺服器**——樣式會打到自己的 shell，指令回 144。
   這條在上一份交接就寫過，本段又犯了一次。

## 未決、需要使用者或外部裁決的

- **`SPEC-E2-000` 第 6 節的 no-op 條文已就地修訂**（`changed: false` →
  段落動作一律 `changed: null` ＋ `verified-format-readback`）。
  **那是把 E2-B 已經出貨的事實寫回上位規格，不是新決定**，但它動到的是
  一條「不可退讓的邊界」，值得使用者看一眼。
- **十個繼承動作的 gesture 宣告沒有人執行**（規格 2.5）：manifest 說
  `collapsed`，引擎只在段落那條路由讀 mask。本輪的處置是**不強制、具名記錄、
  D1 量它但不當通過條件**；要真的執行它得等下一次 relink。
- 對抗性審查提的第 7 項（用 facade 重用 v1 客戶端，省掉第二份驗證規則）
  **判為可行但不採用**，理由寫在規格 2.2。**那條路仍然開著。**

## 本段又學到的兩件事

1. **判準要在能滿足它的東西上先量過。** 對抗性審查要的「每個 inline 格式各對
   自己的錨點在 ODT 上驗」是對的方向，但在契約宣告的 collapsed 手勢下
   **文件位元組根本不會動**——凍著原判準等於凍了四個必敗的格。
   探針花的時間遠少於跑一輪 28 格再回頭改。
2. **`changed: true` 不等於「文件變了」。** inline 格式在收合游標上回
   `changed: true` ＋ revision +1，而 `<office:body>` 逐位元不變；效果在之後
   提交的文字上。E1 的契約一直是這個意思，只是沒寫出來——**候選 finding，
   還沒開號**。

## 本段的提交

`17a5a72`（E2-C 進場）→ 本份交接，全部零 relink。
