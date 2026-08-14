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
| integration（**shift-extend**，新期限落在這裡） | 3/3 | 3/3 |
| recovery（含 `crash-unsaved`） | 6/6 | 6/6 |
| corpus | 5/5 | 5/5 |
| lifecycle | 10/10 | 10/10 |

`artifactBinding`：`boundCases 48`、`supersededCases 0`、`unattributableCases 0`。

**`crash-unsaved` 是最該懷疑的一格**——它的凍結期望是「未存檔的內容**不得**在崩潰後回來」，
而 033 做的正好是讓未存檔內容回得來。先靜態讀出結論再實測，兩邊一致：
那個場景的定位走 `session.placeCaret`（click ＋ 輪詢），**不是**會觸發存檔點的 `selectRange`，
而且定位發生在打字**之前**，那時文件還是乾淨的。存檔點因此不會啟動，
~~凍結期望仍然成立~~ **這一格的期望仍然成立**。

> **2026-08-14 就地更正（外部覆核指出，我原本的宣稱過寬）。** 上面那句原本寫「凍結期望
> 仍然成立」，那是**性質層**的宣稱，而這一格只是**一個順序樣本**。三件事要分開：
>
> 1. **格內推理成立，而且比我寫的更穩**：`placeCaret` 根本不在存檔點的兩個呼叫點裡
>    （只有 `selectRange` 與 `moveCharacter(…, {extendSelection:true})`），
>    所以文件乾不乾淨都不會啟動。
> 2. **但 §4.1／C2 凍結的是產品性質**「未保存內容不得在崩潰後回來」，而 033 出貨的設計
>    就是讓它回來。在「mutation → 選取手勢 → crash → restart」這個順序下，
>    未經 save 的內容**照設計會回來**。**條文與出貨產品現在互相矛盾**，這要規格決定，
>    不是這棵樹能解的。
> 3. **這一格現在是一個打不開的檢查**：它的綠取決於腳本沒做選取手勢這個**腳本形狀**，
>    不取決於產品性質——不管 resurrect 語意怎麼改它都會綠。
>    而「arm → crash → restart → 從存檔點復活」這條新路徑，**48 格裡採樣次數是零**。
>    要嘛修訂 §4.1／C2 並**新增**一格 `crash-after-checkpoint`（收緊，不是放寬），
>    要嘛判 033 的 resurrect 違反凍結範圍。

## validator 對這棵樹發 `E1_STOP_OR_RESCOPE`，三個未達成各有原因

| 性質 | 結果 | |
|---|---|---|
| `profileFailClosed` | ✅ | |
| `evidenceArtifactBinding` | ✅ | 48 格全部綁到 `835b453d…` |
| `browserPhases` | ✅ | 上表 |
| `odtRoundtrip` | ✅ | 48 份輸出 ODT 全部通過桌面版重開 |
| `boundedLifecycle` | ✅ | |
| `regression` | ❌ | **凍結期間無法通過**，見下 |
| `workspaceBaseline` | ❌ | 只有 after，**沒有 before**——我不會把 after 當成 before 寫進去。**外部裁決同意，並推廣一步：也不能把正式樹保存的 before 搬過來**（`phase == "before"` 的特例讀的是**被驗證的那棵樹**自己保存的進場基線，搬檔會讓 `capture: "preserved-entry-baseline"` 替一個從未做過的觀測背書）。before 攔的是「進場時工作區就不對、跑完才復原」，after 與 per-case binding 都補不回那個時間點——per-case 綁的是 dist 三件套，core HEAD／status 不在裡面。正確處置：這棵樹維持缺格，**未來的正式重綁輪在進場時當場擷取自己的 before**（成本近乎零，便宜的觀測不用推論代替） |
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

> **2026-08-14 外部裁決結果**：**項目 2 必須重跑**，項目 1／3／4 可沿用，項目 5 不適用
> 沿用概念（它是綁著某一輪 output 的機器檢查）。**重跑須兩個瀏覽器各一輪、同一個 operator
> 時段完成**——§6 與 §9 的人工證據單位本來就是 per-browser，而擊破沿用的條件
> （delta 改到互動）是瀏覽器無關的，一擊破就是兩邊一起破。
>
> 判準採**互動層**讀法：「delta 落在該項目的執行路徑上，**且**改變了互動期間的引擎流量或
> 可觀察的 session 狀態」。純 session 內部記帳不算改到；而「我相信行為中立」不能代替重跑
> ——那正是人工輪存在的目的所要見證的命題。項目 2 在兩種讀法下都落在「有改到」那側：
> 手勢內多一次引擎 `save`、extend 期限 30000→5000、手勢後 state 多出 `hasCheckpoint`。
>
> 實務上人工輪是**一條整合流程、產出單一 ODT**，項目 2 無法單獨重跑而不產生殘缺證據，
> 所以正確做法是每個瀏覽器重跑完整一輪，並在紀錄裡註明**觸發原因僅為項目 2**，
> 其餘四項是搭便車重驗、不是它們的舊證據失效。
>
> 剩餘風險很窄：「存檔點＋extend＋（合成）取代」這條已由自動 integration 在兩瀏覽器
> 各 3 reps 通過；人工重跑真正補的只有**真 IME（`isTrusted`）對新形狀選取手勢的取代**。

## 結構性缺口：殼層對所有自動閘門是隱形的（2026-08-14，外部覆核指出）

`profile_inventory` 只算三個 sha256：`probe.js`、`probe.wasm`、`sdk-worker.js`。
**`editor-shell/editor-session.js` 不在其中**——所以 033 改了它之後，preflight 與
per-case artifact binding 的輸出**逐位元組相同**。

這就是為什麼這一輪需要人工裁決：**沿用與否是唯一會看到殼層 delta 的關卡**，
而那一關只能 fail-closed。

> **2026-08-14 已補**：`e1/editor-shell-bundle-v1.json` 逐檔記下驗證頁**實際載入**的
> 五個模組與一個彙總 hash，納入 preflight 與 per-case 綁定（矩陣 v2 的 baseline）。
> 排除的模組連同理由一併列在 manifest 的 `excluded` 裡——**沉默的排除會變成下一個同樣的洞**。
> 已實測：`editor-shell/` 任一檔改一個位元組，三個檢查會紅，其中一個指名到檔案。
> 生效於下一次重綁。

順帶記一筆同一次覆核挑出的欠帳：存檔點失敗被靜默吞掉（`CHECKPOINT_FAILED` 只存進
`this._checkpointError`，不進 state）。手勢不該因背景 save 失敗而失敗是對的，
但「最後一次安全存檔」這個承諾失效時，使用者與 host 都無從得知。

## 這一輪**不能**宣稱

- **這不是重綁。** 正式證據樹與 `E1_GO_ODT_EDITOR` 都沒有被改寫。
- 只有自動矩陣。人工 IME／剪貼簿那一輪沒有跑。
- `per-case-results.tgz` 只收 48 份 `result.json`；輸出的 ODT 與 PDF 留在跑的地方，
  它們的 sha256 記在 `summary.json` 裡，重跑即可重建。
