# DEVLOG 2026-08-15 — E2-C 開場：manifest 承諾了十五個動作，殼層到得了五個

接續 [`HANDOFF-2026-08-15e`](../handoff/HANDOFF-2026-08-15e-e2b-go.md)。
那份交接說下一步是「E2-C：規格還沒寫」。寫規格之前先照
memory 那條規矩重讀自己的樹，**在讀的過程裡撞到一件沒有人量過的事**。

## 撞到什麼

出貨的 v2 profile `e2-editor-v2`（artifact `572035ac…`）的 manifest 宣告
**十五個動作**，worker 的 `editorActionV2` 也吃十五個
（`EDITOR_V2_ACTION_IDS` 展開 v1 的十個再加五個）。但是：

| profile | 殼層 | 十個 v1 動作到得了幾個 | 擋在哪 |
|---|---|---|---|
| `e2-editor-v2` | `editor-shell/editor-client.js` | **0／10** | `UNSUPPORTED_OPERATION`——它要求 capability `narrow-editor-v1` **且** `editorContract.version === 1`，v2 兩個都不是 |
| `e2-editor-v2` | `editor-shell-v2/paragraph-editor-client.js` | **0／10** | `EDITOR_ACTION_UNSUPPORTED`——allowlist 只有五個段落動作 |
| `e1-editor-v1` | `editor-shell/editor-client.js` | **10／10** | —（對照組） |

**引擎與協定是完整的，洞在殼層。** 也就是說：出貨的 manifest 承諾了一個
沒有任何 host 用得到的 surface。

## 為什麼既有的檢查看不到

E2-B 第 5 節第 7 項的四路清單檢查（`check_e2_b_inventory.py`）問的是
「header／manifest／worker／client 有沒有指同一組動作」。它的 client 那一份是
**兩個殼層的聯集**，聯集確實是十五個——只是聯集裡有一個殼層**接不上這顆
profile**。

> **「四份清單一致」與「host 真的做得到這十五件事」是兩個宣稱，
> 過去只檢查過第一個。**

這不是那個檢查壞了，它做的事沒有錯。是 E2-B 9.10 的表格那一列被我讀得太寬。
已就地補記（E2-B v13），**判定不變**——E2-B 的範圍是那五個段落動作，
它們確實跑過 132 個 run。

## 處置

新的 `editor-shell-v2/narrow-editor-v2-client.js`，十五個動作。否決的另外兩條：

- **改 `editor-shell/editor-client.js` 讓它接受 v2**：那個檔案由 E1-C 的
  bundle `f9b1a52f…` 逐檔 hash 綁定，改它就解除 `E1_GO_ODT_EDITOR`。
- **從 manifest 砍掉那十個**：要重跑 builder → 新 hash → E2-B 的 132 個 run
  與 12 列全部斷綁。**讓殼層追上承諾，比讓承諾縮回去便宜一個數量級**，
  而且不丟掉已經量到的東西。
- （**出兩顆 profile**：一份文件只能開在一個引擎裡，不成立。）

五個段落動作**委派**給 `ParagraphEditorClient`，不重寫——路線 C 的
`changed: null` ＋ `verified-format-readback` 規則只有一份。
十個 v1 動作在新檔案裡自己驗。

## 兩份複本要怎麼才不會漂

十個動作的驗證規則現在有兩份（v1 那份是 hash 綁定的，動不得）。
**比對原始碼沒有用**——規則可以被改寫、重排、只套一半，看起來仍然很像。
所以比對的是**行為**：

同一個呼叫、同一個引擎回覆，兩個客戶端各跑一次，判決必須逐格相同。
**1 600 格**（10 個動作 × 10 種呼叫參數 × 16 種引擎回覆），
其中 **84 格接受**、364 格 `EDITOR_RESULT_INVALID`、1 152 格 `INVALID_ARGUMENT`，
**兩邊 1 600 格全等**。

回覆的突變清單裡有一格是具名的：`documented-state-noop`。
那是 finding 022 從 stale cache 產出的 completion，兩側都移除過，
所以它必須在兩邊**都**被拒絕。

矩陣自帶兩個守衛：

1. `accepted > 0`——否則「兩邊一致」可能只是兩邊都拒絕全部；
2. 一個把 `_validateInherited` 拿掉的子類別，**必須**讓判決出現差異
   ——否則這個比對證明不了任何事。

## 這一輪的紅先於綠

可達性測試
（`editor-shell-v2/tests/manifest-reachability.test.mjs`）
是**先寫的，而且寫出來就是紅的**，紅的內容逐字是上表第一、二列；
兩個對照組（v1 殼層在 v1 profile 上十個全到／沒宣告過的動作誰都到不了）
當時就是綠的。實作之後才轉綠。

順帶記一個自己的錯：對照組第一版是紅的，因為我的 stub 回了
`{reached: true}` 這種不成形的結果，被殼層的後置條件檢查擋掉——
**「到得了引擎」和「stub 的回覆能通過驗證」是兩件事，混在一起會讓
關著的閘門和寫壞的 stub 長得一模一樣**。stub 改成記錄「請求有沒有離開殼層」。

## 產出

- `specs/SPEC-E2-C-paragraph-format-validation.md` v1（草擬，未執行）
- `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js`／`.d.ts`
- `wasm_sdk_probe/editor-shell-v2/tests/manifest-reachability.test.mjs`
- `wasm_sdk_probe/editor-shell-v2/tests/narrow-editor-v2-client.test.mjs`
- `make test-e2-c-static`（無前置目標——E2-C 的範圍是殼層、runner、判定工具，
  任何需要重連結的改動都不是 E2-C 的）

**零 relink、零 artifact 變動**：`validate_e2_b.py` 重跑仍是
`GO_TO_E2_C | problems: none`，`findings/` 與 `dist/` 逐位元未動。

## 規格裡兩件從樹裡讀出來、不是想出來的事

1. **D3 語料的第六份不是本輪想加的。** E1-C 9.2 在 08-13 就寫下
   「清單動作要進出貨契約之前，必須先補語料或具名排除」，語料
   （`test-docs/e1/list-contexts.odt`）也已經補好。清單動作**現在就在**
   出貨契約裡，所以那條義務到期了，E2-C 是它第一次真的被用到的地方。
2. **D2 那個 `dispatched-rollback` 格要用「有註腳、但註腳本文沒有 frame」的
   fixture。** E1-C 9.1 量過四格：`footnote-no-frame-full` 是 8 ms 可用的，
   `note-full`（註腳裡有 as-char frame）會讓引擎停止回應。
   **拿錯 fixture 這一格不會失敗，會讓引擎不回應**，然後整輪什麼都證明不了。
