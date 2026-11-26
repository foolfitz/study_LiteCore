# 186 — master 上照 README 設定 WASM 建置，configure 以「VCLplugs to be built: gtk3 qt5」失敗

| | |
|---|---|
| **狀態** | **已送 Gerrit，Patch Set 2 待審**：[214345](https://gerrit.libreoffice.org/c/core/+/214345)。PS1（11-18，`b7f3bd7eb41c`，清掉 `USING_UNIX_DESKTOP`）→ 照 Lohmaier 的偏好改成 PS2（11-19 02:44 UTC，`399a9df475a7`，`emscripten)` 區塊加 `test_gtk3/gtk4/kf5/kf6=no`）。分支：`wasm-lite/upstream-master/submit` 的 `emscripten-configure-gtk`（PS1）、`emscripten-configure-gtk-ps2`（PS2）。不開 Bugzilla |
| **Bugzilla** | 不開。回歸來源是 tdf#146153 的 commit |
| **發現日** | 2026-11-11（修 finding 002 時撞到，當時沒開單）；2026-11-18 補登錄 |
| **嚴重度** | 阻斷：文件記載的 WASM 建置在 master 上連 configure 都過不了 |
| **可重現** | 100%（2026-11-11 `e42678e7` 一次、2026-11-18 `ac53621f` 一次）；`d98a796946ff` 失敗、它的前一個 commit `8e543468540d` 通過（2026-11-18 15:41） |
| **是否上游** | **是**：stock 的 `--with-distro=LibreOfficeWASM32`、無本地修改 |

## 現象

```
configure: VCLplugs to be built: gtk3 qt5
configure: error: Can't build --disable-dynamic-loading without --disable-gui and a single VCL plugin"
```

加 `--disable-gui` 的組態不受影響（〔已觀察〕`arms/C4a-unpatched-nogui.log`）。

## 成因〔已觀察：讀 diff 與 configure 的實際輸出〕

`d98a796946ff`「tdf#146153 Enable building the GUI --without-x」（Gerrit 211916，2026-11-10 合併）。

- 回歸前：`emscripten)` 區塊設 `using_x11=yes`，wasm-strip 設 `with_x=no`，於是 `USING_X11` 被清空，`disable_x11_tests` 關掉 gtk3、gtk4、kf5、kf6、cups、dbus 等測試，再因為 `DISABLE_DYNLOADING` 把 qt5／qt6 開回來。
- 回歸後：gtk 那一組改由新的 `USING_UNIX_DESKTOP` 管，`with_x=no` 清不到它。`emscripten)` 區塊被標成 `using_unix_desktop=yes`，gtk3 預設啟用，就多出一個 plugin。

## 修法選了哪一個，為什麼

> **2026-11-19 更新**：下面是 PS1 時的取捨。上游維護者 Lohmaier 看過我們列的差異後，偏好只關 plugin（他認為 WASM 多帶 Unix 桌面設定是好事），所以 PS2 改用變體 A（`test_gtk3/gtk4/kf5/kf6=no`）。A 的設定單與已全量建置的 M 逐行相同（`findings/evidence/186/README.txt` 的 Variant A 段）。下面的原文保留。

| | 內容 | configure | 與回歸前的組態相比 |
|---|---|---|---|
| **M** | `emscripten)` 區塊加 `test_gtk3=no`、`test_gtk4=no`（Christian Lohmaier 11-17 在 211916 上建議的方向） | 過 | `USING_UNIX_DESKTOP=TRUE`、`ENABLE_OPENGL_TRANSITIONS=TRUE`、`ENABLE_OPENGL_CANVAS=TRUE`、`HAVE_FEATURE_OPENGL 1` |
| **R（已 commit）** | 在 `with_x` 那段之後，Emscripten 上清掉 `USING_UNIX_DESKTOP` | 過 | 只多一個空的 `USING_UNIX_DESKTOP`（標頭裡是 0） |

選 R 的理由：`d98a` 把十幾處條件從 `USING_X11` 換成 `USING_UNIX_DESKTOP`。M 讓 configure 過，但其中**只靠這一個變數把關**的部分會在 WASM 建置裡被打開，回歸前它們不建：OpenGL 那段（`HAVE_FEATURE_OPENGL`、轉場、canvas）、PPD 套件、`s*_sh` 啟動腳本套件、vcl 的 desktop detector、Unix 專用的 registry 檔、`CppunitTest` 的 Unix 分支。fontconfig 打包與 sofficeapp 的 LibreOfficeKit 物件另有條件保著，M 之下不變（codex 審查指出，已核對原始碼）。R 可以只靠 configure 證明組態與回歸前相同。M 建出來是什麼樣子，見下面〈全量建置〉。

## 驗收判準與結果〔已觀察〕

判準在跑之前寫在 `RESEARCH-2026-11-18-next-upstream-wasm-contribution.md`。

| # | 判準 | 結果 |
|---|---|---|
| 1 | 未修的 master：configure 以上面那句錯誤結束 | 成立（`ac53621f`，exit 1） |
| 2 | 修好後：`VCLplugs to be built: qt5`，configure 完成 | 成立（R；M 也成立） |
| 3 | 修好後的 `config_host.mk` 與回歸前（`build-nosym`，`2a2335cf`）相比，差異都可解釋 | **R 成立；M 不成立** |
| 4 | 加 `--disable-gui` 的組態修前修後都能 configure | 成立；R 之下 52 個標頭修前修後完全相同，`config_host.mk` 只差 `SOURCE_DATE_EPOCH`（跟著 commit 時間走） |

**判準 3 的更正**：原文把「新增的 `USING_UNIX_DESKTOP`」列為可解釋的差異，沒有限定它的值。M 的結果是 `USING_UNIX_DESKTOP=TRUE`，照原文字面會被放行，而它正是問題所在。實際抓到 M 的是同一份 diff 裡沒被列入的 `ENABLE_OPENGL_*`。判準 3 改讀成：新增的 `USING_UNIX_DESKTOP` 必須是空的。另外加比了 52 個設定標頭（原判準只寫 `config_host.mk`）。

## 證據

`findings/evidence/186/build/`：兩臂的建置收據與 log、產物比對、探針輸出與截圖、預測。

**2026-11-18 午注意**：`build-186-R` 之後為了 finding 159 增量重建成 R＋159 的 bridge 修正，已不是純 R 的建置；R 原本的產物封存在 `wasm-lite/upstream-master/archive-186-R-products-before-159/`（附 SHA256SUMS，與本檔〈全量建置〉的比對一致）。

`findings/evidence/186/`：六臂的完整 log、兩份 patch、三組比對 diff、`conf_arm.sh`、`compare.sh`、上游現況（`upstream-state-2026-11-18.txt`）、`README.txt`。更早的一次失敗在 `findings/evidence/002/fix-2a2335cf/e42678e7-configure-fail.log`。

## 全量建置：兩種修法各建一次〔已觀察〕

擁有者 2026-11-18 指示「幫我建置，先建只關 gtk 的那一個」。兩臂都在 `ac53621f` 上、全新建置目錄、同環境同旗標，依序跑。預測先寫在 `findings/evidence/186/build/PREDICTIONS.txt`：P1–P3 都中，P4 對 R 成立（對 M 的啟動沒有做預測）。細節在 `build/README.txt`。

| | M（只關 gtk） | R（已 commit） |
|---|---|---|
| 建置 | `make exit=0`，2794 秒 | `make exit=0`，2813 秒 |
| `qt_soffice.html` 90 秒 | 到開始中心 | 到開始中心 |
| 開 Writer、打 `abc` | 可以 | 可以 |
| 按 F11 | **打開「樣式」側邊欄** | 沒反應 |

- 開始中心的截圖三方逐位元組相同：M、R、11-11 回歸前的對照組。
- 回歸前的建置（`build-nosym`）跑同一支探針，按 F11 也沒反應。所以 F11 的行為是 M 帶進來的。
- 產物差異全部集中在設定：`soffice.wasm` 只差 552 bytes；檔案系統映像 1598 個檔同名，只有 `main.xcd` 不同（M 多 17,838 bytes、686 行）。
- 那 686 行是 Unix 桌面的設定：106 個快速鍵項目，其中 88 個在英文介面有指令（`Accelerators-unxwnt`，F11、F7、Ctrl+H、Ctrl+M、Calc 的數字格式等）、代理伺服器、使用者姓名、工作／範本／暫存路徑、外部郵件程式等，其中 13 個值寫明要向 `DesktopBackend`（桌面整合服務）查詢。
- `instdir` 多 8 個檔：六個桌面啟動腳本（`program/sbase` 等）與 `share/psprint/` 兩個檔。它們不在映像裡。

**結論**：M 不是壞的，在預設組態下建得起來也跑得起來。它和 R 的差別是它**順帶改了 WASM 版的設定與行為**，而那不是任何人決定過的事。R 回到回歸前的狀態；WASM 版該不該有這些快速鍵，可以另外、明確地提。commit message 與回覆草稿已照這個結果改寫，不再說 M 可能建不起來。

副產品（只登錄，不展開）：回歸前的 WASM 版本來就沒有 F11、F7、Ctrl+H 這一組 unx／wnt 快速鍵。這是既有狀態，是不是缺陷沒有判斷。

## 沒有做的

- 含 Impress 的模組組合（`slideshow` 會建，M 之下 OGLTrans 跟著進來）沒有建。
- M 的 13 個 `DesktopBackend` 值在執行期解析成什麼、其餘快速鍵有沒有作用，沒有看。每支探針每臂只跑一次。
- `--enable-qt6`、`--enable-emscripten-jspi` 的組態沒有跑（沒有 Qt6 的 WASM 工具鏈在這棵樹旁）。讀程式碼：走的是與 `--disable-gui` 相同的 `disable_unix_desktop_tests` 之後把 qt5／qt6 開回來的路，與回歸前的順序相同。〔推論〕

## 審查（codex，2026-11-18，一輪）

原文在 `findings/evidence/186/review-codex-2026-11-18.txt`。對象是第一版 commit `5db4539e85e3`。

- 成立：組態與回歸前相同（含 `--enable-qt6`、`--disable-gui`、`--enable-headless` 的讀碼推演，以及後續的 `8299e4120dfa`）；不影響其他平台；註解正確；比對不是空的。
- 不成立，已採納：commit message 兩句說過頭。一是「`USING_UNIX_DESKTOP` 管的東西回歸前都不在 WASM 建置裡」——fontconfig 打包與 LibreOfficeKit 物件其實一直在；二是「與回歸前相同，只差…」漏列 PATH 順序與 `SOURCE_DATE_EPOCH`。兩處都對過原始碼後改寫，註解也照建議點名 `using_unix_desktop=yes`。
- 未採納：`compare.sh` 不會比對只存在於右側的標頭（兩側都是 52 個且左側每個都在右側，這次沒有這種檔）。

因審核而改的檢查數：0（改的是 commit message、註解與本檔的敘述）。

## 送出

- 推：擁有者在 `submit` 工作樹的 `emscripten-configure-gtk` 分支上推到 `refs/for/master`。這個 repo 沒裝 commit-msg hook，Change-Id 是手動產生的。
- 推上去之後，在 211916 的留言串回一句並附連結：草稿在 `findings/drafts/186-gerrit-reply.txt`。
- 若想讓 bot 在 tdf#146153 留言，把 subject 改成 `Related: tdf#146153 Emscripten: …`（目前沒加）。

## 時間軸

- 2026-11-10：`d98a796946ff` 合併。
- 2026-11-11：`e42678e7` 上撞到，改用 `2a2335cf` 繼續 finding 002；在 tdf#174440 的重現步驟裡順帶寫了這個失敗。
- 2026-11-17：Christian Lohmaier 在 211916 上留言指出成因（14:29 UTC）。原作者 Chris Mayo 回覆認為不是他的改動造成的：「There was already `using_x11=yes`」（19:26 UTC）。
- 2026-11-18：在 `ac53621f` 上重現、比較兩種修法、commit R（`5db4539e85e3`）。codex 審查後 amend 成 `4847e69dd326`。兩臂全量建置與探針之後，commit message 改寫成 `0b1e99d3be44`（tree 與 `4847e69dd326` 相同）。
- 2026-11-18 15:41：為回答 Chris Mayo，在 `8e543468540d`（前一個 commit）與 `d98a796946ff` 各跑一次 configure：前者過、後者以同一句錯誤失敗（`arms/B1`、`arms/B2`）。commit message 補一句「On the parent of that commit, it passes」，trailer 改成當下 session 的 `Claude Opus 5.5`，amend 成 `b7f3bd7eb41c`（tree 不變）。回覆草稿開頭改為先回答他。
- 2026-11-18 15:49：擁有者推上 Gerrit，change 214345，上傳的 revision 與本機 `b7f3bd7eb41c` 相同；Jenkins 排入 `gerrit_master_ml_p/10303`。
- 2026-11-18 16:20 UTC：Lohmaier 回覆。在 configure.ac 那串確認我們的成因分析，並說 WASM tinderbox 已加 `--disable-gtk3` 繞過；在 patchset 層級說「WASM 更完整是好事、不介意多帶東西（但沒細看改了多少），我偏好只關掉 gtk（和其他）VCL plugin」。Chris Mayo 另開 214404 處理 `config_host.mk.in` 的 export（與本 change 無關）。214345 的 Jenkins 11-18 10:42 UTC 已 Verified+1，尚無人審。
- 2026-11-19 10:06：照 Lohmaier 的偏好備好 Patch Set 2（變體 A：`emscripten)` 區塊加 `test_gtk3/gtk4/kf5/kf6=no`，`USING_UNIX_DESKTOP` 不動），本機分支 `emscripten-configure-gtk-ps2`，`399a9df475a7`。configure 兩臂都過，設定單與已全量建置的 M 逐行相同，所以 M 的建置與探針結果適用於 A。推送預演通過，待擁有者決定是否推；給 Lohmaier 的回覆在 `findings/drafts/186-gerrit-reply-2-paste.txt`。
- 2026-11-19 02:44 UTC：擁有者推上 PS2（Gerrit 上的 revision＝本機 `399a9df475a7`），Jenkins 排入 job 10396；Lohmaier 在 reviewer 名單上。02:52 UTC 擁有者在 211916 回覆 Lohmaier（`findings/drafts/186-gerrit-reply-2-paste.txt`）。經過整理在 `devlog/DEVLOG-2026-11-19-upstream-186-configure-regression.md`。
- 2026-11-19 03:54 UTC：PS2 的 Jenkins 給 Verified-1，失敗在 Linux clang dbgutil 的 `CppunitTest_sc_swarmsolvertest`（`testRepeatedSolveResetsState` 期望 3、得 2.9999871、容差 1e-5）。判定與本 change 無關：PS1 同一台機器、同一個父 commit 全過；兩版差異只在 Linux 不會執行的 Emscripten 分支；求解器用 `std::random_device` 取種子。證據 `findings/evidence/186/ci-2026-11-19-swarmsolver.txt`。照擁有者自己的規則不用 rebase 觸發重跑，請有權限的人重跑；留言草稿 `findings/drafts/186-gerrit-ci-comment-paste.txt`。
