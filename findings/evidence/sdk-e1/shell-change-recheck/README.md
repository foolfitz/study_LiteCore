# 殼層改動之後的 E1-C 自動矩陣重跑（**不是重綁**）

**日期**：2026-08-13　**引擎**：`835b453dd85adebbfcc6ada30fd47cdd7d5679a6abaaff3f1faebf47b484979d`
（出貨中的 `e1-editor-v1`，**全程未重連結**）
**瀏覽器**：Chrome 150 與 Firefox 153.0.1
**正式證據樹沒有被碰過**——這一輪寫在別的地方，判定沒有被改寫。

## 為什麼要跑

任務 033 改了 `editor-shell/editor-session.js`：`selectRange` 與 shift-extend 拿到 5000 ms
期限、手勢前會存一次檔、`restart()` 可能從那份存檔點重開。artifact 沒有變，
**但 E1-C 驗的是 artifact 加上這個殼層**，而改動落在 E1-C 會走到的路徑上。
所以問題是：**這個改動有沒有動搖 E1-C 已經驗過的任何一格。**

## 結果：48/48 通過，全部綁在出貨 artifact 上

| 相位 | Chrome | Firefox |
|---|---|---|
| integration（`selectRange`，新期限落在這裡） | 3/3 | 3/3 |
| recovery（含 `crash-unsaved`） | 6/6 | 6/6 |
| corpus | 5/5 | 5/5 |
| lifecycle | 10/10 | 10/10 |

`artifactBinding`：`boundCases 48`、`supersededCases 0`、`unattributableCases 0`。

**`crash-unsaved` 是最該懷疑的一格**——它的凍結期望是「未存檔的內容**不得**在崩潰後回來」，
而 033 做的正好是讓未存檔內容回得來。先靜態讀出結論再實測，兩邊一致：
那個場景的定位走 `session.placeCaret`（click ＋ 輪詢），**不是**會觸發存檔點的 `selectRange`，
而且定位發生在打字**之前**，那時文件還是乾淨的。存檔點因此不會啟動，凍結期望仍然成立。

## validator 對這棵樹發 `E1_STOP_OR_RESCOPE`，三個未達成各有原因

| 性質 | 結果 | |
|---|---|---|
| `profileFailClosed` | ✅ | |
| `evidenceArtifactBinding` | ✅ | 48 格全部綁到 `835b453d…` |
| `browserPhases` | ✅ | 上表 |
| `odtRoundtrip` | ✅ | 48 份輸出 ODT 全部通過桌面版重開 |
| `boundedLifecycle` | ✅ | |
| `regression` | ❌ | **凍結期間無法通過**，見下 |
| `workspaceBaseline` | ❌ | 只有 after，**沒有 before**——我不會把 after 當成 before 寫進去 |
| `trustedManualDelta` | ❌ | 人工 Chewing 證據在正式樹裡，這棵樹沒有 |

**三個都不是回歸**，都是我沒有放進這棵樹的輸入。

### `regression` 為什麼過不了

`validate_e1_c.py --run-regression` 會跑 `test-e1-c-static`，而它相依
`e1-editor-validation-assets`。`make -n` 顯示那會先重編四個目的檔，然後在連結那一步
被凍結防護擋下（`refusing to relink a frozen profile … exit 1`）。
**防護是有效的、artifact 全程未變**，但這條路徑的結果只能是失敗。
所以只要 artifact 還凍著，這個性質就無法達成——這是現況的一個事實，不是本輪的失誤。

（目的檔的時間戳是 **08-12**，上一輪 session 留下的；本輪沒有任何東西碰過它們。）

### 人工那一輪不能直接沿用

SPEC E1-C 第 6 節允許同 artifact 沿用人工證據，條件是
**「自動 delta 沒有改到相關互動」**。人工項目 2 是「用產品 Shift-character 按鈕建立 selection」
——那正是 `moveCharacter(…, {extendSelection: true})`，**033 改動的兩條路徑之一**。
照條文的字面，這一輪落在「有改到」那一側。要不要沿用是判斷題，不是我能自己決定的。

## 這一輪**不能**宣稱

- **這不是重綁。** 正式證據樹與 `E1_GO_ODT_EDITOR` 都沒有被改寫。
- 只有自動矩陣。人工 IME／剪貼簿那一輪沒有跑。
- `per-case-results.tgz` 只收 48 份 `result.json`；輸出的 ODT 與 PDF 留在跑的地方，
  它們的 sha256 記在 `summary.json` 裡，重跑即可重建。
