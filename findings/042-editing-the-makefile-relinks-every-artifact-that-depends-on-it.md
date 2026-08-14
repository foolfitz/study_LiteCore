# 042 — 改一行 Makefile 就會重連結，而它在我兩次量測之間發生了

| | |
|---|---|
| **狀態** | **已確認（自作，當場抓到）／已記錄，未修** |
| **Bugzilla** | —（我方 build 系統，不是上游） |
| **發現日** | 2026-08-15 |
| **嚴重度** | 中——不會壞掉任何東西，但**會讓證據綁到一顆已經不存在的 artifact 上** |
| **可重現** | 100%，就是 make 的相依規則 |
| **是否上游** | 否 |

## 摘要

`Makefile` 是**每一個目的檔的相依**：

```make
$(E2_COMBO_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h \
		src/editor_discovery_api.h Makefile | $(E2_COMBO_BUILD)
```

所以**任何一次 Makefile 編輯**——即使改的是註解、或是一條跟這個 profile 無關的規則——
都會讓那個 profile 的全部 `.o` 過期，下一次 `make` 就重編＋重連結，**產出新的 hash**。

而 [finding 036](036-the-shipped-wasm-hash-is-not-a-function-of-the-source.md) 說 hash
不是原始碼的函數，所以**新 hash 不等於「一樣的東西」**，任何綁在舊 hash 上的證據都得重跑。

## 它怎麼咬到我的（2026-08-15，任務 #47）

1. 使用者建好組合 artifact：`e2-combination` ＝ **`938b4ff3…`**。我當場封存並釘住它。
2. 我在 `938b4ff3` 上跑 P2，發現產品 ABI 全被拒絕（0 ms，
   `editor v1 operations require the isolated narrow editor profile`）。
3. 成因不在引擎，在打包：`sdk-worker.js:98`–`101` 的 `editorV1Enabled()` 除了 capability
   還要 `editorContract.version === 1`，而 discovery 的 profile builder 從來不發那個欄位。
4. 我改了 builder（Python）**並且在 Makefile 加了一行斷言**，然後 `make e2-combination-profile`。
5. **Makefile 一動，六個 `.o` 全部重編、重新連結** → artifact 變成 **`ba1a5dd5…`**。

我原以為那一步「只會重打包 manifest」。**`make -n` 其實已經印出六行 `em++`，我沒有讀。**

## 損害盤點（量過的，不是推的）

| | |
|---|---|
| 三個凍結 artifact | **未變**：`835b453d`／`679def61`／`c89f069e`，重連結前後都核對過 |
| `938b4ff3` 這顆 | **還在**，`build/archive/e2-combination-938b4ff3/`，hash 核對相符 |
| 綁在 `938b4ff3` 的證據 | 只有一份 P2 執行，而**它的產品臂全部是 `unsupported`**——也就是它沒有量到任何 P2 的東西，只證明了打包閘門是錯的 |
| 判定 | **沒有任何判定綁過 `938b4ff3`** |

所以**實質損害為零**，但這是運氣好：如果第 4 步發生在一次已經成功的 P2 之後，
那一輪證據就會綁到一顆磁碟上已經不存在的 artifact。

## 為什麼這不是 finding 041 的重複

[041](041-static-test-targets-build-and-mint-through-a-phony-asset-chain.md) 講的是
**`.PHONY` 資產鏈會建置並鑄 release id**——「測試目標有副作用」。
本篇講的是**相依邊本身**：`Makefile` 在每個 `.o` 的相依清單裡，所以「編輯建置腳本」
與「修改原始碼」對 make 而言是同一件事。

E1-C 的 `regression` 屬性也是被這條邊咬的（SPEC-E1-C v9 修訂紀錄），但那一次的症狀是
**屬性永遠為假**；這一次的症狀是**artifact 在量測中途被換掉**。同一條邊，兩種傷害。

## 該怎麼做（未實作）

- **最小規矩，現在就開始用**：在任何一次 relink 之後，若還要動 Makefile，
  先跑 `make -n <target>` 並**讀完**——它會把重編印出來。這一次它印了，我沒讀。
- 可考慮把「與編譯無關」的斷言移出 recipe（改成獨立的 `test-*` 目標），
  這樣加檢查就不會使目的檔過期。**本篇不做這個改動**：它本身又是一次 Makefile 編輯，
  應該和下一次本來就要發生的 relink 一起做。
- 更根本的做法是把 `Makefile` 從 `.o` 的相依裡拿掉、改依賴一份只含編譯旗標的檔案。
  **代價要先想清楚**：那條邊的存在是為了「改了旗標就重編」，拿掉會少一層保護。

## 相關

- [036](036-the-shipped-wasm-hash-is-not-a-function-of-the-source.md)——新 hash 不等於同一個東西。
- [041](041-static-test-targets-build-and-mint-through-a-phony-asset-chain.md)——同一棵樹的另一種副作用。
- SPEC-E1-C 修訂紀錄 v9——`regression` 屬性被同一條相依邊釘死的那一次。
