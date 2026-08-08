# 027 — R8-D 的判定在 release 內容變更後靜靜過期四天；「static」測試目標會重鑄 release id

| | |
|---|---|
| **狀態** | 已確認（mtime ＋ 確定性重建 ＋ `make -n` 三方一致）；修復campaign已重跑 |
| **發現日** | 2026-08-08（重跑 R8-D soak 後 `validate_r8_d.py` 由 `PARTIAL_GO_LOCAL_DELIVERY` 變成 `STOP`，追下去才發現） |
| **嚴重度** | 一般偏高：判定會在無人察覺的情況下描述一個不存在的 release |
| **可重現** | 100 %（靜態事實） |
| **是否上游** | 否，我方 harness |

## 一句話

R8-D 的瀏覽器證據綁在一個**由 bundle 內容算出來的 release id** 上。bundle 裡有一個檔案在
2026-08-07 被改動，於是所有 08-04 錄下的瀏覽器證據**當下就過期了**——但**沒有任何東西會發現**，
因為 release id 只在有人重建 `dist/r8c/release-set.json` 時才會重算，而那要等到某個
`make` 目標被執行。判定因此連續四天宣稱 `PARTIAL_GO_LOCAL_DELIVERY`，描述的卻是一個已經
不存在的 release。

## 證據鏈（已觀察）

| 事實 | 來源 |
|---|---|
| R8 release bundle 含 17 個 artifact，其中一個是 `profiles/writer-review-r6/sdk-worker.js` | `dist/r8c/releases/*/release-manifest.json` 的 `artifacts[].url` |
| 該檔 mtime ＝ **2026-08-07 11:19** | `stat` |
| compatibility 證據 mtime ＝ **2026-08-04 15:38**，記的 `releaseId` ＝ `writer-review-5fa3ca0d38f2b46d` | `evidence/sdk-r8/production/compatibility/chrome/summary.json` |
| 現行 release set ＝ `writer-review-d6bee07b960a942d`（A） | `dist/r8c/release-set.json` |
| 其餘 bundle 檔案 mtime 全部 ≤ 08-03，**內容沒變的不是它們** | `stat` |
| builder **是確定性的**：連續重建兩次三個 id 逐字相同；`CREATED_AT` 是寫死常數 `2026-08-04T00:00:00+08:00` | `tools/r8_bundle.py:31`；實測連跑兩次 |

所以 id 改變**不是重建噪音，是真的內容變更**，時間點是 08-07。

## 為什麼四天沒人發現

`validate_r8_d.py:65` 的 `activeCachedRelease`（`value.get("releaseId") == release_id`）**就是**
擋這件事的閘門，它沒有壞——它只是**沒有機會執行到會失敗的那一刻**：

- `release_id` 來自 `dist/r8c/release-set.json`（`run_r8_production.py:131` 只**讀**它）；
- 那個檔只有在 `make` 跑到 `build_r8_c_release_set.py` 時才重寫；
- 在那之前，舊的 set 檔還躺在 `dist/`，記的還是 `5fa3ca0d…`，於是比對照樣通過。

**過期的是證據，但察覺過期需要一次重建。**判定的新鮮度因此取決於「最近有沒有人跑過 make」，
而不是「證據是否仍描述現況」。

## 附帶兩個同族問題

1. **`make test-r8-d-static` 會改動建置產物。**`make -n test-r8-d-static` 明確跑
   `python3 tools/build_r8_c_release_set.py --output dist/r8c`。名字叫 static 的目標會鑄出新的
   release id，把既有瀏覽器證據的綁定當場作廢。（同族前例：`make test-e1-c-static` 會重建凍結的
   `e1-editor-v1`；`validate_e1_c.py` 會覆寫 `desktop.pdf`，已於 2026-08-08 修掉。）
2. **證據根分裂：修好之後的重跑餵不進判定。**`validate_r8_d.py` 讀
   `findings/evidence/sdk-r8/`，但 finding 023／025 修復後的重跑（Firefox compatibility 28/28）
   與 2026-08-08 的兩輪 30 分鐘 soak 都寫到了 `findings/evidence/sdk-r8-post-023-fix/`。
   **那些是真量測，但 validator 從來沒看過它們**；`formalGaps` 裡「Firefox 沒有以單一 campaign
   重跑」那幾條之所以還在，正是因為證據放在它讀不到的地方。

## 修復（2026-08-08）

四個相位以**單一 campaign** 重跑進 `findings/evidence/sdk-r8/`，中間**完全不呼叫 `make`**——
因為 `make` 會重鑄 id，把已錄好的相位當場作廢。這正是 SPEC-R8-D「必須是同一次 campaign」
的實際機制，先前只寫成文字、沒有寫成可執行的約束。

compatibility 兩瀏覽器已完成並綁上現行 release `d6bee07b…`：各 **28/28、6 批次、12 worker、
每頁最高 3**，與歷史紀錄逐項相同（＝忠實重跑，不是換了行為）。soak 兩輪隨後。

## 待處理（未做）

1. **讓過期可被偵測，而不是等 make。**最省的作法：把「證據記的 releaseId」與「bundle 內容雜湊」
   一起記進證據，validator 直接重算 bundle 雜湊比對，不經過 `dist/` 的快取狀態。
2. **`*-static` 目標不該改動建置產物**，或至少改名，讓「static」名副其實。
3. **證據根統一**：`sdk-r8` 與 `sdk-r8-post-023-fix` 並存會讓「修好了」與「判定看得到」脫節。

## 證據

- `wasm_sdk_probe/dist/r8c/release-set.json`、`dist/r8c/releases/*/release-manifest.json`
- `wasm_sdk_probe/tools/r8_bundle.py:31`（`CREATED_AT` 常數）
- `wasm_sdk_probe/tools/validate_r8_d.py:61-74`（`compatibility_check` 與 `activeCachedRelease`）
- `wasm_sdk_probe/tools/run_r8_production.py:131`（`release_ids()` 只讀不寫）
- `findings/evidence/sdk-r8/production/`（重跑後）

## 修訂紀錄

- 2026-08-08：建檔。起因是重跑 soak 後判定變 STOP；追查發現 `compatibility` 的
  `activeCachedRelease` 失敗，再回溯到 08-07 的 `sdk-worker.js` 變更。
  一併記錄「static 目標會重建」與「證據根分裂」兩個同族問題。
