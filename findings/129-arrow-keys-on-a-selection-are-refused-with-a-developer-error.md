# 129 — 反白選取之後按方向鍵，一律被拒絕，而且畫面跳出開發用的英文錯誤

| | |
|---|---|
| **狀態** | **已確認、未修** |
| **所在** | 兩處。(1) profile `e2-editor-v19` 的 manifest：六個移動動作（`move-character-left/right`、`move-line-up/down/home/end`）的 `gestures` 都只有 `["collapsed"]`，也就是只宣告給「游標」，不給「選取範圍」；引擎的手勢閘門（`src/probe_engine.cpp`）照 manifest 拒絕，什麼都沒送出。(2) 我們的頁面 `wasm_sdk_probe/web/e2-editor-app.js`（`8909564e…`）：方向鍵的 keydown（:2398–2405）只問 `session.offers(action)`，**不問目前的選取形狀**就送出；被拒絕之後，`run()` 把錯誤碼和引擎的英文訊息原樣放進 toast（:1729） |
| **發現日** | 2026-10-12（擁有者手測宿主 0.2.12） |
| **嚴重度** | 一般：不丟資料，文件和工作階段都沒事。但「選了字之後按方向鍵」是最常見的操作之一，現在每次都失敗，而且失敗訊息是給開發者看的英文 |
| **可重現** | 每次（Chrome 與 Firefox 157；◀、下、End 各 1/1，兩個瀏覽器相同） |
| **是否上游** | 否 |

## 現象

擁有者原話：「將文字反白選取的時候，使用方向鍵會報錯」。

## 重現步驟

1. 在宿主 0.2.12 開任何文件，用滑鼠拖曳反白幾個字。
2. 按 ◀（或 ▶、上、下、Home、End）。

**預期**：選取取消，游標移到合理的位置（一般文書處理器的行為；LibreOffice 桌面版的確切行為要先量原生）。
**實際**：選取原地不動，狀態列顯示「◀ 失敗」，toast 顯示：

> `◀：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged`

（下：「下移一行：EDITOR_FORMAT_GESTURE_UNSUPPORTED：…」；End：「移到行尾：…」。）工作階段維持「就緒」、Worker 世代不變、revision 不變。

## 證據

`findings/evidence/128/` 的 `chrome-1.json` 與 `firefox-1.json`，`selection` 臂（拖曳經過頁面自己的 pointer handler，拖完 `#toolbar[data-selection-shape]` 是 `range-single`，再按一個真的鍵）；說明在 `evidence/129/README.md`。

## 原生參考：Writer 自己怎麼做（2026-10-12 量，`evidence/129/native/round-20261012T020528Z/`）

原生 LibreOffice 26.8（`native-lok-26-8`，LOK，`tools/f129_native_arrow_on_selection.cpp`，fixture `test-docs/f129/arrow-selection.fodt`）。P2＝`P2 ALPHA BETA GAMMA DELTA`，選取 `BETA GAMMA`（位置 9–19），兩種方向各做一次：**往前選**（從 9 按 Shift+▶ 十下，游標停在尾端 19）、**往後選**（從 19 按 Shift+◀ 十下，游標停在前端 9）。按一個鍵之後打一個 `#`，看 `#` 落在哪裡。

| 鍵 | 往前選（游標在 19） | 往後選（游標在 9） |
|---|---|---|
| ◀ | 18（`GAMM#A`） | 8（`ALPHA#`） |
| ▶ | 20 | 10（`B#ETA`） |
| 上 | P1 位置 24（行尾） | P1 位置 13 |
| 下 | P3 位置 24（行尾） | P3 位置 12 |
| Home | 行首 0 | 行首 0 |
| End | 行尾 25 | 行尾 25 |

**Writer 的規則：從游標所在的那一端（point）照這個鍵移動，同時取消選取。**上、下兩列的落點與「從 point 的水平位置垂直移動」一致（P2 是大寫、P1／P3 是小寫，字寬不同），但 x 座標本身沒有讀，這一句是推論。它**不是**瀏覽器或 Word 的「◀ 收到選取的開頭、▶ 收到結尾」。12 個臂裡，按鍵之後選取都是空的，`#` 沒有取代任何選取的字；對照臂（不按鍵直接打 `#`）則把 `BETA GAMMA` 換掉了，證明選取確實存在。第一輪定位跑到 P1（`round-20261012T020312Z-p1-instrument-fault/`，在 P1 的 `paragraph ` 上得到同樣的規則，上鍵在第一行時改成到行首），保留為儀器失誤紀錄。

**對修法的意涵**：選取中的游標矩形，頁面本來就收得到（`overlayShapes` 的註解寫明 LOK 在選取時仍持續送游標矩形，`e2-editor-app.js` 約 :1425）。所以「先在游標那一端定位收起選取，再送原本的移動動作」只動頁面，結果就應該與 Writer 相同。要用 WASM 上的同一個 `#` 讀法逐鍵對照才算數。

## 相關：Shift＋方向鍵（擁有者同次要求的功能，見規格 §17.25）

現在按 Shift＋▶，頁面**照樣當成 ▶ 送出**：游標移一格、沒有選取（兩個瀏覽器，3/3 下）。keydown 沒有看 `shiftKey`。這不是 129 本身，但和 129 是同一個缺口——頁面只有「游標」的移動，沒有「選取範圍」的移動與延伸——修的時候要一起想。

## 處置方向（未決，交規格）

- **只動頁面**：選取範圍時，方向鍵先在游標那一端定位收起選取，再送原本的移動動作；結果要與上面的原生表逐鍵相同（`#` 讀法）。~~收到哪一端、要不要再移一格，要先量 LibreOffice 原生的行為。~~（已量，見上節）
- **放寬 manifest**：把移動動作的手勢加上 `range-single`／`range-cross`，讓 Writer 自己處理選取中的方向鍵。manifest 是 profile 身分的一部分，要換 profile；引擎在選取狀態下的移動屏障能不能驗證，要先量。
- **toast 的措辭**：引擎的英文訊息不該直接給使用者看——這是頁面上所有 `run()` 失敗共用的路徑，範圍要先普查。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-12 | 初版：擁有者手測宿主 0.2.12 回報；同日用 `tools/probe_hand_test_0212.py` 在宿主上兩個瀏覽器重現 |
| 2026-10-12 | 補原生參考：Writer 從游標那一端移動並取消選取（12 臂＋對照，`evidence/129/native/`）；Shift＋六個鍵也從游標那一端延伸 |
