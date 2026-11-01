# 177：有序引擎上線後，每打一個字都要等 8–9 個 10 ms 的 tick，打字從 4 ms 變 85 ms

| | |
|---|---|
| **狀態** | 成因已定位（鏡像實驗）；修法要改引擎（v29），**未修**。擁有者 2026-11-01 選 B：K 不跑，先修這個 |
| **Bugzilla** | —（本樹缺陷：有序引擎把回覆排到 poll，而 core 的節奏是 100 fps） |
| **發現日** | 2026-10-31 深夜（K 0.2.44 重跑前的 first contact，C2 兩支 judge 都紅） |
| **嚴重度** | 中——沒有資料損失，但打字變鈍；每秒 12 字的快打會積壓到約 1 秒；長文件存檔期間連帶觸發頁面佇列上限（見「同根的第二個症狀」） |
| **可重現** | 100%（分布極窄：85.0／88.4 ms） |
| **首次出貨** | 0.2.39（v24，當天回退到 0.2.38），0.2.40 起留在出貨線；現行 0.2.44 有此缺陷 |
| **不是** | 環境或工具：同工具、同 Chrome 156、同時段換回 v21 就是 4.5 ms |

## 量測

〔實測〕同工具（`probe_typing_latency.py`）、同瀏覽器、同時段，只換引擎，`boundaries` 文件、間隔 200 ms、10 字，Chrome 156：

| 版本 | 每字 commit 中位數／最大 | 上螢幕中位數／最大 |
|---|---|---|
| 0.2.26（v21） | 4.5／10.9 ms | 13.0／16.6 ms |
| 0.2.38（v22） | 4.3／15.5 ms | 12.8／20.1 ms |
| 0.2.39（v24） | 87.0／89.5 ms | 68.3／70.8 ms |
| 0.2.44（v28） | 85.0／88.4 ms | 66.7／71.0 ms |

退化在 v22 與 v24 之間，也就是有序引擎（v23）或新的打字路徑（v24）。v23 沒有出貨套件，沒有單獨量。

〔實測〕擁有者的長文件，桌面上沒有別的量測：

| 格 | commit 中位數／最大 | 上螢幕中位數／最大 | 0.2.26 的 commit 中位數 |
|---|---|---|---|
| Chrome，間隔 80 ms，20 字 | 575.8／1048.8 ms | 615.7／1087.9 ms | 19.7 ms |
| Chrome，間隔 200 ms，10 字 | 107.2／121.7 ms | 103.2／142.6 ms | |
| Firefox，間隔 80 ms，20 字 | 588.3／1059.3 ms（19 筆） | 629.7／1101.2 ms | 21.2 ms |

間隔 80 ms 時每個字的處理時間超過間隔，積壓線性成長。Firefox 第 20 字在讀取時還沒 commit，是偏晚，不是遺失。

## 機制

〔實測，原始碼〕`vcl/headless/svpinst.cxx`：

- `DoExecute`：`emscripten_set_main_loop_arg(loop, this, 100, 1)`。註解寫 somewhat randomly，節拍是 10 ms。
- `ImplYield`：`bool bWasEvent = DispatchUserEvents(bHandleAllCurrentEvents); if (!bHandleAllCurrentEvents && bWasEvent) return true;`。主迴圈傳 false，所以**一個 tick 只派一個使用者事件**就返回，輪不到 poll。

v23 起回覆在 poll 送出（`SPEC-M3-ordered-commands` §5.2）。`.uno:InsertText` 之後排著幾個使用者事件，回覆就要等它們一個 tick 一個地跑完。8–9 個事件 × 10 ms ＝ 量到的 85 ms。v22 以前的引擎不靠這條路回覆，所以沒有這個代價。

〔實測〕決定性實驗：`dist/` 不動，只在鏡像暫存複本裡改 `probe.js` 的節奏（`first-contact/typing-control/diag_tick.py`）：

| 節奏 | Chrome `boundaries` commit | 上螢幕 |
|---|---|---|
| 現狀（setTimeout 10 ms） | 85.0 ms | 66.7 ms |
| `setTimeout(0)`（瀏覽器夾到約 4 ms） | 44.8 ms | 34.9 ms |
| immediate（postMessage，不等） | 9.8 ms | 8.8 ms |

三個點都落在「事件數 × tick」上。immediate 下長文件也恢復：

| 格（immediate） | commit 中位數／最大 | 上螢幕中位數／最大 |
|---|---|---|
| Chrome 長文件 80 ms | 17.0／33.7 ms | 15.9／32.6 ms |
| Chrome 長文件 200 ms | 14.7／38.9 ms | 13.5／36.5 ms |
| Firefox 長文件 80 ms | 13.2／37.1 ms | 11.8／34.8 ms |
| Firefox `boundaries` 200 ms | 10.1／15.8 ms | 8.3／14.1 ms |

長文件三格都過 C2 的門檻。**`boundaries` commit 中位數沒有全過**：≤ 10 ms 這條，這一輪 Chrome 9.8、Firefox 10.1（已超線）；各重複 3 次（`typing-control/reps/`）是 Chrome 9.8–10.9、Firefox 9.2–9.4，v21 是 4.3。

〔更正 2026-11-01，審核第 2 項〕初版寫「C2 的門檻都過，只有 boundaries 貼線」，10.1 其實已經超線，不是貼線。

## 修法方向（要改引擎）

**immediate 不能原樣出貨**：tick 不等待時，文件閒置也會讓一顆核心空轉。方向是「有工作才全速」：有指令排隊或回覆待送時切到 immediate，連續幾個閒置 tick 之後切回 10 ms 節拍。`emscripten_set_main_loop_timing` 引擎就能呼叫，不用動 core。

**emscripten 原生的 mode 2 也不能用**（審核第 1 項，已核對 `probe.js`）：在 pthread 裡每一拍都往 `Module["setImmediates"]` 推一筆，沒有人消費，是無界洩漏；而且每拍經 `sdk-worker` 轉發一圈，兩條執行緒一起轉。改用引擎 worker 內的 `MessageChannel`：`channel` 三次重複 Chrome 8.4／10.1／8.4 ms、Firefox 9.7／9.5／9.3 ms，與原生同級。

要量的事：閒置時 CPU 回到現狀；切換本身不改變指令順序（`SPEC-M3-ordered-commands` 的硬規則都不動）。

## 同根的第二個症狀：AS-5 丟一個字

〔實測，first contact〕`as5` 兩個瀏覽器都 FAIL：存檔的引擎部分期間打 20 個字母，伺服器只有 19 個，少了第 9 個 `i`，兩邊相同。時間線（Chrome）：`i` 在開打後 +1.020 秒，引擎部分 +1.029 秒才結束，頁面在 +1.021 秒跳「有字沒有輸入：打得比引擎處理得快，請檢查最後打的字」。Firefox 同形狀。

所以這不是靜默丟字：頁面暫存的 8 個字（a–h）之後，第 9 個被拒並告知使用者。0.2.26 的計數這一格是過的。

〔推論〕同一個根：引擎部分變慢，佇列才碰得到上限。旁證：小文件按存檔到位元組從 0.22 秒變 0.61 秒〔實測，`same-second`〕。**未驗證**：v29 上要重跑 `as5`，它若還紅就是另一個問題。

**驗證（2026-11-01，0.2.45，v29）**：〔實測〕`as5` 3 次 × 兩瀏覽器 6/6，20 個字母全部到伺服器；`as5-held` 6/6（`findings/evidence/host-0.2.45/section-7/`）。同一天 v28 上（ST2，自有 stack）仍是 19/20，所以差別在引擎，不在 stack。上面的推論成立，不必開新 finding。存檔也確實變快：S1 從按下到 settled 由 0.65–0.78 秒（v28，ddev 與自有 stack）降到 0.35–0.40 秒〔實測，`same-second`〕。

## 為什麼現在才發現

- C2 只在計數鏈裡跑，而計數鏈併批延後（`release-count-batched`）；0.2.26 之後 v22–v28 都沒有跑過 C2。
- 鏈裡 C2 排在最後，第一次鏈又停在 shakedown。這次是為了避免八小時白跑才提前 first contact。
- 擁有者手測沒有回報打字鈍，85 ms 在一般打字下不容易察覺；快打才會積壓。

## 附帶：同一次 first contact 的其他儀器問題

見 `specs/SPEC-M3-K-0.2.44.md` 追加 1–3。都不是產品缺陷。
