# 158 — 含表單控制項的 ODS 在 wasm 核心上一塊 tile 都畫不出來：`com.sun.star.form.Forms` 不存在（`HAVE_FEATURE_DBCONNECTIVITY=0`）

| | |
|---|---|
| **狀態** | **已確認**（Phase E 全語料，2026-10-20；core 原始碼與建置組態讀過）；**158-A 已落地**（擁有者裁示，同晚）：session 在引擎之前以 `<draw:control` 型別化拒絕 `FORM_CONTROLS_UNSUPPORTED`（規格追加 8；全語料 5 拒／298 開，`report-2026-10-20T144351Z.json`）。核心層的缺口（B）未修 |
| **Bugzilla** | 無（上游送出擱置）。**可能是上游 wasm 建置的通病**：上游的 WASM 組態同樣關 DB connectivity；未在上游 build 上重現 |
| **發現日** | 2026-10-20（`findings/evidence/m4-ods/phase-e/report-2026-10-20T133240Z.json`） |
| **嚴重度** | **高**（對使用者）：這類檔開得了、名字讀得到、但畫布空白，每一次畫圖都丟例外。語料 303 份可開的裡有 5 份（1.7%） |
| **可重現** | 5 份檔 × 2 次執行，每張表每次畫圖都是同一個例外 |
| **是否上游** | **未確認**（核心層的建置組態；若上游 wasm 也畫不出來就是上游的） |

## 現象

`move-cell-anchored-shapes.ods`、`tdf106181.ods`、`tdf121963.ods`、`tdf134161.ods`、`tdf154005.ods`——content.xml 都有
`<office:forms>`／`<form:form>`／`<draw:control>`（1、1、9、101、1 個控制項）。開檔成功（`view-ready`、`documentType ==
"spreadsheet"`、`part_name` 正常、E2 綠），但每一次 `render` 都回：

```
DocumentSdkError UNO_EXCEPTION: idle: UNO exception: component context fails to supply service
com.sun.star.form.Forms of type com.sun.star.form.XForms
```

E3（`part_text` 也走同一條路）與 E4a 對這 5 份全紅；其餘 298 份含圖形、圖片、圖表的檔（例如 `tdf119191_transformedShape`、
`many_charts`）都正常——缺的是 forms，不是 drawing layer。

## 原因（讀原始碼與組態）

- `FmFormPageImpl::getForms()` 第一次被問到時 `css::form::Forms::create(xContext)`（`svx/source/form/fmpgeimp.cxx:300-310`）；
  有控制項的頁在畫圖時會走到這裡。
- 這個 service 的實作 `com_sun_star_form_OFormsCollection_get_implementation` 在 `solenv/bin/native-code.py:186` 被
  `#if HAVE_FEATURE_DBCONNECTIVITY && !ENABLE_FUZZERS` 閘住。
- `wasm-lite/build-a11y-gate0/config_host/config_features.h:27`：`#define HAVE_FEATURE_DBCONNECTIVITY 0`；
  原生 oracle 的 `build-native-26-8` 是 `1`。核心的 `services_constructors.list`（700 筆）裡**沒有** `OFormsCollection`〔已觀察〕。
- 所以這是**核心建置層**的缺口，連結層改不了；編輯器 profile 用同一顆核心，含控制項的 ODT **未量**。

## 處置（擁有者決定）

- A. 核心重建時開 DB connectivity（或只補 forms 那一組元件——`native-code.py` 的閘是整組的，要改閘）；代價是重建與體積，未量。
- B. v1 先登錄為具名限制，session 在引擎之前用 C6 的 package probe 偵測 `<office:forms>` 給**型別化拒絕**（`FORM_CONTROLS_UNSUPPORTED`），
  不要讓使用者看到空白畫布；不用連結。
- 無論 A／B，E3／E4a 對這 5 份保持紅到處置落地；不改判準。

## 處置結果（2026-10-20 深夜）

擁有者選的是**型別化拒絕**（上一節編為 B；handoff 10-20i 與當晚的回覆裡編為 A——以選項內容為準，不以字母為準）。判別子是 `<draw:control`（不是 `<office:forms`——LO 對 49／306 份都寫空元素；也不是 `<form:form`——`tdf138507.ods` 有表單沒控制項、畫得出來）。`viewer-shell/odf-package-probe.js` 串流解壓 content.xml 找到就停；單元測試 4 條新紅案（`findings/evidence/m4-ods/phase-e/158-a/`）；全語料 5 份拒絕、298 份照開。B（核心開 DB connectivity）留在 v2 的核心重建批次；混合文件（控制項只在某一張表）能不能畫其餘的表**未量**（`L-mixed-form-control-sheets-unmeasured`）。
