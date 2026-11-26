# 凍結前的磁碟盤點：哪些可以刪（2026-11-26）

> 背景：擁有者決定凍結 study_LiteCore 的開發，心力移到 `../study_COOL/`。
> 本文只做盤點與分級，**沒有刪任何東西**。
> 證據標記：**已觀察**＝這次實際量過或讀過；**推論**＝依原始碼或過往紀錄推得，未實跑。

## 0. 結論

專案目錄 `du` 約 124 GiB，硬碟剩 108 GiB（88% 已用）。分成四級：

| 級 | 內容 | 可回收 | 刪了失去什麼 |
| --- | --- | ---: | --- |
| **A** | 中繼物、瀏覽器暫存、已定案的對照組 | **約 21 GiB** | 什麼都不失去（大檔逐位元在保留區有副本） |
| **B** | 建置樹、工具鏈、沒在用的原始碼 worktree | **約 43 GiB** | 恢復開發時要重建（每棵 1–2 小時，擁有者的 make） |
| **合併** | `dist/profiles`＋`build/archive` 用 hardlink 去重 | **約 9.6 GiB** | 不刪任何位元組 |
| **C** | 唯一副本、別處依賴的東西 | 0 | **不要刪** |

另外，上游 WASM 貢獻的工作樹（`wasm-lite/upstream-master/`，27 GiB）要看 002／186／159 之後還做不做，見 §4。

A＋B＋合併全做大約回收 74 GiB，剩約 50 GiB。

## 1. 動手之前先做的事（跟刪除無關，但凍結前該處理）

這些是**這顆硬碟是唯一副本**的東西。刪建置樹不會碰到它們，但凍結之後也不會再有人想起來。

1. **study_LiteCore 有 2,187 個 commit 沒推**：`github/main` 停在 2026-09-07（已觀察）。兩個多月的工作只在這顆硬碟上。
2. **186 的檔案還沒 commit**：`findings/186-*.md`、`findings/evidence/186/`、`findings/drafts/186-*`、`EXPLAINER-2026-11-18-*.md`、`RESEARCH-2026-11-18-*.md`、`devlog/DEVLOG-2026-11-19-*.md`，另有 `RESEARCH-2026-11-10-tdf130857-qt-weld-commits.md`、`codex-claude-code-delegation.md`（已觀察，`git status`）。
3. **Nextcloud app** `~/Projects/Nextcloud_Apps/litecore`：`main` 比 `github/main` 多 13 個 commit；`litecoreprobe` 沒有任何 remote（已觀察）。
4. **159 的上游分支只在本機**：`emscripten-bridge-scaddins`（`ab916909bf26`）沒推到 Gerrit，存在 `libreoffice-25-2/.git` 裡（已觀察）。002、186 已在 Gerrit 上。
5. **沒進任何 git 的手寫文件**（整個目錄刪掉會一起消失）：
   - `native-lok-26-8/` 底下的 `bugzilla-triage.md`、`bugzilla-triage-白話說明.md`、`bugzilla-B3-草稿說明.md`、`bz_result.md`、`bugzilla-triage-work/`（2 MiB）
   - `libreoffice-26-8/` 底下的 `LibreOffice_VCL_Qt6_研究報告.md`、`scriptforge-26.8-findings.md`
6. **出貨 profile 的樹外備份只有 08-08 那一份**（`../study_LiteCore-artifact-backup/`）。之後凍結的 v8、v19、a11y、ods 系列只在這顆硬碟（`docs/ARTIFACT-BACKUP.md`、既有紀錄）。

## 2. A 級：現在就能刪

| 項目 | 大小 | 為什麼安全 |
| --- | ---: | --- |
| `wasm_sdk_probe/build/` 裡除 `archive/` 與另外 9 個目錄以外的全部（約 167 個項目） | 9.5 GiB | 見下方 §2.1 |
| `wasm_sdk_probe/dist/r8-c-profiles/`、`dist/r8-d-profiles/` | 3.0 GiB | 8 月 R8 量測時的 Chrome／Firefox 使用者資料夾，大檔是 Service Worker 快取與 Firefox `cache/morgue`。沒有證據把它們當錨點（已觀察，grep 只命中 `findings/evidence/` 底下另一份同名路徑） |
| `wasm-lite/upstream-master/build-186-M`＋`src-186-M` | 7.6 GiB | 186 Patch Set 1 的對照組。上游已選 PS2 並推出，比較結果在 `findings/evidence/186/`。本機分支 `finding186-fixM-test-only` 留在 git 裡，用 `git worktree remove` 不會刪分支 |
| `wasm-lite/tools/qt6-wasm-build-6.10.2-r2`、`qtbase-everywhere-src-6.10.2` | 1.3 GiB | Qt6 本身的編譯中繼。Qt6 線的 LibreOffice 建置樹 10-12 就刪了；沒有任何 Makefile、工具、`config_host.mk` 引用這兩個目錄（已觀察）。安裝好的 `qt6-wasm-6.10.2`（85 MiB）、原始碼 tarball 和 `wasm-lite/patches/qtbase-*.patch` 都留著 |
| 零碎 | 約 0.05 GiB | `.playwright-mcp/`（截圖）、`wasm_sdk_probe/.pytest_cache`、自家目錄裡的 `__pycache__`、`findings/evidence/**/session-*/profile/`（LibreOffice 使用者 profile，刻意不 commit 的那批，約 5 MiB）、`upstream-master/relink-*.log` 與 `build-nosym-e42678e7-configure-fail/` |

合計約 21 GiB。

### 2.1 `wasm_sdk_probe/build/` 怎麼判的

這次用 sha256 比對了 `build/` 每一個檔案和保留區（`dist/profiles/`＋`build/archive/`）（已觀察）：

- 候選目錄共 10,553 個檔：**9,667 MiB 在保留區有逐位元相同的副本**。
- 沒有比到副本的 846 MiB 裡，754 MiB 是 `.odt`，幾乎全在 `merge-native-pmpc*` 和 `merge-wasm-private`。這些是合併回合的輸入；`merge-native-pmpc*` 有被 `findings/evidence/v17/v5/e02-discriminator/` 用 sha256 綁住（已觀察），`merge-wasm-private` 沒查。三個都**留著**（列在 B 級）。
- 剩下約 90 MiB 是 `.o`、組裝出的 `.js`、log、原生小 harness 執行檔、字型子集，都是工具產出的中間物。

**刪除時保留**這 10 個：`archive`、`release`、`merge-native-pmpc`、`merge-native-pmpc-e02d`、`merge-wasm-private`、`ms-formats-w`、`mono-reach`、`cjk-subset`、`merge-native-r0-limit`、`probe-hand-0212`。後 5 個裡有保留區沒有的內容，合計約 0.3 GiB，不值得為了它們去判讀。

刪掉之後會有兩個副作用：

- 證據檔裡記錄的 `build/e2/...`、`build/ods/...` 路徑會指向不存在的檔案。位元組本身還在保留區，所以「這份證據綁的是哪個 artifact」照樣答得出來；但讀路徑的重讀腳本要先把路徑還原才能跑。凍結期間不會跑它們。
- **之後若有人在 `wasm_sdk_probe/` 跑 `make`，它會發現中繼物不見而重新連結，再用 `cp` 蓋掉 `dist/profiles/` 裡的凍結 artifact**（推論，依 `Makefile` 的規則形狀）。wasm 建置不可重現，蓋掉就回不來（finding 036 的前例）。所以 A 級做完要接著做 §3 最後一步的唯讀保護。

## 3. 用 hardlink 合併保留區（不刪任何東西）

`dist/profiles/` 和 `build/archive/` 是出貨 profile 的唯一副本，不能刪，但裡面重複很多：例如 e2-editor-v9 到 v14 每個 232 MiB，大檔全都在別的 profile 裡有一模一樣的副本。

| | 磁碟佔用 | 去重後 | 可回收 |
| --- | ---: | ---: | ---: |
| `dist/profiles` | 10.4 GiB | 7.1 GiB | 3.3 GiB |
| `build/archive`（11-04 已在內部去重過） | 8.2 GiB | 7.0 GiB | 1.2 GiB |
| **兩者合併** | **18.6 GiB** | **9.0 GiB** | **9.6 GiB** |

（已觀察，sha256 全檔比對，不到 1 MiB 的小檔不計。）

之前不對 `dist/` 做 hardlink，理由是 `make` 用 `cp` 原地覆寫，會連帶改掉所有連結到同一個 inode 的副本。凍結後不再跑 `make` 了，再加上唯讀保護就安全：對唯讀檔，`cp` 會直接失敗，`cp -f` 則是先刪掉再建新檔、連結自然斷開，兩種都不會改到其他副本。

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
hardlink -n -c dist/profiles build/archive     # 預演，看會合併多少
hardlink -c dist/profiles build/archive
chmod -R a-w dist/profiles build/archive       # 唯讀保護（A 級做完也要做）
```

`dist/r8c/`（1.1 GiB）與 `dist/releases/`（0.7 GiB）是 R8 時期的發布包，內容大多跟保留區重複，可以一起列進 `hardlink` 的參數。

## 4. 上游 WASM 貢獻的工作樹（27 GiB，要擁有者決定）

`wasm-lite/upstream-master/` 是 002、186、159 送 Gerrit 用的工作區。它算不算「凍結的那一部分」，要看你之後還會不會回 Gerrit 的 review：

| 目錄 | 大小 | 用途 |
| --- | ---: | --- |
| `submit/` | 1.5 GiB | 推 Gerrit 的 worktree，上面有 `emscripten-configure-gtk-ps2`、`emscripten-bridge-scaddins`、`vcldemo-wasm-gerrit` 等分支 |
| `build-186-R`＋`src-186-R` | 7.6 GiB | 現在是 R＋159，159 的增量重建只要 317 秒 |
| `build-nosym`＋`src` | 8.2 GiB | 002（vcldemo）的建置樹，重新連結 vcldemo 約 3 分鐘 |
| `ccache/` | 1.2 GiB | 這棵樹自己的 ccache |
| `archive-*` | 0.4 GiB | 159 之前的 R 產物、未修版的 vcldemo |
| `build-186-M`＋`src-186-M` | 7.6 GiB | 已列入 A 級 |

- **A. 上游也一起凍結**：先把 159 推出去（或決定不推），再刪 `build-*`、`src*`、`ccache`。分支都留在 git 裡，`submit/` 可以留著。可回收約 17 GiB。
- **B. 上游繼續做**：只刪 A 級那一組（186-M），其餘留到 002、186 合併、159 推出去之後。
- **C. 上游工作搬到 study_COOL**：一樣先推 159。之後要改 patch，都得 rebase 到新的 master 重建；舊建置樹只有在增量重建時省時間。

**任何一種都不能刪 `libreoffice-25-2/`**，見 §6。

## 5. B 級：凍結後可刪，恢復開發要重建

| 項目 | 大小 | 刪了的代價 |
| --- | ---: | --- |
| `wasm-lite/build-headless-probe`、`build-a11y-gate0`、`build-ods-viewer-v2` | 17.4 GiB | 三棵 wasm 核心（`Makefile` 的 `LOBUILD`、`E2_V5_CORE`、`ODS_*_CORE`）。任何重新連結都要它們，重建每棵 1–2 小時。重建出來的 hash 會跟舊的不同，但已出貨的 profile 在 `dist/` 裡不受影響 |
| `build-native-26-8` | 6.6 GiB | 原生 core（`build_calc_undo_native.py`、`build_msformat_native.py` 等 harness 連它）。來源是 `libreoffice-26-8` |
| `native-lok-26-8/build`＋`src` | 7.8 GiB | 另一棵原生 LOK 建置，`src` 是乾淨的 detached worktree。**先搬走 §1 第 5 點的 md 檔**，再用 `git worktree remove` 移除 `src` |
| `libreoffice-26-2` worktree | 4.0 GiB | 沒有任何建置樹用它（已觀察，三棵 wasm 與原生樹的 `SRCDIR` 都是 `libreoffice-26-8`）。它唯一的修改跟 26.8 那兩份 fs-image patch 是同一件事。移除前先 `git -C libreoffice-26-2 diff > wasm-lite/retired-builds/libreoffice-26-2-worktree.diff`；它是髒的，`git worktree remove` 要加 `--force` |
| `collabora-25.04` worktree | 1.5 GiB | 乾淨，沒有東西引用它。分支 `distro/collabora/co-25.04` 留在 git |
| `libreoffice-26-8/external/tarballs`、`libreoffice-26-2/external/tarballs` | 1.3 GiB | 第三方原始碼的下載快取，重建時重新下載 |
| `wasm-lite/tools/emsdk`、`qt5-src`、`qt5-wasm` | 2.8 GiB | 重建 wasm 核心必需。`qt5-src` 的 `qtbase` 子模組有未提交的改動（已觀察，`M qtbase`），刪之前要先看是什麼 |
| `build/merge-native-pmpc*`、`merge-wasm-private`、`build/release`，以及 §2.1 的 5 個小目錄 | 1.3 GiB | 合併回合的 `.odt` 輸入（證據用 sha256 綁住）、0.2.1／0.2.2／0.2.5 的 app 發布包。刪了就失去重讀那幾份證據的能力 |

合計約 43 GiB。

`libreoffice-26-8` 的未提交修改不用擔心：這次把 `wasm-lite/patches/` 的 10 份 26.8 patch 依序套到 HEAD 的原檔上，**9 個被改動的檔逐位元等於現在的 worktree**（已觀察）。所以就算哪天要動這棵樹，它的狀態也能從 patch 重建。

## 6. C 級：不要刪

| 項目 | 大小 | 理由 |
| --- | ---: | --- |
| `libreoffice-25-2/`（含 `.git` 7.8 GiB） | 9.2 GiB | **它的 `.git` 是另外 9 個 worktree 共用的物件庫**：`libreoffice-26-2`、`26-8`、`collabora-25.04`、`native-lok-26-8/src`、`upstream-master` 的 4 個，還有**專案外的 `/home/jiajun/LibreOffice/lo-submit`**（分支 `table-style-sort`，tdf#173931）。159 等沒推的分支也只在這裡。刪了全部一起壞 |
| `libreoffice-26-8/` | 4.3 GiB | 所有建置樹的 `SRCDIR`；study_COOL 的 `litecore-on-collabora-core-research.md` 引用它的 commit；有兩份未追蹤的 md |
| `cool-26-04/` | 1.9 GiB | 已經是斷掉的 worktree（主 repo `/home/jiajun/LibreOffice/collabora_online` 不在了），但 study_COOL 的研究文件逐行引用這份快照（`c64a7343a5c6`），而 study_COOL 的 `co-26.04/`、`online/` 裡**找不到這個 commit**（已觀察）。建議搬進 study_COOL，不要刪 |
| `wasm_sdk_probe/dist/profiles/`、`build/archive/` | 18.6 GiB | 出貨 profile 的唯一副本，證據綁定的錨點。用 §3 的 hardlink 回收空間 |
| `findings/`、`.git`、`specs/`、`handoff/`、`devlog/`、`research/`、`docs/` | 約 10 GiB | 研究本體。`findings/` 有 3.6 GiB 進了 git，工作樹的副本不能刪 |
| `wasm_sdk_probe` 的原始碼與 `test-docs`、`wasm-lite/patches`、`retired-builds` | < 0.1 GiB | 進 git 的原始碼 |

## 7. 專案外、但屬於這個專案的東西

| 項目 | 大小 | 建議 |
| --- | ---: | --- |
| docker volume `litecore-mariadb`、`litecoreprobe-mariadb` | 0.4 GiB | 沒有任何容器掛著（舊 ddev 專案的 DB），可刪 |
| 容器 `litecore-rehearsal-*`＋volume `litecore-rehearsal_database` | 0.2 GiB | 搬離 ddev 前的預演環境，可刪 |
| 容器 `litecore-own-*`＋volume `litecore-own_database` | 0.5 GiB | 現行宿主（`host-stack/litecore.env` 的 `STACK_NAME=litecore-own`，已觀察）。凍結期間留著，手測時才開得起來 |
| image `ddev-webserver:*-litecore-built`、`*-litecoreprobe-built`、對應的 dbserver | 幾乎 0 | 每個 image 自己的層只有 17–38 kB，其餘和別的 ddev 專案共用，刪了省不到空間。`ddev-webserver:v1.25.3-litecore-built` 是現行宿主的 image，不要刪 |
| `~/Projects/Nextcloud_Apps/litecore-rehearsal`、`litecoreprobe-downloads` | 1.2 GiB | 預演用的 Nextcloud 與下載快取，可刪 |
| `~/Projects/Nextcloud_Apps/litecoreprobe` | 1.1 GiB | 裡面的 `nextcloud/` 可刪；app 原始碼沒有 remote，要先決定要不要留 |
| `~/Projects/Nextcloud_Apps/litecore` | 1.6 GiB | 產品原始碼，留著。`nextcloud/`（1.3 GiB）是解開的 Nextcloud core，可以重新下載 |
| `~/Projects/Nextcloud_Apps/litecore-own-state` | 18 MiB | 切換前的 DB dump，留著 |
| `~/.cache/ccache` | 5.1 GiB | 跟其他專案（含 study_COOL）共用，不要清 |
| `../study_LiteCore-artifact-backup/` | 0.6 GiB | 唯一的樹外備份，留著 |

## 8. A 級的指令（給擁有者檢查，本文撰寫時都沒跑）

```bash
cd /home/jiajun/LibreOffice/study_LiteCore

# 1. wasm_sdk_probe/build：保留 10 個，其餘刪除
cd wasm_sdk_probe/build
KEEP='archive|release|merge-native-pmpc|merge-native-pmpc-e02d|merge-wasm-private|ms-formats-w|mono-reach|cjk-subset|merge-native-r0-limit|probe-hand-0212'
ls -A | grep -vxE "$KEEP"                          # 先看清單
ls -A | grep -vxE "$KEEP" | xargs -d '\n' rm -rf --
cd ../..

# 2. R8 的瀏覽器資料夾
rm -rf wasm_sdk_probe/dist/r8-c-profiles wasm_sdk_probe/dist/r8-d-profiles

# 3. 186 PS1 對照組（分支留在 git）
git -C wasm-lite/upstream-master/submit worktree remove "$PWD/wasm-lite/upstream-master/src-186-M"
rm -rf wasm-lite/upstream-master/build-186-M

# 4. Qt6 編譯中繼
rm -rf wasm-lite/tools/qt6-wasm-build-6.10.2-r2 wasm-lite/tools/qtbase-everywhere-src-6.10.2

# 5. 唯讀保護（一定要做，理由見 §2.1）
chmod -R a-w wasm_sdk_probe/dist/profiles wasm_sdk_probe/build/archive
```

`git worktree remove` 若因為子模組或 ignored 檔被拒，加 `--force`（`src-186-M` 沒有追蹤中的修改，已觀察）。

## 9. 執行紀錄（2026-11-26 補充）

擁有者同意刪 A 級，當天執行。和 §8 不同的地方：

- **`build/` 頂層的檔案全部留著，`m3-count-*`／`m3-witness-*` 也留著。**清單裡混有連結 log（`link-*.log`）、commit 紀錄（`*-commit.txt`）、鏈的輸出（`*.out`）和計數鏈的目錄，合計 3.4 MB，沒有副本，而且被 `findings/evidence/` 引用。實際只刪了 `build/` 底下 99 個**目錄**，共 9.58 GiB。
- `upstream-master/relink-*.log`：在 `findings/evidence/002/fix-2a2335cf/` 找到 7 份 gzip 副本，逐一解壓用 `cmp` 比對，7/7 相同，才刪除原檔。
- `build-nosym-e42678e7-configure-fail/` 留著（8.5 MiB，刪了省不到空間）。
- `findings/evidence/**/session-*/profile/` 刪掉 1,092 個未追蹤的檔；這類路徑沒有任何檔案在 git 裡。

結果（已觀察）：

- 可用空間 110,558 MiB → 132,520 MiB，**回收 21.4 GiB**。
- `git status` 沒有任何追蹤中的檔案變動。
- `git worktree remove` 之後，分支 `finding186-fixM-test-only`（`099c40da1a99`）仍在。
- 唯讀保護：`dist/profiles`、`build/archive` 裡可寫的檔數是 0。對 `e2-editor-v33/probe.js` 做 `cp` 得到 `Permission denied`；事後比對 sha256，與 `build/archive` 的副本相同，mtime 仍是 11-03。

study_COOL 的引用路徑（§6 的 `cool-26-04`）：study_COOL 的 session 照 §6 的建議選了 B，已經做完。完整 sha 的 commit 抓進 `study_COOL/co-26.04`，用本地 tag `snapshot/co-26.04-2026-07-31` 釘住；它比對 81,957 個檔逐位元相同；引用改成 commit＋路徑。`cool-26-04` 要不要刪，等擁有者決定。

上游工作樹（§4）：擁有者選 **B（上游繼續做）**。`upstream-master/` 除了 A 級已刪的 186-M 以外全部保留，等 002、186 合併、159 推出去之後再清。

### B 級（同日，擁有者同意）

和 §5 不同的地方：

- **`wasm-lite/tools/emsdk`、`qt5-wasm`、`pw` 沒刪。**上游工作樹選了 B，而 `upstream-master/build-186-R`、`build-nosym` 的 `config_host.mk` 以及 `build.sh`、`relink_vcldemo.sh`、`run_probe.sh` 都用到它們（已觀察）。`qt5-src` 照刪：`qt5-wasm` 只在 `.prl` 的 `QMAKE_PRL_BUILD_DIR` 記著它的路徑，上游建置的設定沒有引用它；它 `qtbase` 的「修改」只是 9 個編譯產生的未追蹤檔。
- `native-lok-26-8/` 只刪了 `build/` 和 `src/`。那幾份 Bugzilla 分類的 md 留在原位，仍然不在 git 裡。
- `native-lok-26-8/src`、`libreoffice-26-2`、`collabora-25.04` 用 `git worktree remove --force` 移除。前者有 checkout 的子模組只有 `dictionaries`，乾淨、HEAD 是 core 釘住的那個上游 commit。分支 `libreoffice-26-2-5`、`distro/collabora/co-25.04` 仍在。26-2 的未提交修改存成 `wasm-lite/retired-builds/libreoffice-26-2-worktree.diff`。
- 刪除前把五棵建置樹的 `autogen.input`、`config_host.mk`（有 `env.sh` 的也存）與主要輸出的 sha256 存進 `wasm-lite/retired-builds/`，做法和 10-12 那次相同。

結果：可用空間 132,429 MiB → 174,448 MiB，**回收 41.0 GiB**。今天兩輪合計 62.4 GiB，硬碟可用空間從 108 GiB 增加到 171 GiB。§3 的 hardlink 合併尚未執行。

### 收尾（同日，擁有者同意）

- **`cool-26-04` 已刪。**study_COOL 的引用已改成 commit＋路徑，commit 在 `study_COOL/co-26.04`，用 tag `snapshot/co-26.04-2026-07-31` 釘住。刪之前我獨立驗證了一次：從 online.mirror 只抓 `c64a7343a5c6` 的 tree（`--filter=blob:none`），再把本機 81,957 個檔用暫時 index（`update-index --info-only`）算出 tree hash。結果 `718f5be4a5a9…` 與上游完全相同，沒有子模組，也沒有多出來的檔（已觀察）。還原：`git -C ~/LibreOffice/study_COOL/co-26.04 archive c64a7343a5c6 | tar -x -C <dir>`。回收 1.8 GiB。
- `codex-claude-code-delegation.md` 已刪（與本專案無關，從未 commit）。
- **hardlink 合併已做**（§3）：`hardlink -c -O dist/profiles build/archive`，只對目錄暫時開寫入，做完 `chmod -R a-w`。合併 771 個檔，回收 9.61 GiB；inode 1,291 → 634。合併前後 1,473 個路徑的 sha256 清單逐行相同，正向對照（改一個字元）會報不同。**恢復開發前的注意事項寫在 `docs/ARTIFACT-BACKUP.md` 末段。**
- `native-lok-26-8/*.md` 與 `libreoffice-26-8` 的兩份未追蹤 md：擁有者決定不收進 git。

**今天合計**：硬碟可用空間 108 GiB → 182 GiB。

## 修訂紀錄

| 日期 | 變更 |
| --- | --- |
| 2026-11-26 | 初版 |
| 2026-11-26 | 加 §9 執行紀錄（A 級已刪，回收 21.4 GiB） |
| 2026-11-26 | §9 補 B 級執行結果（回收 41.0 GiB；emsdk／qt5-wasm／pw 因上游工作保留） |
| 2026-11-26 | §9 補收尾：`cool-26-04` 經 tree hash 驗證後刪除、hardlink 合併（回收 9.61 GiB） |
