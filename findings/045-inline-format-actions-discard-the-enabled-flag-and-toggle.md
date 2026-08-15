# 045 — 四個 inline 格式動作把 `enabled` 丟掉，派送的是 toggle

| | |
|---|---|
| **狀態** | **已確認（兩瀏覽器實測 ＋ 原始碼對照）／擋住 E2-C D1** |
| **Bugzilla** | —（**不是上游缺陷**） |
| **發現日** | 2026-08-15 |
| **嚴重度** | 嚴重（出貨契約收一個明確的布林值，引擎完全不用它；`enabled: false` 關不掉格式） |
| **可重現** | 100%（Chrome／Firefox 各一輪，全新文件、純文字游標） |
| **是否上游** | **否——我方的派送形式**，與 [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md) 缺陷一同型 |

## 摘要

`set-bold`／`set-italic`／`set-underline`／`set-strikethrough` 的 ABI 收一個
**明確的 `enabled` 布林值**，客戶端強制要求它（`editor-client.js`：
「the inline format actions require an explicit enabled boolean」），
worker 一路帶到引擎——**然後引擎把它存進一個只拿來回報的變數，
派送的是不帶參數的 `.uno:Bold`**。

core 的 slot 宣告是 `Toggle = TRUE`。不帶參數派送 ⇒ **切換現況**，不是設定成目標值。

**後果**：`enabled: false` 不會關掉格式。在**全新文件、純文字游標**上派送
`set-bold(enabled: false)`，之後打的字**是粗體**。

**這正是 finding 030 缺陷一的同一個形狀**，030 修好了兩個清單命令
（`kListOnArguments`，`probe_engine.cpp:3091`），**四個 inline 格式沒有跟著修**。

## 最小重現

出貨 profile `e2-editor-v2`（wasm `572035ac…`），語料 `test-docs/e2/d1-anchors.odt`，
**全新文件**（每一格自己的引擎與文件，前面沒有任何派送）：

```text
把收合游標放在一段純文字上（E2-D1-BOLD-ON plain）
派送 set-bold(enabled: false)   → changed: true、revision +1、uno-command-result
在同一個游標提交 "OFFONLY"
存檔
```

**Chrome 與 Firefox 逐字相同**：

```xml
<text:p text:style-name="P1">E2-D1<text:span text:style-name="T1">OFFONLY</text:span>-BOLD-ON plain</text:p>
<style:style style:name="T1" …><style:text-properties fo:font-weight="bold" …/></style:style>
```

**要求關閉，得到開啟。**

## 機制（原始碼層級，逐行）

| 位置 | 做什麼 |
|---|---|
| `wasm_sdk_probe/src/probe_engine.cpp:3897` | `case OXSDK_EDITOR_SET_BOLD: startEditorUnoAction(command, name, ".uno:Bold")` |
| `…:3034` | `gEditorUnoOption = command.values[2] != 0;` ← `enabled` 進到這裡 |
| `…:3036` | `startUnoMutation(command, "editor-action-completed", unoCommand, {});` ← **參數是空的** |
| `…:2073` | `gEditorUnoOption` 的第一個用途：只用來認出 delete 的 manual-observation 分支 |
| `…:2083` | 第二個用途：原樣回報成 `"option"` 欄位 |
| `libreoffice-26-8/svx/sdi/svx.sdi:832,838` | `SvxWeightItem Bold SID_ATTR_CHAR_WEIGHT` ＋ **`Toggle = TRUE`** |

**`enabled` 在引擎裡沒有第三個用途。** 它從來沒有離開過我方的程式碼。

### 順帶：這幾個動作的 `changed` 是常數

`probe_engine.cpp:2085` 把 `changed` 寫死成 `"true"`（delete 的手動觀察分支除外）。
所以 inline 格式回的 `changed: true` **不是對文件的觀察**，是一個字面值。

同一輪另外量到：在收合游標上派送這四個動作，**`<office:body>` 逐位元不變**
（效果在之後打的字上）。兩件事合起來的意思是：
**`changed: true` 在這裡既不代表文件變了，也沒有任何東西去看過文件。**

## 已排除／未排除

| 假說 | 結果 |
|---|---|
| 客戶端沒把 `enabled` 送出去 | **排除**——D0 的請求信封逐欄比對過，`enabled: false` 確實在 payload 裡 |
| worker 沒轉發 | **排除**——`sdk-worker.js` 把 `payload.enabled ? 1 : 0` 放進呼叫 |
| 瀏覽器差異 | **排除**——兩瀏覽器逐字相同 |
| 前一次派送的打字屬性殘留 | **排除**——重現用的是全新引擎、全新文件，前面沒有任何派送 |
| 「連按兩次會關掉」（toggle 的正常行為） | **未排除，而且我第一版的對照是髒的**：第二個標記插在第一個標記旁邊，會**繼承**鄰接 span 的格式，所以「第二次沒關掉」這個觀察分不出 toggle 與繼承。**不採信**。真要量得換一個彼此不相鄰的位置。 |

## 影響範圍

- **出貨的 E1 契約也有這個問題。** 這四個動作從 E1-B 起就是這樣派送的；
  `e1-editor-v1`（`835b453d…`）與 `e2-editor-v2`（`572035ac…`）走同一段程式碼。
- **E1-C 為什麼沒抓到**：它驗的是 revision 與 typed 後置條件，
  **沒有任何一格去存檔看那段文字到底變成什麼**。demo 手動驗過的是「開啟」那一側。
- **違反上位規格**：[SPEC E2-000](../specs/SPEC-E2-000-overview.md) 第 8.1 節寫
  「以 explicit closed enum **設定**，不是 toggle」。那句話是為清單寫的，
  但同樣的理由適用於這四個。
- **擋住 [SPEC E2-C](../specs/SPEC-E2-C-paragraph-format-validation.md) 的 D1**：
  凍結矩陣裡 `d1-set-*-false` 四格的判準是「之後打的字**不帶**那個屬性」，
  在現行 artifact 上**不可能通過**。

## 還缺什麼才能處置

- [ ] **決定要修還是要縮限**（使用者裁決）：
      - **修**＝照 030 的作法送參數（`.uno:Bold` 要的是 `SvxWeightItem`，
        不是布林；正確的參數形狀**還沒查**），**需要重連結**，
        而 E2-C 第 3 節禁止重連結、E2-B 的 132 個 run 會斷綁。
      - **縮限**＝在契約裡明說這四個是 toggle、`enabled` 不生效——
        但 manifest 的 `limits` 要寫進去也**需要重連結**。
      - **兩條路都要 relink**，所以這是一個 E2-C 範圍之外的決定。
- [ ] 查 `.uno:Bold` 正確的參數形狀（`SvxWeightItem` 的 dispatch 表示法），
      並在原生測試裡先驗過再進 WASM。
- [ ] 補一輪乾淨的 toggle 對照（兩個**不相鄰**的位置），把上表那格從
      「未排除」變成量到的。
- [ ] 決定 E1 側要不要一併發修訂（同一段程式碼，同一個缺陷）。

## 時間軸

| 日期 | 事件 |
|---|---|
| 2026-08-11 | finding 030：兩個清單命令是 toggle，**已修**（送 `On` 參數） |
| 2026-08-15 | E2-C D1 第一輪 smoke 的四個 `-false` 格全紅 → 追到同一個形狀，四個 inline 格式從來沒被修過 |
| 2026-08-15 | 全新文件對照 ＋ 原始碼逐行對照，兩瀏覽器一致；本 finding 建立 |

## 證據

`findings/evidence/045/`（英文 README），兩瀏覽器各一輪，含存出來的 ODT。
