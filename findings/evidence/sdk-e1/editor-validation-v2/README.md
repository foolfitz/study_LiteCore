# E1-C 重綁輪（矩陣 v2）——**已完成，判定重發 `E1_GO_ODT_EDITOR`**

**日期**：2026-08-14　**引擎**：`835b453dd85adebbfcc6ada30fd47cdd7d5679a6abaaff3f1faebf47b484979d`
（出貨中的 `e1-editor-v1`，**全程未重連結**）
**殼層 bundle**：`f9b1a52f3ff2e2a3f35eae4366993f40b2035f309509aac0a3b7b6864a8cfeb9`
**矩陣**：`e1/validation-matrix-v2.json`　**瀏覽器**：Chrome 150、Firefox 153

> **2026-08-14：這棵樹現在就是正式證據樹。** 八個屬性全真、`automaticPass: true`、
> `decision: E1_GO_ODT_EDITOR`。前一輪（08-07、三個雜湊）的 `editor-validation/`
> **原封保留、未被覆寫**——證據不覆寫，只增加。

## 為什麼要重綁

任務 #33 改了殼層（手勢前 checkpoint、`restart()` 可自 checkpoint 重開），而
**殼層對三個 artifact hash 完全隱形**，所以既有的 48 格證據在位元組上完全沒有反應。
外部裁決據此判定人工項目 2 必須重跑，並要求把殼層 hash 納入綁定。
規格 §4.1／C2 同日修訂為 v8，矩陣 v2 新增 `crash-after-checkpoint` 一格。

## 結果：50/50，全部綁到 artifact **與殼層**

| 相位 | Chrome | Firefox |
|---|---|---|
| integration | 3/3 | 3/3 |
| recovery（含新的 `crash-after-checkpoint`） | 7/7 | 7/7 |
| corpus | 5/5 | 5/5 |
| lifecycle | 10/10 | 10/10 |

`artifactBinding`：**`boundCases 50`、`supersededCases 0`、`unattributableCases 0`**，
而 `expected` 現在有四個雜湊——loader、wasm、worker，**加上 `shellBundleSha256`**。
這是附款二存在的理由，端到端生效了：**#33 那種改動再也不可能靜靜通過**。

`odtRoundtrip` 通過（輸出 ODT 全部經桌面版重開）。

## `workspaceBaseline` 這次過了

上一輪（`shell-change-recheck`）這一格未達成，因為只有 after 沒有 before，而我不肯把
after 當 before 寫。裁決也否決了「從正式樹搬一份 before 過來」。

**這一輪在進場當場擷取自己的 before**（`baseline/preflight-before.json`，
`capture: "live-workspace"`，`pass: true`），跑完再擷 after。所以這一格是靠**做對**過的，
不是靠放寬。

## 人工那一輪（2026-08-14，兩瀏覽器同一時段）

照裁決跑：項目 2 是觸發原因，其餘四項搭便車重驗；每個瀏覽器一輪完整九項。
**兩份第一次送出就成功，沒有 attempt。**

| | Chrome 150 | Firefox 153 |
|---|---|---|
| `pass` | true | true |
| `operatorInputMethod` | Fcitx5 Chewing（operator 確認） | 同 |
| `trustedComposition` / `trustedPaste` | true / true | true / true |
| 取消探針 | `requestDelta 0`、`revisionDelta 0`、`trustedPreedit true` | 同 |
| 原生 Ctrl+C | `isTrusted: true` | 同 |
| Clipboard API 寫／讀 | passed / passed（`revisionDelta 1`） | 同 |
| 三筆搜尋 | 全中 | 全中 |
| server 驗證（zip/crc/xml） | pass | pass |
| **`artifact.shellBundleSha256`** | `f9b1a52f…` | `f9b1a52f…` |

最後一列是這一輪的重點：**人工證據也綁到殼層了**。以前它只綁 loader／wasm／worker，
所以 #33 那種改動對人工證據同樣隱形。

（歷史對照：attempt-02 那次 Chrome 的 `trustedPaste: false` 沒有再現——那本來就已判定為
焦點不在 SDK sink，不是 Chrome 特有問題。）

**`preflight-after` 重擷了一次。** 原本那份是自動那半跑完當下擷的，而人工這半在它之後才發生，
所以它不是這一輪真正的結尾。原檔保留為 `preflight-after-automatic-half.json`，**沒有覆寫**。

## validator：八個屬性全真，`E1_GO_ODT_EDITOR`

> 下表是**修好 `regression` 屬性之前**的狀態，保留作為過程紀錄。
> 修法與最終結果見本節末〈屬性修好之後〉。

| 性質 | 結果 | |
|---|---|---|
| `profileFailClosed` | ✅ | |
| `evidenceArtifactBinding` | ✅ | 50 格全綁，含殼層 |
| `browserPhases` | ✅ | 上表 |
| `odtRoundtrip` | ✅ | |
| `boundedLifecycle` | ✅ | |
| `workspaceBaseline` | ✅ | **上一輪缺的那一格** |
| `regression` | ❌ | **唯一未達成**，成因見下——它量的不是回歸 |
| `trustedManualDelta` | ✅ | 兩瀏覽器人工輪已完成 |

**它不是回歸。**

### `regression` 量的不是回歸，是「凍結之後有沒有人改過 Makefile」

`--run-regression` 會 `make test-e1-c-static`，而它相依 `e1-editor-validation-assets`：
`make -n` 顯示那會先重編四個目的檔，然後在連結被凍結防護擋下。

> **2026-08-14 追查到成因，而它不是「凍結」。** `Makefile:486`：
> ```make
> $(E1_B_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h Makefile | $(E1_B_BUILD)
> ```
> **`Makefile` 自己是每個目的檔的相依。** 實測四個 `.o` **都比它們的 `.cpp` 新**
> （objects 08-12 22:52，最新的 source 是 `probe_engine.cpp` 08-12 16:38），
> 所以觸發重編的是 Makefile 的 mtime，不是原始碼。而 Makefile 自 08-08 凍結後
> 被改過至少八次——包含今天為了矩陣 v2 加的一條 `cp` 規則與兩行 JSON 檢查。
>
> **推論**：08-07 那次 GO 的 `regression: true` 之所以成立，是因為當時還沒有人改過
> Makefile，**不是因為它驗到了比今天更多的東西**。加一條無關的複製規則就會讓這個屬性失敗，
> 而且是以「嘗試重連結凍結 artifact 然後被防護擋下」的方式失敗。
>
> 這一段已送外部裁決；判定要不要據此重發 GO **不由我決定**——
> 「我把檢查重新詮釋了一下，於是我的判定就過了」是這條線一直在記錄的失效模式。

照 A7 回歸那一輪的先例，改以直接執行其檢查的方式跑，**結果另外具名記錄、不冒充那個屬性**：

| 目標 | 結果 |
|---|---|
| `test-r6-release` | 通過 |
| `test-r7-b-static` | 通過 |
| `test-r7-c-static` | 通過 |
| `test-r7-d-static` | 通過 |
| `test-e1-a-static` | 通過 |
| `test-e1-b-static` | 通過 |
| `test-e1-c-static` 的**配方本體**（跳過會重連結的相依） | 通過（Python 21、Node 87、四項語法／JSON／py_compile 檢查） |
| `test-r8-d-static` | **具名排除，未跑**，理由見下 |

**`test-r8-d-static` 排除的理由，而且這是我這一輪踩到的坑，不是預先知道的**：
它名字看起來是測試，實際會呼叫 `build_r8_release_manifest.py` 與 `build_r8_bundles.py`
——**鑄 release id 是它的副作用**。我第一次跑回歸替代時它鑄出一個不在 `dist/releases/`
的新 id（`c9f3c6fb…`），我在 bundle builder 動手之前停掉。

損害核對過，**沒有實質損害**：`dist/releases/` 兩個綁定中的 release 目錄與 `index.json`
都沒被動到；`findings/evidence/sdk-r6/summary.json` 雖被重寫但內容與 git HEAD 逐位元組相同
（只有 mtime 變）；三個凍結 artifact 未變；本輪 50 格在它之前就跑完了，不受影響。

**由此推出一件該記下來的事**：E1-C 的 `regression` 屬性**定義裡就含這個目標**，
所以 `validate_e1_c.py --run-regression` **每跑一次就鑄一次 release id**。
這個屬性即使 artifact 解凍也應該先修，否則它是一個有副作用的閘門。

## 這一輪**不能**宣稱

- **這不是重綁完成，因為判定還沒重發。** 正式樹未動，現行 GO 的具名界定
  （不涵蓋 08-13 之後的殼層）在判定重發之前仍然有效。
- **`regression` 未達成，而且它未達成的理由本身是一個缺陷**（見上）。要不要據此發
  沒有註記的 `E1_GO_ODT_EDITOR`，是判斷題，已送外部裁決，**不由跑這一輪的人決定**。
- 回歸替代**不是**那個屬性。它跑的是同一批檢查，但少掉建置新鮮度那一層，
  而且第 8 個目標被排除——這兩件事都寫在上面，不要在引用時省略。

## 屬性修好之後：八項全真（2026-08-14 16:26）

外部裁決確認成因分析成立，並裁定 **7/8 不得發 GO**（替代 log 不折抵屬性），
但門檻是**修屬性後單獨重跑 regression 相位**，不是讓那個反向檢查變綠。
修法四項全數落地（見 SPEC-E1-C 修訂紀錄 v9），其中第二項是**淨收緊的關鍵**：

- **`test-e1-c-frozen-guard`**：`make --always-make -n build/e1/editor-v1/probe.js`
  必須印出 `refusing to relink a frozen profile`。它與 mtime 拓撲完全無關，
  問的是「如果現在重建，連結會不會被擋」。**實測：把防護那一行拿掉即紅（exit 2），
  還原即綠（exit 0）。** 舊相依那個只能靠違規變綠的「反向訊號」，換成一個正向斷言。

重跑結果：

```
{"automaticPass": true, "complete": true, "decision": "E1_GO_ODT_EDITOR",
 "failedProperties": [], "artifactBinding": {"boundCases": 50, ...}}
```

兩項新收緊的閘門**都是真的跑了、不是被跳過**：

- 錨點數在 `== 1` 判準下實測 **1／1／1／1**（兩瀏覽器），取消字串 0 次；
- 人工輸出的 desktop reopen 產出 `chrome-output.desktop.pdf`／`firefox-output.desktop.pdf`
  各 38999 bytes、`pass: true`。**這是 E1-C 歷來第一次真的對人工輸出做桌面重開**
  ——§6 項目 5 字面要求它，而之前每一次 GO 都沒有執行過。

`regression` 這次 `returnCode: 0`，而且**重跑之後 `dist/r8/release-manifest.json` 的
sha256 不變**——finding 041 的副作用確實消失了。

## 外部覆核糾正了我兩處，記在這裡

1. **kill 點**：我原本寫「在 bundle builder 動手前停掉」。`dist/releases/index.json`
   的 mtime 15:44 證明 **`build_r8_bundles.py` 已經跑完**，被 Terminated 的是再下一步的
   `build_r8_c_release_set.py`。已更正。
2. **損害面要拆成兩句**：綁定面為零（已量測），但 `dist/r8/release-manifest.json`
   的 15:44 之前內容**不可知**——`dist/` 不進 git 也沒有 checksum 基線。
   「沒有損害」是過寬的說法。詳見 [finding 041](../../../041-static-test-targets-build-and-mint-through-a-phony-asset-chain.md)。

還有五條它替我補查的人工證據，最重要的一條是：**`hasCheckpoint` 在人工輪裡真的武裝了**
——兩瀏覽器各 **37 個 state 為 true**、首見於 `checkpointRevision: 4`／`dirty: true`。
這是整次重跑存在的理由：如果 operator 的順序碰巧讓文件不 dirty，就沒有見證到新手勢形狀，
而九項照樣會全綠。**我沒查這一項，是它替我查的。**
（順帶更正：搜尋是**五筆**不是三筆——第五筆是取消字串在輸出位元組上為 0 次。）
