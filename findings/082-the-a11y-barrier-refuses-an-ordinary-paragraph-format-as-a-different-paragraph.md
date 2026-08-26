# 082 — a11y core 上一個普通的段落格式被 barrier 判成「讀回的是別的段落」，而那個閘門只有 a11y build 走得到

| | |
|---|---|
| **狀態** | **已特徵化**（四輪四中，2026-08-26）。**成因未確立**——payload 不帶指紋，指認會是猜的 |
| **發現日** | 2026-08-26，執行 `HANDOFF-2026-08-24` 開放項目 2（「v9 的產品路徑」）時掉出來 |
| **嚴重度** | **高（對 a11y 產品線）**：使用者按一次工具列的「內文」，session 就進 `recoverable-error` 而且**沒有檢查點**，產品接著告訴他「自上次儲存以來的內容不會回來」 |
| **可重現** | **4/4**，`e2-editor-v9`（wasm `b60cc46f…`＝a11y core ＋ calloc），chrome，同一台機器 |
| **出貨那顆 core** | **走不到**。閘門 gate 在 accessibility 上，沒有 accessibility 的 build 一路 fail-open，同一支臂在 `e2-editor-v8` 上是 PASS |
| **是否上游** | **否**。程式在我們自己的 `src/probe_engine.cpp` |

## 一句話

在 a11y core 上，把第一段從「標題」改成「內文」會被 format barrier 以
`readback-is-a-different-paragraph` 拒絕（`MUTATION_OUTCOME_UNKNOWN`，處置 rollback），
佇列被擋住、session 進 `recoverable-error`，而且**沒有檢查點**。

## 量到的

`format-a-paragraph-changes-that-paragraph` 這一格的前兩支臂，四輪完全一致：

| 臂 | 動作 | 目標 | 結果 |
|---|---|---|---|
| 1 | `set-paragraph-heading` | 第 1 行（`E1-LC-ISOLATED`，body→heading） | **PASS**，`標題 31–36 ms`，讀回 `Heading_20_1`，鄰居與行數都在 |
| 2 | `set-paragraph-body` | 第 0 行（`E1-LC-HEADING`，heading→body） | **FAIL**，`內文 失敗` |

臂 2 的型別化 payload（`--barrier-details-diagnostic` 把 `run()` 丟掉的那一份留了下來）：

```json
{ "code": "MUTATION_OUTCOME_UNKNOWN", "recovery": "rollback",
  "formatBarrier": {
    "failureShape": "readback-is-a-different-paragraph",
    "dispatched": true, "route": "collapsed",
    "paragraphIdentity": { "checked": true,
                           "dispatchKnown": true, "readbackKnown": true },
    "readbackParsed": true, "readbackBlockCount": 1,
    "containment": { "checked": true, "held": true } } }
```

**這不是 fail-open 也不是讀失敗。**兩次讀都成功（`dispatchKnown`／`readbackKnown` 皆
true），閘門真的跑了（`checked: true`），讀回的是**單一 block**
（`readbackBlockCount: 1`，所以不是 `multi-block-readback` 那一族），而且
**containment 成立**——選取確實蓋住了動作發出時的游標。
在這些都成立的情況下，兩個指紋仍然不同。

## 後果，以及它為什麼是產品缺陷不是儀器問題

`MUTATION_OUTCOME_UNKNOWN` 在 `RECOVERY_ERRORS`
（`editor-shell/editor-session.js:15`），所以臂 2 一失敗佇列就被擋住：

```
臂 3–5   定位游標 失敗          ← session 已經死了
存檔      EDITOR_NOT_READY      ← latency 只留下這一筆，於是它看起來像原因
```

頁面狀態：`state: recoverable-error`、`pending: 0`、**`checkpoint: 無`**、
通知寫著「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。」

**使用者按的是工具列上的一顆按鈕，做的是把一段從標題改成內文。**

## 為什麼現在才看到

這支臂在 a11y 這條線上**從來沒有真的跑到自己的 dispatch**。上一份 v5 報告
（`findings/evidence/075/pp-v5-product.json`）五支臂全部 NOT_ESTABLISHED，理由都是
同一句：「9 行只看到 7 條帶，所以這支臂說不出是**哪一段**」——那是 finding 075，
off-page 的垃圾把兩行併成一行。今天的 v9 報告是 `bands: 9, lines: 9`。

**是 076 的 calloc 修法讓這支臂第一次跑到 dispatch，而它跑到的第一件事就是被拒。**
在那之前它一直是**棄權**，不是通過——這兩件事在報告裡長得不一樣，但在人的記憶裡很容易
變成同一件。

## 出貨那顆 core 為什麼看不到

`probe_engine.cpp:4232` 的閘門條件是
`dispatchParagraphKnown && readbackParagraphKnown`，兩個都來自 accessibility；
`refreshCaretParagraph()` 在 `gEditorAccessibilityEnabled` 為 false 時直接回 false。
所以在沒有 accessibility 的 build 上這個比較**從來沒有跑過**，閘門一路 fail-open——
原始碼的註解自己寫了這是刻意的（fail-closed 會讓產品的每一個格式動作都失敗）。

**打開 accessibility 等於打開一個從未在產品上執行過的比較。**

## 沒有量的（因此不指認）

- **讀回的到底是哪一段。**payload 帶 `paragraphIdentity.{checked,dispatchKnown,readbackKnown}`
  但**不帶兩個指紋本身**（`probe_engine.cpp:1382`）。要拿到它們有兩條路，都沒走：
  在 barrier payload 裡吐出來（引擎改動＝一次連結），或從頁面讀引擎認為游標所在的段落
  （`a11yContentHash`／`a11yParagraphText` 已經在 editor state 裡，但頁面公開出來的是投影
  不是欄位——見 `queue-product-page-holds-the-raw-editor-state`）。
- **為什麼臂 1 過而臂 2 不過。**兩個候選，都沒量：臂 2 打的是**文件的第一段**；
  以及臂 1 剛把它正下方那一段變成標題，版面因此重排。
- **指紋算錯的可能性已經被讀掉一半但不是全部。**指紋是 FNV-1a 取在
  **去掉清單前綴之後**的段落文字（`parseEditorSemanticJson`），註解寫明就是為了讓
  `.uno:DefaultBullet` 不要觸發這個閘門；而 `set-paragraph-body` 根本不改文字。
  所以「換樣式就換指紋」這個最直覺的假說**與 derivation 相牴觸**——但沒有量到的是
  a11y 焦點段落在動作前後是不是同一段。

## 同一輪裡的第二種 barrier 失敗（不同缺陷，記在這裡是因為它在同一份報告裡）

`bulleting-a-blank-line-does-not-demand-a-rollback` 在同一輪、更早的地方 FAIL，
failureShape 是 **`stage-deadline:awaiting-selection`**（2026-08-23 就記過 stage-deadline，
但沒有這個子階段），`paragraphIdentity: {checked: false, dispatchKnown: true,
readbackKnown: false}`——**那一次閘門沒有跑**，讀回那一側根本沒有答案。
它同樣把 session 推進 `recoverable-error`，但緊接著的回復臂按了通知、session 回到 ready。

所以 a11y core 一輪會產生**兩種不同的 barrier 失敗**，兩種都是 session 終結級的；
第一種有人救，第二種沒有。

## 證據

- `findings/evidence/queue-a11y-path-drives-a-dead-session/product-path-e2-editor-v9-chrome-guard-stopped-it.json`
  （第一輪）與 `RESULT-the-guard-fired-unprompted.md`
- `findings/evidence/082/`：四輪的 v9 報告與 step 軌跡。第 1 輪**沒有** payload
  （`--barrier-details-diagnostic` 是看到第 1 輪之後才寫的），第 2–4 輪有——
  所以「四輪一致」講的是 step 軌跡、死亡現場與逐臂結果，型別化 payload 是 3/3。
- 對照：`findings/evidence/075/pp-v5-product.json`（同一支臂在 075 修好之前全部棄權）

## 修訂紀錄

- 2026-08-26：建檔。四輪四中；barrier 的型別化 payload 首次被收下來，確立這不是
  fail-open、不是讀失敗、不是 multi-block，而且 containment 成立。成因未確立。
