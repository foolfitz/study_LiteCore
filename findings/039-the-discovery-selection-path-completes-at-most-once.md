# 039 — discovery 的選取路徑每份文件只完成得了一次，之後把 handle 一起帶走

| | |
|---|---|
| **狀態** | **已確認並已歸因：缺陷在我方 engine，core 行為正確；未修** |
| **Bugzilla** | — |
| **發現日** | 2026-08-13 |
| **嚴重度** | 嚴重（讓「點一下段落再按按鈕」這種一般手勢在第二次就死掉） |
| **可重現** | 11 組全部如預期，**Chrome 150 與 Firefox 153.0.1 逐格相同**；原生 26.8 對照 2/2 |
| **是否上游** | **否（一般情形）——已用原生對照證明**。core 只在「有選取可清」時廣播，那是正確行為；等待它無條件到來的是我方 engine。**但格式動作之後那一個實例是上游的，見下方 2026-08-15 的補記** |

> **2026-08-15 補記（任務 #49）：「格式動作之後選不到東西」這一個實例已歸因到上游，
> 記在 [finding 043](043-fn-select-para-leaves-the-shell-in-selection-mode-and-the-next-lok-range-selection-is-silently-dropped.md)。**
>
> 本篇的一般結論**不變**：core 只在有選取變化時廣播，是正確行為；無條件等待的是我方 engine。
> 新的是**那個特定情境下 core 為什麼沒有東西可廣播**——因為 barrier 用的 `.uno:SelectText`
> （`FN_SELECT_PARA`）留下 `SwWrtShell::m_bInSelect` 沒人關，害後續 `END` 的 `SttSelect()`
> 提前返回、`SetMark()` 從未執行，**選取根本沒有成立**。原生四輪、WASM 兩瀏覽器。
>
> 我方在 `probe_engine.cpp` 的 `text-handles` 加了標註過的 workaround
> （`RESET`＋`START`＋`END`）。實測在組合 artifact `940b7723…` 上，
> **沒有 bounded readback 的那一條由逾時 10 001 ms 變成回呼 10 ms 完成**——
> 也就是本篇「每份文件只完成得了一次」的症狀，在那個情境下消失了。
> 證據：[`evidence/sdk-e2/discovery/049-selection-after-format/`](evidence/sdk-e2/discovery/049-selection-after-format/)。

## 摘要

E2 discovery ABI 的 `editorDiscoverySelect` 在**沒有選取變化可廣播**的時候不會返回。
它等的是選取變更 callback；當選取已經是空的、或前一個動作剛把選取還原掉，
core 沒有東西可以廣播，於是請求永遠不完成——而 `gEditorPending` 不會清掉，
之後每一個 editor 操作都被回 `BUSY`，等於 handle 死掉。

> **善後那一段不是新的。** 「逾時會讓 `gEditorPending` 卡住、同一個 worker 之後全回 `BUSY`」
> 是 [finding 018](./018-lok-line-navigation-completion-nondeterministic.md) 早就記過的行為，
> 本篇只是又踩到它。**新的是觸發條件**：選取路徑會在「沒有選取變化可廣播」時掛住，
> 而那是一個由呼叫順序決定、不是由文件內容決定的狀態。

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

換句話說，**掃描證據沒有被推翻**。
（初版在這裡還寫了「被否證的是『這條 ABI 可以拿來做點擊定位』」——**那句也撤回了**，
點擊定位可用，只是不能走 reset，見下方第 10／11 組。）

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
| 10 | Document SDK `click`：立刻讀 vs 輪詢 | 立刻讀是**舊值**；輪詢約 **245 ms** 後游標跟著點擊走 |
| 11 | click 定位 → 派送，四次 | **8 步全過**（定位 244–245 ms、動作 23–25 ms） |

> ### 2026-08-13 撤回：第 10 組的初版結論是我的探針造成的
>
> 初版第 10 組寫的是：~~「`click` ×5，每次 0–1 ms 成功，**游標五次都停在 `1418,1418`**——
> 回報成功而什麼都沒做，這是 [finding 022](./022-e1-release-set-bold-false-noop.md) 的形狀」~~。
> **那是錯的，而且錯法正是本專案一再立法反對的那一種**：`click` 是 fire-and-forget，
> 游標由 callback 幾百毫秒後才到，而我**在呼叫返回的當下讀了一次狀態就下結論**。
> 一個讀得太早的探針，看起來和「什麼都沒發生」一模一樣。
>
> 照 `EditorSession.placeCaret` 本來就在做的方式輪詢之後：
> 立刻讀是 `1418,1418`（舊值），**約 245 ms 後穩定在 `1838,1418`**；
> 點 y=2800 得 `1768,2795`、點 y=3600 得 `1764,3645`——**游標確實跟著點擊走**。
> 產品 artifact `835b453d…` 上量到**完全相同的行為**，所以這也不是兩個 profile 的差異。
>
> 第 11 組是照這個更正做的實測：**click 定位 → 派送格式動作，連續四段全部成功**，
> 存檔 13 345 bytes。**所以「這條 ABI 上沒有可用的點擊定位手勢」這個結論一併撤回。**
>
> 重現頁的自判定也跟著改：現在要求 `clickMovedTheCaret === true` 且
> `immediateReadIsStale === true`——**把我犯過的那個錯本身變成一條會失敗的檢查**。

重現頁自己判定：該逾時的必須逾時、該通過的必須通過、click 的立刻讀必須是舊值、
輪詢後的游標必須有移動，`reproduced` 才會是 true。

## 重現

```
make f039-caret-reset-assets && python3 web/serve.py
# 開 http://127.0.0.1:8765/f039-caret-reset-repro.html
# 頁面自己跑十一組，結果在 globalThis.__f039，reproduced 欄位就是判定
```

## 影響

**產品 `e1-editor-v1` 不受這條影響——已由對照實測，不再是推論。**
在出貨 artifact `835b453d…` 上：`click` ×5 全部成功且**沒有任何逾時**、
`editorSelectRangeV1` ×5 全部成功（112／19／251／8／10 ms）。
產品根本沒有匯出壞掉的那條 discovery reset。
（初版這裡寫「本輪沒有在產品 profile 上量過，根據是程式碼路徑不同」；已補量並改寫。）

> **2026-08-15：上面這五個數字沒有證據檔可以指。** 追了加進這句話的 commit
> （`b8270c8`），它新增的證據是 `demo-structure/` 與 `secondary/chrome.json`，
> **兩份都不含 `835b453d` 也不含這幾個時間**；整棵 `findings/evidence/` 裡也搜不到。
> 也就是說，「已由對照實測，不再是推論」這句**目前無法從樹裡重現或核對**——
> 數字大概是當場跑出來的，但沒有落地。
>
> **不撤回這個結論**，因為它另有一條不依賴那次量測的根據：
> 產品的 `oxsdk_editor_select_range` 傳 `/*boundedReadback=*/true`
> （`editor_api.cpp:123`），discovery 那條沒有——**機制上的差別是讀得到程式碼的**。
> 但「五次全過、112／19／251／8／10 ms」這一串在補上證據之前應當標為**未落地**。
> 下一次動產品 profile 時順手補一輪，並記下 `completion` 欄位（見本節末的 251 ms 假說）。

**對任務 #36 路線 B 的影響：不擋，但把可用的路徑縮到一條。**

> **2026-08-13 撤回。** 這一段初版寫的是「**擋住**路線 B，ABI 上沒有可用的點擊定位」。
> 那是建立在第 10 組的錯誤讀數上的（見上方撤回），**已不成立**。
> 可用的定位手勢是 **`click` ＋ 輪詢**——也就是 `EditorSession.placeCaret`
> 從一開始就在做的事，一條產品已驗證的路徑，不是為了繞過缺陷發明的手勢。
> 第 11 組實測四段連續「點一下、按按鈕」全過。

要避開的是**另外兩條**：`selection-reset-unstable`（第二次就死）與
range 選取（格式動作之後就死）。demo 兩條都不需要碰。
harness 的 search-prime 配方（先搜尋再 reset）也是活的，
但既然 click ＋ 輪詢可用，就沒有理由選它。

> **2026-08-13 更正（外部覆核指出）。** 這一段原本寫：這個配方「**在非收合選取上派送格式動作，
> A3／A4／A5 從來沒有量過**」。**那句話跟本篇第 9 臂的資料互相矛盾。**
> 第 9 臂的順序是 search → **reset** → 動作，而 reset 放下的是**收合游標**——
> 跟 375 次判定派送**同一個前置狀態**，`caretAtAnchor` 的實作就是這個順序。
> 只有「search 之後直接派送、跳過 reset」的變體才會是非收合，而沒有人需要那個變體。
> 已就地更正；下面關閉路線 B 的理由**不是**可行性。
>
> 順帶一提，「在 range 選取上按標題／清單」**確實**是 A3～A5 沒量過的格子，
> 但那是**產品**的問題（`editorSelectRangeV1` 加上 `extend_selection`，v2 的使用者一定會這樣按），
> 與本篇無關，應該記進 E2-B 未來的產品側掃描矩陣。

> **關於「關閉路線 B」的兩段論證，也一併撤回。** 初版在這裡寫了一整段
> 「唯一蓋得起來的做法是殼層繞過兩個活缺陷、因此是誤導」——那段論證的前提
> （沒有可用的點擊定位、必須用 search-prime 繞道）已經被上面的更正推翻。
> click ＋ 輪詢是產品自己的路徑，用它不是繞道。
> 外部覆核在我更正之前就已指出「關閉理由應該是誤導而非不可行」，
> 那個修正在當時的事實下是對的；現在事實變了，兩個版本的關閉理由都不再適用。

## 已歸因：core 沒有錯，錯的是我方等待的條件（2026-08-13）

原生 26.8 探針（`tools/f039_native_caret_reset.cpp`，跑在 `build-native-26-8/instdir`）
直接註冊 callback 數，同一份 fixture、同樣的五個情境。**兩次獨立執行結果逐格相同。**

| arm | `selectionTypeBeforeReset` | `TEXT_SELECTION` | 有沒有選取 callback |
|---|---|---|---|
| `reset-1` | **1** | 1 | **有** |
| `reset-2` | 0 | 0 | 沒有 |
| `reset-3` | 0 | 0 | 沒有 |
| `range-then-reset` | **1** | 1 | **有** |
| `format-then-reset` | 0 | 0 | 沒有 |

`resetWithNothingToClearIsSilent: true`。

**結論：core 只在「有選取可以清」的時候廣播選取變更，這是正確行為**——沒有變更就沒有事件。
我方 engine 卻在每一次 RESET 之後都無條件等那個 callback，於是在選取已空時等到天荒地老，
並且不清 `gEditorPending`。**缺陷是我方的，上游欄位因此改判為「否」。**

**修法的判準已經在資料裡**：`selectionTypeBeforeReset` 就是那個區分子——
兩個有 callback 的 arm 它是 1，三個沒有的它是 0。引擎在 RESET 之前本來就讀得到選取型別
（037 的擋法用的就是同一個呼叫），所以「選取已經是空的就不要等」是可以判的，不必猜。
兩次有 callback 的 arm，`TEXT_SELECTION` 的 payload 都是**空字串**——
也就是說那個事件本身只說「現在沒有選取了」，正好是 RESET 該有的語意。

順帶記一個環境事實：這顆原生 build 在 process-static clipboard teardown 會 Signal 11
（SAL stack 落在 `desktop_LOKClipboard_get_implementation`），與本探針要量的東西無關。
探針在**銷毀 document 與 kit、且 summary 已經 flush 之後**才 `_Exit(0)` 跳過那段靜態解構；
載入或開檔失敗仍然回非零。這件事寫在這裡，是因為「用 `_Exit` 換到 exit 0」是很容易變成
掩蓋失敗的手法，所以它的位置與適用範圍要看得見。

## 第 8 臂是這裡面對 E2-B 最要命的一格

「一個格式動作之後，連 range 選取都逾時」不是 demo 的麻煩，是**規格的輸入**。
E2-B 要把**同一個 barrier** 編進產品；如果 barrier 收尾的選取還原會把下一次選取悶死，
那麼 v2 出貨的就是「格式化一次、選取路徑陪葬」——不是在 E2-B 昂貴的產品側重掃時才發現，
就是使用者先發現。E2-000:134 說 B 的規格待 A 有結果後另寫，**這一格就是 B 必須先消化的 A 結果**。

（本篇初稿把原生歸因寫成「對 contract v2 沒有幫助」。那是反的，已由外部覆核指出並更正。
歸因本身**不需要 relink、不解綁任何證據**；貴的是之後的修復與重掃，那可以延到下一次
discovery 本來就會發生的 relink。）

## 2026-08-15：修法要的機制**早就存在而且已經出貨了**，discovery 是**刻意**不裝它

準備任務 #47（修 039 ＋ 批次 relink）時去讀了兩條 ABI 的進入點，結果是：

| ABI | 進入點 | `boundedReadback` |
|---|---|---|
| **產品** `editorSelectRangeV1` | `src/editor_api.cpp:123` | **`true`** |
| **discovery** `editorDiscoverySelect` | `src/editor_discovery_api.cpp:58` | 省略 ⇒ 預設 `false` |

`boundedReadback` 開著的時候，`handleEditorSelect` 會武裝一個 250 ms 的 readback 期限
（`probe_engine.cpp:3756`、`EditorSelectReadbackDeadlineMs`），到期由
`completePendingEditorSelectByReadback()` 以**具名的** `verified-selection-readback`
完成——它不是把逾時當成功，而是**回報當下實際讀到的選取**，讓呼叫端自己判斷。

而 `probe_engine.hpp:69`–`72` 把這個取捨寫得很清楚：

> boundedReadback: complete from a selection readback if the requested range
> changes nothing and core therefore emits no selection callback (SPEC E1-D).
> **The product range-select sets it; the diagnostic path does not, so the
> profiles the findings were measured on keep pure callback semantics.**

**所以 039 不是「引擎忘了判斷」。** 那個判斷已經寫好、已經出貨、而且 SPEC E1-D 說的
情境（「請求的範圍什麼都沒改，於是 core 不廣播」）**逐字就是 039 的情境**。
discovery profile 沒有它是**設計決定**：把純 callback 語意留給拿來量 core 行為的 profile。

### 這件事改寫了 E2-B 進場條件真正在問什麼

- **出貨的 `e1-editor-v1` 根本沒有編進 format barrier**（`OXSDK_E2_FORMAT_BARRIER`
  只出現在 E2 系列的 build 規則，`Makefile:504` 起；`E1_B_BUILD` 沒有）。
  所以**第 8 臂在今天的產品上不可能發生**——它沒有格式動作。
- 而 E2-B 要送進產品的組合是**barrier ＋ 產品那條有 buffered readback 的 select**。
  **那個組合目前不存在於任何 artifact 上，所以第 8 臂在它上面會不會發生，是未量的。**

一句話：E2-A 縮限 4 寫的「已知在 **discovery 引擎上**為假」用字是準的，
而「修好 039」現在有三條意思不同的路，選哪一條會決定 E2-B 繼承到什麼。**未定，見任務 #47。**

> ~~**順帶一個假說，沒證實**：039〈影響〉那一節量產品時，`editorSelectRangeV1` 五次是
> 112／19／**251**／8／10 ms。**251 很接近 250 ms 的 readback 期限**⋯⋯~~
>
> **2026-08-15 當天就量了，假說成立。** 證據
> [`039-combination/p1-product-readback/`](evidence/sdk-e2/discovery/039-combination/p1-product-readback/README.md)，
> 在凍結的 `835b453d…` 上（**沒有任何重建**），兩個瀏覽器逐格相同：
>
> | 步驟 | completion | 耗時 |
> |---|---|---|
> | 選一個範圍 R | `documented-callback-text-selection` | 9 ms |
> | **再選一次同一個 R** | **`verified-selection-readback`** | **251 ms** |
> | 對照：選取真的會變的兩次 | 兩次都走 callback | 9／10 ms |
>
> 而且**那個 bounded completion 沒有說謊**：兩次之後讀回的選取都是 `"ASCII abc XY"`，
> pending slot 也沒卡住。
>
> **但這不算補上原本那五個數字的證據**——我跑的是不同序列。
> 落地的是**機制**與「251 ms 出自那條路徑」這件事；`112／19／251／8／10` 仍然未落地。

## 2026-08-15：第 8 臂在 E2-B 要出貨的組合上**還在**，只是換了失敗的樣子

裁決（外部，Option C-plus）要求把組合建出來量，而不是去改 discovery 的語意。
建了（`e2-combination` ＝ `ba1a5dd5…`），量了，**預測落在預先寫下的失敗分支**：

| 進入點 | 格式動作之後的範圍選取 | 事後回報的選取 |
|---|---|---|
| discovery（不 buffered，**照設計保留**） | **逾時 10 000 ms** | — |
| **產品（有 bounded readback）** | 完成，`verified-selection-readback`，251 ms | **`none`，空字串** |
| 同一個選取但**前面不做格式動作**（歸因控制） | 完成，callback，20 ms | **`"moji 😀 graphe"`（14 字）** |

**兩個瀏覽器逐格相同。**

所以 bounded readback 做到的是**把「掛住」換成「誠實地說沒選到」**——
引擎不再卡（`gEditorPending` 有清、後續操作 1 ms 完成、沒有 BUSY 連鎖），
**但底下的缺陷原封不動**：一個格式動作之後，範圍選取選不到東西。

**E2-A 縮限 4 因此留著**，措辭要從「下一次選取請求永遠不返回」擴成
**「會返回，但選不到東西」**——兩種都是「格式化一次、選取路徑陪葬」。
**E2-B 的進場條件沒有滿足。**

證據：[`039-combination/p2-composition-scan-ba1a5dd5/`](evidence/sdk-e2/discovery/039-combination/p2-composition-scan-ba1a5dd5/README.md)。
鑑別控制成立：同一支工具**先在封存的 `c89f069e` 上重現了逾時**才去量新 artifact。

> **這一輪我漏了一格、事後補上。** 第一版沒有「不做格式動作的同一個選取」這個控制，
> 而「格式動作之後選到 `none`」和「y=2600 是空行」**讀數一模一樣**。
> 補上之後結論沒變，但在補上之前它不成立。

## 還不知道的

1. ~~**歸因未做。**~~ **已完成**（見上一節）：core 正確，我方等錯條件。
   **修法未實作**——那要動引擎，於是要 relink discovery profile 並重掃 A3／A4／A5，
   可以等到下一次本來就會發生的 relink。
2. ~~**產品 profile 沒有量。**~~ **已補量**（見〈影響〉），這一條結案。
3. ~~**`click` 為什麼在這顆 artifact 上不動游標。**~~ **問題本身不成立**——它會動，
   是我讀得太早（見第 10 組的撤回）。兩顆 artifact 行為相同。
4. ~~**只有 Chrome。**~~ **Firefox 153.0.1 已補跑**，11 組逐格相同
   （`evidence/…/f039-caret-reset/firefox/result.json`）。這一條結案。
5. **修法之後 barrier 會怎樣，沒有量。** 第 8 臂說 barrier 收尾會悶死下一次選取；
   如果修法是「空選取就不等」，那第 8 臂應該一併好轉——但那是預測，不是量測。
