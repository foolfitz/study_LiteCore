# 019 — E1-A 段落樣式映射到 UI 別名，該名稱不是可派送命令

| | |
|---|---|
| **狀態** | **已確認（專案 SDK 映射缺陷）／E2-A 已定位修法** |
| **Bugzilla** | — |
| **發現日** | 2026-08-05 |
| **嚴重度** | 嚴重（使一項候選能力在 E1-A 被誤判為 completion 缺口） |
| **可重現** | 100%（原生 26.8，同一次 run 內以別名與參數化命令對照） |
| **是否上游** | **否**（專案 SDK 內部映射） |

## 摘要

`src/probe_engine.cpp` 把 `set-paragraph-heading`／`set-paragraph-body` 映射到 `.uno:Heading1ParaStyle` 與
`.uno:TextBodyParaStyle`。這兩個名稱在 LibreOffice 全樹**只**出現在
`officecfg/registry/data/org/openoffice/Office/UI/WriterCommands.xcu` 的 `UserInterface/Popups` 節點，**沒有
任何 `.sdi` slot 定義它們**。它們是選單項目的別名，其 `TargetURL` 指向參數化的 `.uno:StyleApply`。

以 `postUnoCommand()` 派送別名字串等於什麼都沒做：不改文件、不回 command result、不送 state callback。

E1-A 因此把段落樣式歸類為「fixed command 沒有回 UNO command result」的 completion 缺口。**這個歸因是錯的** ——
不是命令沒有回應，是那個字串根本不是命令。

## 最小重現

原生 26.8，同一份文件、同一個游標位置，先後派送兩種形式：

```text
.uno:Heading1ParaStyle                          → 無 result、無 state、文件不變
.uno:StyleApply  {"Style":"Heading 1",
                  "FamilyName":"ParagraphStyles"} → success:true、
                                                    .uno:StyleApply=Heading 1、
                                                    text:style-name=Heading_20_1
```

重跑：`wasm_sdk_probe/tools/run_e2_a_native.sh`

## 證據

- 原始 callback 串流與逐步存檔的後置條件 ODT：
  `findings/evidence/sdk-e2/discovery/state-readback/native-26-8/`
- `after-heading-alias.odt` 的目標段落仍為 `text:style-name="Standard"`；
  `after-heading.odt` 為 `Heading_20_1`。兩者由**存檔內容**判定，不是由 callback 判定。
- 別名定義：`officecfg/registry/data/org/openoffice/Office/UI/WriterCommands.xcu:3881`（heading）、
  `:4033`（body），`TargetURL` 分別為
  `.uno:StyleApply?Style:string=Heading 1&FamilyName:string=ParagraphStyles` 與
  `.uno:StyleApply?Style:string=Text body&FamilyName:string=ParagraphStyles`。
- 真正的 slot：`SfxTemplateItem StyleApply SID_STYLE_APPLY`，
  `sfx2/sdi/sfx.sdi:4496`，參數含 `Style` 與 `FamilyName`。
- 錯誤映射位置：`wasm_sdk_probe/src/probe_engine.cpp`（E1-A discovery action 對照表）。

## 已觀察／推論／待驗證

### 已觀察

- 別名派送後，文件、command result 與 state callback 三者皆無變化。
- 參數化 `.uno:StyleApply` 在同一次 run 內成功套用 `Heading 1` 與 `Text body`，並送出對應 state。
- 一個樣式在三個位置有三種字串：送出用 `Text body`、ODT 存為 `Text_20_body`、state 回報 `Body Text`。
  取任何一個當成另一個都會失敗。

### 推論

- E1-A 對 bold／italic 的成功掩蓋了這個問題：那兩個是真 slot，所以「格式類命令部分可用」看起來像
  completion 的強弱差異，而不是映射錯誤。

### 待驗證

- WASM profile 是否同樣接受參數化 `.uno:StyleApply`（原生已成立，尚未在瀏覽器重現）。
- `Body Text` 這類 state 顯示名稱是否隨 UI locale 改變。若會，postcondition 不能直接比對顯示名稱。

## 影響與修法

- 修正映射為 `.uno:StyleApply` 加固定參數。**這不擴大公開 surface**：JS 端仍只送 closed enum，
  命令名稱與參數都固定在 C 端，字串不跨 ABI。
- E1-A 對 paragraph style 的「無 completion」結論必須撤回；該能力尚未被證明不可行，只是從未被正確派送過。
- 清單（`.uno:DefaultBullet`／`.uno:DefaultNumbering`／`.uno:RemoveBullets`）是真 slot，不受本 finding 影響，
  但另有 [finding 020](020-lok-list-command-result-contradicts-document.md) 的可信度問題。

## 還缺什麼才能關閉

- [ ] 修正 `probe_engine.cpp` 映射並在 WASM profile 重現。
- [ ] Chrome／Firefox 各達 E2-A 門檻次數。
- [ ] 確認 locale 對 state 顯示名稱的影響。

## 環境

- Core commit：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- 原生建置：`build-native-26-8`，`SAL_USE_VCLPLUGIN=svp`
- Fixture：`wasm_sdk_probe/test-docs/e1/styled-list.odt`

## 時間軸

- 2026-08-05：E2-A 的 A2 原生 state-readback 首次同時派送別名與參數化命令，以存檔後置條件確認別名無效；
  全樹搜尋確認無 `.sdi` slot，建立 finding。
