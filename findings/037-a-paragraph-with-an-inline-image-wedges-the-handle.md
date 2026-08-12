# 037 — 對「含行內圖片的段落」派送格式動作會卡死 document handle，而 deadline 沒有救到

| | |
|---|---|
| **狀態** | **已確認（兩個 build 各一次，行為一致）／未修** |
| **Bugzilla** | —（我方 barrier；COMPLEX 選取本身是 core 行為） |
| **發現日** | 2026-08-12 |
| **嚴重度** | **嚴重**——不是拒絕而是**卡死**，整個 session 之後的操作全部逾時 |
| **可重現** | 2/2（`ee185b3d` 與 `38168306`，同一份 fixture、同一列） |
| **是否上游** | **否**（我方 format barrier） |

## 摘要

對一個**含行內圖片**（`draw:frame` `text:anchor-type="as-char"`）的段落派送封閉格式動作
（實測用 `set-list-none`），barrier 不會回來：

```
editorDiscoveryAction   timed out after 20000 ms   ← 動作
search                  timed out after 30000 ms   ← handle 已經不回應
handleUsableAfter       false
（之後每一列）editorDiscoveryGetState timed out after 30000 ms
```

**引擎的 5 秒 per-stage deadline 沒有讓它以 typed 失敗收場。** 那個 deadline 是
[034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md) 那一輪
從「縱深防禦」升格為**必要配件**加進去的，理由正是「採用 `.uno:SelectText` 會製造出
可達的 stall」。這裡就是一個它沒接住的 stall：動作在 **20001 ms** 死於用戶端逾時，
而不是在 5000 ms 死於 `stage-deadline:*`。

文件本身還關得掉（`closeMs: 10906`），所以卡死的是**操作**不是整個 worker。

## 這一列有什麼不一樣

`PC-IMAGE` 是 M2 的 21 種段落形態裡**唯一 `selectionType` 是 3
（`LOK_SELTYPE_COMPLEX`）的一列**，其餘 20 列都是 1（`LOK_SELTYPE_TEXT`）。
原生 26.8 量到過（`paragraph-content/native-26-8/`），當時只記成一則註記，
因為 barrier 的判定**完全沒有讀 selection type**。

原生那一輪讀得回 markup（798 bytes，`<img …/>` 巢狀在 `<p>` 裡，錨點文字也在），
**所以問題不在序列化器**，而在 wasm 側 barrier 的階段推進。

## 不是這次改動造成的

`ee185b3d`（本次結構深度 parser）與 `38168306`（改動前、A3/A4/A5 現行綁定）
**各跑一次，同一列都在 20001 ms 逾時、同樣沒有 readback**。

這件事本來無法斷定：新 parser 是純字串處理、跑在 readback 之後，理論上造不出 20 秒停頓，
但「理論上」不是證據，而舊 build 從沒在這份 fixture 上跑過。
把 `build/archive/e2-format-discovery-38168306/` 換進 `dist/profiles/`
跑同一份 app、同一批 21 列，再換回來——**這是既存缺陷，只是新 fixture 才讓它被看見**。

證據：`paragraph-content/wasm-ee185b3d/` 與 `paragraph-content/wasm-38168306-control/`，
各自附 `ARTIFACT.sha256`。

## 為什麼 375 次判定派送一次也沒碰到

同 [034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md)／
[035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)
的形狀：A3／A4／A5 的錨點段落全是純文字，**沒有一份既有 fixture 的被派送段落帶行內圖片**。
`r7-t2-styled.odt` 裡有圖片，但它不是任何一輪的派送目標。
覆蓋軸從來沒進過矩陣——這是同一個病第三次以不同的軸出現。

## 它害掉了什麼（方法論代價）

第一次跑這批討論器時 `PC-IMAGE` 排在第 16 列。它卡死之後，**後面五列全部連鎖失敗**
（`pc-break`、`pc-cjk-bold`、`pc-section`、`pc-footnote`、`pc-list-item`），
其中 `pc-footnote` 正是整個 (a′) 裁決所依賴的那一列。

把它移到最後重跑才拿到那 20 列。**測項的順序影響了哪些事實能被觀察到**——
這不是整理癖，是證據完整性：一個會卡死 handle 的案例排在中間，等於讓它後面的每一項
都變成「未量測」而不是「失敗」，而兩者在報告裡長得很像。

## 沒有做的事（誠實界線）

- **卡在哪一個 stage 沒有量到。** page log 裡 20 筆 `stage":"awaiting-restore"` 是那 20 列
  各自的收尾，不是這一列的現場；`PC-IMAGE` 沒有回來，所以它的 stage 沒有被寫出來。
  要定位得在引擎側加一條「逾時當下把現行 stage 印出來」的探針。
- **沒有分辨是選取階段還是還原階段卡住。** COMPLEX 選取下
  `setTextSelection(LOK_SETTEXTSELECTION_RESET, …)` 的行為未量測。
- **只量了 Chrome、只量了 `set-list-none`。** 其他四個封閉動作、Firefox 都沒跑。
- **沒查上游重複單。** 是否有既知的「LOK COMPLEX 選取下某操作不回 callback」單未查。

## 相關

- [034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md)——deadline 就是那一輪加的，這裡是它沒接住的一個 stall。
- [035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)——同一批 M2 量測逼出來的；那一單是 fail closed，這一單是卡死。
- [016](016-lok-forward-delete-completion-gap.md)、[018](018-lok-line-navigation-completion-nondeterministic.md)——同屬「completion 訊號不來」這一族。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md)
