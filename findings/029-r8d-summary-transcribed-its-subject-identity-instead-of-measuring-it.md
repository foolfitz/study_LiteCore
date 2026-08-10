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

## 待驗證

1. 另外 14 份寫死的 `671c848b…` 副本裡，有哪些也是「只寫出不比對」。
   本檔只查了 `validate_r8_d.py` 這一份。
2. `sdkVersion` 與 `capabilities` 同樣是手工宣稱且無交叉比對，
   本次未納入 `shippedIdentity`（它們不影響 artifact 身分，但會影響
   `RELEASE_UNSUPPORTED` 那條路徑的語意）。
3. 是否該把 15 份副本收斂成單一來源。**改動範圍跨 E1／R6／R7／R8，未評估。**

## 證據

- `wasm_sdk_probe/tools/validate_r8_d.py:18-20`、`:424-425`（修復前的抄寫）
- `wasm_sdk_probe/tools/r8_release.py:214-250`（`build_release_manifest` 的來源）、
  `:288-289`（只驗格式）
- `wasm_sdk_probe/Makefile:1120-1121`（sdk-manifest 是 `cp`）
- `wasm_sdk_probe/dist/r8/release-manifest.json`（實際出貨身分）
- `findings/evidence/sdk-r8/production/summary.json`（修復後含 `shippedIdentity`）

## 修訂紀錄

- 2026-08-10：建檔並同日修復。起因是查 finding 027 待處理第 3 項的「殘留層」，
  發現真正會影響最上層判定的不是 release manifest 的照抄，而是
  `validate_r8_d.py` 把驗證對象的身分抄成常數寫進摘要。
  一併修正 027 對該項的描述：那些欄位**有**被 release id 雜湊，
  所以缺口不是「id 不變」，而是「宣稱從未被對照」。
