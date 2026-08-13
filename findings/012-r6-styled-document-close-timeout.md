# 012 — R5 writer-review 對 t2 styled image frame 的 paragraph wrapper close 不回應

| | |
|---|---|
| **狀態** | 歸因完成：same-commit native正常、WASM停在document destroy；下一步`wasm-fix`，R7 STOP |
| **Bugzilla** | — |
| **發現日** | 2026-08-02 |
| **嚴重度** | 嚴重 |
| **可重現** | 100%（內容軸與diagnostic destroy stage跨瀏覽器一致；180秒邊界確認一致） |
| **是否上游** | 未確認 |

## 現象

以 R5 `writer-review` 開啟 `t2-styled.odt`，公開 `DocumentHandle.close()` 不回應。R6 最初在相鄰／部分越界
render、三筆 render queue（其中一筆 queued cancel）及搜尋後重現；R7-D 已進一步證明只做
`open → close` 也會在 Chrome／Firefox 的完整 180 秒上限 timeout。相同 artifact 的 t1、t3 與 R7 100頁
stress ODT lifecycle 可正常 close。

## 重現步驟

1. 執行 `make -C wasm_sdk_probe r6-discovery-assets`。
2. 執行 `python3 tools/run_r7_longevity.py --browser chrome --scenario s5-normal --s5-variant open`，Firefox 同理。
3. 等待 public close response；未提供縮短 timeout 時使用凍結的 180 秒上限。

**預期**：close 完成並使 handle 進入 closed。  
**實際**：180 秒後得到 `TIMEOUT`；Worker 未回 `closed` event。

## 證據

- `evidence/sdk-r6/discovery/chrome.json`：第一次，完整矩陣中 30 秒 timeout。
- `evidence/sdk-r6/discovery/chrome-t2-styled.json`：第二次，單 fixture 180 秒 timeout。
- `evidence/sdk-r6/discovery/chrome-t2-styled.log.txt`
- `evidence/sdk-r6/discovery/chrome-t2-styled.png`
- `evidence/sdk-r7/longevity/finding-012-audit/summary.json`：R7 跨瀏覽器最小化摘要。
- `evidence/sdk-r7/longevity-smoke/s5-minimize-open-180s/chrome/s5-normal/run-1/result.json`：Chrome 176 筆
  process sample與完整 lifecycle。
- `evidence/sdk-r7/longevity-smoke/s5-minimize-open-180s/firefox/s5-normal/run-1/result.json`：Firefox 176 筆
  process sample與完整 lifecycle。
- `evidence/012/r7-minimization/summary.json`：16組 feature matrix、跨瀏覽器邊界確認與machine判定。
- `evidence/012/r7-minimization/classify/`：Chrome／Firefox各16份10秒分類raw result、log、screenshot與process
  samples。
- `evidence/012/r7-image-axis/summary.json`：9組image-object屬性／結構軸、跨瀏覽器邊界確認與machine判定。
- `evidence/012/r7-image-axis/classify/`：Chrome／Firefox各9份10秒分類證據。
- `evidence/012/r7-image-axis/confirm/`：`t2-image-unwrapped`各3次成功與byte-identical原始t2各1次180秒timeout。
- `evidence/012/r7-minimization/confirm/`：無image邊界每browser 3次成功與原始含image邊界各1次180秒timeout。
- `evidence/012/r7-attribution/summary.json`：native LOK對照、diagnostic WASM destroy stage與machine歸因判定。
- `evidence/012/r7-attribution/native/`：系統LibreOffice 26.2.4原始／unwrapped各3次native LOK結果。
- `evidence/012/r7-attribution/wasm/`：Chrome／Firefox的短測、成功控制與180秒diagnostic確認。
- `evidence/012/native-26-8-attribution/summary.json`：same-commit native 26.8與既有WASM證據的最終歸因判定。
- `evidence/012/native-26-8-attribution/native/`：原始t2／unwrapped各3次same-commit native結果。
- `evidence/012/native-26-8-attribution/native-sandbox-failed/`：受限環境造成共同post-complete失敗的保留證據。
- `evidence/012/native-26-8-attribution/configure.log`與`build.log`：隔離native build完整歷程。

## 分析

### 已觀察

- open、tile render 與 queued cancel 都有 public response；cancel-result 是 `OK`。
- t2 的 `close` 沒有 response，且 180 秒上限仍會逾時。
- t1 在相同流程（另含 mutation）可正常 close。
- R7-D Chrome 150 與 Firefox 153.0.1 只執行 `open → close`，兩端都在 180,000 ms 得到公開
  `SdkTimeoutError/TIMEOUT`；文件 handle 未完成 close。
- timeout 後 harness 明確記錄 `closed=0`，再由 `engine.dispose()` 終止 Worker；強制終止沒有被計為成功 close。
- Chrome 的 open 約 523 ms、Firefox約 351 ms，因此問題發生在 close 階段，不是 open timeout。
- 以ODF package XML直接建立table／image／annotation／page-break完整2⁴=16種組合；所有ZIP CRC／XML與desktop
  LibreOffice PDF驗證通過，原始組合保持byte-identical。產生器未使用UNO。
- Chrome／Firefox分類完全一致：8個含image組合全部在10秒timeout；8個不含image組合全部正常close。
- 最大無image組合仍保留table、annotation、3頁page break：Chrome close 18.55～22.81 ms、Firefox
  7.54～8.08 ms，各3/3。只加入原始embedded 640×360 RGB PNG後，Chrome 180000.42 ms、Firefox
  180005.28 ms timeout，handle未close並需明確終止Worker。
- **反例**：L4 100頁stress ODT嵌入完全相同PNG（SHA `f2e18c7c…f57f`），同樣使用`as-char`、onLoad與package
  relationship，且R7-D S1可正常render/save/close。因此「任意embedded PNG」或PNG bytes本身不是充分條件。
- 第二階段建立9份image-axis ODT，逐一控制`draw:mime-type`、style reference、name/z-index、clip、全部
  graphic properties、paragraph wrapper與L4 geometry/frame形狀；9/9通過ZIP/XML、feature assertion與desktop PDF。
- Chrome／Firefox 10秒分類逐項一致：只有移除image frame直接外層`text:p`的`t2-image-unwrapped`正常close；
  原始t2與其餘7個單軸變體全部timeout。所有變體保留相同PNG SHA。
- 完整邊界確認：`t2-image-unwrapped`在Chrome 3/3 close 18.22～20.80 ms、Firefox 3/3 close
  6.60～9.74 ms；byte-identical t2在Chrome 180000.41 ms、Firefox 180000.90 ms仍timeout。
- 系統native LibreOfficeKit 26.2.4對原始t2與unwrapped各3/3均正常進入並離開document destroy；完整程序
  約243～269 ms。此結果只代表不同版本的native反例。
- 隔離diagnostic WASM使用相同core commit與linkdeps，只在document destroy前後發出stage；未覆蓋R5 artifact。
  Chrome／Firefox原始t2短測與180秒確認都只見`document-destroy-enter`，沒有return；unwrapped各3/3同時
  具有enter與return並正常close。
- 隔離same-commit native build版本為`LibreOffice 26.8.0.1.0 671c848…`；原始t2與unwrapped各3/3均出現
  `document-destroy-enter`、`document-destroy-return`與`complete`，正常結束。
- 第一輪same-commit native runner在受限環境中，兩份文件都已完整return／complete後遭共同環境限制影響；
  該失敗已獨立保存。相同binary與fixtures在可用環境重跑後6/6正常，未把受限結果當文件差異。
- R5 large artifact 未改變。

### 推論

- 觸發條件不需要 render、search、comments 或 queued cancel；diagnostic stage證明SDK Worker與engine queue已
  派送close，停點位於同步`LibreOfficeKitDocument::destroy()`呼叫內或其下層，不是等待中的Worker response。
- 第一階段的`image`是t2 feature軸分類，不代表任意embedded image都失敗；第二階段已排除PNG bytes、
  `draw:mime-type`、style reference、name/z-index、clip、graphic properties與geometry各自為充分條件。
- 目前最小的公開可觀察邊界是「image frame作為`text:p`直接子節點」：移除該wrapper即正常close。這可能是
  wrapper本身或其與image／anchor teardown的交互作用。
- system native 26.2與same-commit native 26.8都不重現，而同commit WASM跨瀏覽器重現；因此版本差異與
  Worker queue皆已排除，最終候選層級是Emscripten組態／runtime特定的document teardown。
- R6 v1 可使用規格允許的既有多頁 `t3-long.odt` 驗證 viewport，無須把 t2 當成功門檻。

### 待驗證

1. ~~分解t2 image object的style、clip、mime、name/z-index、wrapper與geometry軸。~~ 第二階段已完成。
2. ~~以系統native LibreOfficeKit對原始／unwrapped做版本範圍內對照。~~ 26.2.4各3/3正常，不重現。
3. ~~在`destroy()`前後增加隔離diagnostic stage。~~ 已確認跨瀏覽器皆進入destroy但原始t2不返回。
4. ~~建立same-commit 26.8 native LOK build／測試。~~ 原始／unwrapped各3/3正常，最終路由為`wasm-fix`。
5. ~~Firefox 是否相同。~~ R7-D 已重現。
6. ~~t3 多頁 fixture 是否正常 close。~~ 已由 Chrome／Firefox discovery 與 R6-A／R6-C 重複驗證正常。
7. ~~R7 remediation。~~ SDK已加入10秒bounded close recovery：native document destroy timeout時終止該
   Worker、建立新generation並讓engine可重用；原始t2在Chrome／Firefox各3/3完成SDK close recovery。
   這修復產品生命週期，但不宣稱Emscripten document teardown本身已返回。

本輪不以 `Worker.terminate()` 取代成功 close；若 R6 正式 corpus 的 t1／t3 也重現，需重新評估
R6-A lifecycle gate。

## 2026-08-12：在另一份 fixture、另一個引擎上重現，且旁邊出現同軸的第二個 hang

E2-A 的 `paragraph-content` fixture（**獨立寫的、與 t2 無關**）在
`wasm_sdk_probe/tools/create_e1_corpus.py` 裡自帶一張**手寫的 1×1 PNG**，
以 `draw:frame` `text:anchor-type="as-char"` 掛在 `text:p` 底下——就是本單第二階段
最小化出來的那個軸。

**16/16 次 close 都要走 SDK 的 10 秒 bounded recovery**（`document-close-recovery-complete`），
其他每一份 E2 fixture 都是 6–25 ms、零次 recovery：

| fixture | 輪數 | recovery | closeMs |
|---|---|---|---|
| empty-paragraph | 3 | 0 | 10–11 |
| multi-paragraph | 45 | 0 | 6–17 |
| plain-grapheme | 42 | 0 | 6–25 |
| styled-list | 51 | 0 | 6–18 |
| table-boundary | 12 | 0 | 8–16 |
| **paragraph-content** | **16** | **16** | **10782–11622** |

這批補上了本單原本沒有的東西：**t2 那張圖片的任何屬性都不是必要條件**。
新 fixture 的圖片是另外做的、內容不同、樣式不同，唯一相同的是那個 wrapper 形狀。
引擎也換過兩代（`ee185b3d`、`c89f069e`），行為不變。

**旁邊還有一個同軸的 hang**：
[037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md) 量到
`getTextSelection(…, "text/html", …)` 在**含同一種 frame 的選取**上不返回，
原生同一個呼叫 1 ms 回傳 798 bytes。兩單的形狀一模一樣——
**WASM 特有、原生正常、觸發點是同一個內容特徵，只是進入點不同**（一個是 `destroy()`，
一個是選取序列化）。這是推論不是證明：兩處都沒有堆疊，也沒有人證明它們共用同一段程式碼。
但要找 `wasm-fix` 的人應該先看這一點——**兩個獨立入口在同一個內容特徵上停住，
比一個入口更能指出是共用的下層**。

**2026-08-12 補**：那個「同一個內容特徵」現在兩邊都獨立量到是 **frame 而不是 image**
（本單見下一節；037 見它的〈擋法涵蓋範圍〉），所以這條推論比初寫時強——
但**仍然是推論**，兩處都沒有堆疊。

### 2026-08-12：卡的是 frame，不是 image——已量

第一階段的 2⁴ matrix 把「image」當成一個特徵在開關，而 **ODF 裡 `draw:image` 只能長在
`draw:frame` 裡面**，所以那條軸從來是「整個 image frame」；第二階段自己也把候選寫成
`frame.wrapper`。**沒有試過的是「有 frame 但裡面沒有 image」。**

新 fixture `frame-no-image`：三段文字，中間那段帶一個 as-char `draw:frame`，
裡面只有 `draw:text-box`。**整份文件沒有任何圖片**——沒有 `Pictures/` 成員、
`draw:image` 出現 0 次、manifest 只有兩個 XML 部件。系統 LibreOffice 正常開啟並轉出 PDF。

**WASM：`closeMs` 10829，走 `document-close-recovery-complete`。**

對照乾淨：六份**完全沒有 `draw:frame`** 的 fixture 共 153 輪，closeMs 6–25 ms、零次 recovery；
三份**有 frame** 的（`paragraph-content` 1 個、`image-variants` 7 個、`frame-no-image` 1 個）
每一輪都要 recovery。

**所以 image 不是必要條件，frame 才是。** 本單第一階段的 `image` 只是比較粗的名字，
第二階段的 `frame.wrapper` 才是對的，而且現在有正面證據而不只是「移掉 wrapper 就好了」。

### 再一刀：錨定方式，一個屬性的邊界

`frame-paragraph-anchored` 與 `frame-no-image` **只差一個屬性**——
`text:anchor-type` 由 `as-char` 換成 `paragraph`，其餘逐字相同（同樣三段、同樣的
`draw:text-box`、同樣沒有圖片）：

| fixture | 錨定 | 選取型別 | closeMs | recovery |
|---|---|---|---|---|
| `frame-no-image` | **`as-char`** | **complex** | **10829** | **要** |
| `frame-paragraph-anchored` | `paragraph` | `text` | **11** | 不用 |

**所以觸發條件是「as-char 錨定的 frame」，不是任何 frame。** 這是目前為止最窄的一刀：
一個屬性、兩個答案、其餘全部相同。

而且**兩單的觸發條件在同一個屬性上重合**：037 那邊的選取型別也正好在 as-char 是 `complex`、
在 paragraph 是 `text`。「兩個入口共用下層」的推論因此又強一階——**仍然是推論**，
兩處都還沒有堆疊。

**`char` 錨定已補量，而且它把兩件事拆開了**：`frame-char-anchored`
（與 `frame-no-image` 只差 `text:anchor-type`）的 **`closeMs` 12 ms、零 recovery**，
但它的選取型別**是 `complex`**。

| 錨定 | 選取型別 | close |
|---|---|---|
| `as-char` | `complex` | **卡（10829 ms ＋ 重啟 worker）** |
| `char` | `complex` | 正常（12 ms） |
| `paragraph` | `text` | 正常（11 ms） |

**「選取型別是 COMPLEX」與「close 會卡」不是同一件事**：`char` 兩者只中一個。
本單的觸發條件因此收窄到 **`as-char`**，而 037 的擋法判準（非 `TEXT` 即拒絕）
比它寬——那是保守，不是錯，但代價要記在 037 那邊。

## 2026-08-13 再一刀：frame 要**在段落裡**，屬性本身不算（證據 `sdk-e1/checkpoint-cost/`）

量存檔成本那一輪順帶收到六份文件的 close 時間，而它們分成清楚的兩群：

| 文件 | as-char frame（屬性） | **在段落裡的** | closeMs |
|---|---|---|---|
| `frame-contexts` | 2 | **2** | **10848（走 recovery）** |
| `l0-t2-styled` | 1 | **1** | **10777（走 recovery）** |
| **`l4-stress-100`** | **100** | **0** | **4** |
| `l0-t1-plain-zh`／`l0-t3-long`／`l1-review` | 0 | 0 | 4／4／7 |

**`l4-stress-100` 有一百個帶 `text:anchor-type="as-char"` 的 `draw:frame`，close 只要 4 ms。**
差別在它們**直接掛在 `office:text` 底下，不在任何段落裡**——as-char 是「文字流裡的一個位置」，
在那裡沒有意義，core 顯然也是這樣處理的。

**所以觸發條件是「段落裡的 as-char frame」，不是「檔案裡有 as-char 屬性」。**
這比先前那一刀更窄，而且是 **100 比 1 的樣本數對上兩個相反的行為**——
先前所有「這份文件有 as-char frame 所以會卡」的推理，都要先確認那個 frame 在段落裡。

**同一批數字也修掉了我自己的盤點工具**：`tools/inventory_corpus_axes.py` 初版只數屬性，
於是 SPEC-E1-C 9.1 的「C3 語料有 101 個 as-char frame」在行為上其實是 **1 個**
（`l0-t2-styled` 那一個）。工具已加 `frame-as-char-in-paragraph`／`-body-level` 兩軸，
9.1 已就地更正。

## 環境

- Core commit：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- writer-review WASM：`ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6`
- Chrome：`150.0.7871.128`
- Firefox：`153.0.1`
- Native control：`LibreOffice 26.2.4.2 620(Build:2)`
- Same-commit native：`LibreOffice 26.8.0.1.0 671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- Fixture SHA-256：`0f69906035cb5d96f86b034cf2596994d5de82ee6347a47c00f35784c9888d31`

## 還缺什麼才能送

- [x] 最小化是哪一項內容特徵觸發（t2 image frame 的直接 paragraph wrapper／交互作用）
- [x] Firefox 重現狀態
- [x] 排除SDK Worker／engine queue未派送；確認停在WASM LOK document destroy呼叫內或其下層
- [x] 使用系統native LOK 26.2.4對照；原始／unwrapped各3/3正常
- [x] 以same-commit native LOK區分；原始／unwrapped各3/3正常，路由至Emscripten特定修復
- [ ] 完成`wasm-fix`並使原始t2 public close跨瀏覽器正常返回
- [x] 規格必要 t1／t3 corpus 正常 close，未擴散為 R6 lifecycle gate

## 時間軸

- 2026-08-02：完整 discovery 首次在 30 秒 close timeout。
- 2026-08-02：單 t2 fixture 以 180 秒上限再次重現；建立 finding。
- 2026-08-02：t1／t3 在 Chrome／Firefox reader 與雙 context reference app 正常；R6 GO，t2 問題保留待最小化。
- 2026-08-03：R7-D 六個 10 秒區分測試全部 timeout；Chrome 純 open→close 在完整 180 秒再次 timeout。
- 2026-08-03：Firefox 純 open→close 同樣在完整 180 秒 timeout；finding 升級為跨瀏覽器 R7 STOP 阻礙。
- 2026-08-03：2⁴ feature matrix跨瀏覽器32/32完成；image presence與timeout形成完全分界。
- 2026-08-03：最大無image邊界Chrome／Firefox各3/3 close，加入image後各1/1完整180秒timeout；第一階段
  machine decision為`MINIMIZED`，候選trigger feature為`image`。
- 2026-08-03：確認L4使用相同PNG與基本relationship仍可close；下一階段焦點縮為t2 styled image屬性，
  不把結論誤寫成所有embedded image都失敗。
- 2026-08-03：9組image-axis跨瀏覽器分類完成；只有移除frame直接`text:p` wrapper會恢復close。
- 2026-08-03：unwrapped邊界Chrome／Firefox各3/3成功，byte-identical原始t2各1/1完整180秒timeout；第二階段
  machine decision為`MINIMIZED`，候選trigger axis為`frame.wrapper`，R7 STOP不變。
- 2026-08-03：系統native LOK 26.2.4原始／unwrapped各3/3正常；不同版本native未重現。
- 2026-08-03：隔離diagnostic WASM跨瀏覽器均證明原始t2進入document destroy但不返回，unwrapped各3/3
  正常返回；machine decision為`DOCUMENT_DESTROY_BOUNDARY_CONFIRMED`，Worker queue排除，R7 STOP不變。
- 2026-08-03：same-commit native 26.8原始／unwrapped各3/3正常；最終machine decision為
  `EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY`、next action為`wasm-fix`。Finding歸因階段結束，R7待修復仍STOP。
- 2026-08-04：R7 remediation以bounded Worker recycle完成；原始t2 Chrome／Firefox各3/3 close recovery，
  Worker與handle歸零且engine可再開文件。Finding 012不再阻斷normal／known S5；底層destroy root cause仍保留。
- 2026-08-12：**觸發條件收窄為「as-char 錨定的 frame」**，兩刀。第一刀 frame vs image：`frame-no-image`（三段文字＋一個只裝
  `draw:text-box` 的 as-char frame，**全檔零張圖片**）在 WASM 一樣 `closeMs` 10829 走 recovery；
  六份完全沒有 `draw:frame` 的 fixture 共 153 輪 6–25 ms、零次 recovery。
  第一階段的 `image` 軸其實是「整個 image frame」（`draw:image` 只能長在 `draw:frame` 裡），
  第二階段的 `frame.wrapper` 才是對的名字。第二刀錨定方式：`frame-paragraph-anchored`
  與前者**只差一個 `text:anchor-type` 屬性**，`closeMs` **11 ms、零 recovery**
  ——**as-char 是必要的**。兩單的觸發條件在同一個屬性上重合（037 的選取型別同樣在
  as-char 是 complex、paragraph 是 text）。**未量 `char` 錨定的 close。**
- 2026-08-12：E2-A 的 `paragraph-content`（另一份 fixture、另一張圖、另外兩代引擎）
  **16/16 走 close recovery**，其餘五份 fixture 共 153 輪零次；`frame.wrapper` 軸因此
  不再依賴 t2 的任何屬性。同日 [037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md)
  在同一個內容特徵上量到第二個 WASM 特有的 hang（`getTextSelection("text/html")` 不返回，
  原生 1 ms），兩個入口指向同一個下層是**推論**，兩處都還沒有堆疊。
