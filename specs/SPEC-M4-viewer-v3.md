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

## 13. E4b／E9、E6 與人工預覽已備（2026-10-24，只追加；全語料進行中）

- 產品頁改指 v3（`99859cd4`）：E4b 2／2、E9 1／1 全過（`phase-e/e4b-e9/report-2026-10-23T162756Z.json`）。no-refit 紅案兩筆 E4b 都紅，E9 仍綠；工具明確回報紅案重現（`162839Z`）。
- E6（`phase-e/e6/report-2026-10-23T162930Z.json`）：三份檔的各五輪 boots／reopen shape 都過，one-cell-a1 的五次 `open.begin` 一致，**B＝0**。未帶 `--bound`；重開序列只記錄。distinct-sheets 尾段仍每次 +12,288 B，不把它寫成「沒有洩漏」，finding 164／L-E6-leak-sbrk 不撤。
- 人工 mirror `http://127.0.0.1:8794/ods-viewer.html?diagnostics=1`：頁面綠色橫幅標 `ods-viewer-v3`／`ebb7e0cb`，用本機 load-only host 自動載入 `tdf134161.ods`；沒有 ddev。交出前以新瀏覽器讀到正確 worker、fixture sha、opened 與畫出的 tile，並留截圖／頁面狀態。證據 `phase-e/human-preview/`；**擁有者尚未確認 V3-SEE**，不得以我的截圖取代。
- V3-NR 的產物讀取器 `tools/check_ods_viewer_v3_nonregression.py`（`9d248fe6`）讀固定 `aa576ce7` 全語料報告中的 **298 筆 opened**，每筆套既有 E2。306 筆語料只有 304 個不同 sha，因此用 staged path＋索引化 case URL 配對，沒有把同位元組的不同檔合併。先做合成綠案，以及少了／開不了 `tdf138507`、換檔案位元組、錯 wasm 身分的紅案，全依預期。這是 §4 既定 V3-NR 的落地，不修改既有 runner／判讀條件；實際全語料對帳尚待報告。

全語料 N＝3 照 §4 執行，不在執行期間修改它讀取的檔案。§34.4 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §13：E4b／E9 與紅案、E6、人工鏡像與 V3-NR 讀取器；全語料仍在執行 |

## 14. 第一趟全語料通過本輪要求（2026-10-24，只追加；N＝3 尚未完成）

`phase-e/full-corpus/report-2026-10-23T163018Z.json`，640.2 秒：**303 開、3 加密拒絕**；E1／E2／E4a／E5／E6／V2-157／V2-158B／V2-160 全過。E3 只紅既有的 `upstream/user-defined-function.ods`（`L-no-basic-udf`），raw runner exit 1 如實保留，不改成全綠。

V3-NR 讀產物對帳 **298／298**：v2 實際 opened 的每一筆在 v3 仍滿足 E2，包括 `tdf138507.ods`。470 次文字讀取、未確認 **0**、SelectAll 等待最大 177 ms。V2-160-D **PASS**：`tdf167450_source.ods` 有一次 LOK 派送失敗，引擎也記一次，重送後確認，無 never dispatched。報告與純讀取器輸出均留在 full-corpus/。

第二趟開始後，第三趟使用獨立 cold Chrome／HTTP server／log 與報告檔並行執行。開始前主機 12 個邏輯核心，load 1.05／1.36／1.37，沒有 make；本輪沒有跨趟的時間比較，E2 的 60 秒條件與所有既有判準照舊。引擎／語料／runner 不改、每趟都留自己的 preconditions；N 仍是三份完整報告，不因並行改變。

人類 V3-SEE 仍待擁有者原話；不得由第一趟的開檔／tile 成功代替。§34.4 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §14：第一趟全語料、V3-NR／160-D；後兩趟並行的執行記錄 |

## 15. 三趟全語料完成，剩 V3-SEE（2026-10-24，只追加）

完整證據與產物讀取指令：`findings/evidence/m4-ods/viewer-v3/phase-e/README.md`、`full-corpus/summary-all.json`。

| 報告 UTC 開始時間 | 秒 | 開／拒 | 讀取／未確認 | 等待最大 ms | stage sbrk 最大 B | V3-NR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `163018Z` | 640.2 | 303／3 | 470／0 | 177 | 553,840,640 | 298／298 |
| `164128Z` | 672.3 | 303／3 | 470／0 | 182 | 553,844,736 | 298／298 |
| `164203Z` | 672.5 | 303／3 | 470／0 | 266 | 553,840,640 | 298／298 |

三趟 E1／E2／E4a／E5／E6／V2-157／V2-158B／V2-160 全過，E3 每趟都只紅 §4 已保留的 `L-no-basic-udf`（`upstream/user-defined-function.ods`）。沒有新增失敗，raw exit 1 保留。V3-NR 三份完整報告各 298 筆全過；V2-160-D 三趟 **PASS**，LOK 派送失敗次數 **1／0／0**，第一趟的那一次引擎記錄相符且重送後確認，沒有 never dispatched。符合 v2 §8.3「重送有被走到且有效」的讀法。

N＝3 已滿；§4 的第三趟乾淨執行截止已到，之後的新增顧慮另立 finding／工作項，不再往這輪加判準。定向／E4b-E9／E6 的既有結果照 §12–13。引擎身分未再改，沒有再跑建置。

**剩下且不能代答的是 V3-SEE**：擁有者尚未確認具名 mirror 上的控制項外觀。原話未到，§4 的預設照舊：不宣稱「控制項已畫出」、158-B 尚未完成，也尚未執行 §5 的全成立後 host 0.2.33 包裝。現行宿主與 ddev 未更動；下一步是擁有者在 8794 預覽頁確認，之後接隔離 worktree／package／離線閘門／安裝手冊，最後才排 ddev 時段。§34.4 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §15：三趟全語料／V3-NR／160-D 全部結果；機器部分封閉，V3-SEE 待擁有者 |

## 16. 擁有者確認 V3-SEE；準備 host 0.2.33（2026-10-24，只追加）

擁有者在具名 v3／`ebb7e0cb` mirror 上回報原話：

> 綠色橫幅 OK
> 黃色格子裡的小方框 OK

證據 `phase-e/human-preview/owner-confirmation.md` 綁該頁／fixture 身分與原話。**V3-SEE 成立**；取代 §15「仍待人工」的狀態。§4 的這輪要求已全成立（保留原有 `L-no-basic-udf`），不追加別的人類項目。接續 §5 的 host **0.2.33** 準備；這不是 ddev 時段授權。

### 16.1 包裝、隔離與退路（任何 0.2.33 包裝／安裝之前釘下）

- 主 app 目前讀到 `main`／`bffc7dc`（0.2.32），工作樹乾淨。建立隔離 worktree／`host-0.2.33`，宿主只把 `appinfo/info.xml` 版本升成 0.2.33，不改路由／控制器／Files 動作。
- 先執行已讀過的 cp-only `make ods-viewer-assets`，不觸發編譯或 relink；再用 `package_m3_engine.py --app <隔離 worktree>` 包裝。**預設 app 是 LIVE，不能省略參數**。
- 依 schema 3 的既有流程產生實測 buildId；比較每個解碼檔與 0.2.32 archive，編輯器頁的閉包與引擎身分必須相同。這個包只帶新的 viewer page／profile，實際差異由 manifest 對帳列出，不把手工檔數當硬條件。
- 離線沿用 K0／Z0／H5-1、22 個 package 紅案及 packager 自測。`check_m3_assets.BUILD_ID` 在實測後改綁新值；是換包的綁定，不改判讀條件。以 live 0.2.32 包作負對照，不動它。
- 新包封存於 `build/archive/host-0.2.33-engine-<buildId>/`，逐檔驗過。安裝腳本、Phase H 鏈、手冊、release 草稿與退路先完成，再詢問 ddev 時段。
- 退路：宿主只有版本差異，換回 `build/archive/host-0.2.32-engine-80349a1a24cecb17/` 的 package 即回到原有功能；不 reset、不降 app 版本、不另跑 occ。新的 archive 與舊 archive 都保留。

### 16.2 Phase H 的判準與讀法（任何這次宿主執行之前釘下）

沿用 SPEC-M4 §4 H1–H7 與 viewer-v2 §10.3 的既有讀法；H4＝H-154c／H-154o／H-155，兩個瀏覽器各三輪並 `--require-h155`，加 host-entry runner；H5 是本次 package 的離線閘門。不新增判準，H7 仍是**裝好後擁有者從 Files 點開 .ods**，本輪 mirror 的 V3-SEE 不替代它。

- H1–H4、H6 全過 → 0.2.33 成為日常用的未計數候選，交擁有者 H7。
- 有紅 → 先讀 raw、時段內不修檢查，照 16.1 換回 0.2.32 package，記錄後停止。
- 只有 NOT_ESTABLISHED → 留候選、登錄，由擁有者決定。
- 沒有 ddev 時段 → 不安裝、不跑 H，0.2.32 留著。K 一律維持併批，不自行啟動或重綁。

§34.4 本段 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §16：V3-SEE 原話成立、0.2.33 的隔離包裝與 Phase H 原有判準／退路 |

## 17. 0.2.33 包裝與離線成立（2026-10-24，只追加；安裝之前）

宿主 `host-0.2.33`／`4f7f870` 在 `bffc7dc` 上，只改版本號。隔離 worktree 包裝出 schema 3／**`a67beefefebe57d6`**，35 檔、345,292,248 B，gzip 118,065,155 B、zstd 85,087,410 B。最大單檔 gzip 49,530,696 B、zstd 37,177,361 B，均未超既有上限。

對 0.2.32：28 檔完全相同，common path 只改 `ods-viewer-app.js`，六個 v2 profile 路徑換成六個 v3 路徑；**編輯器整個工具推導閉包 22 檔連編碼 metadata 都相同**。封存 `build/archive/host-0.2.33-engine-a67beefefebe57d6/`，71 檔比來源並驗 checksum。live `main` 與 `engine/` 在準備時仍是 0.2.32／80349a1a，沒有被 packager 寫入。

證據 `findings/evidence/host-0.2.33/`：packager 自測 13／13、K0／Z0／H5-1 零問題、22／22 紅案；live 0.2.32 負對照 exit 1、16 個問題。BUILD_ID 改綁實測的新包，是綁定不是判準修改。安裝／還原／Phase H 腳本與手冊已備，自製 ddev 狀態 fixture 的停止／忙碌拒絕、preflight-only 不寫 live、過期時段拒絕皆成立；這些 fixture 沒有操作真實 ddev。

## 18. 擁有者睡前授權自主執行（2026-10-24，只追加；啟動／安裝之前）

擁有者原話：

> 我要睡了，請你自主執行；告一段落就自主交接和停止
> 如果遇到難以判斷的地方就先記錄下來

將這項新指示用在已備妥的 0.2.33 安裝與 Phase H：`ddev list` 實讀目前沒有 running 專案，litecore stopped、nc-bridge paused（`ddev-before-slot.json`）。受託者採當下空閒時段，設定 **30 分鐘**的 WINDOW_END（實際起訖記於 `slot.json`）；只啟動自己的 litecore、不停別的專案，依 §16.2 讀結果。遇到難判處記錄，不擴張成 patch／審查鏈。

完成這段後寫交接、停止自己啟動的 litecore、恢復原本 stopped 狀態並結束。H7 仍需擁有者日後從 Files 親手開檔，不能由 agent 代答；今晚不追加人工要求。K 保持併批。§34.4 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §17：套件／離線結果；§18：睡前自主指示、實讀空閒 ddev、界限與停止點 |

## 19. 0.2.33 安裝與機器 Phase H 成立；已停止（2026-10-24，只追加）

在 §18 的受託空閒時段，只有 litecore 被啟動。`install.txt`（01:14:31–01:14:44）：前提全成立、main 快轉到 `4f7f870`、package **`a67beefefebe57d6`**，occ 升至 0.2.33、maintenance disabled、兩路由未登入 401。`post-install-identity.txt` 證實 live package 與新 archive 相同。

`chain.log`（01:15:14–01:23:42），各步 exit 0；完整判讀與路徑在 `findings/evidence/host-0.2.33/README.md`、`phase-h-summary.json`：

- H1／H2／H3／H6：**VIEWER HOST HOLDS**，無問題，含唯讀正對照與拿鎖紅案；原始報告 `m4-ods/phase-h/shakedown/2026-10-23T171515+0000.json`。
- Apache 在該步時窗有 **12 筆 v3 profile 請求，全部 200**，沒有 v2 profile 請求。
- H4：H-154c／H-154o／H-155，Chrome／Firefox 各三輪，全 PASS；host-entry **LANDS**，兩個瀏覽器 open-save／conflict 各 3／3，兩個 Chrome broken-host 對照各 1／1，problems 空；報告 `m3-host-entry/shakedown/2026-10-23T171807Z.json`。
- H5 是 §17 的本包離線閘門，已過。沒有需要 rollback 的紅，也沒有尚待裁決的難判結果。

依 §16.2，**0.2.33 取代 0.2.32 成為已安裝、未計數候選**。H7 仍未做：擁有者睡醒後在 Files 開 `M4 phase-h/M4 檢視 測試 plain.ods`（fileId 24674），看 Alpha／Beta／Gamma 並切換。保留這個測試資料夾；今晚不追加人工操作。先前的 V3-SEE 不冒充 H7。

01:25 收尾：停止自己啟動的 litecore，所有 ddev 專案狀態逐項與開始前相同（litecore stopped、nc-bridge paused、其他 stopped）；8794 自有 preview server 比過 PID／命令後停止、port 關閉，mirror 檔案保留。隔離 worktree 在驗過乾淨且 package 與 archive 相同後移除；新舊 archive、main 與 host-0.2.33 分支保留。`cleanup.json` 是紀錄。

K 沒有啟動／重綁，名義出貨版本仍 0.2.26。依擁有者指示，在本段寫好交接後停止工作；後續從 H7 或擁有者新指定的工作接續，不自行加跑量測。§34.4 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-24 | 追加 §19：安裝／Phase H 成立，H7 待日後，恢復服務狀態與自主停止 |

## 20. 接續 H7 的離線準備；ddev 時段被占用（2026-10-25，只追加）

擁有者要求依 `handoff/HANDOFF-2026-10-24-host-0233-installed-phase-h-holds-stopped.md` 展開後續任務。接續項目沿用 §19 的 H7，不新增判準。00:39:02（Asia/Taipei）實讀 `ddev list --json-output`：**fgp-nc running、litecore stopped**；依既有安裝手冊「別的專案正在執行就不另啟 litecore」的規則，本段沒有啟停任何專案，待新的可用時段。前一晚的 WINDOW_END 已過期，不沿用。

離線讀到宿主仍乾淨、`4f7f870`／0.2.33；磁碟上的 manifest 宣告 **a67beefefebe57d6**，sha256 與 `release.json` 相符，位元組與 archive 的 manifest 相同。這只確認 checkout 與 manifest，沒有重新驗完整引擎檔、容器或伺服器測試檔。證據 `findings/evidence/host-0.2.33/h7-preparation-2026-10-25/` 明列讀取範圍；未重跑 Phase E／H、語料或 K。

接續手冊 `handoff/RUNBOOK-host-0.2.33-h7.md` 已整理實際 Files 入口、`M4 phase-h/M4 檢視 測試 plain.ods`（fileId 24674）、Alpha／Beta／Gamma 切換、擁有者原話的紀錄位置，以及服務收尾。H7 的機械證據沿用同候選／同測試檔的既有 H2／H3，照 viewer-v2 §10.5 的前例；人類那半仍待擁有者在新時段親手操作。**未操作時 H7 維持 pending，0.2.33 維持未計數候選。**完成 H7 後 K 仍待擁有者明確排程，名義出貨版本仍 0.2.26。§34.4 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-25 | 追加 §20：接續 H7 的離線身分讀取、實讀 ddev 占用狀態與操作手冊 |

## 21. 擁有者空出時段；litecore 已啟動待 H7（2026-10-25，只追加）

擁有者原話：「我把fgp容器停掉了，請繼續」。02:50:35（Asia/Taipei）重新實讀：沒有 running 專案，fgp-nc／nc-bridge paused、litecore 與其餘專案 stopped；本段取代 §20 的「時段被占用」現況。啟動前已記錄新授權與本輪 H7 的工作界限，不沿用前一晚 WINDOW_END。受託者只執行 litecore 的 `ddev start`，exit 0；02:51:35 的狀態快照證實只有 litecore 從 stopped 變 running，其餘逐項相同。

02:52:02 在容器內直接讀到 installed_version **0.2.33**、maintenance false、package **a67beefefebe57d6**；manifest sha 與 viewer 完整項目均符合 `release.json`，viewer 是 **ods-viewer-v3／ebb7e0cb**。並經 Nextcloud 檔案 API 讀到保留的測試檔：`M4 phase-h/M4 檢視 測試 plain.ods`、fileId **24674**、7,537 B、sha256 **0402e527…**，名稱／id／大小／內容雜湊均與既有 H2／H3 報告相同。這些是本次實讀，沒有重跑瀏覽器閘門或重新驗全部引擎酬載。證據 `findings/evidence/host-0.2.33/h7-2026-10-25/`。

Files 的未登入 HTML 請求到登入頁 HTTP 200，已交擁有者實際 Files 入口與 Alpha／Beta／Gamma 切換步驟。**H7 仍待擁有者原話，尚未成立**；litecore 保持執行供本輪操作，收到結果或取消後停止本輪自行啟動的服務，除非擁有者要求保留。沒有重新安裝／升版、核心編譯／連結、Phase E／H 或語料重跑；K 維持併批未執行／未重綁。§34.4 **+0／+0**，累計 **46／27**。

| 日期 | 變更 |
| --- | --- |
| 2026-10-25 | 追加 §21：新時段授權、啟動 litecore、容器與測試檔身分實讀，待擁有者 H7 |
