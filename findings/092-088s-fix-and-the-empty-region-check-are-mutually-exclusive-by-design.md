# 092 — 088 的修法與產品路徑檢查 `the-document-region-says-why-it-is-empty` 的 oracle 由設計互斥，v12 頁面 6/6 FAIL

| | |
|---|---|
| **狀態** | 已確認 |
| **Bugzilla** | 不送出——`wasm_sdk_probe/web/e2-editor-app.js` 與 `wasm_sdk_probe/tools/run_e2_c_product_path.py`，我方 |
| **發現日** | 2026-09-07 |
| **嚴重度** | 一般（機制沒有退步；擋的是 soak 的計數，見「對 cutover 的意涵」） |
| **可重現** | v12 頁面 6/6（依 `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`「T2 came back red」R-1 段落所記）；v8 出貨頁 0/0 |
| **是否上游** | 否（我方檢查與我方修法，兩邊都是本樹自己的程式碼） |

## 現象

Task T2（`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`）在最終頁面
`9b29e39b…`／殼層 v48 上重新跑產品路徑回歸網，`the-document-region-says-why-
it-is-empty` 這一條在候選 `e2-editor-v12` 上反覆 FAIL，payload 逐字相同：

```json
"observed": {"present": true, "text": "", "reason": "paragraph", "offers": "1"}
```

`offers: "1"` 表示這個 profile 宣稱能供應段落文字、`reason: "paragraph"` 把
「這裡沒有值」的原因指名為段落文字本身，但即時區域 `#a11y-para` 量到的
`text` 是空字串。同一份 payload 出現在 soak run 1、2（`queue-v12-cutover-soak/
soak-run-01-candidate.json`、`soak-run-02-candidate.json`）、condition 2 的
三筆診斷（`queue-v12-cutover-soak/diagnostic-01/02/03-caret12.json`）、以及
revert 演練的 post-cutover 那一輪（`queue-v12-cutover-revert-rehearsal/
rerun49-after-cutover.json`）。出貨的 `e2-editor-v8` 控制組上這一條從未紅過。

## 重現步驟

1. 在頁面 `9b29e39b…`（殼層 v48、候選 profile `e2-editor-v12`）上跑：
   ```
   python3 tools/run_e2_c_product_path.py --browser chrome \
       --candidate-profile e2-editor-v12 --out report.json
   ```
2. 讀 `report.json` 裡 `checks` 陣列中 id 為
   `the-document-region-says-why-it-is-empty` 的那一筆。

**預期**：依這條檢查自己的 oracle（`tools/run_e2_c_product_path.py:7297-7300`
逐字）——

> the accessibility region always carries something to read: the focused
> paragraph on a profile that offers one, and a sentence naming the cause on a
> profile that does not. Empty is the failure. `reason` must be a code this
> page can produce and must agree with `offers`, so that a region holding
> stale text, or one claiming the engine cannot do what its contract says it
> can, cannot pass.

**實際**：`outcome: "FAIL"`，即時區域文字為空字串，同時 `reason` 與 `offers`
兩者本身都合法、彼此相容（`reason == "paragraph"` 且 `offers == "1"`，符合
`consistent` 判準），檢查判定失敗的唯一理由是 `text` 空。

## 證據

- `findings/evidence/queue-v12-cutover-soak/RUNS.md`（「Re-taken on `9b29e39b…`
  / v48 — runs 1 and 2」一節）
- `findings/evidence/queue-v12-cutover-soak/soak-run-01-candidate.json`、
  `soak-run-02-candidate.json`
- `findings/evidence/queue-v12-cutover-soak/diagnostic-01-caret12.json`、
  `diagnostic-02-caret12.json`、`diagnostic-03-caret12.json`
- `findings/evidence/gate-4a-on-9b29e39b/RESULT-4a.md`（term 6 一節，交叉引用
  同一個機制）
- `findings/evidence/queue-v12-cutover-revert-rehearsal/RESULT-2026-09-07-revert-condition-3-discharged-on-9b29e39b.md`
- `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`，「T2 came back red;
  the schedule is stopped」一節，R-1 段落

## 分析

**oracle 讀的是即時區域，不是它自己判定的來源。** 檢查用來讀頁面狀態的探針
（`tools/run_e2_c_product_path.py`，`READ_A11Y_REGION`）：

```js
const para = document.querySelector('#a11y-para');
const doc = document.querySelector('#a11y-doc');
if (!para || !doc) return { present: false };
return { present: true, text: para.textContent,
         reason: para.dataset.reason, offers: doc.dataset.offers };
```

只讀 `#a11y-para` 的 `textContent` 與 `dataset.reason`、`#a11y-doc` 的
`dataset.offers` 三樣，從未讀 `para.dataset.deferredToStructure`。

**而那個屬性正是 088 的修法為了這件事才加的。** `web/e2-editor-app.js` 的
`projectFocusedParagraph`（第 159–215 行）：結構投影（`aria-activedescendant`）
已經指到同一個焦點段落時（`structureSpeaks !== null`），即時區域被**刻意**
寫成空字串——

```js
const doubled = structureSpeaks !== null;
const next = doubled ? "" : (text ?? A11Y_REASONS[reason]);
if (el.a11yPara.textContent !== next) el.a11yPara.textContent = next;
el.a11yPara.dataset.reason = reason;
// Said out loud in the DOM, so a probe can tell "silent because the structure
// has it" from "silent because there is nothing to say".
el.a11yPara.dataset.deferredToStructure = doubled ? "1" : "0";
```

`dataset.deferredToStructure = "1"` 就是修法自己留給探針的旗標，用來把「因為
結構通道已經在講了所以沉默」跟「沒有東西可說所以沉默」分開——但探針不讀它。

**兩件事因此由設計互斥，不是任何一邊的退步**：088 的修法要求「同一段落只能
有一個聲音」，於是在結構通道接手時讓即時區域沉默；`the-document-region-says-
why-it-is-empty` 的 oracle 假設「這個 profile 宣稱供應段落文字時，即時區域
永遠不該是空的」。只要焦點段落同時被結構通道講出來（`e2-editor-v12` 這個
profile 開了結構投影，`e2-editor-v8` 沒有），修法就會讓這條檢查如實地紅——
它量到的正是修法要它量到的行為，只是判準沒有把「已交給另一個通道」算作
合法的「不是空」。

**十筆 `20f09cc9…` 的 soak run 從未量過這個交互。** 那十筆全部早於 088 的兩次
修法落地（`findings/evidence/queue-v12-cutover-soak/RUNS.md` 的作廢紀錄、
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md` 的「T0」一節），所以
`the-document-region-says-why-it-is-empty` 與 088 的修法**今晚是第一次**在
一次 soak run 裡碰頭；v45、v46 都不曾被這個檢查量過。**這不是 v46 的退步**
——是同一個檔案裡兩塊各自正確的邏輯，第一次同框。

## 對 cutover 的意涵

擋的是 soak 的計數，不是任何使用者可見的行為：4b 的機械那半（擋門）問的是
「游標所到之處的段落文字有沒有進 log、標題有沒有連層級被唸出來」，兩者在
`aria-activedescendant` 指到焦點節點時都成立（見 `findings/088-*.md`）。這條
檢查問的是另一個更窄的問題——「即時區域本身是不是空的」——而修法讓它在焦點
段落被結構通道接手時如實地空。**只要 soak 的計數規則不承認「有東西可讀，但
讀的來源是結構通道」也算「有東西可讀」，這個 profile 就永遠到不了 12 之0 之
上**，因為每一次游標停在一個有結構投影的段落上，這條檢查都會紅。

## 處置選項（主 session 的建議，不是裁定）

**A（建議）**：改檢查讓它驗**宣稱**本身，而不是驗**代理**（`AGENTS.md` §7）
——「有東西可讀」的來源可以是即時區域**或**結構通道的 active descendant：讀
`data-deferred-to-structure="1"` 且結構投影目前的焦點節點文字非空，兩者滿足
其一就算「不是空」。這是**測試變更**，`AGENTS.md` §4 允許（判準的前提——
「即時區域是這個 profile 唯一的通道」——被 087/088 證偽之後就不該再用它去量
一個承認第二通道存在的產品）。要附紅案：兩個通道**都**沉默時必須仍然 FAIL，
否則改動本身就失去鑑別力（`AGENTS.md` §6）。這個改動**改變了「clean」的定義**
，所以依 §9 的計數語意，soak 的計數要歸零——但現在本來就是 0，歸零沒有代價。

**B**：讓即時區域恢復帶文字，不再對結構通道接手時沉默。這會讓 088 的殘留
（同一段被唸兩次）重新出現——擁有者已經用耳朵否決過這個行為
（`findings/088-*.md`，「殘留」段落），所以這個選項等於撤銷一個已經被使用者
驗收過的修法去換一個檢查通過。

**C**：維持現狀，不改檢查。soak 永遠關不了——只要 `e2-editor-v12` 開著結構
投影且使用者的游標停在任何段落上，這條檢查就會紅，12 之 0 沒有上升的路徑。

**殘餘風險（無論選哪個處置都要記下）**：只依賴即時區域、不支援
`aria-activedescendant` 的螢幕閱讀器，在 `e2-editor-v12` 上會拿到完全空的
播報——這個組合目前**沒有量測涵蓋**。Orca（支援 activedescendant）已實測
沒有問題；4a 第 8 項釘的正是「結構投影在游標路徑上」這件事，但它假設的讀取
方式本來就是 activedescendant，不是即時區域退化的情況。若這個殘餘風險永遠
沒有被排入量測，預設結論是：**只支援即時區域的 AT 在這個 profile 上是已知
但未量測的可用性缺口**，不是「已經檢查過沒事」。

## 環境

```
候選頁面 9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c（e2-editor-v12）
殼層     v48，bundleSha256 ecfb6866117673c21a7c21995f7ea76fe60beb9f94a73c222053a18cc573a6ef
出貨頁面 e2-editor-v8（同一份 soak/condition-2/revert-rehearsal 報告裡的控制組），此檢查 0/0 紅
瀏覽器   headless Chrome，run_e2_c_product_path.py / check_caret_diagnostics.py 的自動化路徑
```

## 處置：A，由擁有者裁定（2026-09-07 追記）

擁有者的回覆逐字是「A」——改檢查去驗**宣稱**（「有東西可讀」）而不是驗**代理**
（某一個 DOM 節點的文字）。裁定與 T5a 的工單記在
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md` 的「R-1 = A, by the
owner」一節。

判準本身寫在閘門文件裡，**先於程式碼**：
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`，
`# Amendment, 2026-09-07 — the region check verifies the claim, not the node`
（append-only）。那一段帶著改寫後的 oracle 逐字句、一條式的通過式、五個值各自的
DOM 來源、`AGENTS.md` §9 的四個條件、計數語意（**改變了 clean 的定義所以計數
歸零**——現在本來就是 0；run 1、2 以舊措辭銀行為 FAIL 且不重判，本修正 commit
之前的任何一次執行都不能計入），以及本修正欠的紅案。

實作在 `wasm_sdk_probe/tools/run_e2_c_product_path.py`（commit `7dbbcc70`）：
`READ_A11Y_REGION` 在同一次求值裡多讀 `deferredToStructure`、`activeDescendant`
與 `structureText`；通過式加上「兩條通道都沉默才是失敗」與「deferral 只在
`reason == "paragraph"` 且 `offers == "1"` 時合法」。突變表加了兩個紅案
（commit `dbf0a820`）。**沒有動任何產品檔**——本次修法是測試變更，
`web/`、`dist/`、profile 一律未動，頁面 sha 與殼層 generation 都沒有移動。

**紅案還欠著，由 T5b 跑。** 在有人拿這條檢查的綠燈當證據之前，預設結論照
`AGENTS.md` §6：**這條檢查在這個頁面上是 NOT_ESTABLISHED，不是通過**；4a 第 6
項一併維持 NOT_ESTABLISHED（4a 為 7/8），soak 也不能開始計數。

「殘餘風險」那一段不因處置 A 而消解：只讀即時區域、不跟 `aria-activedescendant`
的 AT，在 `e2-editor-v12` 上仍然是**已知但未量測**的可用性缺口。修正把這句話
一併抄進閘門文件，因為那之後閘門裡不會有別的地方講它。
