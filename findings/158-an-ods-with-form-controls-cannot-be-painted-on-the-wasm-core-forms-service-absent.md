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

## 158-B 的結果（2026-10-22）：forms 編得進來，但沒有 dbaccess 就連開檔都會失敗

v2 的核心（`build-ods-viewer-v2`）開了 DB connectivity，`OFormsCollection` 等 forms 元件都在（元件 700 → 783），但 dbaccess 仍被 wasm strip 拿掉。
在這顆核心上連結的 `ods-viewer-v2`（`a6390eef`）：

- 5 份含控制項的檔**開不了**（`loadComponentFromURL returned an empty reference`），比 v1（開得了、畫不出來）還糟。
- **回歸**：`tdf138507.ods`（有表單、沒有控制項；v1 開得了也畫得出來）也開不了。
- 成因（讀原始碼）〔已觀察〕：`forms/source/component/DatabaseForm.cxx:358` 的 `ODatabaseForm` 建構時以 `UNO_QUERY_THROW` 聚合 `com.sun.star.sdb.RowSet`，
  那是 **dbaccess** 的服務（`dba.component`）；引擎 stderr 正是 `unsatisfied query for interface of type com.sun.star.uno.XAggregation!`。每個 `<form:form>`
  都會在匯入時丟例外。v1 的核心連 forms 服務都沒有，匯入時直接略過表單，所以反而開得了。
- 推論：要讓表單畫得出來，核心必須**也有 dbaccess**（至少 `dba` 函式庫的 RowSet）。dbaccess 含整套資料庫 UI，體積未量；v2 的 gzip 餘裕只剩 3.28 MB。

證據：`findings/evidence/m4-ods/viewer-v2/phase-e/`；規格 `SPEC-M4-viewer-v2` §7。

## 158-B 另立工作項（2026-10-22，SPEC-M4-viewer-v2 §7.1 第 5 步）

擁有者選了退路：出貨的 v2（`e96e01ec`，`build-a11y-gate0`）不帶 forms，含控制項的檔照 158-A 拒絕。158-B 從 v2 拆出來，成為獨立工作項，**還沒排程**。

- **目標**：含 `<draw:control` 的檔在檢視引擎上開得了、控制項畫得出來；而且 v1 開得了的檔（`tdf138507.ods` 這類有表單沒控制項的）不能變成開不了。
- **已知前提**〔已觀察〕：forms 匯入時要 dbaccess 的 `com.sun.star.sdb.RowSet`（`ODatabaseForm`，`DatabaseForm.cxx:358`，`UNO_QUERY_THROW`）。
  `ENABLE_WASM_STRIP_DBACCESS` 只有 Make 變數、沒有 C++ 巨集（§7 的讀法），所以讓 dbaccess 回來是組態層的事；dbaccess 回來時 reportdesign 會跟著回來
  （第九個 patch 讓兩者同進退）。
- **未量**：dbaccess 進核心的體積。gzip 餘裕：`e96e01ec` 是 47,972,953，距上限 52,428,800 還有 **4,455,847**；`a6390eef` 的經驗是 DB connectivity
  一組就吃掉約 1.18 MB。只帶 RowSet（`dba`）不帶資料庫 UI（`dbu`）可不可行，也未查。混合文件（控制項只在某一張表）能不能畫其餘的表仍未量
  （`L-mixed-form-control-sheets-unmeasured`）。
- **起點**：`wasm-lite/build-ods-viewer-v2`（6.0 GB，DB connectivity 已開、K-1／K-2 已綠）可以增量往上加；`a6390eef` 封存作為「有 forms 沒 dbaccess」的診斷件。
- **判準**：沿用 §4 的 V2-158B 原文，另加「`tdf138507.ods` 開得了」為不得回歸條件；排程時照 CLAUDE.md §9 先釘再跑。
- **如果永遠沒做的預設結論**：158-A 的型別化拒絕就是產品行為；5 份含控制項的檔拒絕，其餘照開。
