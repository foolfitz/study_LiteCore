# `dist/profiles/` 的備份（不進 git，但不可遺失）

這個目錄裡的 artifact **不在版控裡**（見根目錄 `.gitignore` 的說明），但它們
**不是可有可無的建置產物**：

- 它們是**證據綁定的錨點**。`findings/evidence/` 底下每一筆結果都記著自己是對哪個
  `wasmSha256`／`loaderSha256`／`workerSha256` 取得的；`validate_e1_c.py` 的
  `artifact_binding()` 會拿現場 profile 跟證據比對。artifact 沒了，就再也無法確認
  「那批證據描述的是不是這個出貨物」。
- 至少 **R5 profile 目前無法從 source 重建**（見 SPEC-R10-000 的前置條件 P5）。
  也就是說這不是「刪了再 build 一次」的東西。

## 備份現況

| | |
|---|---|
| 位置 | `/home/jiajun/LibreOffice/study_LiteCore-artifact-backup/`（**在 repo 之外**） |
| 檔案 | `dist-profiles-20260808.tar.zst`（1.64 GiB → 567 MiB） |
| 校驗碼 | 同目錄的 `.sha256` |
| 內容 | `profiles/` 全樹，79 個項目 |
| 已驗 | `zstd -t` 通過；解出 `profiles/e1-editor-v1/sdk-manifest.json` 確認 `wasmSha256 = 835b453d…`、10 actions（＝現行出貨物） |

**未驗證的備份不算備份**——上面那行「已驗」是實際解開來對過雜湊，不是「tar 有跑完」。

## 重建備份

```sh
cd wasm_sdk_probe/dist
tar -c profiles | zstd -T0 -3 -o <備份路徑>/dist-profiles-<日期>.tar.zst
sha256sum <備份路徑>/dist-profiles-<日期>.tar.zst > <同名>.sha256
# 驗證（別跳過）
zstd -t <檔案>
zstd -dc <檔案> | tar -xO profiles/e1-editor-v1/sdk-manifest.json | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['editorContract']['wasmSha256'])"
```

**每次重新凍結 artifact 就要重做一份**（改 hash ＝ 換出貨物）。歷史備份不要刪：
舊證據綁的是舊 hash。
