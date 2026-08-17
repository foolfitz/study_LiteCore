# SPEC-P — 短期產品目標：一個可以讀檔、能基本編輯的編輯器

> 2026-08-17 使用者裁示的短期目標。a11y／block identity 移到長期。
>
> **這一頁不是驗收條件本身。** 驗收條件是
> [`wasm_sdk_probe/e2/usable-editor-checklist.json`](../wasm_sdk_probe/e2/usable-editor-checklist.json)，
> 由 `tools/check_usable_editor.py` 執行。這一頁只說明它為什麼長這樣、怎麼讀。

## 1. 為什麼是資料不是散文

被問到「短期目標感覺零碎」的時候，直覺的回應是寫一頁散文清單。**那是錯的回應**，
理由這棵樹已經付過學費：散文清單在程式碼移動的那一刻就過期，而且沒有人會發現——
finding 044 就是判定發布一天之後，判定綁定的 `summary.json` 還寫著「沒有判定」。

所以清單是**資料**，而且每一格都必須指到一個真的存在的東西：

| 種類 | 指到哪裡 |
|---|---|
| `check` | `tools/run_e2_c_product_path.py` 裡的檢查 id |
| `queue` | `e2/relink-queue-v3.json` 的項目 id |
| `finding` | `findings/` 底下的編號 |

`check_usable_editor.py` 逐一解析，指不到就是紅的。**一份不會紅的清單不是清單**——
這是 `probe-measurement-discipline` 那條紀律套用到產品定義上。

自測七格，含三個反向對照（每一種 evidence 各一個指到不存在的東西）、一個沒有
evidence 的列、一個不在字彙內的 status。

## 2. 為什麼以「使用者做得到什麼」為單位

因為**產品介面從來沒有被設計過，它是從「驗證需要哪十五個動作可達」長出來的**。

證據就在工具列上：它有「游標左移」和「游標右移」**按鈕**。沒有任何使用者需要那種
東西；它們存在，是因為契約需要那十五個動作在頁面上可達。

這一點是外部審查（fable，2026-08-17）指出來的，而且它推翻了我原本的診斷。我本來
以為零碎的原因是「沒有清單」；真正的原因深一層——**照現有頁面反推出來的清單，會把
那個累積物固化成規格**。所以清單的每一列是一句使用者說得出口的話，不是動作 id。

## 3. 狀態字彙

| | 意思 |
|---|---|
| `done` | 有一格**會失敗**的檢查在跑，而且它是綠的 |
| `unverified` | 產品裡有，但沒有任何檢查驅動它 |
| `missing` | 使用者做不到 |
| `blocked` | 要一次 relink 才做得到 |

`unverified` 不是小事。這棵樹被「按鈕在、沒有人按過」咬過**五次**——
049、050、Ctrl+C、058（畫面沒人看過）、059（修法出貨之後沒人按過那顆按鈕）。

## 4. 「做完」的定義

三件事同時成立：

1. `check_usable_editor.py` 綠（每一格都指得到東西）；
2. 每一個 `done` 列所指的檢查，在 `run_e2_c_product_path.py` 裡是綠的；
3. 沒有 `blocked` 列——也就是它們指的佇列項都已經隨某一次 relink 出貨。

**今天三件都不成立**，而且第 2 件現在有一格是**刻意紅著**的：
`bold-can-be-turned-off-again`（finding 059）。它登記在 runner 的 `KNOWN_RED` 裡，
連同 finding 編號；一旦它變綠，runner 會**主動報告這個宣告過期**，所以宣告活不過
缺陷本身。

## 5. 這份清單不涵蓋什麼

- **契約與驗證範圍**仍然是 [SPEC E2-C](./SPEC-E2-C-paragraph-format-validation.md) §4。
  兩者不是同一件事，而且 §4 明文排除 Redo 與 line up/down——那是**契約**的話，
  這一頁是**產品**的話。清單裡把它們標成 `blocked` 並指向佇列。
- **link-class 的工作不另立佇列。** 需要 relink 的項目一律寫進
  `e2/relink-queue-v3.json`，清單只引用。在旁邊再開一份就是把被診斷的零碎複製一次。

## 修訂紀錄

- 2026-08-17 建立。同日 058（畫游標）轉 `done`、059 掉出來使
  `turn-formatting-off` 轉 `blocked`。
