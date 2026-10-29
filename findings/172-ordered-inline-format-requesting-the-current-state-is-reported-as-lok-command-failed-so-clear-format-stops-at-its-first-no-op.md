# 172：有序路徑把「要求目前已經是的格式狀態」判成 `LOK_COMMAND_FAILED`，清除格式在第一個 no-op 就中斷，後面的格式沒被清掉

| | |
|---|---|
| **狀態** | 已確認（文件存檔＋Worker 回覆）／**v25 已修並量過**（F1、F2，2026-10-29）；尚未出貨——宿主仍是回退後的 0.2.38 引擎 |
| **Bugzilla** | —（本樹缺陷） |
| **發現日** | 2026-10-29 |
| **嚴重度** | 中——使用者可見：清除格式跳出 `LOK_COMMAND_FAILED` 而且沒清乾淨；接著工具列的斜體等按鈕顯示「開著」，按下去反而送出「關」 |
| **可重現** | v24：diag run-01/02（2/2）、H3、T4、four-arms-counted-01；v23：10-27 integration。v21、v22：0 次 |
| **首次出貨** | 宿主 0.2.39（v24） |

## 現象（`k-nine-cells/diag-format/run-0{1,2}`，同一個步驟序列）

游標放在普通文字裡：斜體 → 打 `MKITALON` → **清除格式** → 打 `MKAFTERCLEAR` → 斜體 → 打 `MKITALAGAIN` → 粗體 → 打 `MKBOLDON` → 清除格式 → 打 `MKAFTERCLEAR2`，最後存檔。

| 存檔裡的標記 | v22 | v24 |
|---|---|---|
| `MKAFTERCLEAR` 斜體 | 否（已清） | **是**（沒清掉） |
| `MKITALAGAIN` 斜體 | 是 | **否**（按斜體反而關掉） |
| `MKBOLDON` 斜體 | 是 | 否 |

v24 的 Worker 回覆：第一次清除格式的 `set-bold {enabled:false}`（當時粗體本來就關著）回 `LOK_COMMAND_FAILED`；第二次清除格式的 `set-italic {enabled:false}`（斜體本來就關著）回 `LOK_COMMAND_FAILED`。v22 兩次清除格式，四個動作全部成功。

## 機制（讀碼＋上面的量測）

1. 清除格式是頁面依序 `await` 四個動作：`set-bold`／`set-italic`／`set-underline`／`set-strikethrough`，每個都帶 `{enabled:false}`（`web/e2-editor-app.js` `clearInlineFormatting`）。任一個拋錯，後面的就不送了。
2. finding 059：參數化的 inline 格式，core 有照做卻回 `success:false`。所以引擎改用 `inlineFormatArgumentResolved` 救回：問格式狀態有沒有等於要求的值。註解明說要問的是**狀態**，不是**事件**，因為要求游標已經是的狀態時，core 根本不會廣播（`src/probe_engine.cpp:2190-2197`）。
3. v23 在這個函式最前面加了 `if (!gOrderedProof.stateItems.count(unoCommand)) return false;`（`probe_engine.cpp:2209-2212`，`9b6d4a6fb`，2026-10-25）：本次分派期間沒收到該格式的廣播，就判不成立。這正好把第 2 點刻意排除的情況加了回來：no-op 要求沒有廣播，於是 `success:false` 沒被救回，回報 `LOK_COMMAND_FAILED`。
4. 清除格式的第一個 no-op 一失敗就中斷，斜體等留在原狀態。頁面的格式快取（正確地）顯示斜體還開著，使用者再按斜體時頁面送出 `enabled:false`，結果是關掉。

## 連帶的格子

- `every-inline-format-reaches-the-document`（Chrome、Firefox NE）、`clear-format-removes-every-inline-format`（Chrome NE）：前置的「先清除格式歸零」中斷，前提建立不起來。
- `an-inline-format-reaches-a-selection`（Chrome FAIL）：v22 的拖曳選到不是粗體的 `KITAL`，v24 選到已經是粗體的 `KBOLD`（`wasBoldBefore: true`）。選中的是不同的行（y 0.389 對 0.342），因為前面格式那幾格留下的文件不同。**沒有量到「選取範圍套粗體」本身失敗**；這一格掛在本 finding 底下，修好後重量。

## 修法方向（2026-10-29 已由裁決 Q1 決定，見下一節；以下為當時的原文）

- 引擎：有序路徑下，同步分派完成時，若「分派前的狀態已等於要求」且沒有廣播，應該判成立（在 unipoll 有序分派裡，會改變狀態的指令其廣播在分派內就會到）。這需要先釐清 `9b6d4a6fb` 加這道條件想防的是什麼（看起來是不想拿分派前的快取當證據），屬於判斷題。
- 頁面：清除格式可以逐個送、不因一個失敗就中斷（它本來就「什麼都不聲稱」）。這能減輕症狀，但第 3 點的錯誤回報仍在。
- 兩者都會產生新身分（引擎→v25 連結；頁面→新頁面雜湊）。

## 修法與量測（2026-10-29，v25）

- 修法（裁決 Q1 的 (a′)，規格 `SPEC-M3-link-batch-v25` §4.1，全部在 `OXSDK_E2_V25_FORMAT_PROOF` 之下）：有序路徑照常派送；`success:false` 而且本次 flush 沒有該狀態項時，若快取已知且等於要求，判「已驗證的 no-op」，回覆與真的改變相同，多帶 `witness`（`uno-success`／`on-time-item`／`state-noop`）。`inlineFormatArgumentResolved` 本身不改。
- 量測一（`findings/evidence/link-batch-v25/f1/`，上面「現象」的同一步驟序列，Chrome 3 回）：v25 存檔的 `MKAFTERCLEAR` 不是斜體、`MKITALAGAIN` 是斜體（與 v22 相同），沒有任何格式回覆失敗；no-op 的要求在引擎紀錄裡是 `state-noop`。v24 同工具 3/3 重現本 finding。〔實測〕
- 量測二（`findings/evidence/link-batch-v25/f2/`，普通文字上連按兩次清除格式、判第二次，兩瀏覽器各 3 回）：v25 四個回覆都 ok、witness 都是 `state-noop`；v24 在 `set-bold` 就 `LOK_COMMAND_FAILED`。〔實測〕
- 量測時學到的觸發條件：**剛放好游標後的第一次清除格式不會觸發本 finding**——LOK 在那次 flush 裡會廣播四個狀態項，v24 也回四個 ok。觸發需要「狀態沒變所以 LOK 不重播」，也就是之前已經按過格式或清除過一次。上面「機制」第 3 點的敘述不變，只是補上 LOK 何時不廣播。〔實測〕
- 仍待：F3（product-path 一般臂）上 `every-inline-format-reaches-the-document`（兩瀏覽器）、`clear-format-removes-every-inline-format`、`an-inline-format-reaches-a-selection`（Chrome）要 PASS，才算對 K 的處置解除；出貨要等宿主新版本與 DDEV 時段。

## 對 K 的處置（裁決修正一）

上述四格都是**產品缺陷**（其中選取那一格是連帶結果，修好後重量），修好之前判紅。

## 證據

`findings/evidence/host-0.2.39/k-nine-cells/diag-format/run-01/`、`run-02/`（含兩邊存檔的 ODT）；定位見 finding 171 的證據段。
