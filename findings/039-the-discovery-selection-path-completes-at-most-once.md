# 039 — discovery 的選取路徑每份文件只完成得了一次，之後把 handle 一起帶走

| | |
|---|---|
| **狀態** | **已確認（我方 engine／discovery ABI）；未修** |
| **Bugzilla** | — |
| **發現日** | 2026-08-13 |
| **嚴重度** | 嚴重（讓「點一下段落再按按鈕」這種一般手勢在第二次就死掉） |
| **可重現** | 10/10（自判定重現頁，Chrome 150，引擎 `c89f069e…`） |
| **是否上游** | **尚未歸因**。目前只證明我方 engine 等的那個 callback 沒有到，沒有證明 core 該送而沒送 |

## 摘要

E2 discovery ABI 的 `editorDiscoverySelect` 在**沒有選取變化可廣播**的時候不會返回。
它等的是選取變更 callback；當選取已經是空的、或前一個動作剛把選取還原掉，
core 沒有東西可以廣播，於是請求永遠不完成——**而且 `gEditorPending` 不會清掉**，
之後每一個 editor 操作都被回 `BUSY`，等於 handle 死掉。

具體地：

- `selection-reset-unstable`（放游標用的那個）在**剛開檔後第一次成功**，之後每一次都逾時。
- **和座標無關**：同一個點按兩次也一樣死。
- **讀狀態不能解**：中間插一個 `getState` 沒有用。
- **一個格式動作之後，任何方法的選取都死**——包含原本看起來免疫的 range 選取。
  所以擋住它的是 barrier 收尾（把選取還原掉），不是某個方法。
- **中間放一個真的會改變選取的操作就會活**：search 可以，range 選取可以。

一句話：**這條路徑要求「現在有東西可清」，否則就掛著不返回。**
形狀和 SPEC E2-A 2.7（二）對格式狀態講的那件事一模一樣
（「值沒變就沒有 STATE_CHANGED，合法 no-op 沒有後置條件可等」），只是搬到選取路徑上。

## 為什麼 375 次判定過的派送沒有碰到

A3／A4／A5 的每一次定位都走 `caretAtAnchor`：**先 search anchor 文字，再 reset 到座標**。
search 一定會留下一個選取給 reset 清，所以 reset 一定完成。
重現頁的第 9 組就是照這個配方跑三輪（search → reset → 動作），**9 步全過**。

換句話說，**掃描證據沒有被推翻**，被否證的是「這條 ABI 可以拿來做點擊定位」這個推論——
那從來沒有人量過，因為 harness 從來不需要它。

## 量到的（`evidence/sdk-e2/discovery/f039-caret-reset/chrome/result.json`）

每一組各自開一顆引擎——卡住的選取會把 handle 帶走，共用引擎會讓前一組的損壞決定後一組的答案
（[finding 038](./038-a-frame-inside-a-footnote-wedges-the-engine-on-selection.md) 的教訓）。

| # | 情境 | 結果 |
|---|---|---|
| 1 | reset ×2，不同點 | reset-A 19 ms／**reset-B 逾時** |
| 2 | reset ×2，同一點 | reset-A 18 ms／**reset-A-again 逾時** |
| 3 | 中間插 getState | **仍然逾時** |
| 4 | 中間插 search | **兩個都成功**（10 ms） |
| 5 | 中間插 range 選取 | **兩個都成功**（10 ms） |
| 6 | 只用 range 選取 ×3 | 全成功（19／9／10 ms） |
| 7 | 中間插格式動作 | 動作 30 ms 成功／**reset 逾時** |
| 8 | 格式動作後改用 range | **range 也逾時**——擋住它的是 barrier 不是方法 |
| 9 | search → reset → 動作，三輪 | **9 步全過** |
| 10 | Document SDK `click` ×5 | 每次 0–1 ms 成功，**游標五次都停在 `1418,1418`** |

第 10 組要單獨講：`click` 是產品 shell 放游標用的路徑，在這顆 artifact 上
**回報成功而什麼都沒做**。這比掛住更糟——掛住看得見，這個看不見，
下一個格式動作會落在沒有人選過的段落上。這正是 [finding 022](./022-e1-release-set-bold-false-noop.md) 的形狀。

重現頁自己判定：前面該逾時的必須逾時、該通過的必須通過、`click` 必須沒有移動游標，
`reproduced` 才會是 true。

## 重現

```
make f039-caret-reset-assets && python3 web/serve.py
# 開 http://127.0.0.1:8765/f039-caret-reset-repro.html
# 頁面自己跑十組，結果在 globalThis.__f039，reproduced 欄位就是判定
```

## 影響

**產品 `e1-editor-v1` 不受這條影響**：它的選取走 `editorSelectRangeV1`（TEXT_HANDLES），
放游標走 Document SDK 的 `click` ＋ 讀回輪詢（`editor-session.js:310`），
兩者都不是這裡壞掉的那條 discovery reset。本輪也沒有在產品 profile 上量過這件事，
所以這句話的根據是**程式碼路徑不同**加上同一天在產品 demo 上連續點擊多次都正常，
不是一次對照實驗。

**擋住的是任務 #36 的路線 B**（把標題／清單的 demo 跑在 discovery profile 上）。
點擊定位在這條 ABI 上沒有可用的做法：reset 第二次就死、`click` 靜靜地不動、
range 在格式動作後就死。唯一活的是 harness 的 search-prime 配方，
而那要求每次點擊前先搜尋一個文件裡一定存在的字串——可行，但那是為了繞過缺陷而設計的手勢，
且**在非收合選取上派送格式動作，A3／A4／A5 從來沒有量過**（375 次判定派送全部是從收合游標出發的）。

## 還不知道的

1. **歸因未做。** 只證明我方等的 callback 沒到。是 core 不送、還是我方等錯了條件（例如
   `LOK_CALLBACK_TEXT_SELECTION` 在空選取轉空選取時本來就不送），沒有做原生對照。
   下一步應該是原生 26.8 的 `lok_frame_hang.cpp` 風格探針。
2. **產品 profile 沒有量。** 上面那句「產品不受影響」需要一次真正的對照才能升格。
3. **`click` 為什麼在這顆 artifact 上不動游標**，沒有查。它在產品 profile 上是會動的
   （同日 demo 實測），所以差異可能在編譯旗標，也可能在別的地方。
