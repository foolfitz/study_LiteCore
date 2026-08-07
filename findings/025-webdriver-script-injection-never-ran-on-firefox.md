# 025 — 注入腳本在 Firefox 上從未執行：`return`＋換行的 ASI，加上 WebDriver sandbox

| | |
|---|---|
| **狀態** | **已確認、已修**（我方 harness，非上游、非產品） |
| **Bugzilla** | 不適用 |
| **發現日** | 2026-08-08（追 [finding 014](014-firefox-long-lived-wasm-worker-init-exhaustion.md) 的 R8-D 停擺時） |
| **嚴重度** | 對產品零影響；**對歷史結論破壞力大**——R8-D 的 Firefox 缺口與 R8 的部分 GO 敘述都建立在這上面 |
| **可重現** | 100%，三個缺陷各有獨立量測 |
| **是否上游** | **否**——`tools/r7_support.py` 與 R8 runner |

## 現象

R8-D 的 Firefox compatibility 相位在 2026-08-04 以兩種策略各等滿 **900 秒、零頁面結果、
`completedBatches: 0`**，被記成 finding 014「跨 process 大型 WASM generation 耗盡」。

用修好的 harness 重跑（**且這次沒有先跑 R8-C**，條件比當年更乾淨）：**28/28 份文件全過**，
6 個批次、12 個 worker、每頁最高 3——與 Chrome 當年記錄的形狀相同。

## 三個缺陷，一個擋著一個

修好前一個才看得見下一個，這也是它們能一起躲四天的原因。

### 缺陷一：輪詢迴圈把自己的失敗原因吞掉（`run_r8_production.py`）

```python
try:
    raw = evaluate(session, f"JSON.stringify({expression})")
    ...
except Exception:
    pass                      # ← 唯一能解釋失敗的東西
```

於是「腳本根本沒跑」與「頁面還沒完成」產生**一模一樣**的終局：
`R8-D browser value timed out: None`。改成記錄 `polls`／`evaluateErrors`／
`lastEvaluateError` 後第一次得到方向：**`evaluateErrors=0`**——evaluate 全程正常，
讀到的是真的 `null`，所以問題在腳本端而不是通訊端。

> 這與 [finding 023](023-sdk-init-wedges-at-fixed-session-depth.md) 是同一類錯誤：
> **診斷迴圈遮蔽了它存在的理由。**

### 缺陷二：`return` ＋ 換行 ＝ ASI，整個注入腳本是死碼（`r7_support.evaluate`）

```python
return session.execute(f"return {expression};")     # 修前
```

WebDriver 把 body 當函式執行，而每一份多行注入腳本的字串都是**換行開頭**，於是實際送出的是：

```js
return
      (() => { ... })();     // ASI 補上分號 → 立刻回傳 undefined，IIFE 是死碼
```

實測（2026-08-08，Firefox 153.0.1）：

| 送出的 body | 回傳 | side effect `window.x` |
|---|---|---|
| `return ⏎ (()=>{window.x='ran'; return 'v'})()` | **`null`** | **未設定** |
| `return (()=>{window.x='ran'; return 'v'})()` | `'v'` | `'ran'` |

**Chrome 不受影響**：CDP `Runtime.evaluate` 直接評估原字串，沒有 `return` 包裝。
這就是「只有 Firefox 卡住」的全部原因——不是瀏覽器慢，是腳本從未執行。

修法＝`expression.strip()`。對所有既有單行呼叫語意不變。

### 缺陷三：WebDriver sandbox 不是頁面的 global（`run_in_page`）

修掉 ASI 後停擺消失（900 秒 → **6.99 秒**），露出真正的第二層。Firefox 的 WebDriver 在
**sandbox** 裡評估注入腳本，其 global 不是頁面 window。實測：

| 注入腳本寫入方式 | Firefox 下一次讀 | 頁面自己看得到 | Chrome |
|---|---|---|---|
| `globalThis.X = v` | **`null`** | **看不到** | 留下、看得到 |
| `window.X = v` | 留下 | 看得到 | 留下 |

讀取不受影響（sandbox 的原型鏈上有 window），所以 `__r8_update_command` 這類頁面設的
東西讀得到——前置步驟（`freshReleasePrepared: true`、status page）才會全部正常。

而且它咬的不只是變數。產品程式碼 `delivery/verified-loader.js:315` 的
`fetchImpl = globalThis.fetch?.bind(globalThis)` 在真實頁面完全正確
（`globalThis === window`），在 sandbox 裡卻把 fetch 綁到 sandbox，於是每次呼叫拋出：

```
TypeError: 'fetch' called on an object that does not implement interface Window.
→ DeliveryError RELEASE_MANIFEST_INVALID (stage: manifest-fetch)
```

**這是 harness 製造出來、真實頁面碰不到的交付錯誤。**

修法＝新增 `r7_support.run_in_page()`：把腳本文字塞進 `<script>` 元素附加到
`document.head`，讓瀏覽器在**頁面自己的 global** 執行。兩個瀏覽器走同一條路，
才談得上互相比較。

## 修了哪些檔

| 檔案 | 內容 |
|---|---|
| `tools/r7_support.py` | `evaluate()` 加 `.strip()`；新增 `run_in_page()` |
| `tools/run_r8_production.py` | `wait_value` 記錄錯誤；compatibility 與 soak 兩條路徑改走 `run_in_page`；注入腳本寫 `window.`；soak 清理改成單一運算式（原本 `a; b; c` 只有 `a` 會執行） |
| `tools/run_r8_service_worker.py` | 同型：`__r8_multi_result` 改 `window.`、改走 `run_in_page`。該注入路徑**目前只有 Chrome 走**（見下），改動是為了兩瀏覽器同機制並防止日後回頭踩 |

## 影響

- **[finding 014](014-firefox-long-lived-wasm-worker-init-exhaustion.md) 的 R8-D 那組觀察撤回**
  ——900 秒停擺是本 finding，不是 Firefox 的 worker 耗盡。
- **R8-D Firefox compatibility 28/28 通過**（`evidence/sdk-r8-post-023-fix/`）。
- **R8-C 的既有 Firefox 結果不受影響，而那個 Firefox 專用分支確定是為本 finding 而寫的**
  （**已確認，2026-08-08 實測**）。`run_multi_client()` 有一段 `if isinstance(session, FirefoxSession)`
  的 **`strategy: "webdriver-tabs"`** 分支，在碰到注入路徑之前就 `return`；
  出貨的 firefox summary 走的正是它（`pass: true`，t0 46 案＋t1 37 案，已查證）。
  而被保留下來的失敗嘗試
  `service-worker/attempts/firefox-t0-full-iframe-client-timeout/` 走的是注入路徑，
  死法是 `TimeoutError: R8-C multi-client update timed out`、
  **`runnerElapsedMs: 900531`**——與 R8-D 完全同一個指紋（輪詢永遠讀不到值、等滿逾時）。
  也就是說：**當年為了繞過這個 bug 而替 Firefox 另寫了一條分支，卻沒查出 bug 是什麼。**
  後果不是結果錯誤，而是 **Firefox 從未實際跑過 iframe-client 那條多 client 路徑**。

  **判別實驗（已觀察）**：加一個預設關閉的
  `OXSDK_R8C_FORCE_INJECTED_MULTICLIENT=1`，把 Firefox 強制走共用的注入路徑：

  | | 結果 |
  |---|---|
  | 2026-08-04（bug 在） | `TimeoutError`，**900,531 ms** |
  | 2026-08-08（bug 已修，強制同路徑） | **`pass: true`，4,929 ms**，`strategy: null`（＝共用路徑） |

  差了 **182 倍**，而且是同一段程式碼、同一個瀏覽器。歸因閉合。
  證據 `evidence/sdk-r8-post-023-fix/service-worker-firefox-injected-path/`。

  **建議（未執行，屬產品／流程決定）**：`run_multi_client()` 的 Firefox 專用
  `webdriver-tabs` 分支可以退休，讓兩個瀏覽器回到同一條路徑。本次**不逕行刪除**——
  出貨的 R8-C 證據是用 tabs 策略取得的，換策略等於換證據來源，該由使用者決定。

  > 更正紀錄：本檔初版寫「R8-C 的多 client 測試在 Firefox 上同樣從未執行過，結果待重看」。
  > 查證後那是錯的——Firefox 走的是另一條分支，結果有效。錯誤來自看到同型的
  > 換行開頭 expression 就外推，沒有先確認呼叫路徑。
- `SPEC-R8-*` 的 `PARTIAL_GO_LOCAL_DELIVERY` 中「Firefox 單一 combined campaign 未通過」
  一項須重新檢視（T2 HTTPS/CDN 缺口與本 finding 無關，仍在）。

## 教訓

1. **診斷迴圈不准吞例外。**第一個缺陷讓另外兩個藏了四天。
2. **跨瀏覽器 harness 的兩條路徑不對稱，就是在量不同的東西。**Chrome 走 CDP 原字串、
   Firefox 走 `return <字串>` 進 sandbox——同一份腳本在兩邊根本不是同一件事，
   而所有「Firefox 特有」的結論都是從這個不對稱長出來的。
3. **產品程式碼沒有錯也會被 harness 判死。**`globalThis.fetch.bind(globalThis)`
   在任何真實執行環境都對；是 harness 把它放進了一個不存在於產品的環境。

## 環境

Firefox 153.0.1（headless，geckodriver）；Chrome 150.0.7871.128（headless=new）；
Linux 7.0.0-28-generic。

## 證據

- `findings/evidence/sdk-r8-post-023-fix/production/compatibility/firefox/`（28/28、6 批次）
- `findings/evidence/sdk-r8-post-023-fix/driver-stderr/`（各輪 geckodriver 輸出；
  900 秒停擺那輪全程僅 926 B，順帶**排除** driver pipe 對 R8-D 的解釋）
- 2026-08-04 的原始失敗紀錄仍在
  `findings/evidence/sdk-r8/production/attempts/compatibility-firefox-*/`，未改動

## 時間軸

- 2026-08-04 R8-D Firefox 兩種策略各等滿 900 秒，記為 finding 014
- 2026-08-08 以修好 pipe 的 harness 重跑仍停擺 → driver pipe 排除（926 B）
- 2026-08-08 `wait_value` 加錯誤記錄 →`evaluateErrors=0`，方向轉向腳本端
- 2026-08-08 ASI 實測確認 → 修 `evaluate`；停擺 900 秒 →6.99 秒
- 2026-08-08 sandbox `fetch` 綁定實測確認 → 新增 `run_in_page`；**28/28 通過**
