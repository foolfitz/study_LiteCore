# SPEC-M4-viewer-v3：158-B，只補 dbaccess 核心函式庫

> 建立：2026-10-23。在任何本輪 patch、建置、檢查執行之前釘下。閘門文件只追加；更正指名取代的段落並保留原文。
> 來源：[交接 10-23b](../handoff/HANDOFF-2026-10-23b-to-codex-158b-dba-only.md)、[finding 158](../findings/158-an-ods-with-form-controls-cannot-be-painted-on-the-wasm-core-forms-service-absent.md)、[v2 規格](SPEC-M4-viewer-v2.md)。

## 0. 決定、現況與範圍

擁有者 2026-10-23 選 **A**（原話「A」）：只補回 dbaccess 的 `dba`＋`dbahsql`，不帶資料庫 UI／reportdesign；核心建置由擁有者手動執行（原話「我可以手動建置」）。本輪依交接接續這個已決定的處方，不重新選方案。

158-A 是現行行為：含 `<draw:control` 的檔在建立引擎之前拒絕 `FORM_CONTROLS_UNSUPPORTED`。158-B 的目標是這類檔開得了、控制項畫得出來，且原本可開的檔不能退步。10-22 的 `a6390eef…` 帶 forms 但缺 RowSet，五份含控制項的檔與 `tdf138507.ods` 都開不了（v2 §7；finding 158）。

起點是 **`wasm-lite/build-ods-viewer-v2`**：DB connectivity 已開，159 的 bridge 已在；新 profile 必須叫 **`ods-viewer-v3`**。引擎沿用出貨 `aa576ce7…` 的原始碼與 `OXSDK_ODS_VIEWER_V2` 介面，包括 157／160 的修法；v3 的差異是核心與 profile 身分，不新增引擎 ABI。

現行宿主是 **0.2.32**、package `80349a1a24cecb17`（editor `e2-editor-v22`、viewer `ods-viewer-v2`）。名義出貨仍為 0.2.26；0.2.29–0.2.32 累積未計數。完整計數鏈 K 維持併批，不自行啟動。ddev 時段由擁有者指定；交接時 litecore 是 stopped。

本輪不重建 `build-a11y-gate0`、`build-headless-probe` 或原生樹，不覆寫凍結 v2。`libreoffice-26-8` 是四棵建置樹共用的原始碼，既存修改及未追蹤研究檔保留；只把本輪兩個 hunk 存成新 patch。

## 1. 已建立的事實與體積推估

以下引用交接 §2.2 的原始碼調查，屬〔讀原始碼〕，不是本輪的新量測：

- `config_host.mk.in:262`：`ENABLE_WASM_STRIP_DBACCESS=@ENABLE_WASM_STRIP@`，沒有獨立 configure 開關。Emscripten 的 global strip 一直開。
- strip 的四個位置：`RepositoryModule_host.mk:38–48`（dbaccess／reportdesign 模組）、`Repository.mk:1235`（UI configs）、`filter/Configuration_filter.mk:285`（StarBase type／filter）、`postprocess/CustomTarget_registry.mk:41`（base.xcd 的 database filter fragments）。A 只讓 dbaccess 模組在明確開 DB connectivity 的 strip 組態進來，其他三處照 strip。
- `dbaccess/Module_dbaccess.mk` 無條件加入 `Library_dba`、`Library_dbahsql`、`AllLangMoTarget_dba`；DBCONNECTIVITY 條件一路包到檔尾，包住 `dbaxml`、`dbu`、`sdbt`、UI configs 與測試。修改這一個條件即可取現有的核心函式庫形狀。
- `Repository.mk:409–410` 已無條件登錄 dba／dbahsql；原生未開 DB connectivity 時本來就建這兩個。`Library_dba.mk:35–58` 的相依函式庫在起點核心均已建好。
- `forms/source/component/DatabaseForm.cxx:358`：`ODatabaseForm` 用 `UNO_QUERY_THROW` 聚合 `com.sun.star.sdb.RowSet`。RowSet 的建構子在 `dbaccess/util/dba.component`。
- `static/CustomTarget_components.mk:23` 呼叫 `native-code.py -c services_constructors.list`；`native-code.py:828–850` 在這個模式引用每個已建元件的建構子。不能用 native-code.py 內建短清單估連結範圍。
- `.component` 才是建構子的真值源：交接讀得 dba 8、dbu 26、sdbt 1、dbaxml 0、rpt 8、rptui 6。本輪檢查直接解析檔案屬性，不抄建構子清單；上述數量只作調查登錄。

〔推論，約 ±50%〕原生 `.text`：dba 2,173,962 B、dbahsql 55,841 B；以 v2 §5.3 的 DB connectivity 增量（native 約 3.95 MB → wasm gzip +1,153,716 B）校準，A 約增加 0.65 MB gzip，viewer 約 49.8 MB。這不是放行依據。

量測基準：10-22 DB connectivity 核心 `soffice.wasm` gzip **49,572,266 B**；它對應的診斷 viewer `a6390eef…` gzip **49,153,029 B**。建好後投影＝49,153,029＋（新核心 gzip－49,572,266）。連結後仍以 viewer 自己的實測判。上限 **52,428,800 B**（SPEC-M4 追加 2；packager 的 gzip level 9、mtime 0）。

## 2. 本輪 patch（先釘再套）

新檔：`wasm-lite/patches/libreoffice-26.8-wasm-dbaccess-core-with-explicit-dbconnectivity.patch`。

1. `dbaccess/Module_dbaccess.mk` 的 DBCONNECTIVITY 條件改成：

   ```make
   ifneq (,$(and $(filter DBCONNECTIVITY,$(BUILD_TYPE)),$(if $(filter TRUE,$(ENABLE_WASM_STRIP_DBACCESS)),,yes)))
   ```

   strip 空值也應容許原生組態，不能用 `filter-out TRUE`（空值仍會是空）。
2. `RepositoryModule_host.mk` 在 accessibility 區塊的 `endif` 之後，加 `ifeq ($(ENABLE_WASM_STRIP_DBACCESS),TRUE)` 區塊，只加 `$(call gb_Helper_optional,DBCONNECTIVITY,dbaccess)`。與 reportdesign patch 的 hunk context 保持距離，兩份都要能 reverse-check。
3. INVENTORY 加表列、headless 段與日期紀錄；十份 LibreOffice patch 逐份 `git apply --check --reverse`。不動 `configure.ac`／autogen 輸入，不重跑 autogen。

組態讀法：strip TRUE＋DBCONNECTIVITY → dba／dbahsql；strip TRUE＋沒有 DBCONNECTIVITY → 不加入 dbaccess；strip 空值的原生組態照原本分支，含 DB connectivity 的原生組態仍有 UI／reportdesign。這是本次修改的範圍說明，不把手工清單升成未來所有建置的硬性判準。

## 3. 核心閘門 K3 與停手條件

新工具：`wasm_sdk_probe/tools/check_ods_viewer_v3_core.py --stage built`。重用 `check_ods_viewer_v2_core.py` 的 helper 與 K-2a／c／e；不修改 v2 的 K-2d（「無 dba」是 v2 當時的期望）。configure 階段仍用 v2 工具的 K-1，在 patch 後、擁有者 `make` 前跑。

| id | 判準 | 形式 | 永遠沒做的預設結論 |
| --- | --- | :---: | --- |
| K-1 | v2 §2.3 的五項 configure 條件仍成立 | 1 | 不開始 make |
| K3-a | `services_constructors.list` 包含從 `dbaccess/util/dba.component` 解析的每個 constructor；來源不存在或應有的集合為空不得通過 | 2 | v3 不連結 |
| K3-b | 同一清單不含從 `dbu.component`、`sdbt.component`、`reportdesign/util/rpt.component`、`rptui.component` 讀出的任何 constructor；來源缺失或這些集合為空不得通過 | 2 | v3 不連結 |
| K3-c | v2 K-2a（add-in 完整簽章）、K-2c（OFormsCollection＋scaddins）、K-2e（五個連結輸入存在且非空）都成立 | 2 | v3 不連結 |
| F3-1 | 建置在 dbaccess（dba／dbahsql）內失敗 → 保存完整 log 與 tail 200，停手交擁有者決定，不連續補 patch（v2 §2.7 的教訓） | 停手規則 | 未建好，不連結 |
| F3-2 | K3 後投影或連結後實測 viewer gzip > 52,428,800 B → 停手 | 1 | 體積未判，不出貨 |

只登錄：新 `soffice.wasm` 大小、sha256、gzip 大小、相對基準增量與 viewer 投影；dbaxml 的 component 沒有 constructor，僅記錄。K3 本身的硬性結果是 a／b／c，體積另依 F3-2 讀。

**建置前紅案**：今日 `build-ods-viewer-v2` 必須 K3-a 紅（缺 dba）、K3-b 綠；從真值源取一個 dbu constructor 加進合成清單，K3-b 必須紅。補全 dba 的合成清單可作檢查器的綠案，必須明標 synthetic，不能當核心已建好的證據。輸出存 `findings/evidence/m4-ods/viewer-v3/core/`，先保留第一次輸出才判讀。

建置腳本：`handoff/ods-viewer-v3/build-core.sh --make-only`，只收這個參數，不跑 autogen；emcc 4.0.10 guard、K-1、每次獨立 log、失敗保存 tail 200、`timing.txt`、成功後跑 K3 並讀 F3-2。擁有者手動執行，估 15–40 分鐘（起點上次完整建置 45 分鐘，本次加 dba／dbahsql 與重連結）。交出前讀 `uptime`、`pgrep -a make`；有其他建置或長時間量測先說明狀況。

## 4. 連結與 Phase E（任何本輪連結／執行之前釘下）

K3 綠且投影未超限之後才準備 v3 Makefile／獨立 profile builder，核心指向 `build-ods-viewer-v2`。沿用 v2 §3.5 E8′ 的程序：base 正向對照、DROP 恰好一次、相對 v1 差異列出並在連結前讀過；CJK／fallback 沿用 v1 位元組。manifest 必須宣告 `form-controls`，由核心標頭與引擎能力位元相符來建立，不用旗標假裝支援。

在任何連結前先核對並封存現行 profile（`build/archive/`；wasm 不可重現），準備連結手冊，由擁有者跑連結。不用 v3 覆寫 v2。Phase E 的 runner 加 v3 名稱；每次明給 `--profile ods-viewer-v3` 與 **`--out`**，不碰 v1／v2 已計數證據。

| id | 判準 | 形式 | 永遠沒做的預設結論 |
| --- | --- | :---: | --- |
| V2-158B（沿用 v2 §4 原文，在 v3 上） | profile 宣告 `form-controls` 時，每筆 `formControls === true` 的檔開得了（E2 的開檔條件）、E4a（每張表 tile OK）與 E3（文字＝期望）成立。母體由 package probe 產生，目前五份：`move-cell-anchored-shapes`、`tdf106181`、`tdf121963`、`tdf134161`、`tdf154005` | 1 | 158-B 未修；0.2.32 留著 |
| V3-NR | 每筆在 `aa576ce7…` 的既有全語料報告裡成功開啟的語料，在 v3 仍滿足 E2 的開檔條件；以語料身分逐筆對帳，包含 `tdf138507.ods` | 2 | v3 不出貨 |
| V3-SEE | 擁有者在鏡像頁看 `tdf134161.ods`（101 個控制項），明確確認控制項可見；原話與頁面／profile 身分記錄在樹裡 | 人類殘餘／記錄 | 不宣稱「控制項已畫出」；158-B 未完成 |
| E1–E9、V2-157／159／160／160-D、E8′ | 沿用 SPEC-M4 與 v2 的既有判準與追加修正，在 v3 重跑。V2-160 全語料 N＝3；160-D 照 v2 §8.3，包括「沒有派送失敗則重送未被走到」的預設讀法。E6 採 SPEC-M4 追加 12，只判 stage 高水位 < 896 MiB，洩漏半句已撤回（finding 164） | 1／2 | 各項原來的預設結論；v3 不打包 |

既有具名限制照舊（例如 `L-no-basic-udf`、揮發表的 E3 讀法）；不能把它們當本輪新紅或自行改判準。V3-SEE 是明列的人類殘餘，不假稱機器可判；像素不同不能證明控制項可見。

**預先寫好的讀法**：全成立 → 準備 host **0.2.33**。V2-158B 或 V3-NR 紅 → v3 不出貨，0.2.32 留著，finding 158 記下下一個阻礙。控制項在 headless LOK 的繪製路徑、其他 dbaccess service 是〔未量〕候選，不先歸因。不出貨「核心有 forms、殼層仍拒絕」或反向的組合（v2 §2.5）。

計數語意：新連結的 E 全部從零；v3 wasm sha 改變就重來。新增判準由 158-B／`tdf138507` 的既有失敗逼出，先於滿足，逐實例或工具封閉母體；第三筆乾淨全語料落地即封閉，之後的顧慮另立 finding／工作項。V3-SEE 不用等待「穩定」來作硬性判準。宿主計數鏈 K 仍併批。

## 5. 包裝、宿主與接續順序

1. 本規格單獨 commit。
2. 兩個 hunk＋patch inventory、十份 reverse-check、K-1，commit。
3. 新 K3 工具＋建置前真實紅案與合成紅案／綠案，commit。
4. 擁有者建置腳本與手冊，commit，交短指令。停在等建置結果；不越過 K3 準備實際連結。
5. 建好後讀 K3／F3-2 → v3 連結準備／E8′ 差異判讀／封存 → 擁有者連結 → 連結後核對 → Phase E。
6. 全成立才依 `findings/evidence/host-0.2.32/` 準備 host 0.2.33：隔離 worktree、`package_m3_engine.py --app <worktree>`（預設是 LIVE app，不可漏）、離線閘門、archive、安裝腳本與還原配方、Phase H 鏈、手冊與 release 草稿。
7. 只有擁有者指定 ddev 時段後才安裝／跑 H1–H7；未排時段就維持現況，K 不自行啟動。

§34.4：交接起點累計 **46／27**（因執行而修／因審核而修）；本輪新增規格、K3、腳本不算修既有檢查。本輪因審核而修須維持 **0**；若誠實執行證實既有工具誤判，先 commit 證人再照 §34 處理。

## 6. 修訂紀錄

| 日期 | 變更 |
| --- | --- |
| 2026-10-23 | 事前釘下 A、兩個 hunk、K3／F3、Phase E／人類殘餘與停手讀法、後續工作順序 |

## 7. 建置前準備完成（2026-10-23，只追加；核心尚未建置）

規格先提交（`10e8f917`），再套兩個 hunk 與 inventory（`d17e31b6`），再提交 K3 與紅案（`940f2294`）。證據：`findings/evidence/m4-ods/viewer-v3/core/README.md`。

- 十份 LibreOffice patch 各自 reverse-check 通過；舊 reportdesign patch 仍獨立通過。K-1a–e 全綠，沒有跑 autogen。
- 實際讀兩個模組檔、用 GNU make 的記錄巨集展開四種組態（不編譯）：strip＋DBCONNECTIVITY 只選 dba／dbahsql，沒有 reportdesign；原生＋DBCONNECTIVITY 的五個函式庫照舊。這是一次性範圍量測，不升成新閘門。
- K3 的真實建置前報告 exit 1：**K3-a 紅、K3-b 綠、K3-c 綠**。缺少從 dba.component 讀出的全部 8 個建構子；這是還沒建置的預期紅，不是已修好。
- 合成對照：補全 dba 的清單 a／b 綠；再加入一個從 dbu.component 讀出的建構子，b 紅。self-test exit 0。沒有改動核心的真實清單。
- 新檢查器第一次中止在我填錯的 `dbaxml.component` 路徑，原始輸出留於 `first-run-missing-dbaxml/`；改用實際的 `dbaccess/source/filter/xml/dbaxml.component` 後才產出上述紅案。這是工具尚未判過資料時的建構修正，既有 v2 工具未改。
- 現有核心 `soffice.wasm` 153,330,836 B，gzip **49,572,266 B**，恰好重現 §1 的基準；目前投影仍只是舊診斷 viewer 的 **49,153,029 B**，不是新核心的體積。
- `handoff/ods-viewer-v3/build-core.sh --make-only` 備好。`bash -n`、四個提前拒絕案例、現場 emcc 4.0.10 guard 都過；沒有執行編譯。每次獨立 run 目錄、完整 log、失敗 tail 200、timing、K-1→make→K3→F3-2。
- 2026-10-23 23:44（Asia/Taipei）讀主機 `uptime`：0.16／0.32／0.35；`pgrep -a make` 無結果，程序清單沒有看到相關長時間量測。這是交出時的一次觀察，不保證之後仍空閒。

下一步：擁有者從 repo 根執行 `bash handoff/ods-viewer-v3/build-core.sh --make-only`，估 15–40 分鐘；回報 DONE／STOP 與 run 路徑。接手讀 K3 與 F3-2 後才準備 v3 連結。現行宿主、凍結 profile 與 ddev 都未變動；§34.4 本輪 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-23 | 追加 §7：建置前結果、保留首次工具中止、建置腳本與交接點 |

## 8. 核心建好、允許準備連結（2026-10-24，只追加）

擁有者執行 `build-core.sh --make-only`，run `20261023T235528-ctpzQR`：make／tee 都 exit 0，**184 秒**。K-1 與 K3 全綠，且已將報告中的 component、constructor list、五個連結輸入、wasm 與 checker 雜湊逐項對到現場檔案。證據在 `findings/evidence/m4-ods/viewer-v3/core/runs/20261023T235528-ctpzQR/`。

- 建構子 **783 → 791**：dba.component 的 8 個全部進來（含 RowSet）；dbu／sdbt／rpt／rptui 的建構子都沒有。bridge 仍是 80 個，forms／scaddins 與五個連結輸入照過。
- 核心 wasm **154,650,988 B**，gzip **49,951,424 B**；gzip 增量 **379,158 B**。viewer 投影 **49,532,187 B**，距上限 **2,896,613 B**。F3-1 未觸發；投影未觸發 F3-2，實際 viewer 仍待連結後判。
- 更正 §1 的調查登錄與 §3 的「dbaxml 沒有 constructor」：交接把它記成 0，本輪工具實際讀 `dbaccess/source/filter/xml/dbaxml.component` 是 **6** 個；這 6 個在已建核心均缺席。它仍是 record-only，K3-b 的既定四個來源不變，不改檢查器與判準。

## 9. v3 連結準備的具體落地（2026-10-24，任何本輪連結之前，只追加）

沿用 §4／§5 的範圍，落地 `ODS_VIEWER_V3_*` 規則、`build/ods/viewer-v3/`、`dist/profiles/ods-viewer-v3/` 與獨立 `tools/build_ods_viewer_v3_profile.py`。核心預設 `../wasm-lite/build-ods-viewer-v2`；引擎 define **仍是 `OXSDK_ODS_VIEWER_V2`**，沒有新的 ABI／C++ define。worker 沿用 v2 的 pin。v3 的 builder 使用獨立 profile／base stem，包裝時要求核心有 DB connectivity；`--check --core gate0` 只是 base 程序的對照，不是可出貨的 v3。

連結行與 v2 逐 token 比，差異只容許物件、核心、匯出清單與輸出路徑；引擎原始碼要與 `aa576ce7` 封存所記的 `2430916d` 相同。static 的 carrier 清單新增 `ODS_VIEWER_V3=probe_engine,sdk_api`，是新 profile 的綁定宣告，不改既有檢查器。

建置工具的紅案／對照照 v2：gate0 內部正向對照重現 9901e9be；`--check --core gate0` 對 v1 差異 0／0／0；`--red-drop` 多刪一個真實檔，removed 必須看見它。用合成 loader／wasm 在暫存輸出測包裝身分與 form-controls，標為 synthetic，不當作實際連結；錯 worker／缺匯出與 gate0 核心不得包成 v3。既有單元與 `test-e2-c-static` 照適用範圍執行；不為既有檢查新增判準。

在交出連結前讀 E8′ 的 base 差異、封存現行 editor／viewer 與所引用資源、記錄凍結集合；短指令放在 `handoff/ods-viewer-v3/link.sh`。連結由擁有者執行，估幾分鐘。連結後依 §4 核對實測 gzip、manifest `form-controls`／位元 63539、字串、stack、既有 profile 不變與 E1-C，再立即封存 v3。Phase E 的 profile 選項在需要時加 v3，執行一律明給 `--out`。

以上是 §4 的實作與驗證順序，沒有放寬或新增閘門；§34.4 本段 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §8：核心實測與 dbaxml 記錄更正；§9：連結準備的具體步驟 |

## 10. 連結準備完成，交擁有者（2026-10-24，只追加；尚未連結）

v3 規則與獨立 builder 已提交（`624f4399`）；引擎 `src/` 與 `aa576ce7` 封存所記的 `2430916d` 無差異。證據：`findings/evidence/m4-ods/viewer-v3/pre-link/README.md`。

### 10.1 E8′ 差異已讀

base **`21bec646…`**，39,934,615 B，1,488 檔；對 v1 **0 新增、0 移除、9 變動、1,479 相同**。逐檔讀實際切片（`base-pack-reading.json`）：

| 檔 | 對 v1 的大小差 | 讀法 |
| --- | ---: | --- |
| `services.rdb` | +24,954 B | forms／connectivity 的既有登錄，再加 dba；對 `a6390eef` 只多 **2,051 B**，XML component 集合恰好多 `libdbalo.a`（8 個 implementation），舊 component 無刪除／變動 |
| `main.xcd` | +11,045 B | 與 `a6390eef` 逐位元相同，是 v2 §5.2 已讀過的 DB connectivity 驅動設定 |
| `calc.xcd`／`writer.xcd` | +1,216／+1,217 B | 同上 |
| `registry_en-US.xcd`／`qtz`／`zh-TW` | +715／+1,736／+1,704 B | 同一組驅動設定的語系字串，與 `a6390eef` 相同 |
| `mytexts.bau`／`images_colibre.zip` | 0 B | zip 內每個檔案的 SHA256 與 v1 相同，容器不同；不是內容變動 |

對 DB connectivity 診斷核心 `a6390eef` 的 base，**只有 services.rdb 改變**；字型、fontconfig 與其他檔沒有意外差異。這是新增 dba 的預期結果。

內部正向對照重現 9901e9be；另指 gate0 的 base 對照重現 `6f7424a1…`、差異 0／0／0。紅案多刪 `main.xcd`，removed 確實看到它。CJK／fallback 沿用 v1 位元組。E8′ 的連結前讀法成立。

### 10.2 規則、檢查與封存

- v2／v3 的 Makefile 展開逐 token 比較：正規化核心、物件、匯出清單與輸出路徑後完全相同，define／link flags 不變。三個 v3 單元對新核心標頭 `-fsyntax-only` 都過，沒有寫物件。
- builder 用合成 loader／wasm 驗過：v3 身分、獨立 base stem、`form-controls`、bits **63539**；錯 worker、缺 part-info export、沒有 forms 的 gate0 都在建立輸出目錄前拒絕。這不是引擎執行證據。
- carrier 宣告前的真實紅案：恰好 v3 的 `sdk_api`／`probe_engine` 兩個物件紅。新增宣告之後 `make -k test-e2-c-static` **exit 0**（含 490＋5 條 Node、31 條規則／121 個物件普查與 guard、既有 Python 與 E1-C）；viewer 三支單元測試 **57／57**。既有 checker 未修改。
- 核心提供 Calc 的既有檢查通過；v3 最後那行 gzip recipe 實際指到舊 v2 wasm 跑過（唯讀對照），引號正確、量得 47,971,896 B；v3 真實值仍待連結。
- 現行 editor／viewer 的本地檔與 manifest 引用的資源 **16 檔、388,892,439 B**，複製到 `build/archive/before-ods-viewer-v3-20261023T160805Z/`，先逐檔比來源 SHA256、再跑 `sha256sum -c SHA256SUMS`，全過。相對路徑保留 manifest 引用。
- 現有 `dist/profiles/` 與 `build/archive/` 的 **1,643** 檔記入 `frozen-set-before.sha256`。v3 profile 此刻不存在；連結後每一筆舊檔都必須仍相同。
- 2026-10-24 00:11（Asia/Taipei）交出前 `uptime` 0.60／1.10／1.34，`pgrep -a make` 無結果。

下一步：擁有者從 repo 根執行 `bash handoff/ods-viewer-v3/link.sh`，估幾分鐘。手冊 `handoff/RUNBOOK-link-ods-viewer-v3.md`。連結後先核對實測 F3-2、manifest／位元、凍結集合、bytes／stack／E1-C、封存，再進 Phase E；158-B 此刻尚未證明修好。宿主仍為 0.2.32，ddev 未啟動。§34.4 本輪 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §10：E8′ 九檔差異判讀、連結前檢查與 archive／凍結快照、交擁有者連結 |

## 11. 第一次連結成立（2026-10-24，只追加；Phase E 尚未執行）

擁有者執行 `link.sh`，make／tee exit 0（`link-ods-viewer-v3-20261024T001307-kZZfMV.log`）。wasm 身分 **`ebb7e0cb…`**，loader **`a6f77b08…`**；worker 沿用 `9c85043a…`。實測 gzip **49,530,696 B**，距上限 **2,898,104 B**，比投影少 1,491 B，F3-2 未觸發。

連結後核對全過（`findings/evidence/m4-ods/viewer-v3/post-link/`）：舊凍結集合 1,643 檔完全相同；manifest 為 v3、`part-info`＋`form-controls`、bits 63539、base `21bec646…`／metadata `43da6a24…`；wasm 的 viewer／SelectAll retry／Calc／forms／RowSet 字串存在、editor completion 不存在；stack PASS、E1-C intact。已立即封存到 `build/archive/ods-viewer-v3-ebb7e0cb-worker-9c85043a/`，比來源並驗 checksum，沒有再連結。

Phase E runner 只擴充 profile 名稱清單，判讀邏輯未改；phase-e／E6／E4b-E9 自測 **43／43、17／17、16／16**（`45b75452`）。接著在這顆身分上執行 §4，先定向；這些產物核對尚未證明控制項畫得出來。§34.4 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §11：連結身分、實測 F3-2、凍結核對與封存，Phase E 從零開始 |

## 12. 定向測試全過；產品頁指向 v3 的步驟（2026-10-24，只追加）

`phase-e/targeted/report-2026-10-23T162535Z.json`：18 份語料＋ODT 負對照，E1／E2／E3／E4a／E5／E6／V2-157／V2-158B／V2-160 全過。五份含控制項的檔都開得了、各張可見表的 tile 與文字均過；`tdf138507.ods` 也滿足 E2。這尚未代替全語料的 V3-NR，也未代替人類 V3-SEE。

接續 §4 的 E4b／E9：先把 `web/ods-viewer-app.js` 唯一 worker 字面量從 v2 改 v3，再用既有 runner（不改判讀）測產品頁與 no-refit 紅案。只動原始碼頁面，凍結的 dist／宿主 package 仍是 v2；E4b／E9 的 mirror 讀本輪原始碼頁面。這不改引擎身分，也不讓同身分的定向 E 歸零。

人類 V3-SEE 準備獨立本機 mirror：同一份產品頁與 v3 profile，明顯橫幅標出 profile／wasm 身分，指名 `tdf134161.ods`（101 個控制項）。擁有者的原話與頁面身分另記，尚未確認前不宣稱「控制項已畫出」。E6 不帶 `--bound`；全語料仍按 §4 跑 N＝3。新舊開檔對帳讀既有報告，以 `aa576ce7` 報告中每一筆 opened 的檔為母體，不手抄清單。

§34.4 本段 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §12：定向結果，產品頁與人類 mirror 的接續範圍 |
