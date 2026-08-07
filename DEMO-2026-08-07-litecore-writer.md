# LiteCore Writer demo 執行說明（2026-08-07）

給同事看的前端編輯器，跑在 `e1-editor-v1` 上（wasm `835b453d…`）。

**2026-08-07 更新**：拖曳選取需要窄版契約新增一個範圍選取操作，隨後又加入底線／刪除線
（契約 8→10 actions），因此**已重建 artifact 兩次**（見
[SPEC E1-D](specs/SPEC-E1-D-range-selection.md)）。連帶後果：**E1-C 的全部證據綁在舊 hash 上
而失效** —— 不只人工輪，48 個瀏覽器 case 也一樣，只是驗證器原本沒查（當天已補上綁定閘門）。
裁決 `E1_STOP_OR_RESCOPE`，需重跑自動相位與雙瀏覽器人工輪才會回到 GO。
**demo 本身不受影響**：跑起來的就是那個新 artifact，缺的是對它的驗收證據。

## 怎麼跑

```bash
cd wasm_sdk_probe
make serve-demo
# 瀏覽器開 http://127.0.0.1:8765/demo-editor.html
```

`make serve-demo` 只做兩件 `cp` 再啟動 `web/serve.py`，不觸發任何建置。

**一定要從 `127.0.0.1` 開**。引擎需要 cross-origin isolation（`SharedArrayBuffer`），
COOP/COEP 由 `serve.py` 送出，而 secure context 只在 `127.0.0.1`／`localhost` 成立。
若要從別台機器看，用 SSH port forward 保住 origin，不要改 bind 位址：

```bash
ssh -L 8765:127.0.0.1:8765 jiajun@<這台>
```

## demo 動線建議

1. **開場**：整個 LibreOffice 文件引擎編譯成 WebAssembly，跑在瀏覽器的 Worker 裡。
   畫面是引擎算出的點陣圖，不是 DOM 排版。右上角顯示 profile 與契約版本。
2. **點一下文件**放游標 —— 游標會閃在你點的位置，狀態列顯示「定位游標 2～4 ms」
   以及游標的 twips 座標（那個座標是引擎給的，不是前端算的）。
3. **直接打字**，含中文與 emoji。每個字素一個 revision，狀態列即時跳動。
4. **Shift+→ 選幾個字**，藍色選取塊會出現（矩形一樣是引擎給的）。**按 B** —— 存檔後
   `content.xml` 會出現 `fo:font-weight="bold"`，且 emoji 算**一個**字素。
5. **按 ↶ 復原**。
6. **儲存 ODT** → 下載的檔案用桌面版 LibreOffice 直接開得起來。
   檔案是引擎自己存出的，不是前端拼的 XML。
7. **按「這個 demo 能做什麼」** —— 裡面誠實列出不支援的項目，以及執行中成品的
   WASM SHA-256。這頁是重點：窄版契約是刻意的，不是做不完。

## 游標與選取（2026-08-07 新增）

畫面上現在有閃爍的游標與藍色選取塊。幾何**來自引擎**（`editorGetStateV1` 回傳的
`caret` 與 `selection.rectangles`，單位是 twips），不是前端猜的；轉換就是
`px = twips / 15 × 縮放`，與 canvas 用的是同一個轉換。

畫在 canvas **之上的疊層 div**，不畫進點陣圖 —— 游標閃爍不該讓引擎重繪。反白用
`mix-blend-mode: multiply` 合成：底下的文字是引擎點陣圖的一部分，用 multiply 才能讓
色帶看起來是實心選取而字仍然清楚，單純半透明疊色在這個尺寸只會像一片髒污。

**兩種觸發方式**：Shift+←／→ 逐字元擴張，或**直接用滑鼠拖曳**（2026-08-07 加入，
見 [SPEC E1-D](specs/SPEC-E1-D-range-selection.md)）。拖曳可跨行、跨段落。

拖曳的手勢在 JS，範圍請求交給引擎：瀏覽器知道指標去了哪裡，所以是「請選這兩點之間」，
不是餵合成滑鼠事件讓引擎自己猜。閘門發現後者會回報一個它其實沒做的選取。

在空白處拖曳是安全的——回報「沒選到」並保持可編輯。那條路徑第一版建置時會卡死 60 秒，
修法是有界的選取讀回（250 ms 後去看實際選到什麼，而不是無限等一個不會來的 callback）。

**這裡有一個誠實設計，值得講。** 大部分操作在回覆時幾何就已經更新，唯獨**打字**例外：
文字送進去後 caret callback 會晚幾十毫秒才到（finding 021 的落後，最輕微的形式）。
所以每次操作後會**有界等待引擎的 `sourceSequence` 前進**——那是等一個可觀察訊號，不是
盲目 sleep——上限 400 ms。等不到就保留舊幾何，並把游標畫成**虛線空心**，狀態列寫
「位置未確認」。**絕不把游標移到引擎沒告訴我們的位置。**

### 已驗證（Chromium 與 Firefox 153.0.1，逐格相同）

| 動作 | 游標 | 選取 |
| --- | --- | --- |
| 開檔 | 94.5px，confirmed | 無 |
| 點擊文件 | 259.4px | 無 |
| ＋700 ms（debounce 補抓） | 仍 259.4px、仍 confirmed | 無 |
| Shift+→ ×3 | 283.4px | 一塊，259.4px 起、24px 寬 |
| 打字覆蓋選取 | 269.1px | 選取塊消失，revision +1 |
| 連打 A B C（Chromium） | 270.9 → 281.6 → 292.3px | 無 |

## 兩個設計決定，被問到時可以講

**粗體／斜體按鈕不讀引擎的前置狀態。** finding 021 發現這個 build 的格式狀態不隨
游標移動更新，finding 022 證明信任它會產生「成功但文件沒變」的靜默 no-op。產品路線 C
的作法是**不讀前置條件**：按鈕送出明確的布林值，而按鈕本身只反映「自游標上次移動以來，
我們自己要求過什麼」。游標一動就回到未知，按鈕的 tooltip 會直說。

**不支援的操作會出聲拒絕。** 上下行移動（finding 018）、Home／End、Redo 按下去會跳
提示，不是靜靜地不動。寧可讓人知道邊界在哪。

## 已驗證（2026-08-06 深夜，Chromium 與 Firefox 153.0.1）

| 項目 | Chromium | Firefox |
| --- | --- | --- |
| 啟動、cross-origin isolated | `ready`、true | `ready`、true |
| 點擊定位游標 | 2～4 ms | 1 ms |
| 打字 `DEMO臺灣😀` | revision 0→7，存檔含該字串 | 未測（見下） |
| Shift+→ 選取（真鍵盤） | 38 ms | 37 ms |
| 選取後套用粗體 | revision +1，`T1` 帶 `fo:font-weight="bold"`，套在 `臺灣😀E1` 五字素 | revision +1，同樣的 `T1`，套在 `E1-PL` 五字素 |
| 取消粗體（finding 022 反向操作） | revision +1，真的變更 | 未測 |
| 復原 | revision +1，格式意圖回到未知 | 未測 |
| 不支援鍵提示 | ArrowUp／Home／Ctrl+Y 三種各自正確 | ArrowUp 正確 |
| 存出 ODT | 10.5 KB，zip／CRC 通過，9 entry | 10.3 KB，同上 |
| Worker 世代 | 維持 1（上限 3） | 維持 1 |

兩邊的粗體都由**存檔 `content.xml`** 判定，不是看回呼；emoji 在 Chromium 那輪確認算
一個字素。

**待驗證**：真 IME 組字未在這頁測過（E1-C 的人工輪是在驗收頁做的）。demo 前若要保險，
自己打一行注音確認。

## 檔案

- `wasm_sdk_probe/web/demo-editor.html`（含疊層 CSS）、`wasm_sdk_probe/web/demo-editor-app.js`
  （`refreshGeometry()` 是有界等待那段，`paintOverlay()` 是繪製）
- `wasm_sdk_probe/Makefile`：`demo-editor-assets`（**刻意不相依 `e1-editor-profile`**）、
  `serve-demo`
- 引擎：`src/editor_api.{h,cpp}` 的 `oxsdk_editor_select_range`、`src/probe_engine.cpp`
  的有界選取讀回（搜 `EditorSelectReadbackDeadlineMs`）。
- 其餘沿用既有且已驗收的 `EditorSession` / `NarrowEditorClient`。
