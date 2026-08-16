# 交接 2026-08-16b — D3／D4／D5 都跑完了，relink 的門檻達成，佇列多了兩項

上一份是 [`HANDOFF-2026-08-16-e2c-d3-done-048-fixed.md`](HANDOFF-2026-08-16-e2c-d3-done-048-fixed.md)。
本輪的計畫是 [`PLAN-2026-08-16-autonomous-queue.md`](PLAN-2026-08-16-autonomous-queue.md)。

## 一分鐘版

- **對抗性審查第 8 項的門檻達成**：D2～D5 全部寫好並在 v2 上跑過。
  D3 的語料半邊 **PASS**、D4 **PARTIAL**、D5 的機器半邊 **PASS**、人工四格待 operator。
- **048 的引擎側機制量掉了**：原生點擊 0.6 ms，瀏覽器 22–28 ms。兩個假說都出局，
  但**只排除 core 的點擊處理，不指認肇因**（040 的前例）。
- **E1-C 的收復已裁決＝延後**，解除條件具名（SPEC E1-C §11.8）；同時修好一個
  **紅了一整天沒人看見**的靜態目標。
- **relink 佇列多了兩項**，兩項都是跑 D3／D4／046 才知道的：引擎要報 WASM heap、
  barrier 要驗自己動過的那一段。**3b 仍不能寫**，卡住的問題換了一個更尖銳的。
- **矩陣 v2 草稿已寫**（84 格），這一輪量到的每一件都寫成「跑之前就存在」的判準。

## 現在的狀態

| | |
|---|---|
| 分支 | `main`，工作樹乾淨（`AGENTS.md`／`CLAUDE.md` 仍未追蹤，不是這兩輪產生的） |
| 出貨 profile | `e2-editor-v2`（wasm `572035ac…`），**一個位元組都沒動**（每一輪掃描前後都核對） |
| 殼層 bundle | E2 仍是 v3 `34e95e10…`（D5 的觀察沒有動到它，前後都記） |
| 靜態 | `test-e2-c-static` exit 0；**`test-e1-c-static` 也 exit 0**（本輪修好） |
| E2-C 判定 | 仍是第一輪的 `E2_STOP_OR_RESCOPE`。D3／D4／D5 的結果**不改變它**——改變它要等 relink 後的第二輪 |

## 五件做完的事

### 1. `test-e1-c-static` 的恆紅（`d2afc8a`）

它從 08-16 早上起紅在**三處**（`tests/test_e1_c.py` 兩條 ＋ 配方最後一行的
`regenerate_shell_bundle.py`），三處都不認 divergence 檔。一個在申報期恆紅的靜態
目標，正是 intact 守衛自己註解裡警告的「會被關掉的守衛」形狀。

申報判定抽成一份共用規則（`e1_support` 的 `declared_divergences`／
`classify_divergence`），三處都改用它。**裁決路徑一個字沒動**——`validate_e1_c.py`
仍是嚴格比對、`intact` 仍是 `false`。**放寬的邊界由六個突變釘住**（沒申報／已申報
又動一次／旁邊加檔／dist 不一致／申報對不上位元組全部仍然紅），四個已寫進
`--self-test`。

### 2. D3 的語料半邊（`c986919`）

八格兩瀏覽器全過、carried 兩份全過、桌面重開與 PDF 全過。掉出兩件：

- **`l4-stress-100` 的 100 張圖存出來變零**——這是停止條款的形狀，但**兩個
  LibreOffice build 在完全沒有編輯的 ODT→ODT 轉換下也全部丟掉**。語料缺陷，
  不是產品缺陷。判準改成與「什麼都不做的存檔」比較。
- **第一輪三格被我自己的容差常數擋掉**（195 twips 是清單語料算出來的，標題行 520）。
  改用量到的行框重疊，沒有常數。

一條預測不成立（P-C5，`c-l1-review` 的追蹤修訂 ID），**照原樣記**。

### 3. D4（`647524e`）：`PARTIAL`

`d4-sessions`／`d4-residuals` 全過，`d4-regression` 11 個目標全綠、artifact 未變。
**`d4-memory` 是 PARTIAL：產品沒有任何路徑報得出 WASM heap。** 這是 D4 掉出來的
relink 佇列項。另記 Firefox 的 PSS 斜率 7.52／8 過但絕對成長 +35.1 MB，
**我自己登記的預測第二子句因此不成立**——格子與預測分開計分。

### 4. 046 的原生量測（`1b65072`）

**空段落上，barrier 的選取對會把游標往上帶一段，讀回描述上一段**——而**動作是
成功的**（存檔證明空段落確實變成 list item）。所以不是「bullet 沒生效」，
是「檢查看了別的地方」。

引擎自己的 parser 另外定案兩件：**空的讀回是 `parsed = false`**（不是「parsed 但
零 block」）；「零 block ＋ itemCount ≥ 2」確實是「沒有 block 的 multiBlock」。

**3b 不撤回也還不能寫**：core 說「上一段、一個 block」，出貨 build 說「零個 block」，
兩者不一致。

### 5. D5 的機器半邊（`666fa0c`）＋矩陣 v2 草稿（`bee15a6`）

產品頁面**一個位元組都沒動**——它在殼層 bundle 裡，所以 D5 頁面把它放進同源 iframe
從外面觀察，`URL.createObjectURL` 的 shim **明寫在證據裡**。四條機器半邊的預測全部
成立，自我測試 10／10，承重的一對是「補齊其他條件會過、翻一個事件成合成就不過」。

矩陣 v2 草稿 84 格，五個雜湊全是佔位字串、`status` 是 `DRAFT-NOT-FROZEN`
（v3 還不存在，出現真雜湊就代表是抄來的）。

## relink 佇列的現況

| 項 | 狀態 |
|---|---|
| 1 inline 參數、2 gesture mask、3 route 不謊報、4 ABI → 3、5 Makefile v3、6 builder、7 header test | **在樹裡**（第二方稽核逐項查過） |
| 3c `itemCount` 進投影 | **做完**（引擎那半本來就在，worker 投影本輪補上） |
| 8b `routeFormatBarrier` 的 `selectionObserved` | **做完**（審查說「一併修」但實際沒修，本輪修） |
| 9b `inlineFormatEnabledIsHonoured` | **已記進規格**（樹裡有、文件沒有的 manifest 宣告） |
| **3b `empty-readback`** | **仍不能寫**——卡住的問題換成 native／WASM 的不一致 |
| **新：引擎報 WASM heap** | 待做。沒有它，第二輪的 `d4-memory` 一樣只能 PARTIAL |
| **新：barrier 驗自己動過的那一段** | 待做。比 046 原本的改名修法更根本 |
| 矩陣 v2 | **草稿已寫**，等 v3 的五個雜湊才能凍結 |

**P1 完成才能 relink。漏一項就是第二次 relink。**

## 下一步（沒有排序）

1. **relink 本身**——由使用者決定。佇列的門檻（D2～D5 寫好並跑過）已經達成，
   但佇列本身還有三項未完成（3b、引擎 heap、barrier 段落）。
2. **operator 時段**：D5 的四格 ＋ E1-C 的收復。**兩者要的設置完全一樣**
   （Fcitx5 新酷音、真剪貼簿、可信指標事件），而 §11.8 指名的解除條件正是這個時段。
3. **048 剩下的四十倍**：0.6 ms 與 22 ms 之間還沒分成「我們的 transport」與
   「Emscripten 主迴圈整合」。下一個可控變數已寫進 048。
4. **native／WASM 對空段落讀回的不一致**（3b 卡住的地方）——這是一個新的量測，
   不是一個決定。

## 這一輪的三個教訓

- **沒有人跑的檢查會爛掉，而且會在最需要它的那天爛著。** `test-e2-a-static` 從
  08-15 起紅著沒人跑過；`test-e1-c-static` 紅了一整天；`regenerate_shell_bundle`
  的 patch 錨點失配讓診斷 profile 建不起來——三件都是同一個形狀。
- **下結論之前先做對照，尤其是當結論看起來像停止條款的時候。** `l4` 的 100 張圖
  存出來變零，看起來就是「清單動作造成內容遺失」；兩個對照（系統 LO、原生 build，
  都沒有編輯）把它變成語料缺陷。
- **量到的幾何打敗算出來的常數。** 195 twips 在清單語料上是對的、在標題行上是錯的，
  而錯的方式是「擋掉正確的落點」——最難發現的那一種。
