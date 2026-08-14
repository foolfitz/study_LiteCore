# 041 — 「靜態測試」目標會經由 `.PHONY` 資產鏈建置並鑄造 release id

| | |
|---|---|
| **狀態** | **已確認、已修**（`test-r8-c-static`／`test-r8-d-static` 去除資產相依，2026-08-14） |
| **Bugzilla** | —（我方基礎設施，不是上游） |
| **發現日** | 2026-08-14 |
| **嚴重度** | **中**——沒有造成損害，但它是一個**會寫入的閘門**，而閘門不該有副作用 |
| **可重現** | 100%（`.PHONY` 相依保證每次走到都重跑） |
| **是否上游** | 否 |

## 摘要

`make test-r8-d-static` 讀起來是測試目標，實際的相依鏈是：

```
test-r8-d-static → test-r8-c-static → r8-service-worker-assets
  → dist/r8c/release-set.json → dist/releases/index.json
  → dist/r8/release-manifest.json
```

而最後這條的相依 `r7-assets` 在 `.PHONY` 裡，**所以每次 make 走到它就必然重跑**
`build_r8_release_manifest.py` 與 `build_r8_bundles.py`。**鑄造 release id 是路由造成的
副作用，從來不是這個目標的斷言。**

**推論比事件重要**：E1-C 的 `regression` 屬性定義裡就含 `test-r8-d-static`，所以
`validate_e1_c.py --run-regression` **每跑一次就鑄一次 release id**。

## 怎麼撞到的

2026-08-14 跑 E1-C 重綁輪的回歸替代時。它鑄出 `writer-review-c9f3c6fb73e6df9e`
——一個不在 `dist/releases/` 裡的新 id。

**我第一次的說法是錯的，已更正**：我寫「在 bundle builder 動手前停掉」，但
`dist/releases/index.json` 的 mtime 15:44 證明 **`build_r8_bundles.py` 已經跑完了**；
被 `Terminated` 的是再下一步的 `build_r8_c_release_set.py`（`Makefile:1299`）。
外部覆核指出這一點，我核對過成立。

## 損害：綁定面為零，staging 檔為**不可知**——兩者要分開記

**綁定面為零，已核對**：`dist/releases/` 沒有新目錄、`index.json` 內容仍只列
`d6bee07b…` 與 `da9e9a18…` 兩個 release、`createdAt` 保持 2026-08-04；
`findings/evidence/sdk-r6/summary.json` 雖被 `test-r6-release` 重寫，但**內容與 git HEAD
逐位元組相同**（只有 mtime）；三個凍結 artifact 未變。

**但 `dist/r8/release-manifest.json` 現在帶著新鑄的 id 躺在磁碟上，而它 15:44 之前的內容
無從驗證**——`dist/` 走 allowlist 不進 git，也沒有 checksum 基線。所以正確的說法是
**「綁定面損害為零（已量測）＋ 這個 staging 檔的前狀態不可知（未量測）」**，
不是籠統的「沒有損害」。照實記在這裡，不靜默留置。

## 同族案例：會寫入的閘門不只一個

`test-r6-release` 會**重寫** `findings/evidence/sdk-r6/summary.json`。這一次它恰好寫出
逐位元組相同的內容，所以看不出來——**但「恰好相同」不是「不會寫」**。
一個會改寫自己所驗證之證據的閘門，違反 finding 027 那一輪立下的第二條紀律
（validator 不得改動它驗證的證據）。

**這一族要一起看**：目前只確認 r8-c／r8-d 會鑄造、r6 會重寫。
其餘五個目標我只驗過它們不發 `em++`／`emcc`，**那不等於驗過它們沒有副作用**。

## 修法（2026-08-14）

`test-r8-c-static` 去掉 `r8-service-worker-assets` 相依，配方本體一行不動；
`test-r8-d-static` 只相依 `test-r8-c-static`（測試目標，無資產）。實測：

- 兩個目標仍然通過；
- 連跑之後 `dist/r8/release-manifest.json` 的 sha256 **不變**——副作用消失。

## 這一則要留給下一個人的話

**閘門的相依鏈是它行為的一部分，而 `.PHONY` 讓相依鏈變成「每次都跑」。**
看一個測試目標會不會動到東西，讀配方不夠，要讀它整條相依鏈；
`make -n` 是最便宜的判別法，我這次是**先踩到才去讀的**。
