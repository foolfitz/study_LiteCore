# 087 — 游標一移動，螢幕閱讀器拿到的是沒有結構的純文字：標題不會被唸成標題

| | |
|---|---|
| **狀態** | 已確認 |
| **Bugzilla** | 不送出——這是我方頁面的缺陷，不是上游 |
| **發現日** | 2026-09-03 |
| **嚴重度** | 阻斷（擋住 v12 cutover 閘門，裁決 2026-09-04） |
| **可重現** | 2/2（同一份 log 裡兩次；另一份語料的 log 再現一次） |
| **是否上游** | **否**——`web/e2-editor-app.js`，我方 |

## 現象

在候選 `e2-editor-v12` 上開一份有標題的文件，開著 Orca 把游標移到標題那一段，
Orca 唸出的是**光禿禿的段落文字**。它沒有說那是標題，也沒有說層級。

清單項目同理：符號在文字裡（`• E1-LC-BULLET-ONE`），而**沒有「清單項目」這個角色**。

出貨的 `e2-editor-v8` 沒有這個缺陷，因為它**什麼都不報**——`documentTextInTree: false`。
所以這不是退步，是**新功能沒有把它承諾的東西送到使用者面前**。

## 重現步驟

1. 服務候選頁面（`tools/serve_candidate_page.py --profile e2-editor-v12`，
   `pageSha256` 必須是 `3dfdcfef…`）
2. 開 `list-contexts`（或 `a11y-audible`）
3. 開 Orca 並把語音錄到 log：`orca --replace --debug-file=…`
4. 把游標移到標題那一段

**預期**：Orca 唸出標題的文字，並說明它是標題、第幾層。
**實際**：只唸文字。

## 證據

`evidence/manual-round-v12/orca-speech-3-agent.log`（已押的那份，15,216,073 bytes）

```
18:15:41.151744 - SPEECH OUTPUT: 'E1-LC-HEADING'
18:16:45.450255 - SPEECH OUTPUT: 'E1-LC-HEADING'
```

整份 log 裡沒有任何一行 `SPEECH OUTPUT` 帶標題角色或層級。

**而樹裡有。**同一份 log，18:15:41.184，Orca 自己 dump 出 `#a11y-structure` 的子節點：
`name='E1-LC-HEADING' role='heading' level:1 xml-roles:heading`。

`evidence/manual-round-v12/orca-speech-4-audible.log` 用另一份語料再現一次
（18:30:08 標題被唸成光禿禿的文字，結構節點仍帶 `level:1`）。

## 分析

**頁面有兩個投影，帶的東西不一樣，而被唸的是沒有結構的那一個。**

| 元素 | 帶什麼 | 何時被唸 |
|---|---|---|
| `#a11y-structure` | `role="heading"` ＋ `aria-level`、`role="list"`、`role="listitem"` | 只有 AT **瀏覽**該區域時 |
| `#a11y-para` | **只有 `textContent`** | **游標一動就唸** |

`e2-editor.html:237`：`<p id="a11y-para" aria-live="polite" aria-atomic="true">`
——AT-SPI 的角色是 `paragraph`。
`e2-editor-app.js:159-178` 的 `projectFocusedParagraph()` **只指派 `textContent`**。

所以編輯文件時最常做的事——移動游標——送出的是沒有結構的文字。

**這不是 Orca 的呈現選擇，是頁面的缺陷。**判準把好處拆成兩個環節，而這個失敗落在
**第一個**（引擎 → 頁面 → 樹），也就是「機器可量、擋門」的那一個。

### 4a 為什麼沒抓到——是覆蓋缺口不是分歧

4a 第 3 條選 `role == heading` 的節點（那是 `#a11y-structure`），第 4 條讀
`#a11y-para`。**沒有任何一條 4a 判準斷言「游標移動所改變的那個節點帶角色」。**

所以 4a 和 4b **對樹是一致的**（Orca 的 dump 和 4a 找到同一個 `level:1` 節點）。
它們讀的是不同節點。裁決因此給 4a 加了第 8 條，讓解封靠機器檢查而不是靠一次
Orca session。

## 修法的界限，先寫下來

**「把角色當文字寫進即時區域」不算修好。**產品自己的原始碼（roadmap 3.4）承諾的是
**可程式判定的結構**，不是唸得出來的字；4a 第 8 條明文排除那條捷徑。

**兩個候選機制都未量測**：（一）在即時區域的節點上放角色——Orca 的即時區域呈現
在 log 裡只帶文字，**它會不會唸出放上去的角色是未知的**（那裡現在有 `paragraph`
這個角色，而那是 Orca 從不唸的一個，所以它的沉默證明不了任何事）；（二）用
`aria-activedescendant` 從 `#sink` 指進 `#a11y-structure`。**兩個都要先用 Orca 量過
再相信。**

## 代價

修法落在 `web/e2-editor-app.js`——殼層 bundle 十三個 included 路徑之一，也是候選頁面
自己的來源。**`pageSha256` 會移動**，而那個值在 soak 的乾淨判準裡。

所以：12 筆乾淨 run（修好之後跨 ≥3 個 UTC 日）、3 筆 diagnostic、4a 八條、revert 演練
含 step 3、ODT 雙向、人工輪含 4b（**方向鍵、焦點全程不離開**）全部重賺。
**不需要**改引擎、重新連結或重新打包 profile。

## 環境

```
候選頁面 3dfdcfef4abfe6b7…（e2-editor-v12）
殼層     editor-shell-v2-bundle-v43（7e99d3a3b8ba789b）
Orca     由代理人驅動，擁有者明確同意（evidence/manual-round-v12/CONSENT.md）
瀏覽器   有頭的 Chrome，--force-renderer-accessibility，開在擁有者的桌面 session
```
