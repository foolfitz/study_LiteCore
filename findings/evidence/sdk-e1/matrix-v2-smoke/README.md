# matrix v2 冒煙：新的那一格真的跑得起來，而且真的會紅

**日期**：2026-08-14　**引擎**：`835b453dd85adebbfcc6ada30fd47cdd7d5679a6abaaff3f1faebf47b484979d`
（出貨中的 `e1-editor-v1`，**全程未重連結**）
**這不是重綁，也不是矩陣輪。** 正式證據樹與 `E1_GO_ODT_EDITOR` 都沒有被碰過。

## 為什麼跑這一輪

矩陣 v2 新增的 `crash-after-checkpoint` 是**寫出來但從未執行過**的程式碼。
這條研究線一再抓到的毛病就是「寫了檢查卻沒證明它會動」，所以在使用者花 operator 時間
跑完整一輪之前，先單獨把這一格跑起來。

## 結果一：它跑得起來，而且每一項斷言都有實值

| 步驟 | 結果 |
|---|---|
| `checkpoint-created-before-selection` | passed，`hasCheckpoint: true`、`checkpointRevision: 1` |
| `E1C-CKPT-MUST-SURVIVE` | **found**——存檔點的內容回來了 |
| `E1C-CKPT-MUST-NOT-RETURN` | **not found**——存檔點之後、未 save 的內容沒回來 |
| `E1C-CKPT-PREEDIT-FORBIDDEN` | not found |
| `E1C-CKPT-QUEUED` | not found（該 promise 以 `WORKER_CRASHED` 被拒） |
| 舊 document handle | `STALE_DOCUMENT` |
| 重開後 | `dirty: true`、`generation: 2` |
| `post-recovery-save-clears-checkpoint-and-dirty` | passed，`hasCheckpoint: false`、`dirty: false` |

**「全部通過」在這裡不是空話**：如果 restart 開的是 authority 而不是 checkpoint，
第二列會是 not found；如果 stamp 序壞掉，第三列會是 found。兩列互為反向約束。

## 結果二：把 #33 關掉，它會紅——而且紅在該紅的地方

這才是這一格存在的理由。`crash-unsaved` 那一格不管 resurrect 語意怎麼改都會綠，
因為它的綠取決於腳本沒做選取手勢。所以新格必須證明自己不是同一種東西。

**第一次嘗試沒有證到我要的東西，記在這裡**：只把 `_checkpointBeforeSelection` 改成
立即 return，頁面**根本沒開始跑**——附款二的殼層 hash 閘門先攔下來了
（`served shell bundle does not match ./e1/editor-shell-bundle-v1.json`）。
那證明了 hash 閘門會紅，**不是**證明那一格會紅。

第二次照**真實回歸的樣子**做：改殼層 ＋ 一併重算 manifest 與矩陣 baseline
（一個真的把 #33 退回去的人本來就會這樣做），於是頁面跑得起來，而它死在：

```
passed   pre-checkpoint-commit
passed   checkpoint-selection-gesture
failed   checkpoint-created-before-selection   → hasCheckpoint: false
error:   selection gesture completed without creating a checkpoint
```

**紅在第 3 步的斷言上，不是紅在別的地方。** 改動全部已還原，還原後 21 個單元測試全過。

## 結果三：收緊後的 `crash-saved` 也跑得起來

它加了兩步：手勢前先 arm 一個 checkpoint，然後在顯式 save 之後斷言 `hasCheckpoint === false`。
釘的是鏡像危害——**顯式 save 之後，舊的 checkpoint 不得復活**。

Chrome 與 Firefox 逐格相同：

```
passed   pre-crash-commit
passed   pre-crash-checkpoint-arm
passed   pre-crash-checkpoint-armed        ← 新增
passed   pre-crash-save
passed   pre-crash-save-clears-checkpoint  ← 新增
passed   crash-restart
passed   crash-recovery-authority-and-no-replay
passed   post-recovery-save
```

`crash-unsaved` 沒有跑，因為它一個字都沒改。

## 順帶量到的一個維護風險

做上面那個變異時我自己撞到：**沒有任何工具可以重算殼層 manifest**。
一次合法的殼層改動要手改三個地方——`e1/editor-shell-bundle-v1.json` 的逐檔 hash 與彙總、
`e1/validation-matrix-v2.json` 的 baseline、以及 `tests/test_e1_c.py` 裡釘死的那個字面值。

摩擦本身是刻意的（跟凍結 artifact 的 hash 同一個道理），**但三處手改而且沒有工具，
最可能的失效方式是有人改成「把檢查放寬」而不是「把 manifest 更新」**。
凍結 artifact 那邊是有工具的（`build_*` 會寫 manifest），所以補一個帶 diff 輸出的
重算模式與既有慣例一致，不是放寬。已記為待辦。

## 界線：這一輪**不能**宣稱什麼

- **不是重綁**。正式樹沒有被改寫，`E1_GO_ODT_EDITOR` 的具名界定（不涵蓋 08-13 之後的殼層）
  仍然成立，要撤除那個界定必須跑完整的重綁輪。
- **只跑了 recovery 相位的兩格**，其餘 48 格沒跑。
- **人工那一輪沒有跑**——照裁決，項目 2 必須重跑，而且兩瀏覽器同一 operator 時段。
- 這棵樹**沒有** before-preflight，而且照裁決**不得事後補**。正式重綁輪要在進場時當場擷取自己的。
