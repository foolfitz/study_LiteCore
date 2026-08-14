# 038 是不是 040 的第三個入口——**跑之前先寫下的預測**

**寫定時間**：2026-08-14（**在任何一次 038 的堆疊被取得之前**）
**要用的 artifact**：`e2-preguard-profiling`
＝`e05fd156180e205037990591bab4d94b4199b8d378a970795d0a0aa8ff7365ca`
（037 擋法以 `OXSDK_037_GUARD_OFF` 編掉、`--profiling-funcs`；**永不出貨、不綁任何判定**）

這一份的存在理由：任務 #42 的預測是先寫再驗的，**結果它成立了**。
如果這一次先看堆疊再說「這本來就是我想的那樣」，那不是預測，是事後解釋。
所以四種結局在跑之前就各自寫好對應的處置。

## 現在確定的事（不是預測）

- 038 殺死引擎的**不是選取，是選取之後第一個「讀選取」的呼叫**
  （`getState`／`getSelection`，都走 `readSelection()` → `getSelectionTypeAndText`）。
  這是 2026-08-13 對 038 的更正，已有出貨 artifact 上的活性梯佐證。
- 038 的堆疊**至今未取得**。`wait-primitive-names/chrome/f038-wedge.json` **不是**它——
  那一份第 28 格是 `doc_destroy`，是 012 的路；該目錄的 README 自己就寫了這件事。
- **037 的擋法對這條路無效，而且理由是結構性的**：擋法本體
  `formatBarrierSelectionIsReadable()` 的第一件事就是 `readSelection()`——
  也就是 038 會卡住的那一個呼叫。**擋法問不到問題就先卡住了。**
  推論：`OXSDK_037_GUARD_OFF` 對「能不能重現 038」**不構成差別**，
  它只是讓這顆 artifact 同時能用來對照 037。真正必要的是 name section。

## 預測（要能失敗）

**卡住的引擎執行緒堆疊，自上而下應該是：**

```
emscripten_futex_wait ← …（012／037 共用的六格等待前綴）…
  ← Scheduler::IdlesLockGuard::IdlesLockGuard()
  ← sw::DocumentLayoutManager::DelLayoutFormat(SwFrameFormat*)
  ← …（SwDoc 解構路徑）…
  ← 一個在 doc_getSelectionTypeAndText／doc_getTextSelection 之下、
     解構區域 SwTransferable（連同它自己那份剪貼簿 SwDoc）的框架
  ← probe::(anonymous namespace)::dispatch ← engineLoop
```

也就是：**與 037 同型**——文字／型別已經取出來了，卡的是**取出之後的清理**。

### 判準

| 觀察到的 | 判定 | 要做的事 |
|---|---|---|
| （甲）出現 `IdlesLockGuard`，且經由 `getSelection` 系呼叫下的 `SwTransferable` 解構抵達 | **預測成立**：038 是同一缺陷的第三個入口 | 040 的上游單增列第三個入口；038 檔案改判並連到 040 |
| （乙）出現 `IdlesLockGuard`，但抵達路徑不同（例如不經 `SwTransferable`） | **同一缺陷、不同路線** | 上游單照實寫路線差異，**不可把甲的敘述套上去** |
| （丙）停在別的等待原語或別的條件 | **038 是另一個缺陷** | **040 的上游單不得宣稱 038**；另開 finding |
| （丁）這顆 artifact 上重現不出卡死 | **什麼都沒量到** | 照實記「未重現」，**不准事後解釋為什麼**；038 維持「推論、未取得堆疊」 |

（丁）要特別提防：它看起來最像「沒事」，而它其實是**這一輪失敗**。
上一次就是在 `e2-wait-diagnostic` 上落到了一個看起來很像答案、實際上是別條路的堆疊。

## 這一輪不會宣稱的

- **不宣稱產品受影響程度有變。** 038 對出貨編輯器的界定寫在 SPEC-E1-C §9.1，
  是具名收窄；本輪只取堆疊，不動那條收窄。
- **不宣稱修法。** 入口相同不等於擋法相同——037 的擋法對這條路無效已如上述。
- **不用這顆 artifact 支持任何判定。** 它是診斷用的。

## 跑法（照 #42 的既有程序，不新建工具）

```
tools/probe_wait_primitive_names.py \
  --profile e2-preguard-profiling --fixture frame-contexts \
  --fixture-mode wedge-split --cases "" --wait-for-hang \
  --output …/038-entry-point/chrome/result.json
```

控制組內建：同一份 fixture 的 FX-PLAIN 與 FX-CELL 在 038-scope 那一輪是**通過**的
（讀選取 2 ms／0 ms），所以「引擎在 FX-NOTE 之前是活的」由同一次執行自己證明，
不必另跑一輪對照。
