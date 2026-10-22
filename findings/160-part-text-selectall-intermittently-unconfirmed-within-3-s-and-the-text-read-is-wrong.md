# 160 — `part_text` 的 `.uno:SelectAll` 間歇性在 3 秒內沒等到命令結果；那一次讀到的文字是錯的（全語料 482 次讀取中 2 次）

| | |
|---|---|
| **狀態** | **已觀察、間歇**（2026-10-20）；未修 |
| **Bugzilla** | 無 |
| **發現日** | 2026-10-20（`phase-e/report-2026-10-20T133240Z.json`） |
| **嚴重度** | 一般：E3 會抓到（`selectAllConfirmed: false` 加文字不等）。~~但在產品路徑上就是讀到錯的文字~~（2026-10-21 更正：產品頁面、session、adapter 沒有任何地方呼叫 `partText`，呼叫它的只有 E3；所以這是 E3 的量測儀器與 SDK 能力 `part-text` 的正確性問題，使用者看不到。`SPEC-M4-viewer-v2` §0） |
| **可重現** | **2／482**（全語料那一輪：`tdf160329_sortWithHiddenRows.ods` 讀到 1 個字、`tdf139258_rotated_image.ods` 讀到空）；診斷重跑同兩筆 **0／2**（都 `true`、文字正確）。次數就是量測，別拿單次下結論 |
| **是否上游** | 否（我們的引擎，`probe_engine.cpp:2632-2690`） |

## 現象

A4.7 把 `part_text` 改成「最多等 SelectAll 的 `UNO_COMMAND_RESULT` 3 秒，等不到也照讀、照取消、照切回，回覆 `selectAllConfirmed: false`」。
全語料的 10 分鐘 sweep 裡有 2 次走到這條路：`tdf160329` 期望 74 字讀到 1 字（選取還沒落地就讀）、`tdf139258` 期望空讀到空（碰巧對）。
兩筆單獨重跑都在 3 秒內確認。

## 讀法

- 這不是 A4.7 的錯——它如實說了原因，E3 也因此紅在對的地方。**是 3 秒在負載下不夠**，或 SelectAll 在某些文件（隱藏列、只有圖片的表）
  上偶爾不回 `UNO_COMMAND_RESULT`。兩個假說都沒證據，不指認。
- 不在 harness 裡重試：重試會把產品的時間弱點藏起來。E3 對未確認的讀取保持紅，次數記在 handoff。

## 下一步

- 把 `kPartTextSelectAllDeadlineMs` 拉長或改成「等到選取真的存在」（讀回 `getTextSelection` 非空或 `SelectAll` 的 state 變化）要**連結**；
  排進下一個檢視連結（與 finding 157 的 `part_info` 同批）。
- 在那之前，若要量發生率：同一份全語料再跑 N 次、數 `selectAllConfirmed: false` 的次數。

## 10 秒的期限沒有用（2026-10-22，`ods-viewer-v2` `e96e01ec`）

v2 把期限拉到 10 s，回覆帶 `selectAllWaitMs` 與 `lateSelectAllResults`（SPEC-M4-viewer-v2 §3.3）。全語料 ×3（`findings/evidence/m4-ods/viewer-v2/fallback-phase-e/full-corpus/`）：

- 未確認 **0、2、1／464**：`tdf115655_HideDetail.ods`、`tdf125938_anchor_after_copy_paste.ods`、`tdf137082_LTR_arrow_image.ods`，都是 part 0、都等滿 10,001 ms。
  與 10-20 那兩筆不是同一批檔——間歇、不挑檔〔已觀察〕。
- 已確認的 1,389 次等待最多 **106 ms**；106 ms 到 10 s 之間 0 次。v1（3 s）2／1,392，v2（10 s）3／1,392。
- **假說一（3 秒在負載下不夠）駁倒**〔推論，強〕：如果只是慢，拉長期限會救回一些；一筆都沒有，時間分布是兩極的。**假說二留著**：SelectAll 偶爾
  不回 `UNO_COMMAND_RESULT`，或晚得遠超過 10 s。
- `lateSelectAllResults` 分不出這兩者：每份檔一顆新引擎，計數器在每份檔的最後一讀之後是瞎的；同一份檔的下一讀期間晚到的結果會被當成下一讀的確認
  （`notePartTextUnoResult` 只比對 payload 有沒有 `.uno:SelectAll`）。SPEC-M4-viewer-v2 §7.7。

**下一步（要連結）**：不要再靠拉長期限。候選：等到選取真的存在（`getTextSelection` 非空，或 SelectAll 的狀態變化）、或逾時後重送一次 SelectAll；
要分「晚到／沒來」就要讓計數器在關檔前看得到（例如關檔時把未認領的結果數放進最後一個回覆），並且讓結果帶得出它是哪一次的請求。產品不呼叫
`partText`，所以這仍是 E3 儀器與 SDK 能力的問題。

## 成因：SelectAll 根本沒派送出去（2026-10-22，從既有報告讀到）

**已觀察**：6 趟全語料（v1 `f6ab3cdb` 三趟、v2 `e96e01ec` 三趟）共 5 次未確認，**每一次**那份檔的引擎 stderr 都有
`warn:lok:…:desktop/source/lib/init.cxx:285: lok exception 'Failed to dispatch .uno:SelectAll'`；其他任何一份檔、任何一趟都沒有這一行。
一對一：`133240Z` 2／2、`023406Z` 2／2、`024415Z` 1／1、其餘三趟 0／0（`messages` 欄，報告本來就記著）。

- 所以不是「晚到」也不是「選取做了但通知丟了」：**指令沒有被派送**，沒有 listener 被呼叫、沒有結果、選取也沒做（`tdf125938` 等了 10 s 仍讀到 6／14 字）。
- **暫時性的**：`tdf125938` 第 0 張表失敗後，第 1 張表的 SelectAll 成功（同一份 stderr 有它的 `UNO_COMMAND_RESULT`，`success: true`）。
- 5 次都在 part 0（開檔後的第一次讀取）。讀取中約三分之二是 part 0，所以這只是傾向，不是證據。

**為什麼派送會失敗**〔由原始碼推論，未量〕：`doc_postUnoCommand`（`desktop/source/lib/init.cxx:5514-5525`）用的是不帶 frame 的
`comphelper::dispatchCommand`，它的目標是 `Desktop::getActiveFrame()`（`comphelper/source/misc/dispatchcommand.cxx`），沒有作用中的 frame 就退回 Desktop
本身，找不到派送就回 false，LOK 記下 `Failed to dispatch`。設 Desktop 作用中 frame 的是 `SfxLokHelper::setView`（上游註解：「Make
comphelper::dispatchCommand() find the correct frame」，`sfx2/source/view/lokhelper.cxx:231`），但目前的 view 已是它時會提早 return。
Calc 的 `queryDispatch` 查的是靜態的 slot pool，不依賴殼層堆疊，所以「frame 不對」是最可能的那一個。

**修法的方向**：引擎在每次 post 之後讀 `getError()`；是 `Failed to dispatch .uno:SelectAll` 就稍等再送，直到期限。訊號是 LOK 自己給的那一句，不靠回呼、
不靠計時。另一條路是核心 patch（`doc_postUnoCommand` 改派送到文件自己的 frame），比較乾淨，但要重建核心；先不走。
原生對照在跑（`findings/evidence/m4-ods/viewer-v2/160-native/`），它決定這是不是 LOK 本身的行為（可送上游；上游送出仍擱置）。
