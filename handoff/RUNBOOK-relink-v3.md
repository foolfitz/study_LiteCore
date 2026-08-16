# v3 連結的操作手冊（**指令交給使用者跑**）

寫於 2026-08-16，接在 [`HANDOFF-2026-08-16c-queue-shrunk.md`](HANDOFF-2026-08-16c-queue-shrunk.md)。

> **2026-08-16 的決定：先不連結。** 使用者裁定等一等。
> 佇列說 `p1Complete: True`——那是「沒有東西擋著」，**不是「現在就該連」**。
> 刻意留著的理由：今天剛量出來的引擎缺陷（`.uno:SelectText` 在空段落上選過頭）
> 只能透過連結才上得了線，**今天連了它就得再連一次**。
> 這份手冊在決定改變之前不執行。

**這份不決定要不要連結**——那是使用者的決定，而且還在等外部裁決（連結時機、
containment 重排要不要進同一次）。這份只是把「真的要連的時候要做什麼」寫成
可以照著跑的東西，**免得決定做完之後才在現場翻計畫**。

連結會鑄出新身分。舊判定不會變成假的，但**不再描述產品**（finding 027 的形狀）。

## 0. 連結前的檢查（全部可以機器判，現在就能跑）

```bash
cd wasm_sdk_probe

# 佇列：12 項如宣告在樹裡、還在擋的項目會讓 p1Complete 是 False
python3 tools/check_relink_queue.py

# 靜態：兩個目標都要 exit 0
make test-e2-c-static && make test-e2-b-static

# 凍結的四顆沒被碰過（archive 與 dist 逐位元相同——2026-08-16 已核對過一次）
for f in probe.wasm probe.js sdk-worker.js sdk-manifest.json; do
  cmp build/archive/e2-editor-v2-572035ac/$f dist/profiles/e2-editor-v2/$f \
    && echo "same  $f" || echo "DIFF  $f"
done
```

**`p1Complete: False` 就不要連結**——那正是「漏一項就是第二次 relink」的守衛。
唯一可以帶著 False 連結的情況，是使用者**明確裁定**某一項改到下一輪，而且那個
決定被寫進 `e2/relink-queue-v3.json` 的 `blocksRelink`（一次刻意的編輯，會出現在
diff 裡）。

現行狀態（2026-08-16）：**擋著的兩項是 `p1-3b-empty-readback` 與
`queue-barrier-verifies-own-paragraph`**。

## 1. archive（**已經做過，這裡是核對用的**）

`build/archive/e2-editor-v2-572035ac/` 已存在，四個檔與 `dist/profiles/e2-editor-v2/`
**逐位元相同**（2026-08-16 核對）。v3 用自己的 build 與 dist 目錄，所以連結不會碰到 v2。

## 2. 連結（**這一步請使用者跑**）

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v3/sdk-manifest.json
```

- `ALLOW_FROZEN_RELINK=1` 是**刻意的同意**：沒有它，Makefile 會拒絕並印出那顆
  artifact 綁著什麼（`refuse_unasked_relink`，`Makefile:814`）。v3 從第一次連結
  就掛著這個守衛，所以不會有 v3 artifact 意外出現。
- 目標是**檔案路徑**，沒有別名。它會連 `build/e2/editor-v3/`，然後由
  `tools/build_e2_c_profile.py` 打包進 `dist/profiles/e2-editor-v3/`。
- **v2 的 target 一個字都不會動。**

連結完之後把五個身分記下來（第五個是 manifest 自己，第二輪新增的綁定）：

```bash
cd wasm_sdk_probe/dist/profiles/e2-editor-v3
sha256sum probe.wasm probe.js sdk-worker.js sdk-manifest.json
python3 -c "import json;print(json.load(open('sdk-manifest.json'))['editorContract']['abiVersion'])"  # 應該是 3
```

殼層 bundle 的摘要（第五個之外的那一個）由
`python3 tools/build_e2_c_shell_bundle.py` 印出來，**唯讀**；要寫入才加 `--write`。

## 3. 連結之後、第二輪 D0 之前：**先凍結矩陣**

這個窗口是外部裁決指名「第一輪的錯唯一能重演的地方」。現在有守衛了，但守衛只會
拒跑，不會替你填：

1. 把上一步的五個雜湊填進 `e2/validation-matrix-v2-draft.json` 的 `baseline`
   （目前全是 `TO-BE-FILLED-AT-RELINK`）；
2. `status` 改成 `frozen-before-D0`；
3. 更名為 `e2/validation-matrix-v2.json`（草稿與凍結版是兩個檔，`-draft` 留著）；
4. 驗一次：

```bash
python3 tools/e2_c_matrix_entry.py --matrix e2/validation-matrix-v2.json \
  --profile e2-editor-v3
```

**只翻 `status` 不填雜湊會被擋下來**（自我測試裡就有這一條）。
`run_e2_c_d0.py` 與 `analyze_e2_c_d0.py` 都會在動作前呼叫同一個斷言，所以
第二輪的 D0 在矩陣凍結之前根本跑不起來。

## 4. 連結之後要重跑的（P3，**這是第二次 relink 的實際代價**）

- **E2-B**：132 個正向 run ＋ 12 列 negative matrix ＋ no-op 方程式 ＋ 四路清單，
  `validate_e2_b.py` 重推判定。（E2-B 對 v2 的判定仍為真，但不再描述產品。）
- **E2-C 第二輪**：D0 → D5，用凍結後的 `validation-matrix-v2.json`，
  證據寫到 `e2-c-validation-v3/`（**不覆寫第一輪**）。
- **E1-C**：可分割，先不做（另一顆 artifact、另一套人工輪）。

## 5. 連結之後**不要**做的事

- **不要在連結與凍結之間改任何原始碼**。改了就要重連，而重連又是一個新身分。
- **不要覆寫第一輪的證據目錄**。第一輪是紀錄，不是草稿。
- **不要在 sweep 與判定之間重編**（`wasm-build-not-reproducible`：artifact 的
  雜湊不是原始碼的函數）。
