# 結構 demo 的「復原」：判準是存出來的檔案，不是按鈕有沒有反應

**日期**：2026-08-15　**引擎**：`c89f069e…`（`e2-format-discovery`，**未重連結**——
`make -n demo-structure-assets` 只印兩行 `cp`，跑完前後 `probe.wasm` 的 sha256 都是
`c89f069e…`）
**瀏覽器**：Chromium（Playwright）　**fixture**：`dist/e1-fixtures/list-contexts.odt`
**頁面**：`web/demo-structure.html`（任務 #50 新增的「↶ 復原」鈕）

十五個步驟一次跑完，全部經由 demo 自己的 UI，逐步的延遲與修訂號在
[`step-log.json`](step-log.json)。

## 判定：**過**。六份檔案、兩個正對照

| 檔案 | 該長什麼樣 | 實際 |
|---|---|---|
| `00-pristine.odt` | 基準 | — |
| `01-after-heading.odt` | **與基準不同**（正對照） | `E1-LC-ISOLATED` 由 `Standard` 變 `Heading_20_1` |
| `02-after-undo.odt` | 與基準相同 | **body 逐位元組相同** |
| `03-after-list-none.odt` | **與基準不同**（正對照） | `E1-LC-BULLET-TWO` 的 `text:list-item` 外殼被拆掉，段落變 `Standard` |
| `04-after-undo.odt` | 與基準相同 | **body 逐位元組相同** |
| `05-after-two-extra-undos.odt` | 與基準相同 | **body 逐位元組相同**；已經沒有東西可復原時多按兩次，**不會往前吃掉別的東西** |

重跑：`python3 check.py`（回非零就是不符）。

**復原的延遲**：82／72／70／10 ms。**多按的那兩次也乾淨返回**，之後
「點一下段落定位游標」仍然正常（253 ms），工具列所有按鈕維持可用，狀態列回到「就緒」。

## 兩件會讓人讀錯的事

**一、不要拿整份檔案的 sha256 當判準。** 復原成功時 body 相同，但 zip 有時間戳、
`meta.xml` 有編輯週期計數，所以**整份檔案的 hash 一定不同**。本目錄的 `SHA256SUMS`
是這六份檔案的出處證明，**不是**判準；判準是 `content.xml` 的 `<office:body>`。

**二、第一版的比對沒有鑑別力，而且是被正對照抓到的。**
初版摘要器用錯 XML namespace 去讀 `text:style-name`，於是每一段都讀成 `None`，
結果「復原後 == 原始」通過了——**但「按標題後 == 原始」也通過了**，那不可能。
[同目錄的 2026-08-13 那一輪](../demo-structure/README.md)踩過同一類的坑（比對太粗），
這一次的成因不同（欄位根本沒讀到），症狀一樣：**分不出「有沒有生效」的比對不是弱的比對，是不能用的比對。**
`check.py` 因此把兩個「必須不同」的正對照寫死在同一支檢查裡，
並用「把 `02` 換成 `01`」的變異確認過它會紅（exit 1，只點名被換掉的那一列）。

## 復原走的是哪一條路，以及為什麼

按鈕呼叫的是 **Document SDK 的 `document_.undo()`**，也就是出貨編輯器 `demo-editor`
的「復原」呼叫的同一支——**不是**診斷 ABI 自己的 undo 動作。
後者在 `e2/demo-structure-client.js` 的 `FORBIDDEN` 裡被具名擋掉，理由寫在那裡：
它不是 E1 驗過的路徑。**大家犯錯之後最常按的那顆按鈕，是最不該接沒量過的路徑的地方。**

## 這一輪不涵蓋

- **只有 Chromium 一輪、一份 fixture、兩種動作**（段落樣式與清單各一）。這是 demo 的
  可用性證據，**不是** A3／A4／A5 那種矩陣判定。
- **沒有涵蓋「格式動作之後做範圍選取」**——那是縮限 4，仍然壞著（任務 #49）。
  這一輪的定位一律走 `click` ＋ 輪詢，也就是產品 shell 的路徑。
- **沒有量「復原之後工具列的粗體／斜體狀態對不對」**：路線 C 本來就不讀前置格式狀態
  （finding 021、縮限 6），這顆按鈕做的是把 `intent` 帳清成 null，與 `applyStructure` 一致。
