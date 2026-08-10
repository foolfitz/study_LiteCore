# 028 — 取消若落在 manifest body 讀取階段，會被回報成「manifest 損毀」並要求 fallback

| | |
|---|---|
| **狀態** | **已修（2026-08-10）**，兩處 body catch 都補上 abort 檢查，附三站點回歸測試＋正控制。先前：已確認但未修 |
| **發現日** | 2026-08-08（R8-B／R8-C 重跑進 `sdk-r8` 時，Firefox t0 單一 case 失敗） |
| **嚴重度** | 一般偏高：使用者主動取消會被當成 release 損毀，並被導向 fallback。**08-10 全檔審計後上修**——另一處誤標成 `reject-release`（直接作廢 release），且至今從未被觀測到 |
| **可重現** | 瀏覽器上競態相依（取決於取消落在 fetch 或 body 讀取）；**原始碼的不對稱是確定的**，且**可用 node 測試確定性重現**（讓 body promise 以 `AbortError` 拒絕） |
| **是否上游** | 否，我方產品程式（`delivery/verified-loader.js`） |

## 現象（已觀察）

R8-B `negative-cancel`（故意取消的負向案例），Firefox 153.0.1、topology t0：

```
code    : RELEASE_MANIFEST_INVALID
message : invalid JSON from http://…/releases/writer-review-d6bee07b960a942d/
          release-manifest.json: AbortError: The operation was aborted.
details : { stage: "manifest-fetch", retryable: false,
            safeNextAction: "select-known-good", mutationState: "none" }
```

同一個 case 在 2026-08-04 的那輪是**正確的**：

```
code    : DELIVERY_ABORTED     stage: artifact-fetch     retryable: true
```

差別在取消落在哪裡——08-04 落在 artifact-fetch，這次落在 manifest 的 body 讀取。

證據：`findings/evidence/sdk-r8/delivery/browser/firefox/summary.json`（t0 第 40 個 case，
`caseId: negative-cancel`）；對照組 `git show c7b899e:` 同路徑。

## 成因（已觀察，就在同一個函式裡）

`delivery/verified-loader.js:186-202` 的 `fetchJson`，兩個 `catch` 不對稱：

```js
try {
  response = await fetchImpl(url, options);
} catch (error) {
  if (options?.signal?.aborted || error?.name === "AbortError")
    throw error;                    // ← 取消原樣拋出，正確
  throw new DeliveryError(code, …, { stage, cause: … });
}
if (!response.ok) …
try {
  return { response, value: await response.json() };
} catch (error) {
  throw new DeliveryError(code, `invalid JSON from ${url}: ${error}`, { stage });
  //                                                    ↑ 沒有 abort 檢查
}
```

`response.json()` 在 signal abort 時**也會以 AbortError 拒絕**（實測訊息就是它）。
第二個 catch 沒有第一個那道檢查，於是把「使用者取消」重新標成
`RELEASE_MANIFEST_INVALID`。作者在 fetch 那層記得檢查、在 body 那層忘了。

### 不對稱是兩處，不是一處（2026-08-10 補；已觀察，原始碼全檔審計）

建檔時只記了 `fetchJson` 一處。全檔審計三個 fetch／body 邊界後：**三個 fetch 的
catch 都有 abort 檢查（`:191`、`:238`），兩個 body 讀取的 catch 都沒有。**

| body 讀取點 | 誤標成 | `ERROR_POLICY` | 對呼叫端的意思 |
|---|---|---|---|
| `fetchJson:197-201`（`response.json()`） | `RELEASE_MANIFEST_INVALID` | `[false, "select-known-good"]` | 這個 release 壞了，退回舊版 |
| `fetchArtifact:276-282`（`response.arrayBuffer()`） | `ARTIFACT_SIZE_MISMATCH` | `[false, **"reject-release"**]` | 這個 release 直接作廢 |

兩件建檔時漏掉的事：

1. **`fetchJson` 服務兩個呼叫點**，不只 manifest——`:339` manifest 與 `:351`
   compression-index，兩者都傳 `RELEASE_MANIFEST_INVALID`／`manifest-fetch`。
   受影響的呼叫點因此是**三個**，不是一個。
2. **`fetchArtifact` 那處更嚴重且至今隱形。** `reject-release` 比
   `select-known-good` 更重，且訊息會宣稱 `${role} response body was incomplete`
   ——把「使用者按了取消」講成「release 的內容不完整」。
   08-04 那輪之所以看到**正確**的 `DELIVERY_ABORTED` at `artifact-fetch`，
   是因為取消落在 `fetchImpl` 呼叫本身的 catch（`:238`，有檢查），
   **不是** body 那條。這處從未被任何一輪觀測到。

### 測試套件的盲點正好落在缺陷所在（已觀察）

`delivery/tests/verified-loader.test.mjs:255`
「timeout and external abort retain their delivery taxonomy」的 `pendingFetch`
是在 **fetch promise** 上 reject：

```js
const pendingFetch = (_url, options) => new Promise((_resolve, reject) => {
  options.signal.addEventListener("abort", () => reject(
    new DOMException("aborted", "AbortError")
  ), { once: true });
});
```

它從不讓 **body promise** reject，所以兩條有檢查的路徑被測到、兩條沒檢查的
路徑沒有。**這也表示修復可以確定性地證明，不必靠競態的瀏覽器重跑**：
讓 `json()`／`arrayBuffer()` 以 `AbortError` 拒絕即可，修前印舊碼、修後印
`DELIVERY_ABORTED`。

## 為什麼這不只是測試會不會過的問題（推論，但有依據）

`verified-loader.js:20-21` 的 `ERROR_POLICY` 把 `RELEASE_MANIFEST_INVALID` 對應到
`[false, "select-known-good"]`：

- `retryable: false`——呼叫端不會重試；
- `safeNextAction: "select-known-good"`——**指示呼叫端退回到已知良好的 release**。

也就是說，**使用者在 manifest 下載途中按取消，產品會告訴呼叫端「這個 release 壞了、
退回舊版」**。正確語意應該是 `DELIVERY_ABORTED`（`retryable: true`），什麼都不必退。
在真實部署裡這條路徑會造成無謂的 rollback／版本回退。

（標推論的部分：我沒有在真實產品流程上觀測到一次因此發生的 rollback，只從
`ERROR_POLICY` 的對應關係推出後果。）

## 建議修法（未執行）

把 fetch 那層已經在用的判斷補到**兩個** body catch，讓四條路徑一致：

```js
// fetchJson:197-201
} catch (error) {
  if (options?.signal?.aborted || error?.name === "AbortError")
    throw error;
  throw new DeliveryError(code, `invalid JSON from ${url}: ${error}`, { stage });
}

// fetchArtifact:276-282
} catch (error) {
  if (signal.aborted || error?.name === "AbortError")
    throw error;
  throw artifactError("ARTIFACT_SIZE_MISMATCH", …);
}
```

**這不是改契約，是讓 body 路徑遵守 fetch 路徑已經在用的那個契約**——
`DELIVERY_ABORTED` 早就存在，只是這條分支到不了它。

**影響範圍（已觀察）**：`delivery/verified-loader.js` **不在** release bundle 的 17 個
artifact 內（bundle 只含 r7 reference、`document-sdk.js`、input adapter、page-navigation
與 writer-review profile）。所以改它**不會鑄出新的 release id、不會作廢
[finding 027](027-r8d-verdict-silently-outlived-its-release.md) 那輪剛綁好的六個家族**。
但它會改變 `negative-cancel` 的觀測結果，因此**要重跑 R8-B**（R8-C 走同一支 loader，
一併重跑較安全）。

## 修復（2026-08-10，已執行）

兩處 body catch 各補兩行，與 fetch 那層同一道判斷；`ERROR_POLICY` 與任何錯誤碼
都沒動，因此**不是改契約**。

修法之所以會產出 `DELIVERY_ABORTED`，是靠 `verifyRelease` 外層既有的 catch
（`:400-408`）：它只轉換**非 `DeliveryError`** 的錯誤，所以先前 body catch 把
raw AbortError 包成 `DeliveryError` 就把這條路攔死了。rethrow 之後外層才接得到，
轉出 `DELIVERY_ABORTED`／stage `artifact-fetch`——**與 08-04 那次正確輸出逐欄相同**。

### 修前讀數（已觀察，`node --test`）

新測試在修復前跑，三個站點各自印出：

```
manifest           RELEASE_MANIFEST_INVALID / false / select-known-good
compression-index  RELEASE_MANIFEST_INVALID / false / select-known-good
entry-html         ARTIFACT_SIZE_MISMATCH   / false / reject-release
```

manifest 那筆的訊息是 `invalid JSON from …/release-manifest.json: AbortError: aborted`
——與 Firefox 實測證據同形。修後三站點皆為 `DELIVERY_ABORTED / true / retry-release`。

### 兩個測試各管一側，且都證明過能失敗

- `abort during a body read stays DELIVERY_ABORTED at every read site`——abort 側。
- `body failure without abort keeps its original typed failure`——**正控制**。
  這兩個 catch 先前**兩側都沒有任何測試覆蓋**（`:174-193` 的
  `ARTIFACT_SIZE_MISMATCH` 案例其實打在 `:270-274` 的 Content-Length 檢查，
  到不了 `arrayBuffer()`；`:208`／`:291` 是 manifest 驗證失敗，不是 JSON parse 失敗）。
- **突變控制**：把兩處判斷暫時改成 `if (true)`（無條件 rethrow）後，
  正控制失敗、abort 測試仍通過。能區分，不是恆真閘門。

## 為什麼不先重跑碰運氣

取消落在 fetch 或 body 是競態，重跑很可能就「過了」。但那只是讓缺陷回到隱形，
不是修好——而且它已經在 08-04 隱形過一次。**判定不該靠競態擲骰子取得。**
本檔因此在缺陷修掉之前，不再重跑 R8-B 求綠。

## 連帶影響（已觀察）

- `validate_r8_b.py`：`safetyChecks.firefox = false` → `decision: STOP`。這是 R8-B
  **唯一**的失敗項（另兩條 `partialGaps` 是既有的 Brotli 與 full-fidelity 圖大小，與本檔無關）。
- `validate_r8_d.py`：連帶 `pass: false`。
- **但 release 綁定已經修好**：`production/release-binding.json` 現在
  **六個家族全 bound、0 superseded**（先前 4 bound／2 superseded）。
  這次失敗與 finding 027 的綁定問題**無關**，是被它擋在後面才露出來的下一層。

### 修復後重跑與重發判定（2026-08-10，已觀察）

R8-B／R8-C 各兩瀏覽器重跑，跑前跑後 release id 逐字不變（頭尾自我驗證），
期間未呼叫 `make`：

| 判定 | 修復前 | 修復後 |
|---|---|---|
| R8-B | `STOP` | **`PARTIAL_GO`**（`safetyChecks.firefox` 恢復） |
| R8-C | `PARTIAL_GO` | `PARTIAL_GO`（改綁修復後的 loader） |
| R8-D | `STOP` | **`PARTIAL_GO_LOCAL_DELIVERY`**，六家族 bound／0 superseded／0 unattributable |

R8-B 剩下的兩條 `partialGaps`（Brotli CLI、full-fidelity 圖 218,486,240 B 超過凍結的
200,000,000 B）是既有項，與本檔無關。**沒有調整任何門檻。**

四個 `negative-cancel`（兩瀏覽器 × t0／t1）都回到
`DELIVERY_ABORTED`／`retryable: true`／`retry-release`。

**但這輪瀏覽器證據不能反過來當成「body 路徑被驗證過」**（重要）：
四筆的訊息都是 `release verification aborted`／stage `artifact-fetch`，
那是外層 catch 轉出來的，而**取消落在 fetch 或 body 現在輸出完全相同**——
這正是修好的定義，卻也讓兩條路徑從外部無法分辨。
**body 路徑修好的證明是上面的 node 測試，不是這輪重跑。**

## 待驗證

1. 取消落在 body 讀取的機率有多高、與什麼相關（機器速度？Firefox 對小 JSON 的
   header/body 切分？）。目前只有一次觀測。
2. Chrome 是否也走得到這條分支（本輪 Chrome 通過，但那只代表這次取消落在別處）。
3. ~~除了 manifest，其他用同一個 helper 的呼叫點是否有相同不對稱。~~
   **2026-08-10 結案：有，而且不只 helper 的呼叫點。** 見上方
   〈不對稱是兩處，不是一處〉——`fetchJson` 另有 compression-index 呼叫點，
   且 `fetchArtifact` 的 `arrayBuffer()` 有各自獨立、同類型的不對稱。

## 證據

- `findings/evidence/sdk-r8/delivery/browser/firefox/summary.json`（t0 `negative-cancel`）
- `git show c7b899e:findings/evidence/sdk-r8/delivery/browser/firefox/summary.json`（08-04 對照）
- `wasm_sdk_probe/delivery/verified-loader.js:20-33`（`ERROR_POLICY`）、
  `:186-202`（`fetchJson` 的兩個 catch）、`:231-282`（`fetchArtifact` 的兩個 catch）、
  `:339`／`:351`（`fetchJson` 的兩個呼叫點）
- `wasm_sdk_probe/delivery/tests/verified-loader.test.mjs:255-277`（只測 fetch promise 的 abort 測試）
- `findings/evidence/sdk-r8/production/release-binding.json`（六家族全 bound）

## 修訂紀錄

- 2026-08-08：建檔。起因是 finding 027 第 4 步重跑 R8-B／R8-C 時 Firefox t0 單一 case 失敗；
  追到 `verified-loader.js` 兩個 catch 的不對稱。未修，因為它改的是產品錯誤契約的行為。
- 2026-08-10：全檔審計，**待驗證 3 結案並改寫本檔的範圍**。原記載的一處不對稱實際是
  兩處：`fetchJson` 的 `json()` 服務 manifest 與 compression-index 兩個呼叫點，
  另有 `fetchArtifact` 的 `arrayBuffer()` 誤標成 `ARTIFACT_SIZE_MISMATCH`
  ＝ `reject-release`，比原記載的 `select-known-good` 更重且至今從未被觀測到
  （08-04 那次的正確 `DELIVERY_ABORTED` 走的是 `:238` 的 fetch catch，不是 body）。
  同時記下測試套件的盲點：現有 abort 測試只在 fetch promise 上 reject，
  因此**修復可確定性證明，不必靠競態重跑**。建議修法據此擴為兩處。
