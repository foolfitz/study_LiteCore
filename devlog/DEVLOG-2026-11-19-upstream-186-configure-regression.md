# 2026-11-18～19：上游 WASM configure 回歸（finding 186）送 Gerrit 的經過

範圍：從「找下一個最適合送上游的 WASM 貢獻」到 Gerrit 214345 的 Patch Set 2 推上去為止。159 由另一個 session 進行，這裡不記。
細節與原始資料：`findings/186-master-wasm-configure-fails-gtk3-qt5.md`、`findings/evidence/186/`。給擁有者的白話說明：`EXPLAINER-2026-11-18-finding-186-wasm-configure.md`。

## 結果

| 項 | 值 |
| --- | --- |
| Gerrit | [214345](https://gerrit.libreoffice.org/c/core/+/214345)，Change-Id `Ic9cba4af78af695b31f5e600882a882e7b8c7761` |
| Patch Set 1 | 11-18 07:49 UTC，`b7f3bd7eb41c`：Emscripten 上清掉 `USING_UNIX_DESKTOP`。Jenkins Verified+1 |
| Patch Set 2 | 11-19 02:44 UTC，`399a9df475a7`：`emscripten)` 區塊加 `test_gtk3/gtk4/kf5/kf6=no`。Jenkins 排入（job 10396），Lohmaier 已在 reviewer 名單 |
| 討論串 | [211916](https://gerrit.libreoffice.org/c/core/+/211916?tab=comments)（造成回歸的已合併 change） |
| Bugzilla | 不開 |
| 本機分支 | `wasm-lite/upstream-master/submit` 的 `emscripten-configure-gtk`（PS1）、`emscripten-configure-gtk-ps2`（PS2） |

## 時間線

1. **11-18 上午：排序。**擁有者要繼續做 WASM 上游貢獻。以 11-10 的盤點為基線對現行 master 重驗，排出 configure 回歸 → 159 → 003（`RESEARCH-2026-11-18-next-upstream-wasm-contribution.md`）。configure 回歸排第一的理由：成因確定、只需跑 configure 就能驗證，而且有時效——Lohmaier 11-17 已在 211916 點出成因，但還沒人修。
2. **configure 臂。**未修的 master 失敗（`VCLplugs to be built: gtk3 qt5`）；`--disable-gui` 不受影響。比較兩種修法：
   - M：只關 gtk 測試，即 Lohmaier 留言的方向。configure 會過，但 `USING_UNIX_DESKTOP=TRUE`，連帶 `ENABLE_OPENGL_*` 與 `HAVE_FEATURE_OPENGL` 都打開。
   - R：清掉 `USING_UNIX_DESKTOP`。設定單與回歸前的 `2a2335cf` 相同。
   - 我選了 R。codex 對抗性審查一輪，指出 commit message 有兩句說過頭，已改。
3. **11-18 凌晨：兩種修法都全量建置**（擁有者：「幫我建置，先建只關 gtk 的那一個」）。各約 47 分鐘，兩棵都成功、都到開始中心、都能開 Writer 打字。M 的 `main.xcd` 多 686 行 Unix 桌面設定（約一百個 unxwnt 快速鍵、13 個向 `DesktopBackend` 查的值），按 F11 會開樣式側邊欄；R 與回歸前都沒反應。
4. **11-18 下午：推之前。**發現原作者 Chris Mayo 回 Lohmaier「not something new caused by this MR」。在 `d98a^` 與 `d98a` 各跑 configure：前者過，後者失敗。commit message 補上這一句，回覆草稿開頭改為先回答他。擁有者推上 PS1，並在 211916 貼出回覆（擁有者要求識別字一律用反引號）。
5. **11-18 16:20 UTC：Lohmaier 回覆。**
   - 確認我們的成因分析。
   - 說 WASM tinderbox 已加 `--disable-gtk3` 繞過。
   - 認為 WASM 版多帶東西是好事（他說沒細看改了多少），偏好只關 gtk 和其他 VCL plugin。
   - Chris Mayo 另開 214404（不 export `USING_*`），與我們無關。
6. **11-19：照 Lohmaier 改成 PS2。**變體 A（gtk3/gtk4/kf5/kf6 測試關掉）的 configure 兩臂都過。設定單與已全量建置的 M 逐行相同，所以 M 的建置與瀏覽器結果適用於 A。擁有者推上 PS2，並在 211916 回覆 Lohmaier。

## 學到的

- **判準的容許清單要寫值。**我把「新增的 `USING_UNIX_DESKTOP`」列為可接受的差異，沒寫它必須是空的。照字面，M 會被放行；是同一份 diff 裡沒列入的 `ENABLE_OPENGL_*` 把它抓出來。
- **說「另一種修法有問題」之前先建它。**我原本猜 M 可能建不起來，實建後是錯的。它能用，只是順帶改了行為。「建不起來」與「能用但不同」是兩種論點，對上游要說哪一種，取決於有沒有建過。
- **原作者說「不是我造成的」時，最有力也最便宜的回答，是在他的 commit 與前一個 commit 各跑一次。**這次 configure 各約 30 秒，比讀 diff 推論有說服力。
- **維護者已表態時，我的偏好只是一個選項。**R 的理由（修回歸只修回歸）站得住，但 Lohmaier 的價值判斷（WASM 更完整是好事）同樣合理，而且是他的專案。第一則回覆就留了「你偏好就改」這條路，所以改成 PS2 沒有成本。
- **Gerrit 的新版本不需要 force push。**同一個 Change-Id 推到 `refs/for/master` 就是同一個 change 的下一個 patch set，舊版本留在歷史。`submit` 工作樹上同時有好幾個分支，推的時候一律寫明分支名。

## 未完成與留著的東西

- 214345 等審查。照擁有者的說法，兩週內沒動靜屬正常，不催。
- 硬碟上：`wasm-lite/upstream-master/build-186-M`（6.1 GB）與 `src-186-M`（1.5 GB，本機分支 `finding186-fixM-test-only`，不可推）。要不要刪還沒問。`build-186-R`、`src-186-R` 現在是 159 在用。
- 這一輪 186 的檔案都還沒 commit 進 study_LiteCore。
- 沒驗的：含 Impress 的模組組合（M／A 之下會多建 OGLTrans）；約一百個快速鍵裡只實測了 F11。

## 追記：PS2 的 CI 失敗（11-19）

Jenkins 對 PS2 給 Verified-1，失敗在 `CppunitTest_sc_swarmsolvertest` 的一個數值斷言（3 對 2.9999871，容差 1e-5）。與本 change 無關：PS1 在同一台 CI 機器、同一個父 commit 上全過，兩版差異只在 Linux 不會執行的 Emscripten 分支，而求解器的亂數種子來自 `std::random_device`。最近 100 次同一個 job 的建置裡只有這一次撞到。處理方式照 `study_OxODF/upstream-libreoffice/README.md`：不 rebase、不補 patch set，請有 Jenkins 權限的人重跑。證據 `findings/evidence/186/ci-2026-11-19-swarmsolver.txt`。
