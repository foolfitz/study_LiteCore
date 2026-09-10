# 097 — 契約欄位宣告了一件與實測相反的事，而產品路徑上沒有人讀它

**狀態**：靜態確認 ＋ 由 096 的量測反證。
**來源**：追查 finding 096 的修法該住在哪一層時掉出來的
（`handoff/DECISION-2026-09-09-which-layer-can-carry-096s-fix-and-what-each-costs.md`）。

## 宣稱

`boundaryRejectionRequiresFreshWorker` 這個欄位：

1. **硬寫成 `True`**，不是量出來的（`tools/build_e2_b_profile.py:155`，
   以及 `build_finding_016_selection_barrier_profile.py:67`、
   `build_e2_discovery_profile.py:210`）。
2. **產品路徑上沒有任何東西讀它。**唯二的讀者是
   `web/e1-discovery-app.js:362` 與 `web/finding-016-selection-barrier-app.js:445`，
   而且它們讀的是 `manifest.diagnostic.*`——那個子物件
   在寫出契約之前就被 `build_e2_b_profile.py:138` 給 pop 掉了。
3. **實測行為與宣告相反。**096 的量測（四臂 40/40）顯示：撞到邊界之後
   **不需要**換一個新的 worker，session 就是死的——`recoverable-error`、
   `rescue: none`，而且 worker 的 JS 執行緒還活著、0.0 秒答得出 CDP。
   換言之這個欄位宣告的補救動作既沒有人執行，實測也不成立。

## 為什麼這是一張單，而不是一行清理

這棵樹在 2026-08-22 為同一個形狀付過錢，而且記在 `AGENTS.md` 裡：
**「manifest 說給了，引擎無條件拒絕」**——當時是 `kMaxInternalEditorAction`
的界限沒跟著清單走。這裡是同一個方向的反面：**契約說「補救需要 X」，
而沒有人做 X，實測也不需要 X 才會壞。**

第 1 節的判別法（動態）：**往真值源塞一個虛構的新成員，看哪個檢查轉紅。**
把這個欄位改成 `False`、或整個刪掉，**零個產品路徑上的檢查會紅**——
而契約已經說了一件假的事。這是手工枚舉的那一種。

## 不是什麼

- **不是 096 的成因**，也不是它的修法。096 的成因未定（三個解釋還在）。
- **不主張刪掉它**。宣告一件真的事、並且有人執行，跟刪掉它，是兩個不同的處置，
  而選哪一個要等 096 的成因定了才知道——那個欄位有可能本來就是要描述
  一個真實的補救路徑，只是從來沒有接上。

## 清點：其他硬寫、產品路徑不讀的契約欄位（2026-09-10）

原「未做」第一條要求普查（AGENTS.md §5：普查不抽樣）。查法：對 v8 profile 的
`editorContract` 逐欄，看 `web/e2-editor-app.js`、四個 `editor-shell-v2/*.js`、
`editor-shell/*.js`、`sdk/document-sdk.js`、`sdk/sdk-worker.js` 有沒有把它**當契約
欄位讀**（`editorContract.<欄>` 或 `contract.<欄>`，不是同名的方法或事件欄位——
裸字比對會把 `undo()` 方法、`result.state`、`event.selectionBarrier` 都誤計）。

**產品路徑會讀的欄位**（作為對照，這些不是這張單的對象）：`version`、`actions`、
`abiVersion`、`gestureBits`、`redo`、`caretParagraphText`、`documentOutline`、
`documentOutlineGeometry`、`wasmSha256`。

**硬寫且產品路徑不讀的欄位——共 14 個，本張的 `boundaryRejectionRequiresFreshWorker`
是其中之一**：

| 欄位 | 值 | 種類 |
| --- | --- | --- |
| `boundaryRejectionRequiresFreshWorker` | `true` | **被實測反證**（本張） |
| `automaticRetry` | `false` | 誠實宣告（「我方不做 X」） |
| `rawCallbackExposed` | `false` | 誠實宣告（診斷頁 `e1-discovery-app.js` 有斷言，但那讀的是 `diagnostic.*`，產品 profile 沒有那個子物件） |
| `arbitraryKeyCodeAccepted` | `false` | 誠實宣告 |
| `arbitraryUnoCommandAccepted` | `false` | 誠實宣告 |
| `diagnosticOperationsExposed` | `false` | 誠實宣告 |
| `inlineFormatEnabledIsHonoured` | `true` | 機制描述（078 量過） |
| `textCommit` | `"document-sdk-insert-text"` | 機制描述 |
| `undo` | `"document-sdk-undo"` | 機制描述 |
| `state` | `"typed-editor-state-v1"` | 機制描述 |
| `selectionBarrier` | `"verified-single-writer-unit-v1"` | 機制描述 |
| `formatBarrier` | `"verified-format-readback-v2"` | 機制描述 |
| `postDispatchFailureDisposition` | `"rollback-to-checkpoint"` | 機制描述 |
| `crossParagraphDisposition` | `"verify-every-block"` | 機制描述 |

**結論：這一格是收斂的，不是發散的。**14 個裡只有
`boundaryRejectionRequiresFreshWorker` 是**被實測反證**的（40/40 卡死，行為與宣告
相反）；其餘 13 個是「產品不讀、但沒被證偽」——一類是給外部／診斷讀者看的誠實宣告
（我方不接受任意 keycode／UNO、不吐 raw callback），一類是描述產品**直接實作**的
機制（不是靠讀那個欄位才決定要不要做）。所以 097 是**單一欄位的缺陷**，不是「契約
整片是虛構」的系統性問題。

**具體佐證欄位不是齊頭死的**：`redo` 有人讀而 `undo` 沒有——`offersRedo`
（`narrow-editor-v2-client.js:218-221`）刻意 gate 在 `contract.redo ===
"document-sdk-redo"`，因為 `oxsdk_document_redo` 是新的編譯匯出，舊 binary 上會抓
不到符號；`undo` 則被假設永遠在，base class 無條件呼叫，沒有對應的 `offersUndo`。
同一種形狀的欄位，一個是承重的、一個是純描述的。

**誠實的界限（AGENTS.md §7／§11）**：「不讀」是這一輪**靜態量到**的。其餘 13 個
「與行為一致」則是**讀出來的分類**，除了 078（inline format）與診斷頁對
`rawCallbackExposed` 的斷言之外，**這一輪沒有對它們逐一重新量測**。所以本節只證明了
`boundaryRejectionRequiresFreshWorker` 是被反證的那一個，**沒有**宣稱其餘 13 個
為真——它們是「未被證偽」，不是「已證為真」。

## 未做

- **其餘 13 個欄位與實測行為是否一致，未逐一重新量測**（見上節誠實的界限）。
  只證明了本張這一個被反證。**這一節是「沒逐一量」，不是「量了都對」。**
- 沒有查 `manifest.diagnostic` 這個子物件在什麼時候、為什麼被 pop 掉。
