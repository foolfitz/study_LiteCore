# 交接 — 2026-08-18：059 兩側都量完了，處置修了，而清單第一次會因為檢查紅而紅

> 進場點。讀完這一頁就能接手，不需要翻前面的交接。
> 前一份是 `HANDOFF-2026-08-17-usable-editor.md`。
> 這一輪的計畫與逐項執行紀錄在 `PLAN-2026-08-18-usable-editor-autonomous.md`。

## 0. 目前綁定

| | |
|---|---|
| artifact | `d538ce0b91478426…`（**未動**，本階段沒有連結） |
| 殼層 | **v17 `34289a7bd8ffc3df…`**（v16 → v17，一代，不需連結） |
| 矩陣 | `e2/validation-matrix-v2.json`，**D0 仍未跑** |
| 清單 | **8 done**／3 partial／2 unverified／1 missing／**2 blocked**（原本 3） |
| 佇列 | `P1 complete: **False**` —— 059 的**引擎那一半**還擋著，**這是對的** |

## 1. 這一輪最重要的一句話

**核心在 WASM 上也照做了。** 出貨的產品按下 B 會把字變粗，然後告訴使用者這個動作
失敗了、請回到檢查點——**叫人丟掉工作，去撤銷一個成功的改動**。

四個 slot 各自量過（`findings/evidence/059/wasm/`）：每一臂的標記回來都掛著正好是
它按下去的那個樣式，而同語料、同游標、同插入、不派送命令的對照臂沒有樣式。

處置那一半**已經修了**（殼層 v17，SPEC E2-C 2.6c，不需連結）。
**引擎那一半沒修，而且仍然擋著連結。**

## 2. 做完的五件事

### T0 — 清單現在會因為檢查紅而紅

`check_usable_editor.py --report <product-path JSON>`，self-test 8 → **24**。
四條規則：`done`／`partial` 必須有 check、那個 check 必須在報告裡而且綠、
`unverified`／`blocked` 的 check 綠了要說狀態過期、**報告本身必須是一次乾淨的
基線跑**。

「乾淨」不是旗標是**導出值**：runner 拿 v17 bundle 宣告的十二個模組、從伺服器
**實際指到的那個 root** 逐檔雜湊（`servedShell`）。突變鏡像與 shim 都會讓 digest
移動，所以忘不了。

`partial` 可以引用一個具名的 KNOWN_RED 當「沒涵蓋的部分」，但仍必須有一格自己的
綠檢查；`done` 一律不准。

**它第一次跑在真報告上就掉出 finding 060。**

### T1 — 059 的判準決定了：是 postcondition，不是「有沒有收到廣播」

預測先提交（`1d4992f`，樹裡沒有探針），再寫探針（`3faa693`）。

- **`wasModified` 出局，讀原始碼就夠**：它是 `DispatchResultListener` 建構時捕捉的
  `IsModified()`，在 `dispatchCommand()` **之前**（`init.cxx:5517-5518`）。
  三次獨立觀察到它照這個語意動。
- **廣播不能當判準**：核心廣播的是狀態**改變**；`value:false` 那幾臂一個廣播都沒有，
  而文件結果完全正確。站得住的是 barrier 已經在用的
  `formatBarrierPostconditionMet()`——比對觀察狀態與要求狀態。
- **四個 slot 都會廣播**，而 `probe_engine.cpp:4308-4310` 說底線與刪除線不在核心的
  `GetKitUnoCommandList()` 裡——**那句話是假的**，兩個都在
  （`unoctitm.cxx:1165ff`）。那句假話正是它們不留 state cache 的理由。

### T2 — WASM 那一半（見 §1）

### T2b — 殼層 v17：一個成功的動作不再叫你回檔

`LOK_COMMAND_FAILED` 回 `dispatched-unverified`。依據可查：那個碼**只**從引擎的
UNO command **result** handler 產生，且在酬載與送出的命令比對成功之後
（`probe_engine.cpp:2279-2291`）——核心回答了，所以「派送出去了」是知道的。

**它掉出一個沒預測到的後果**：佇列不再被擋，兩次按下都跑得完，
`bold-can-be-turned-off-again` **變綠了**——粗體從使用者的位置看真的關得掉。
所以 `turn-formatting-off` 從 `blocked` 改成 `partial`。

### T3a — 游標那兩格，判準改成錨定在**那一行自己的墨水**

`see-where-the-caret-is` 與 `put-the-caret-where-i-clicked` 都收復，060 關掉。

同一行點兩次（靠近行首、遠過行尾）：文字不動，所以多出墨水的那一欄是游標的第二個
位置、少掉的那一欄是第一個。**不需要引擎座標，也不需要 block identity。**
判準：靠近行首那次要落在該行墨水的前四分之一，遠過行尾那次要落在後四分之一。
實測 **-0.006 / 1.003**（span 355）。突變 `caret-ignores-x` 兩格都紅。

**具名極限**：這個判準靠看游標**移動**認出它，所以釘在固定欄位的游標與根本沒畫的
游標讀起來一樣——兩格會一起紅。

## 3. 沒做的（下一個接手的人）

| | 為什麼還在 |
|---|---|
| **T3b `format-a-paragraph`** | 五個動作（含 heading）、目標段落的狀態必須真的會變、判準錨在確切段落文字、鄰居要活著。計畫 §T3b 寫得很細 |
| **T3c `recover-from-an-error`** | fable 裁過的**三分支判準**（按 `#s-checkpoint` 的宣告分），誘發器用 038；計畫 §T3c 有完整設計，包含「欠一個與缺陷無關的第二誘發器」 |
| **T4 長文件的牆** | 事前推算已寫（dpr 1／2／2.67 → 約 26／13／10 頁），四道候選的牆，**必須掃 dpr**、**必須走 change#file**、**必須事前登記延遲門檻** |
| **T1.3 引擎修法** | 判準決定了，但**欠一個真的負向臂**（這一輪證明了判準會同意，沒證明它說得出不）與 state cache 的 priming（021 的形狀） |

## 4. 這一輪真正的教訓：**八次「什麼都沒量到」，沒有一次是核心**

T2 花了九輪。前八輪每一輪都產出一個**看起來可以解讀的 null**，而八個原因沒有一個
是「核心沒做」。這是本階段最貴、也最該記住的東西：

| 沒量到的原因 | 之後加的守衛 |
|---|---|
| manifest 宣告 `gestures: ["collapsed"]`，範圍選取時**頁面把按鈕 disable**，而 `click()` 對 disabled 按鈕不發事件 | 每一臂記錄按鈕 `disabled`；沒發出去的臂不計分 |
| 固定 sleep：每一臂讀回 `busy` ＋ 空 toast | 所有固定 sleep 換成等條件 |
| **游標定位每一臂都失敗**——點在八個字的行尾之外（052 的形狀） | 加寬語料；游標定位變成**要證明成立的前置條件**，多點嘗試並記錄哪個成立 |
| **產品開的是一張 404 頁**：`build_mirror` 只走來源樹，`dist/` 裡不存在的路徑其 override 被靜靜丟掉；而「檔案開起來了」原本比對的是**頁面被交給的檔名**，不是它讀到的位元組 | fixture 直接寫進鏡像；**開檔用位元組驗**；**三秒 preflight**（實測 404 對 200+PK 分得開） |
| shim 太窄：佇列擋在一個沒涵蓋的錯誤碼上，而**早退的 return 把會指名那個碼的 toast 丟掉了** | shim 涵蓋所有 dispatched failure；**失敗的臂也要交出它看到的東西** |
| 範圍那條路：`EDITOR_FORMAT_GESTURE_UNSUPPORTED`——mask 在**引擎那一側也有** | 這一條是**正確的負向**，不是 null；順帶成為 `p1-2-gesture-mask-inherited` 的第一個執行期見證 |

**一個中間結論被撤回**：「產品的插入路徑不帶游標格式」——那是在 404 頁面上量到的。
（原生相反：`paste` 會帶 pending 粗體。）

## 5. 具名留著的鬆頭

- **`insert-path-carries-formatting` 控制臂自己回來沒有樣式**，而產品的 `aria-pressed`
  說游標是粗體。四臂都是正的所以結論不依賴它，但**它的 null 沒有解釋**，游標在粗體
  run 裡的 offset 也沒有確立。
- **判準說不說得出「不」沒有證實**：拒絕臂（`setViewReadOnly`）**沒有拒絕**，核心
  照樣把字變粗。
- **state cache 的 priming** 沒量（021 的形狀）。
- **Firefox 一輪都沒跑。** 這一階段全部是 Chrome。

## 6. 不要重犯

- **不要把 a11y 當推力**（長期目標）。
- **不要撤回 `inlineFormatArgument`**（045 是對的）。
- **不要說 059 修好了**——修好的是**處置**，引擎那一半還在，使用者按下 B 仍然會看到
  一則說它失敗的訊息。
- **不要拿 shim 過的報告當驗收證據**——T0 現在會擋，但別去繞過它。
- **改 runner 的區段時，先確認你刪掉的區段裡沒有下游還在用的變數。** 本階段犯過一次：
  重寫游標那一段時把定義 `bold_toast` 的整個 bold 區塊一起刪了，`NameError` 才發現，
  從 git 逐行還原。
- **D0 一跑，殼層再動就得換矩陣。**
