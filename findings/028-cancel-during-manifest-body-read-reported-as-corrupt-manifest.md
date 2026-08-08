# 028 — 取消若落在 manifest body 讀取階段，會被回報成「manifest 損毀」並要求 fallback

| | |
|---|---|
| **狀態** | 已確認（實測錯誤訊息 ＋ 原始碼不對稱 ＋ 08-04 對照輪）。**未修**，屬產品錯誤契約，待決定 |
| **發現日** | 2026-08-08（R8-B／R8-C 重跑進 `sdk-r8` 時，Firefox t0 單一 case 失敗） |
| **嚴重度** | 一般偏高：使用者主動取消會被當成 release 損毀，並被導向 fallback |
| **可重現** | 競態相依（取決於取消落在 fetch 或 body 讀取）；**原始碼的不對稱是確定的** |
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

`delivery/verified-loader.js:188-201`，兩個 `catch` 不對稱：

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

把第一個 catch 的判斷提到共用位置，讓兩條路徑一致：

```js
} catch (error) {
  if (options?.signal?.aborted || error?.name === "AbortError")
    throw error;
  throw new DeliveryError(code, `invalid JSON from ${url}: ${error}`, { stage });
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

## 待驗證

1. 取消落在 body 讀取的機率有多高、與什麼相關（機器速度？Firefox 對小 JSON 的
   header/body 切分？）。目前只有一次觀測。
2. Chrome 是否也走得到這條分支（本輪 Chrome 通過，但那只代表這次取消落在別處）。
3. 除了 manifest，其他用同一個 helper 的呼叫點是否有相同不對稱。

## 證據

- `findings/evidence/sdk-r8/delivery/browser/firefox/summary.json`（t0 `negative-cancel`）
- `git show c7b899e:findings/evidence/sdk-r8/delivery/browser/firefox/summary.json`（08-04 對照）
- `wasm_sdk_probe/delivery/verified-loader.js:20-25`（`ERROR_POLICY`）、`:188-201`（兩個 catch）
- `findings/evidence/sdk-r8/production/release-binding.json`（六家族全 bound）

## 修訂紀錄

- 2026-08-08：建檔。起因是 finding 027 第 4 步重跑 R8-B／R8-C 時 Firefox t0 單一 case 失敗；
  追到 `verified-loader.js` 兩個 catch 的不對稱。未修，因為它改的是產品錯誤契約的行為。
