# `sdk-r8-post-023-fix/` — 已退休的證據根（保留，不得刪除）

**狀態（2026-08-10）：已退休，但保留。** 沒有任何 validator 讀這棵樹；
它也不再是任何判定的依據。但它**仍是三份文件的主要證據**，刪掉會真的丟東西。

## 為什麼存在

finding 023／025 修好之後的重跑，以及 2026-08-08 的兩輪 30 分鐘 soak，
當時寫到了這裡而不是 `sdk-r8/`。[finding 027](../../027-r8d-verdict-silently-outlived-its-release.md)
把這件事記成「證據根分裂」——是真量測，但 `validate_r8_d.py` 從來沒看過它們。

## 為什麼已經不再需要它來取得判定

2026-08-08 的單一 campaign 已把四個相位重跑進 `sdk-r8/`；
2026-08-10 修 [finding 028](../../028-cancel-during-manifest-body-read-reported-as-corrupt-manifest.md)
後又把 R8-B／R8-C 重跑進 `sdk-r8/`。六個證據家族現在全部 bound 在
`sdk-r8/`，0 superseded、0 unattributable。**R8-C 曾經只有這裡綁對 release，
那個理由已經消失。**

## 為什麼仍然不能刪（已觀察，2026-08-10 逐路徑查證）

以下路徑**只存在於這棵樹**，`sdk-r8/` 沒有對應物：

| 路徑 | 被誰引用 |
|---|---|
| `driver-stderr/`（含 `soak/`） | [025](../../025-webdriver-script-injection-never-ran-on-firefox.md):159、[014](../../014-firefox-long-lived-wasm-worker-init-exhaustion.md):427 |
| `service-worker-firefox-injected-path/` | [025](../../025-webdriver-script-injection-never-ran-on-firefox.md):128 |
| `service-worker-unified/` | [025](../../025-webdriver-script-injection-never-ran-on-firefox.md):134 |

（`production/compatibility/firefox/` 在 `sdk-r8/` 有對應物，是唯一可替代的一項。）

`specs/SPEC-R8-D-production-validation.md:259` 也整棵引用
`production`／`service-worker` 全樹。

## 要真的刪掉，先做什麼

先把 025／014／SPEC-R8-D 引用的那三個路徑改指到別處，或把它們搬進
`sdk-r8/` 以外的長期歸檔區並更新全部引用。**在那之前，刪除等於讓三份
已結案文件失去證據。** 全樹 14 MB，保留成本很低。

## 修訂紀錄

- 2026-08-10：建檔。起因是 finding 027 第 5 步（退休本樹）在 R8-B／R8-C 重跑完成後
  解鎖，但逐路徑查證發現交接文件只考慮了「R8-C 唯一綁對 release 的證據」這一層，
  漏了 025／014／SPEC-R8-D 的引用。因此改為原地退休、保留。
