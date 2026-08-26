# 082 — barrier 拿「空字串的雜湊」當段落身分，於是在 a11y core 上拒絕了一個成功的段落格式，並且沒有檢查點就把 session 推進 recoverable-error

| | |
|---|---|
| **狀態** | **成因確立、已修、修法量到生效**（2026-08-26）。修在我們自己的引擎；上游那半是 finding 074，未修 |
| **發現日** | 2026-08-26，執行 `HANDOFF-2026-08-24` 開放項目 2（「v9 的產品路徑」）時掉出來 |
| **嚴重度** | **高（對 a11y 產品線）**：使用者按一次工具列的「內文」，session 就進 `recoverable-error` 而且**沒有檢查點**，產品接著告訴他「自上次儲存以來的內容不會回來」 |
| **可重現** | **4/4**，`e2-editor-v9`（wasm `b60cc46f…`＝a11y core ＋ calloc），chrome，同一台機器 |
| **出貨那顆 core** | **走不到**。閘門 gate 在 accessibility 上，沒有 accessibility 的 build 一路 fail-open，同一支臂在 `e2-editor-v8` 上是 PASS |
| **是否上游** | **一半**。誤報在我們的 `src/probe_engine.cpp`（已修）；讓它誤報的那個數字來自上游 —— finding 074，`sfx2/source/view/viewsh.cxx` |

## 一句話

在 a11y core 上，把第一段從「標題」改成「內文」**會成功**，但 format barrier 以
`readback-is-a-different-paragraph` 拒絕它（`MUTATION_OUTCOME_UNKNOWN`，處置 rollback），
佇列被擋住、session 進 `recoverable-error`，而且**沒有檢查點**。

**是誤報。**閘門比的兩個指紋裡有一個是「空字串的雜湊」——那顆標題被 LOK 回報
`listPrefixLength == contentLength`（finding 074），切完什麼都不剩，
於是它和「只有一個項目符號的空段落」是同一個數字。

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

## 成因（量到的，不是讀出來的）

`--barrier-details-diagnostic` 把 worker 的 `productFormatBarrier` 白名單在鏡像裡放寬
——**引擎其實一直有送，是 JavaScript 丟掉的**——於是整包 barrier 物件進了報告：

```json
{ "stage": "awaiting-restore", "command": ".uno:StyleApply",
  "expectedStyles": ["Body Text"],
  "resultSuccess": true, "resultModified": true,
  "readback": { "parsed": true, "blockCount": 1, "blockTag": "p",
                "html": "… <p>E1-LC-HEADING</p> …" },
  "containment": { "checked": true, "held": true,
                   "selectionTop": 1418, "selectionBottom": 1693,
                   "restoreCentre": 1625 } }
```

**讀回的就是那一段，而且它已經是 `<p>` 了。**動作成功了。所以「讀到別的段落」是假的。

再把 `editorState.caretParagraph` 逐次狀態轉換錄下來（66 筆），出現過的每一種讀數：

| n | listPrefixLength | contentLength | fingerprint | text |
|---:|---:|---:|---|---|
| 9 | 0 | 20 | `76f09d751bb341f7` | `E1-LC-END甲一乙二丙三插入鈕標記` |
| 3 | 2 | 22 | `76f09d751bb341f7` | `• E1-LC-END甲一乙二丙三插入鈕標記` |
| **7** | **13** | **13** | **`cbf29ce484222325`** | **`E1-LC-HEADING`** |
| **3** | **2** | **2** | **`cbf29ce484222325`** | **`• `** |
| 3 | 3 | 19 | `d0586a07b98862c6` | `1. E1-LC-NUMBER-ONE` |

兩件事同時成立：

- **切前綴是對的、而且有效**：同一段加不加項目符號是**同一個指紋**
  （`76f09d751bb341f7`）。這正是切它的理由，不能拿掉。
- **一顆 13 字的標題和一個只有項目符號的空段落是同一個數字**，而那個數字是
  `cbf29ce484222325` —— FNV-1a 64 的 offset basis，**「什麼都沒餵進去」的值**。
  兩者都是 `listPrefixLength == contentLength`，也就是 finding 074：
  `getListPrefixSize()` 回的是第一個 ATTRIBUTE RUN 的結尾，不是編號前綴的長度。

所以閘門拿一個退化的值去比一個真的值，判「不是同一段」。

## 修法（已做，並且量到生效）

閘門在任一端的指紋退化時**放棄比對**，而不是判它失敗——和它周圍那段註解本來就在論證的
fail-open 同一件事，只是從「值不在」擴到「值在但沒有意義」。理由是：另一邊是**假的拒絕
外加一張 rollback 處方**，比這個閘門本來要抓的缺陷更糟。

規則和雜湊放在同一個檔（`src/a11y_paragraph_identity.hpp`），
`tests/a11y_paragraph_identity_test.cpp` 在**主機上**驅動它們，並且**重現了引擎真的報過的
六個指紋**——所以那是跨實作核對，不是把規則再抄一遍。四種突變都被它抓到。
payload 多三個欄位，讓 `checked: false` 的三種成因不必用猜的。

**對出貨那顆 core 是惰性的**：accessibility 關掉時 `refreshCaretParagraph()` 回 false，
`dispatchParagraphKnown` 本來就是 false、閘門本來就放棄。v8 不需要重新連結。

### 量到的（`e2-editor-v10`，2026-08-26）

`what_the_link_ships.py --variant a11y --since c82a642`（v9 那顆 artifact 連結自的 commit）：
三個 translation unit 前處理**完全相同**、`sdk-worker.js` **逐位元相同**、
`probe_engine.cpp` 的每一個 hunk 都屬於這張 finding。對 v9 是**單一變因**。

| | v9 | v10 |
|---|---|---|
| wasm | `b60cc46fcc6bf572` | `4ec1e389aaab3b03` |
| worker | `070229cd10bda4a0` | `070229cd10bda4a0` |
| 動作／手勢 | 21 個 | 完全相同 |

產品路徑（預測寫在跑之前，見 `handoff/RUNBOOK-relink-v10-a11y-identity.md`）：

| 預測 | 實測 |
|---|---|
| 不會停，40 格全跑 | **`sessionDied: null`**，40 格 |
| `set-paragraph-body` 過 | **過**，而且那一格六支臂全過 |
| 不再有 `readback-is-a-different-paragraph` | **一次都沒有** |
| `bulleting-…` 仍紅在 `stage-deadline:awaiting-selection` | **仍紅，同一個 shape** |
| `notice-action-recovers-the-session` 仍過 | **過**，配對關係 `held: true` |

整輪 **35 PASS / 2 FAIL / 3 NOT_ESTABLISHED**。v9 上這一格四輪四次都撐不過第二支臂。

**三輪三中**：

| 輪 | 判定 | 那一格 | `caret-follows-the-text-you-type` |
|---|---|---|---|
| 1 | 35 PASS / 2 FAIL / 3 NE | **PASS**，六支臂 | **FAIL** |
| 2 | 37 PASS / 1 FAIL / 2 NE | **PASS**，六支臂 | PASS |
| 3 | 37 PASS / 1 FAIL / 2 NE | **PASS**，六支臂 | PASS |

三輪都沒有提早停、都沒有出現 `readback-is-a-different-paragraph`，
每一輪僅存的那一筆 page error 都是 bulleting 那格的
`stage-deadline:awaiting-selection`——另一個缺陷，沒被碰到，和預測一致。

## 這個修法買到的東西（重點在這裡）

**第 17 格之後的 23 格，在這條線上第一次被量到**，而其中一格是紅的：
`caret-follows-the-text-you-type`——第一輪打字文字進了文件（`revisionAdvanced: true`）
但游標沒動（163 → 163），第二、三輪正常。**而且它是間歇的：三輪裡紅一輪。**
那是新的觀察，不屬於這張 finding，已另立
`queue-a11y-caret-does-not-move-on-the-first-commit`——三輪紅一輪正是這棵樹被騙過的那個形狀，
所以它是佇列項不是 finding。而在 session 死在第 17 格的時候，它根本不可能被看到。

## 我第一個假說是錯的，而它錯得有用

第一份預測（`findings/evidence/082/PREDICTION-which-paragraph-was-read.md`，
寫在讀結果之前）押的是**還原點的幾何過期**：barrier 在讀回之前會用**動作發出前**存下的
文件座標點回去，而 `set-paragraph-body` 讓那一段變矮，所以那個點可能掉到下一段去——
引擎自己的註解就寫著這個殘留。

**`readback.html` 一句話否證掉它**：讀回的就是 `E1-LC-HEADING`，而且已經是 `<p>`。

有用在兩件事上：它逼我去分辨 `getTextSelection`（barrier 自己選的）和
`getA11yFocusedParagraph()`（閘門在比的）**是兩個不同的問題**，而 barrier 裡沒有任何東西
把它們綁在一起；也讓第二份預測（指紋那一半）在寫下來的時候就已經是可否證的。

## 沒有量的（因此不指認）

- **為什麼臂 1 過而臂 2 不過。**現在知道臂 2 打的是一顆**有大綱編號**的標題（074 的閘門
  `nLevel >= 0 && bIsCounted` 過得了），而臂 1 用 `.uno:StyleApply` 新做出來的標題
  在那一輪讀回 `listPrefixLength: 0`——**為什麼新做的標題沒有編號**沒有量。
- **`declined: ""` 的第三種讀法。**v10 上僅存的那次 barrier 失敗停在 stage deadline，
  在閘門之前，所以 `paragraphIdentityDeclined` 從沒被指派，`checked: false` 旁邊是空字串。
  空字串要靠 `checked` 才讀得懂；下一次連結應該讓它自己把話說完。
- **074 本身。**上游的 `getListPrefixSize()` 一行未動。這個修法只是讓引擎**不再相信**
  那個數字；數字仍然是錯的，而每一個讀 `listPrefixLength` 的取用端仍然暴露。

## 同一輪裡的第二種 barrier 失敗（不同缺陷，記在這裡是因為它在同一份報告裡）

`bulleting-a-blank-line-does-not-demand-a-rollback` 在同一輪、更早的地方 FAIL，
failureShape 是 **`stage-deadline:awaiting-selection`**（2026-08-23 就記過 stage-deadline，
但沒有這個子階段），`paragraphIdentity: {checked: false, dispatchKnown: true,
readbackKnown: false}`——**那一次閘門沒有跑**，讀回那一側根本沒有答案。
它同樣把 session 推進 `recoverable-error`，但緊接著的回復臂按了通知、session 回到 ready。

所以 a11y core 一輪會產生**兩種不同的 barrier 失敗**，兩種都是 session 終結級的；
第一種有人救，第二種沒有。

## 證據

- `findings/evidence/082/RESULT.md` —— 成因、修法與量測，對著兩份預測逐條核。
- `findings/evidence/082/PREDICTION-which-paragraph-was-read.md`（**被否證**，原樣保留）
  與 `PREDICTION-2-why-the-two-fingerprints-differ.md`（成立）。
- `findings/evidence/082/product-path-v9-engine-payload.json` —— 加寬投影之後的整包
  barrier 物件；`product-path-v9-paragraph-trace.json` —— 66 筆逐次狀態的段落讀數。
- `findings/evidence/082/product-path-v10-round-1.json` —— 修法之後的產品路徑。
- `handoff/RUNBOOK-relink-v10-a11y-identity.md` —— 連結清單與**寫在跑之前**的預測。
- `findings/evidence/queue-a11y-path-drives-a-dead-session/product-path-e2-editor-v9-chrome-guard-stopped-it.json`
  （第一輪）與 `RESULT-the-guard-fired-unprompted.md`
- `findings/evidence/082/`：四輪的 v9 報告與 step 軌跡。第 1 輪**沒有** payload
  （`--barrier-details-diagnostic` 是看到第 1 輪之後才寫的），第 2–4 輪有——
  所以「四輪一致」講的是 step 軌跡、死亡現場與逐臂結果，型別化 payload 是 3/3。
- 對照：`findings/evidence/075/pp-v5-product.json`（同一支臂在 075 修好之前全部棄權）

## 修訂紀錄

- 2026-08-26：建檔。四輪四中；barrier 的型別化 payload 首次被收下來，確立這不是
  fail-open、不是讀失敗、不是 multi-block，而且 containment 成立。成因未確立。
- 2026-08-26（同日，收尾）：**成因確立、已修、修法量到生效。**第一個假說（還原點幾何
  過期）被 `readback.html` 否證；真正的成因是閘門比到了一個「空字串的雜湊」——
  finding 074 讓那顆標題的 `listPrefixLength == contentLength`。修法是**指紋退化時閘門
  放棄比對**，規則與雜湊放在 `src/a11y_paragraph_identity.hpp`、由主機測試驅動並重現
  引擎報過的六個指紋。連結成 `e2-editor-v10`（對 v9 單一變因），產品路徑 40 格全跑、
  那一格六支臂全過、`readback-is-a-different-paragraph` 一次都沒有。
  標題與狀態列同步改寫。
