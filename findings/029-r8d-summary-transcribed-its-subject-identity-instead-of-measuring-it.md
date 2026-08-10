# 029 — R8-D 的判定摘要把「驗證對象的身分」抄成常數，而不是量出來

| | |
|---|---|
| **狀態** | **已修（2026-08-10）**。三個欄位改為當下重算，並把原常數轉成閘門 |
| **發現日** | 2026-08-10（追查 [finding 027](027-r8d-verdict-silently-outlived-its-release.md) 待處理第 3 項「殘留層」時） |
| **嚴重度** | 中：發現當下**數值全部正確**，屬潛伏缺陷。但它報告的是「這次驗證了什麼」，錯了會誤導最上層的判定讀者 |
| **可重現** | 是，確定性。突變任一常數即可 |
| **是否上游** | 否，我方 harness（`tools/validate_r8_d.py`） |

## 現象（已觀察）

`validate_r8_d.py:18-20` 定義三個模組常數，**全檔只有一個用途**——
在 `:424-425` 直接寫進判定摘要：

```python
CORE_COMMIT   = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"
LOADER_SHA256 = "35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566"
WASM_SHA256   = "ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6"
...
    "core": {"commit": CORE_COMMIT},
    "artifacts": {"loaderSha256": LOADER_SHA256, "wasmSha256": WASM_SHA256},
    "matrixSha256": sha256_file(project / "r8" / "production-matrix-v1.json"),
```

**同一個 dict、相鄰三行，兩種認識論地位**：`matrixSha256` 是算出來的，
`core` 與 `artifacts` 是字面值。輸出裡沒有任何東西能讓讀者分辨。

讀 `production/summary.json` 的人會合理地把 `artifacts.wasmSha256` 當成
「這次驗證的那個 wasm 的身分」。它不是——**磁碟上放什麼，它都印同一個值。**

## 為什麼這是缺陷而不只是風格問題

**只被寫出、從不被比對的常數不可能失敗，因此不帶資訊。**
（本輪的既有紀律：「不能印出不同值的探針不是探針」；fable 補充的
「永遠 fail 的閘門和恆真閘門一樣沒資訊」。這是第三種變體：**連閘門都沒有的宣稱**。）

失效形狀與 [027](027-r8d-verdict-silently-outlived-its-release.md) 完全相同——
**判定的自我描述活得比它描述的東西久**。若哪天 wasm 重建，
`release_binding()`（`7e66554`）會抓到證據家族綁錯 release，
但**這三個欄位不在它的守備範圍**：摘要會繼續宣稱驗證的是舊的 `ba257beb…`，
而實際驗證的是新的 artifact。027 是判定過期四天沒人發現；這一個連過期都不會顯示。

## 發現當下的數值是對的（已觀察）

核對 `dist/r8/release-manifest.json`：

| 欄位 | 常數 | 實際出貨 |
|---|---|---|
| `wasm-loader` | `35d96f5f…` | `profiles/writer-review/probe.35d96f5fdcb9ed0c.js`＝`35d96f5f…` |
| `wasm-binary` | `ba257beb…` | `profiles/writer-review/probe.ba257beb038b6a2d.wasm`＝`ba257beb…` |
| `coreCommit` | `671c848b…` | manifest 宣稱 `671c848b…` |

**所以這是潛伏缺陷，不是正在發生的錯誤報告。** 相符是靠人工維護的巧合而非量測。

## 上下文：同一個 hash 在 repo 裡有 15 份獨立寫死的副本（已觀察）

`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb` 出現在 15 個非證據檔裡
（`sdk/manifest.json`、`sdk/r6-writer-review-manifest.json`、
`tools/validate_{e1,r6,r7,r8}_preflight.py`、`tools/validate_r8_d.py`、
`e1/`／`e2/` 的 matrix、`test-docs/r7-compat/manifest.json` 等），
**沒有找到任何交叉比對**。

而 `dist/profiles/writer-review-r6/sdk-manifest.json` 只是
`cp sdk/r6-writer-review-manifest.json`（`Makefile:1120-1121`）——**手工維護的宣稱**，
`build_release_manifest`（`r8_release.py:214-250`）照抄它的
`coreCommit`／`sdkVersion`／`capabilities`，只有 `sha256`／`rawBytes` 是從實際檔案算的。
`r8_release.py:288-289` 也只驗 `coreCommit` 的**格式**（40 位小寫十六進位），不驗值。

**這正是 027 待處理第 3 項所指的「殘留層」。** 但查完之後結論要修正一項：
那些欄位**有**被 release id 一起雜湊（`r8_release.py:249`），
所以「宣稱改了但 id 沒變」這條路是通的、不成立。
真正的缺口比較窄——**宣稱從未與它所描述的東西對照過**，
而 `validate_r8_d.py` 這三個欄位是其中唯一會被寫進最上層判定的。

## 修復（2026-08-10，已執行）

新增 `shipped_identity(project)`：

- `coreCommit` 取自**正在驗證的那份** `dist/r8/release-manifest.json`；
- `loaderSha256`／`wasmSha256` 對 manifest 實際指向的檔案 `sha256_file()`；
- 原本的三個常數改名為 `EXPECTED_*`，**降級成期待值**；
- 摘要新增 `shippedIdentity` 區塊（`observed`／`expected`／`matches`／`pass`），
  並加入 `safetyChecks["shippedIdentity"]`——**不符現在會 STOP，而不是被當成事實報告出去**。

`core` 與 `artifacts` 兩個既有欄位保留原名原位置，但改印實測值，
所以下游讀者不必改。

### 突變控制（已觀察，證明閘門能失敗且有分辨力）

把 `EXPECTED_WASM_SHA256` 暫時改成 `deadbeef…` 後重跑：

```
decision                    : STOP
safetyChecks.shippedIdentity: False
matches                     : {"coreCommit": true, "loaderSha256": true, "wasmSha256": false}
artifacts.wasmSha256         : ba257beb…   ← 印的是實測值，不是被竄改的期待值
```

**逐欄區分**（只有被竄改的那欄 false），且摘要報告的是現實而非期待。
還原後 `decision` 回到 `PARTIAL_GO_LOCAL_DELIVERY`、
`shippedIdentity: True`、六家族仍全 bound。

## 待驗證（三項均已於 2026-08-10 同日結案）

### 1. 另外 14 份副本 ~~有哪些也是「只寫出不比對」~~ → **結案：沒有，`validate_r8_d.py` 是唯一一份**

逐檔審計結果（已觀察）：

| 檔案 | 用法 | 判定 |
|---|---|---|
| `validate_e1_preflight.py:104` | `head == CORE_COMMIT`（比對實測 git HEAD） | 真閘門 |
| `validate_r6_preflight.py:102`、`:113-119` | 同上；另 `result["manifest"] == {…}` | 真閘門 ×2 |
| `validate_r7_preflight.py:170`、`:173` | 同上；另 `manifest_summary == EXPECTED_MANIFEST` | 真閘門 ×2 |
| `validate_r8_preflight.py:92` | `core_commit == EXPECTED_CORE_COMMIT` | 真閘門 |
| `validate_e1_c.py:182` | `head == CORE_BASELINE_HEAD` | 真閘門 |
| `validate_finding_012_native_26_8.py:106` | `--expected-core-commit` 的預設值，validator 比對 | 真閘門 |
| `tests/test_finding_012_native_26_8.py` | 測試 fixture | 不適用 |
| `create_r7_compatibility_corpus.py:198`、`:384` | **producer 在建立時蓋 provenance** | 見下 |
| `sdk/manifest.json`、`sdk/r6-writer-review-manifest.json` | 被上列 preflight 比對的**受檢宣稱** | 受閘 |
| `e1/*.json`、`e2/*.json` 的 `.baseline.coreCommit` | **無人讀取** | 見下 |
| `test-docs/r7-compat/manifest.json`（7 處） | corpus 資料 | 見下 |

**`validate_e1_c.py` 反而是做對的示範**：artifact 雜湊在 `:105-107` 實算、
`:158-173` 以 observed／expected 比對——與本檔對 R8-D 的修法同形。
**R8-D 是唯一的例外，不是通例。**

兩個較弱的殘留（**都不寫進判定，嚴重度低於本檔主體**）：

- **`e1/validation-matrix-v1.json`、`e1/discovery-matrix-v1.json`、
  `e2/discovery-matrix-v1.json` 的 `.baseline.coreCommit` 沒有任何人讀。**
  `validate_e1_c.py:157` 確實讀 `matrix["baseline"]`，但只取三個
  `*Sha256` 欄位；commit 那欄是閘門用**模組常數**比對的，不是用矩陣裡這個值。
  兩者目前一致，但矩陣若過期不會有人發現。
- **corpus 的 `coreCommit` 只驗有無、不驗值**：
  `validate_r7_compatibility_corpus.py:113-114` 是
  `if source.get("kind") == "libreoffice-qa" and not source.get("coreCommit")`。
  屬測試素材的 provenance metadata。

### 2. ~~`sdkVersion` 與 `capabilities` 未納入~~ → **結案：已納入，但改用更好的比對對象**

原本設想是替它們也加寫死的期待值。查證後改法更好——**`capabilities` 確實沒有任何
閘門**（`validate_r7_preflight.EXPECTED_MANIFEST` 只涵蓋 `coreCommit` 與
`sdkVersion`），而 `sdkVersion` 已被 R7 preflight 閘在
`dist/profiles/writer-review-r6/sdk-manifest.json` 上——**正是 R8 release manifest
抄寫的同一份來源檔**。

所以新增的不是第 16 份寫死副本，而是 `faithful_transcription()`：
**比對「抄本」與「它抄的那份來源」**。這檢查的是本檔主體沒涵蓋的一條路——
`validate_r8_d.py` 直接讀磁碟上的 `dist/r8/release-manifest.json` 而不重建，
所以「release manifest 早於 profile manifest 的變更」是可達的，
**又是 027 的形狀**。不符現在併入 `safetyChecks["shippedIdentity"]`。

突變控制（兩次，各自針對不同欄位）：

| 突變 | `decision` | `identity` | `transcription` | 逐欄 |
|---|---|---|---|---|
| 來源指向 `writer-review`（非 `-r6`） | STOP | **True**（不受影響） | False | 只有 `sdkVersion` false |
| 來源 `capabilities` 刪掉一項 | STOP | True | False | 只有 `capabilities` false |

第一次突變**沒有真正考驗 `capabilities`**（兩個 profile 剛好都是 14 項且相同），
所以補了第二次專門針對它的突變。還原後 `PARTIAL_GO_LOCAL_DELIVERY`、
`identity` 與 `transcription` 皆 True、六家族仍全 bound。

### 3. ~~是否該把 15 份副本收斂成單一來源~~ → **結案：不收斂，理由如下**

第 1 項的審計改變了這個問題的前提：**14 份裡沒有一份是壞的**，它們是六個獨立
release（E1／R6／R7／R8／finding 012）各自的**凍結基線**。收斂成單一來源會把
「每個 release 凍結它當時的基線」變成「所有 release 共享一個會動的值」——
那正好破壞凍結的意義，也會讓 `validate_e1_c.py` 這種以模組常數比對實測 HEAD
的真閘門失去獨立性。

**成本高、方向可疑，因此不做。** 值得做的是上面兩個殘留。

## 殘留一已清：矩陣的 `.baseline.coreCommit` 現在有人讀（2026-08-10）

三份矩陣，處理方式依「**它自己所屬的 release 內有沒有可比對的常數**」而定。
跨 release 比對是錯的——E1／R6／R7／R8 的凍結基線本來就允許各自停在不同 commit。

| 矩陣 | 同 release 的對應常數 | 處置 |
|---|---|---|
| `e1/validation-matrix-v1.json` | `validate_e1_c.CORE_BASELINE_HEAD` | 兩處都加：validator 閘門 ＋ 單元測試 |
| `e1/discovery-matrix-v1.json` | `validate_e1_preflight.CORE_COMMIT` | 單元測試（該 preflight 不讀矩陣，硬塞一個新讀取不划算） |
| `e2/discovery-matrix-v1.json` | **無**（E2 沒有任何帶此常數的 validator） | **未動**，見下 |

- **`validate_e1_c.workspace_preflight()`** 新增 `matrixCommitPass`，併入 `core.pass`。
- **`tests/test_e1_c.py`** 新增 `test_e1_matrices_agree_with_the_validators_that_gate_them`，
  以 `subTest` 涵蓋兩份 E1 矩陣。**這才是常態生效的那一個**——
  `Makefile:1319` 讓它進 `test-e1-c-static`，每次都跑。

### 兩者的分工要講清楚（否則會高估 validator 那側）

`workspace_preflight()` **只在 `--write-preflight before|after` 時執行**；判定本身讀的是
已存的 `baseline/preflight-{before,after}.json`。**既存那兩份是本次改動之前寫的，
所以不含 `matrixCommitPass`**——validator 那側要下次擷取 preflight 才會生效。

**沒有為了補這個欄位去重新產生已凍結的證據**：`preflight-before.json` 是
`preserved-entry-baseline`（讀自保存檔），本來就無法忠實重做，只重做 `after`
會讓兩份不對稱；為一個欄位改寫已出貨判定的證據，代價與收益不成比例。
乾跑（不寫檔）確認**今天重新擷取會通過**，`core.pass`／`matrixCommitPass` 皆 True。

### 突變控制

把 `CORE_BASELINE_HEAD` 暫時改成 `0000dead…` 後 `python3 -m unittest tests.test_e1_c`
→ `FAILED (failures=1)`，訊息直指被改動的 hash。還原後 15 個測試全過，
E1-C 判定仍為 `E1_GO_ODT_EDITOR`、`automaticPass: true`、48/48 綁定、0 superseded。

### 為什麼 E2 那份不動（推論）

`e2/discovery-matrix-v1.json` 的 baseline 記的是它**繼承自 E1** 的東西
（`coreCommit`、`e1Decision: E1_GO_ODT_EDITOR`、`e1EditorV1LoaderSha256`），
而 E2 自己沒有任何帶此常數的 validator。要閘住它得先寫明「E2 繼承 E1 基線」
這個契約——那是 E2 的工作，而 E2 尚未啟動。**硬加一個跨 release 比對會把
「凍結基線可各自不同」這條原則破壞掉**，與待驗證 3 不收斂的理由同一條。

**殘留二（corpus 的 commit 只驗有無不驗值）仍未動**——屬測試素材的 provenance
metadata，不進任何判定。

## 證據

- `wasm_sdk_probe/tools/validate_r8_d.py:18-20`、`:424-425`（修復前的抄寫）
- `wasm_sdk_probe/tools/r8_release.py:214-250`（`build_release_manifest` 的來源）、
  `:288-289`（只驗格式）
- `wasm_sdk_probe/Makefile:1120-1121`（sdk-manifest 是 `cp`）
- `wasm_sdk_probe/dist/r8/release-manifest.json`（實際出貨身分）
- `findings/evidence/sdk-r8/production/summary.json`（修復後含 `shippedIdentity`）

## 修訂紀錄

- 2026-08-10（第三則）：**殘留一已清。** E1 兩份矩陣的 `.baseline.coreCommit`
  現在有人比對——`validate_e1_c` 加 `matrixCommitPass` 閘門，並在
  `tests/test_e1_c.py` 加常態生效的交叉檢查（`Makefile:1319` 讓它每次都跑）。
  比對範圍**限制在同一個 release 內**，理由與待驗證 3 相同。
  未為此重新產生已凍結的 preflight 證據，改以乾跑確認今天重新擷取會通過。
  E2 那份與 corpus 那項維持未動，各自記明理由。
- 2026-08-10（第二則）：**三個待驗證同日結案。** 逐檔審計 14 份副本，
  **沒有第二個「只寫出不比對」**——R8-D 是唯一例外，`validate_e1_c.py` 反而是
  做對的示範。待驗證 2 改用比對來源檔而非新增第 16 份寫死副本，
  新增 `faithful_transcription()`（含 `capabilities`，它先前沒有任何閘門），
  兩次針對不同欄位的突變各自證明能失敗。待驗證 3 改判為**不收斂**：
  14 份是六個 release 各自的凍結基線，收斂會破壞凍結的意義。
  留下兩個未動的殘留：矩陣 `.baseline.coreCommit` 無人讀、corpus commit 只驗有無。
- 2026-08-10：建檔並同日修復。起因是查 finding 027 待處理第 3 項的「殘留層」，
  發現真正會影響最上層判定的不是 release manifest 的照抄，而是
  `validate_r8_d.py` 把驗證對象的身分抄成常數寫進摘要。
  一併修正 027 對該項的描述：那些欄位**有**被 release id 雜湊，
  所以缺口不是「id 不變」，而是「宣稱從未被對照」。
