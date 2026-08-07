# 020 — LOK 清單命令的 command result 與文件實際結果矛盾

| | |
|---|---|
| **狀態** | **已確認（原生 26.8）／待搜重複單** |
| **Bugzilla** | — |
| **發現日** | 2026-08-05 |
| **嚴重度** | 嚴重（會使 completion 判定得到相反結論） |
| **可重現** | 100%（原生 26.8，單次 run 內三個命令對照） |
| **是否上游** | **候選為是**；在原生 stock 組態、`svp` backend 上重現，未經自訂旗標 |

## 摘要

`LOK_CALLBACK_UNO_COMMAND_RESULT` 的 `success` 與 `wasModified` 欄位，在 Writer 清單命令上與文件的實際結果
不一致：

| 命令 | command result | 文件實際結果 |
|---|---|---|
| `.uno:RemoveBullets` | `success: false`、`wasModified: true` | **有效**：段落離開清單，樣式回到 `Standard` |
| `.uno:DefaultBullet` | `success: true`、`wasModified: false` | **有效且已修改**：段落被包進 `<text:list><text:list-item>` |
| `.uno:DefaultNumbering` | `success: true`、`wasModified: true` | 有效（一致） |

也就是說 `success` 在一個命令上是假的否定，`wasModified` 在另一個命令上是假的否定。任何以這兩個欄位判定
「操作是否成功、文件是否改變」的 client，都會在這兩個命令上得到相反答案。

## 最小重現

以原生 LibreOfficeKit 開啟一份含普通段落的 ODT，把游標放在該段落，依序派送
`.uno:DefaultBullet`、`.uno:DefaultNumbering`、`.uno:RemoveBullets`，每次派送後 `saveAs` 成 ODT，
再比對 `content.xml` 與 command result。

```bash
wasm_sdk_probe/tools/run_e2_a_native.sh
```

**預期**：`success` 反映命令是否生效，`wasModified` 反映文件是否被修改。  
**實際**：見上表。文件證據取自存檔內容，與被檢驗的 callback 無關。

## 證據

- callback 串流與逐步存檔：`findings/evidence/sdk-e2/discovery/state-readback/native-26-8/`
- `after-bullet.odt`：目標段落位於 `<text:list-item>` 內（`.uno:DefaultBullet` 宣稱 `wasModified:false`）。
- `after-remove.odt`：目標段落回到 `text:style-name="Standard"` 且不在清單內
  （`.uno:RemoveBullets` 宣稱 `success:false`）。
- 三個命令的 `LOK_CALLBACK_STATE_CHANGED` 都正確反映最終狀態，與存檔一致。

## 已觀察／推論／待驗證

### 已觀察

- 三個命令都確實改變了文件；三個命令的 state callback 都與存檔一致。
- 只有 command result 的兩個布林欄位與事實不符。
- command result 在派送後 1～4 ms 抵達，state callback 在 301～602 ms 後才抵達；兩者不同步。

### 推論

- `success` 可能反映 slot 執行路徑的某個內部回傳，而非「使用者可見的操作是否達成」；`wasModified` 可能
  在部分路徑未被設定。本 finding 不宣稱知道 core 內部原因。

### 待驗證

- 上游 Bugzilla 是否已有相同回報。
- WASM profile 是否得到相同的矛盾（原生已確認，瀏覽器尚未）。
- 其他 Writer 命令是否也有同類不一致；本次只測三個清單命令。

## 影響與目前決策

- **command result 可以用來做歸屬，不能用來做真值。** 它帶有 `commandName`，這正是廣播式 state callback
  缺少的東西；但它的成敗欄位在此已被證明會說謊。
- E2-A 的 completion barrier 因此定為：**匹配的 command result（歸屬）＋ 期望的 state postcondition（真值）**，
  兩者皆備才算完成。不接受單獨任一項。
- 這也解釋了為什麼不能退回「用 `success` 判定」的簡單做法 —— 那會讓 `set-list-none` 每次都回報失敗。

## 送出前還缺

- [ ] 搜尋 Bugzilla 重複單。
- [ ] 確認在完全未修改的上游 build（非本專案 worktree）重現。
- [ ] 一張單只講一件事：`success` 與 `wasModified` 若判定為不同成因，需拆成兩張。

## 環境

- Core commit：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- 原生建置：`build-native-26-8`，`SAL_USE_VCLPLUGIN=svp`
- Fixture：`wasm_sdk_probe/test-docs/e1/styled-list.odt`

## 時間軸

- 2026-08-05：E2-A 的 A2 原生 state-readback 以逐步存檔為獨立真值來源，發現三個清單命令中兩個的
  command result 與文件矛盾，建立 finding。
