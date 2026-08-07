# LibreOffice Core Lite 蒸餾研究

> 比對對象（同一個 repo 的三個 worktree）：
> - `collabora-25.04/` — 分支 `distro/collabora/co-25.04`（Collabora Online 用的核心）
> - `libreoffice-25-2/` — 分支 `libreoffice-25-2`（上游正規釋出分支）
> - `libreoffice-26-2/` — 分支 `libreoffice-26-2-5`（較新的上游分支，WASM 支援有進展）
>
> 目標：搞清楚 Collabora 是怎麼做的，據此規劃一個「堪用而精簡」的 LibreOffice core，
> 並評估「自製輕量前端 + 精簡 core」的可行性。
>
> 建立日期：2026-07-31

---

## 目錄

- [第 0 章：摘要](#第-0-章摘要)
- [第 1 章：兩份 source tree 的實際關係](#第-1-章兩份-source-tree-的實際關係)
- [第 2 章：先備知識 — LibreOffice 是怎麼被裁剪的](#第-2-章先備知識--libreoffice-是怎麼被裁剪的)
- [第 3 章：旗標大全（逐一解釋）](#第-3-章旗標大全逐一解釋)
- [第 4 章：ENABLE_WASM_STRIP_* 詳解](#第-4-章enable_wasm_strip_-詳解)
- [第 5 章：native-code.py — 元件白名單](#第-5-章native-codepy--元件白名單)
- [第 6 章：Collabora 究竟加了什麼](#第-6-章collabora-究竟加了什麼)
- [第 7 章：蒸餾 lite core 的建議路線](#第-7-章蒸餾-lite-core-的建議路線)
- [第 8 章：WASM、前後端分離與 UI 精簡](#第-8-章wasm前後端分離與-ui-精簡)
- [附錄 A：查證指令](#附錄-a查證指令)
- [附錄 B：名詞對照](#附錄-b名詞對照)

---

## 第 0 章：摘要

**核心結論：Collabora 的 core 不是「精簡版 LibreOffice」，而是「LibreOffice + 加料」。**

精簡這件事，在原始碼樹裡一行都沒發生。它 100% 發生在 `configure` 與 build 階段。而且那套精簡機制**幾乎全部已經在上游 25-2 裡了**，並不是 Collabora 的私有資產。

三個支撐這個結論的數字：

| 觀察 | 數字 | 意義 |
|---|---|---|
| Collabora 分支**刪除**的檔案 | **39** | 幾乎不刪碼 |
| Collabora 分支**新增**的檔案 | **951** | 大量加碼 |
| 精簡機制中 Collabora 獨有的 | **1 個旗標** | `--enable-lok-always-active` |

（刪除/新增數字已排除 `translations/`、`helpcontent2/`、`extras/`、`dictionaries/`、`icon-themes/` 這些非程式碼目錄。）

換句話說：**你想要的「lite core」，材料已經在上游樹裡了，你要做的是把旋鈕轉對，而不是去 fork 一份來刪。**

### 關於「自製前端 + 前後端分離」

（完整討論見[第 8 章](#第-8-章wasm前後端分離與-ui-精簡)。）

| 問題 | 答案 |
|---|---|
| 26-2 的 WASM 有進展嗎？ | 有，但幅度小。主要是 `--with-wasm-module` 支援複選並直接驅動 strip 旗標。embind 官方仍自評 *"very rough"*、*"might be leaking memory"*。 |
| 能自己用 JS 做前端嗎？ | 能。有三種架構，**只有「LOK + 自製 JS 前端」是成熟的**。 |
| 前後端分離能讓應用輕量化嗎？ | **不能。只能把重量搬到伺服器。** LibreOffice 的重量在 core 與資源，不在 UI。 |
| 那體積要靠什麼？ | 靠 configure 旗標與元件裁剪，跟前後端怎麼切無關。效益排序見 [8.6](#86-體積效益的實際排序) —— **第一名是移除 `--enable-symbols`**。 |

---

## 第 1 章：兩份 source tree 的實際關係

### 1.1 它們是同一個 repo

兩個目錄其實是**同一個 git repository 的兩個 worktree**：

```
$ git worktree list
/home/jiajun/LibreOffice/study_LiteCore/libreoffice-25-2   1c3fb8d928c9 [libreoffice-25-2]
/home/jiajun/LibreOffice/study_LiteCore/collabora-25.04    e588bf8da9dd [distro/collabora/co-25.04]
```

兩者的 `origin` 都是 `https://github.com/LibreOffice/core.git`。Collabora 沒有自己的 core repo — 它的分支就住在上游 repo 裡，叫 `distro/collabora/co-25.04`。同一個 repo 裡還有 `distro/allotropia/*`、`distro/cib/*` 等其他廠商的分支。

| | 分支 | `git describe` |
|---|---|---|
| `collabora-25.04/` | `distro/collabora/co-25.04` | `cp-25.04.9-4-93` |
| `libreoffice-25-2/` | `libreoffice-25-2` | `co-25.04-branch-point-621` |

### 1.2 分歧的規模

共同祖先（merge-base）是 `3eebb13805db`，也就是 `co-25.04-branch-point`。從那之後：

```
Collabora 側：3463 個 commit
上游 25-2 側： 621 個 commit
```

把 Collabora 那 3463 個用 patch-id 比對（`git cherry`），可以拆成：

```
3463 commits
├─  550  與上游 25-2 的 commit 內容完全相同
│        （兩邊都收的同一批修正，只是 hash 不同）
└─ 2913  Collabora 獨有
   ├─  558  commit 訊息裡有 "cherry picked from"
   │        → 從 master 或其他分支回填的上游程式碼
   └─ 2355  原生 commit
            → 真正 Collabora 自己寫的（或直接落在此分支的）
```

**注意第 3 類的性質**：那 2355 個裡有很多仍然是「會進上游、只是先落在 distro 分支」的程式碼。看提交者名單就知道 —— Andras Timar (878)、Miklos Vajna (872)、Caolán McNamara (537)、Michael Stahl (314)，這些都是 LibreOffice 上游的核心開發者，只是受僱於 Collabora / allotropia。而且這些 commit 都帶 `Reviewed-on: https://gerrit.libreoffice.org/...`，走的是**上游的 Gerrit code review**，不是內部私有流程。

這件事對你很重要：**Collabora 不是在維護一份私有 fork，而是在維護一份「上游程式碼的搶先版」。** 你如果 fork 去刪碼，就會走上一條 Collabora 自己都刻意避開的路。

### 1.3 檔案層級的變動

排除翻譯、說明、範本、字典、圖示等非程式碼目錄後：

```
刪除     39 個檔案
新增    951 個檔案
```

刪除的 39 個分布：`external` 20、`sw` 5、`vcl` 4、`svx` 3、`sd` 2、`include` 2、其他 3。這是正常開發過程中的檔案重組，**不是為了精簡而刪的**。

新增的 951 個分布：

| 模組 | 新增檔數 | 大致內容 |
|---|---|---|
| `sw` | 274 | Writer：LOK 多視圖、idle layout、redline API |
| `sc` | 262 | Calc：Sheet Views、Table Styles、pivot 強化 |
| `external` | 119 | 第三方函式庫的 patch |
| `sd` | 93 | Impress/Draw：LOK 唯讀處理、多視圖 |
| `chart2` | 45 | 圖表色盤與佈景主題 |
| `vcl` | 28 | 嵌入字型管理、EOT 字型轉換 |
| `filter` | 23 | 濾鏡 |
| `include` | 22 | 公開標頭 |

（完整 diff 含翻譯檔則是 8174 個檔案、+388238 / -102425 行，但那個數字沒有參考價值 —— 大部分是 `.po` 翻譯檔。）

---

## 第 2 章：先備知識 — LibreOffice 是怎麼被裁剪的

在看旗標之前，要先懂 LibreOffice 的建置有**三個可以下刀的層次**。很多人只知道第一層，結果精簡效果有限。

### 2.1 第一層：configure 階段 → 產生 `config_features.h`

`autogen.sh` 會執行 `configure`（由 `configure.ac` 產生）。你傳給它的 `--enable-xxx` / `--disable-xxx` / `--with-xxx` 旗標，最後會變成兩種東西：

**(a) C++ 的巨集**，寫進 `config_host/config_features.h`：

```c
#define HAVE_FEATURE_UI 0
#define HAVE_FEATURE_SCRIPTING 0
#define HAVE_FEATURE_DBCONNECTIVITY 0
```

程式碼裡用 `#if HAVE_FEATURE_SCRIPTING` 把整段包起來，關掉時那段就不會被編譯。

**(b) Makefile 的變數**，寫進 `config_host.mk`：

```make
ENABLE_SCRIPTING=
DISABLE_GUI=TRUE
```

建置系統用這些變數決定「要不要編譯某個模組 / 某個函式庫」。

> **重點**：這一層的效果**主要是整塊拿掉模組**，不太能做細粒度切割。例如 `HAVE_FEATURE_UI` 全樹只有 6 個檔案引用、`HAVE_FEATURE_XMLHELP` 只有 2 個。它們主要是在建置檔（`.mk`）裡當開關用，而不是在 `sw`/`sc` 內部到處切。

### 2.2 第二層：gbuild — LibreOffice 的自製 make 層

LibreOffice 不用 CMake，用一套叫 **gbuild** 的自製 GNU Make 框架（`solenv/gbuild/`）。三個關鍵概念：

- **Module（模組）**：一個頂層目錄就是一個模組，如 `sw`、`sc`、`vcl`。全部列在 `RepositoryModule_host.mk`（目前 **120 個**）。
- **Library（函式庫）**：一個 `.so` / `.dll`。全部列在 `Repository.mk`。
- **`gb_Helper_optional`**：條件包裝器。寫成 `$(call gb_Helper_optional,SCRIPTING,basic)` 的意思是「只有 `ENABLE_SCRIPTING` 為真時才納入 `basic` 模組」。

在 `RepositoryModule_host.mk` 的 120 個模組裡，只有 **12 個**被 `gb_Helper_optional` 包住：

```
DBCONNECTIVITY  DESKTOP  DICTIONARIES  HELP  LIBRELOGO  NLPSOLVER
ODK  OPENCL  PYUNO  QADEVOOO  SCRIPTING  XMLHELP
```

**這代表其餘 108 個模組沒有現成的關閉開關** —— 這是你要做 lite core 時的第一個施力點。

### 2.3 第三層：UNO 元件註冊（最深、效果最大）

LibreOffice 的功能是用 **UNO 元件**（UNO component）組起來的。可以想成「外掛」：每個功能（PDF 匯出、ODF 讀取、拼字檢查……）都是一個註冊過的元件，執行期用名字去查表拿到實作。

註冊表叫 **`services.rdb`**，是個 XML 檔，長得像這樣：

```xml
<component uri="vnd.sun.star.expand:$LO_LIB_DIR/libswlo.so">
  <implementation name="SwXTextDocument" constructor="..."/>
</component>
```

**關鍵洞見**：即使你在第一、二層關掉一堆東西，只要元件還註冊著、函式庫還被連結進去，體積就還在。真正的「蒸餾」是在這一層做白名單 —— 這就是 `solenv/bin/native-code.py` 在做的事（見[第 5 章](#第-5-章native-codepy--元件白名單)）。

### 2.4 額外一層：mergelibs（連結策略）

`--enable-mergelibs` 把約 100 個小的 `.so` 合併成單一 `libmerged.so`。這不刪功能，但：

- 減少動態連結器的符號解析工作 → **啟動變快**
- 讓連結器有機會做跨函式庫的死碼消除 → **體積變小**
- 減少 PLT/GOT 開銷

清單在 `solenv/gbuild/extensions/pre_MergedLibsList.mk`，合併目標定義在 `Library_merged.mk`。

`--enable-mergelibs=more` 會再吃進更多函式庫，但官方註記「不適合會把 LibreOffice 拆成多個套件的 distro，只適合單一安裝包的情境」—— 對 lite core 來說通常正是你要的。

---

## 第 3 章：旗標大全（逐一解釋）

以下以 Collabora Online 實際使用的 `distro-configs/CPLinux-LOKit.conf` 為主軸，逐條解釋。這個檔案是 Collabora 產品線實戰過的設定，比上游的示範設定 `LibreOfficeOnline.conf` 更完整。

> **怎麼用這些設定檔**：在 core 根目錄建立 `autogen.input`，內容寫 `--with-distro=CPLinux-LOKit`，然後跑 `./autogen.sh`。或直接 `./autogen.sh --with-distro=CPLinux-LOKit`。

### 3.1 A 組：GUI 與平台後端 —— 影響最大的一組

| 旗標 | 意義 |
|---|---|
| `--disable-gui` | **最重要的一個。** 不使用 X11 或 Wayland，整個桌面 GUI 後端不編譯。官方說明：「減少相依，例如為了建置 LibreOfficeKit」。這讓 VCL（LibreOffice 的繪圖/視窗層）只保留 headless 後端 —— 用 Cairo 畫到記憶體 bitmap，而不是畫到螢幕。 |
| `--disable-gtk3` | 不編譯 GTK3 視窗後端（Linux 桌面的預設外觀）。 |
| `--disable-qt5` / `--disable-kf5` | 不編譯 Qt5 / KDE Frameworks 5 後端。 |
| `--disable-randr` | 不使用 X11 的 RandR 擴充（螢幕解析度偵測）。沒有 GUI 就不需要。 |
| `--disable-dbus` | 關掉所有依賴 D-Bus 的功能：簡報模式的螢幕保護程式控制、藍牙簡報遙控、自動字型安裝。 |
| `--disable-gio` | 不使用 GIO（GNOME 的 I/O 抽象層，用於掛載遠端檔案系統等）。 |
| `--disable-dconf` | 不使用 dconf 設定後端（GNOME 的設定儲存）。 |
| `--disable-evolution2` | 不編譯 Evolution 通訊錄連接功能。 |

`--disable-gui` 在建置系統裡的實際落點（`DISABLE_GUI` 變數）：

```
vcl/Library_vcl.mk:631      → 切換 VCL 的後端來源檔
vcl/Module_vcl.mk:267       → 排除 GUI 相關子目標
sw/Module_sw.mk:193         → 排除 Writer 的 GUI 測試
sc/Module_sc.mk:73          → 排除 Calc 的 GUI 測試
sd/Module_sd.mk:62          → 排除 Impress 的 GUI 測試
desktop/Module_desktop.mk:23 → 排除啟動畫面 (Library_spl)
Repository.mk:474           → 同上
```

### 3.2 B 組：功能模組

| 旗標 | 意義 |
|---|---|
| `--disable-database-connectivity` | **關掉整個資料庫連接子系統**（含 Base）。對應 `HAVE_FEATURE_DBCONNECTIVITY`，全樹 27 個檔案引用。會連帶排除 `dbaccess`、`reportdesign` 模組。官方標註「進行中，只在你正在改它的時候用」—— 但 Collabora 生產環境有用，所以實務上可行。 |
| `--disable-scripting` | **關掉 BASIC、Java、Python 與 .NET 巨集支援。** 對應 `HAVE_FEATURE_SCRIPTING`，全樹 78 個檔案引用 —— 是所有 feature 巨集裡覆蓋最廣的。會排除 `basic`、`basctl`、`scripting` 等模組。⚠️ 注意：**很多文件格式的功能會用到 BASIC 引擎**（例如 OOXML 的 VBA 巨集、某些精靈），關掉要測。 |
| `--disable-scripting-beanshell` | 只關 BeanShell 腳本（Java 的一種直譯器）。比 `--disable-scripting` 溫和。 |
| `--disable-scripting-javascript` | 只關 JavaScript 腳本支援（Rhino）。 |
| `--disable-avmedia` | 關掉文件裡影音媒體的顯示與插入。對應 `HAVE_FEATURE_AVMEDIA`，42 個檔案引用。 |
| `--disable-gstreamer-1-0` | 不編譯 GStreamer 影音後端（`--disable-avmedia` 的相依項）。 |
| `--disable-report-builder` | 關掉 Base 的報表產生器（一個 Java 寫的延伸功能）。 |
| `--disable-firebird-sdbc` | 不編譯 Firebird 資料庫驅動（Base 的內建資料庫引擎）。 |
| `--disable-postgresql-sdbc` | 不編譯 PostgreSQL 驅動。 |
| `--disable-ext-nlpsolver` | 不編譯非線性規劃求解器延伸（Calc 的進階規劃求解）。 |
| `--disable-ext-wiki-publisher` | 不編譯 Wiki 發佈延伸。 |
| `--disable-lpsolve` | 不編譯 lp_solve 線性規劃求解器（Calc 規劃求解的後端之一）。 |
| `--disable-librelogo` | 不編譯 LibreLogo（Writer 裡的 Logo 龜圖教學工具）。 |
| `--disable-sdremote` | 不編譯 Impress 遙控的伺服器端。 |
| `--disable-sdremote-bluetooth` | 同上，藍牙部分。 |
| `--disable-online-update` | 關掉線上更新檢查服務。 |
| `--disable-odk` | 不建置 Office Development Kit（第三方寫延伸功能需要的 SDK 標頭與工具）。**純粹是建置產物，關掉不影響功能。** |
| `--disable-poppler` | 不建置 Poppler（PDF 匯入用的函式庫）。⚠️ 關掉就**不能匯入 PDF**。 |

### 3.3 C 組：檔案格式濾鏡 —— 體積肥肉的所在

| 旗標 | 意義 |
|---|---|
| `--disable-lotuswordpro` | 不編譯 Lotus Word Pro 濾鏡（`lotuswordpro` 模組整個不建）。 |
| `--enable-mpl-subset` | **不編譯任何非 MPL（或更寬鬆）授權的部分。** 這是授權旗標，但**副作用是砍掉一堆濾鏡** —— 因為許多冷門格式的解析器是 LGPL/GPL。Collabora 用它同時達成授權合規與瘦身。 |

**這裡是你最該注意的地方**：真正佔體積的往往不是那些一眼可見的模組，而是散在 `external/` 底下的**冷門格式解析函式庫**：

```
libwps       Microsoft Works
libwpd       WordPerfect
libwpg       WordPerfect Graphics
libvisio     Microsoft Visio
libcdr       CorelDRAW
libmspub     Microsoft Publisher
libpagemaker Adobe PageMaker
libqxp       QuarkXPress
libzmf       Zoner Callisto/Draw
libfreehand  Adobe FreeHand
libabw       AbiWord
libe-book    各種電子書格式
libetonyek   Apple Keynote
libstaroffice StarOffice 舊格式
```

`configure.ac:3350` 附近有現成的範例，示範 WASM 建置怎麼一次關掉它們：

```
test_libfreehand=no
test_libmspub=no
test_libpagemaker=no
test_libqxp=no
test_libvisio=no
test_libzmf=no
```

**這段是你第一個該複製的 pattern。**

### 3.4 D 組：資源與語言

| 旗標 | 意義 |
|---|---|
| `--with-lang="..."` | 指定要建置哪些 UI 語言。Collabora Online 列了 38 種；上游 `LibreOfficeOnline.conf` 用 `ALL`（全部 100+ 種）。**這對安裝體積影響巨大** —— 每種語言都是一整套 `.po` 翻譯編譯出的資源。lite core 建議只留 `en-US zh-TW`。 |
| `--without-help` | 不建置說明文件（`helpcontent2` 是個獨立的 submodule，幾百 MB）。 |
| `--with-galleries=no` | 不建置美工圖庫（Gallery，那些預設的圖形素材）。 |
| `--without-templates` | 不建置範本檔。 |
| `--with-theme="colibre colibre_svg"` | 只建置指定的圖示佈景。預設會建 breeze、breeze_dark、colibre、colibre_dark、elementary、sifr… 一大堆。**只留一套省很多。** |
| `--with-fonts` | **包含**第三方字型（給說明、範本、範例用的基礎字型）。如果目標系統保證有字型，可以改用 `--without-fonts`。 |
| `--with-docrepair-fonts` | 包含 DocRepair 專案的字型 —— 為 OOXML 文件常見字型提供**度量等價的替代字型**（例如替代 Calibri、Cambria）。⚠️ 做文件轉換/驗證的話這個很重要，砍了會導致版面跑掉。 |
| `--enable-noto-font` | 額外加入 Google Noto 字型。 |
| `--with-system-dicts` / `--with-myspell-dicts` | 用系統的拼字字典，而非自己編一份。 |
| `--with-external-{thes,hyph,dict}-dir=...` | 指定系統字典/斷詞/同義詞的路徑。 |

### 3.5 E 組：連結與體積

| 旗標 | 意義 |
|---|---|
| `--enable-mergelibs` | 把約 100 個小函式庫合併成單一 `libmerged.so`。見 [2.4](#24-額外一層mergelibs連結策略)。 |
| `--enable-mergelibs=more` | 更激進，再合併更多。適合單一安裝包的情境。 |
| `--enable-lto` | Link-Time Optimization，連結期跨檔案最佳化。**體積與效能都有幫助，但建置時間與記憶體需求大幅上升。** 注意：Collabora 在 `CPLinux-LOKit.conf` 裡把它**移除了**（上游版本有），推測是建置資源考量。 |
| `--enable-release-build` | 釋出版建置。與「有沒有符號/最佳化」是**正交**的兩件事 —— 它主要影響安裝路徑、設定檔位置、是否允許與開發版並存。 |
| `--with-linker-hash-style=both` | 產生 sysv 與 gnu 兩種 ELF hash table，相容性考量。 |
| `--without-system-*` | 一系列旗標（`cairo`、`freetype`、`harfbuzz`、`icu`、`nss`、`openssl`、`curl`、`libxml`、`libpng`、`jpeg`、`expat`…），意思是**自己編一份，不用系統的**。這會讓建置變慢、產物變大，但可攜性最好（產物不依賴目標機器的函式庫版本）。⚠️ **對 lite core 這是個 trade-off**：用系統函式庫（`--with-system-*`）產物小很多，但要求部署環境有對應版本。 |
| `--with-system-zlib` | 相反地，zlib 用系統的（幾乎所有系統都有）。 |

### 3.6 F 組：品牌與授權

| 旗標 | 意義 |
|---|---|
| `--with-vendor=Collabora` | 「關於」對話框裡顯示的廠商名。 |
| `--disable-community-flavor` | 關掉「社群版」品牌標示。 |
| `--with-branding=icon-themes/galaxy/brand_cp` | 指定啟動畫面、關於視窗的品牌圖檔目錄。 |
| `--enable-mpl-subset` | 只編譯 MPL 或更寬鬆授權的部分（見 [3.3](#33-c-組檔案格式濾鏡--體積肥肉的所在)）。 |
| `--enable-extension-integration` | 把建好的延伸功能整合進安裝檔。 |
| `--with-package-format="deb rpm"` | 產生 deb 與 rpm 安裝包。`--without-package-format` 則完全不打包（只留 `instdir/`）。 |
| `--enable-epm` | 使用內建的 epm 打包工具。 |

### 3.7 G 組：開發與除錯

| 旗標 | 意義 |
|---|---|
| `--enable-symbols` | 產生除錯符號。⚠️ **會讓產物變得非常大**（LibreOffice 的完整符號可以到數 GB）。Collabora 開著是為了線上服務崩潰時能分析 backtrace，正式部署時通常會另外 strip 出來。**lite core 若追求體積，這個要關。** |
| `--enable-sal-log` | 讓 `SAL_INFO` / `SAL_WARN` 在非 debug 建置也有作用（可用 `SAL_LOG` 環境變數開啟日誌）。有一定的體積與效能代價。 |
| `--enable-hardening-flags` | 自動加上防護性編譯旗標（stack protector、FORTIFY_SOURCE、RELRO 等）。 |
| `--without-java` / `--without-junit` | 不使用 Java。**這會連帶關掉所有 Java 元件**（Base 的報表產生器、部分精靈、部分濾鏡）。 |
| `--enable-python=internal` | 使用內建的 Python（而非系統的）。可選 `no` / `auto` / `system` / `internal` / `fully-internal`。⚠️ 選 `no` 會關掉 Python 腳本支援與 `pyuno`。 |
| `--with-buildconfig-recorded` | 把 configure 參數記錄進產物，方便日後追查。 |

### 3.8 H 組：兩個「未走完的路」

這兩個不在 Collabora 的 Linux 設定裡，但對 lite core 極為關鍵：

| 旗標 | 意義 |
|---|---|
| `--disable-dynamic-loading` | **完全不使用動態載入。** 所有元件靜態連結成單一執行檔。這是 Android / iOS / WASM 走的路。⚠️ 必須搭配 `--disable-gui` 與**單一 VCL 後端**（`configure.ac:12460` 有這個檢查）。這條路才會啟用 `native-code.py` 的元件白名單機制。 |
| `--enable-wasm-strip` | 「像 WASM/emscripten 平台那樣裁剪靜態建置」。**這是全樹裡最激進的精簡開關**，見[第 4 章](#第-4-章enable_wasm_strip_-詳解)。⚠️ 目前條件是 `cross_compiling = yes` 且 `enable_dynamic_loading != yes`（`configure.ac:4249`）—— 也就是說**原生建置吃不到**，這是你要動手改的地方。 |

### 3.9 I 組：Collabora 獨有的一個

| 旗標 | 意義 |
|---|---|
| `--enable-lok-always-active` | **上游 25-2 沒有，Collabora 獨有。** 見[第 6.3 節](#63-唯一的-collabora-獨有精簡機制)。 |

---

## 第 4 章：ENABLE_WASM_STRIP_* 詳解

### 4.1 這是什麼

這是一組 **20 個**旗標，原本為了把 LibreOffice 塞進瀏覽器（WASM）而開發。與第 3 章那些旗標最大的不同是：

> **前面那些旗標主要在「模組層級」下刀（整個 `dbaccess` 不建）。
> 這組旗標會深入 `sw` / `sc` / `vcl` 的原始碼內部，用 `#if` 切掉程式碼片段。**

例如 `sw/source/core/layout/tabfrm.cxx`（Writer 表格排版）裡有 10 處 `#if`、`fly.cxx`（浮動框架）8 處、`vcl/source/bitmap/BitmapTools.cxx` 16 處。

**這是全樹裡唯一已經證明「可以在 sw/sc 內部做細粒度切割而不破壞建置」的基礎設施。對你的 lite core 來說，這是最有價值的參考範本。**

### 4.2 定義在哪

```
configure.ac:3363-3380   ← 在 Emscripten 平台時一次 AC_DEFINE 這一批
configure.ac:4249-4257   ← ENABLE_WASM_STRIP 主開關 + WRITER/CALC 的條件
```

注意 `configure.ac:3367` 和 `3372` 是**被註解掉的**：

```
#    AC_DEFINE(ENABLE_WASM_STRIP_CHART)      ← 圖表沒被砍
#    AC_DEFINE(ENABLE_WASM_STRIP_HUNSPELL)   ← 拼字檢查沒被砍
```

代表機制存在但預設沒啟用 —— 你可以自己打開。

### 4.3 逐一解釋

| 旗標 | 砍掉什麼 | 落點（代表性檔案） |
|---|---|---|
| `STRIP_WRITER` | **整個 Writer**（`sw`、`swext` 模組） | `RepositoryModule_host.mk:165`、`writerperfect/Module_writerperfect.mk:30` |
| `STRIP_CALC` | **整個 Calc**（`sc`、`scaddins`、`sccomp`、`basctl` 模組） | `RepositoryModule_host.mk:58,133` |
| `STRIP_BASIC_DRAW_MATH_IMPRESS` | **BASIC IDE、Draw、Math、Impress**（`sd`、`sdext`、`starmath`、`animations`、`slideshow` 模組） | `RepositoryModule_host.mk:53,140,147,154`、`svx/Library_svxcore.mk`、`extensions/Module_extensions.mk` |
| `STRIP_CHART` | **整個 chart2 模組**，以及 xmloff 裡的圖表 ODF 讀寫 | `RepositoryModule_host.mk:24`、`xmloff/Library_xo.mk`、`xmloff/source/core/xmlimp.cxx` |
| `STRIP_CANVAS` | `canvas`、`cppcanvas` 模組（舊的 UNO canvas 繪圖抽象層） | `RepositoryModule_host.mk:31`、`Repository.mk:20,358,950`、`drawinglayer/Library_drawinglayer.mk` |
| `STRIP_DBACCESS` | `dbaccess` 模組 + Base 的檔案格式濾鏡註冊 | `RepositoryModule_host.mk:38`、`filter/Configuration_filter.mk`、`postprocess/CustomTarget_registry.mk` |
| `STRIP_ACCESSIBILITY` | `accessibility`、`winaccessibility` 模組，以及 svx 裡各種控制項的無障礙介面實作 | `RepositoryModule_host.mk:44`、`svx/source/dialog/{charmap,dlgctrl,frmsel,graphctl,weldeditview}.cxx`、`vcl/source/helper/svtaccessiblefactory.cxx` |
| `STRIP_EPUB` | EPUB 匯出（`writerperfect` 裡的 libepubgen 整合） | `writerperfect/Library_wpftwriter.mk`、`RepositoryExternal.mk` |
| `STRIP_SWEXPORTS` | **Writer 的非 ODF 匯出濾鏡** | `writerperfect/Library_wpftwriter.mk` |
| `STRIP_SCEXPORTS` | **Calc 的非 ODF 匯出濾鏡** | `writerperfect/Library_wpftcalc.mk` |
| `STRIP_GUESSLANG` | 自動語言偵測（`lingucomponent/Library_guesslang.mk`） | `Repository.mk:372`、`lingucomponent/Module_lingucomponent.mk` |
| `STRIP_HUNSPELL` | **拼字檢查、斷詞、同義詞**（hunspell / hyphen / mythes 三個外部庫） | `Repository.mk:378`、`external/hunspell/`、`editeng/source/misc/splwrap.cxx`、`cui/Library_cui.mk` |
| `STRIP_LANGUAGETOOL` | LanguageTool 文法檢查整合 | `lingucomponent/Module_lingucomponent.mk` |
| `STRIP_RECOVERYUI` | **當機復原 UI** | `desktop/source/app/app.cxx`、`svx/Library_svx.mk`、`framework/Library_fwk.mk` |
| `STRIP_RECENT` | **最近使用文件清單**與其縮圖檢視 | `sfx2/Library_sfx.mk`、`sfx2/source/control/thumbnailview.cxx` |
| `STRIP_SPLASH` | **啟動畫面**（`Library_spl`） | `Repository.mk:474`、`desktop/Module_desktop.mk:23`、`vcl/Library_vcl.mk` |
| `STRIP_PINGUSER` | 「歡迎/提示使用者」的各種對話框（首次執行、捐款提示、更新通知等） | `desktop/source/app/app.cxx`、`sfx2/source/appl/appserv.cxx`、`cui/UIConfig_cui.mk` |
| `STRIP_EXTRA` | 各種次要對話框（在對話框工廠裡整段拿掉） | `cui/source/factory/dlgfact.cxx`、`sw/source/ui/dialog/swdlgfact.cxx` |
| `STRIP_PREMULTIPLY` | bitmap 的 premultiplied alpha 轉換路徑（**效能/相容性取捨，不是功能刪減**） | `vcl/source/bitmap/BitmapTools.cxx`、`vcl/headless/CairoCommon.cxx`、`vcl/source/filter/png/PngImageReader.cxx` |
| `STRIP_LOCALES` | 語言區域資料裁剪（**目前只在 configure 有名字，建置檔裡沒有落點** —— 未完成的機制） | — |

### 4.4 怎麼用（重點）

`ENABLE_WASM_STRIP_WRITER` 和 `ENABLE_WASM_STRIP_CALC` 是由 `--with-main-module` 驅動的：

```
--with-main-module=writer   →  ENABLE_WASM_STRIP_CALC=TRUE   （只要 Writer）
--with-main-module=calc     →  ENABLE_WASM_STRIP_WRITER=TRUE （只要 Calc）
```

也就是說 **WASM 版一次只能有一個主應用程式**。這個「二選一」的設計思路，對 lite core 很有啟發：如果你的使用情境只需要 Writer，那 Calc + Impress + Draw + Math 全部可以砍。

⚠️ **但目前的限制**（`configure.ac:4249`）：

```sh
if test "$cross_compiling" = "yes"; then
    if test "$enable_dynamic_loading" != yes -a "$enable_wasm_strip" = yes; then
        ENABLE_WASM_STRIP=TRUE
    fi
```

**必須是 cross-compile 且 `--disable-dynamic-loading`**。原生的 Linux 動態建置吃不到這組旗標。要在 lite core 用上，你得改這段條件，或另建一組平行的 `ENABLE_LITE_*` 旗標沿用同樣的 `#if` 落點。

---

## 第 5 章：native-code.py — 元件白名單

### 5.1 這是什麼

`solenv/bin/native-code.py`（976 行）是一份**手工維護的 UNO 元件清單**，把所有元件分成 6 組：

```python
factory_map = {
    'core',    # 基礎設施：設定、i18n、檔案存取、UNO 底層…
    'edit',    # 編輯相關
    'math',    # Math 公式編輯器
    'calc',    # Calc
    'draw',    # Draw / Impress
    'writer',  # Writer
}
```

用法：

```sh
# 產生只含 core + writer 的元件註冊表（C++ 原始碼）
native-code.py -g core -g writer  >  native-code.cxx

# 反過來：裁剪一份現成的 services.rdb，只留指定組別的元件
native-code.py -r services.rdb -g core -g writer
```

第一種模式產生一個 C++ 檔，裡面是一張靜態的「元件名 → constructor 函式指標」對照表，供靜態連結時使用（沒有動態載入，所以查表必須在編譯期建好）。

第二種模式（`-r`）**更值得你注意** —— 它直接改寫 `services.rdb`，把不在白名單裡的 `<implementation>` 整個刪掉。這條路**不需要靜態連結也能用**。

### 5.2 目前只有靜態建置在用

```
android/source/Makefile:15              Android
ios/CustomTarget_iOS_setup.mk:44,52     iOS
static/CustomTarget_components.mk:23,31 WASM / 靜態建置
vcl/CustomTarget_native{core,writer,calc,draw,math}.mk   fuzzer
```

**Collabora Online 的 Linux 伺服器版是動態建置，完全不走這條路。**

### 5.3 條件式元件（Collabora 正在強化的方向）

清單裡的項目可以是純字串，也可以是 `(名字, 條件)` 的 tuple。Collabora 分支上最新的一筆 commit `9f18735b173e` 正是在做這件事：

```python
# 之前
"com_sun_star_comp_dba_ODatabaseContext_get_implementation",

# 之後
("com_sun_star_comp_dba_ODatabaseContext_get_implementation",
 "#if HAVE_FEATURE_DBCONNECTIVITY"),
```

這樣產生出來的 C++ 表格會帶 `#if`，讓第一層的 feature 旗標能穿透到第三層的元件註冊。**這正是把三層打通的做法，也正是你該學的模式。**

---

## 第 6 章：Collabora 究竟加了什麼

### 6.1 三條功能主軸

**(a) LOK 多視圖正確性** — LibreOfficeKit（LOK）是 LibreOffice 的嵌入 API，Collabora Online 靠它把文件算成圖磚（tile）送到瀏覽器。多人同時編輯同一份文件時，core 內部要維護多份獨立的「視圖狀態」（游標位置、選取範圍、捲動位置）。大量 commit 在修這件事：

```
sw: add null checks in paintTile/postMouseEvent for LOK
LOK: avoid switching page on selection
svx: fix SIGSEGV in SdrEndTextEdit OutlinerView cleanup (LOKit multi-view)
Fix SIGSEGV in SwXTextDocument LOKit methods with null m_pDocShell
```

**(b) jsdialog 覆蓋率** — jsdialog（`vcl/jsdialog/`，**上游也有**）把 LibreOffice 的原生對話框（`.ui` 檔）序列化成 JSON 送到瀏覽器渲染。Collabora 的工作是一個一個把對話框「啟用」為 jsdialog：

```
jsdialog: enable numbering name dialog
jsdialog: enable Insert Table dialog
jsdialog: enable conditional format dialogs
jsdialog: enable print areas dialog
```

**(c) 協作編輯** — 修訂記錄（redline）、權限控制、唯讀模式：

```
lok: Make SwRedlineAcceptDlg take blocked commands into account
cool#13988 sw redline tooltip LOK API: expose anchor range
```

### 6.2 公開 API 只多了 4 個函式

`include/LibreOfficeKit/` 的 diff 顯示，對外 C API 只新增：

```c
int  (*getDocsCount)(LibreOfficeKit* pThis);
void (*registerFileSaveDialogCallback)(LibreOfficeKit* pThis, ...);
void (*setColorPreviewState)(LibreOfficeKitDocument* pThis, int nId, bool nEnabled);
void (*setAllowManageRedlines)(LibreOfficeKitDocument* pThis, int nId, bool allow);
```

（`LOK_CALLBACK_*` 事件類型目前共 244 種。）

**API 面幾乎沒變 → 代表 Collabora 的 core 對「非 Online 用途」而言，跟上游沒有本質差異。**

### 6.3 唯一的 Collabora 獨有精簡機制

Commit `2601d05bfc26`，只動 4 個檔案、28 行：

```c
// include/comphelper/lok.hxx
#if LOK_ALWAYS_ACTIVE
constexpr bool isActive() { return true; }    // ← 編譯期常數
#else
COMPHELPER_DLLPUBLIC bool isActive();          // ← 執行期查全域變數
#endif
```

```c
// comphelper/source/misc/lok.cxx
#if !LOK_ALWAYS_ACTIVE
static bool g_bActive(false);
bool isActive() { return g_bActive; }
#endif
```

configure 端（`configure.ac:871`）：

```sh
AC_ARG_ENABLE([lok-always-active],
    AS_HELP_STRING([--enable-lok-always-active],
        [Make comphelper::LibreOfficeKit::isActive() a compile-time constant
         returning true.]))
```

**為什麼這個很重要**：全樹有數千處寫成

```cpp
if (comphelper::LibreOfficeKit::isActive()) {
    ... 走 LOK 路徑 ...
} else {
    ... 走桌面 GUI 路徑 ...
}
```

當 `isActive()` 變成 `constexpr` 回傳 `true`，編譯器可以把 `else` 分支整段消掉（dead code elimination）。**這一個旗標對 LOK-only 建置的體積效益，可能大過前面一堆 `--disable-*` 加起來。**

而且它極為乾淨 —— 4 個檔案、28 行、沒有相依。**如果你的 lite core 走 LOK 路線，這是第一個該 cherry-pick 的 commit。**

---

## 第 7 章：蒸餾 lite core 的建議路線

### 7.0 最高原則：不要 fork 去刪碼

Collabora 養了一整個團隊維護 distro 分支，也只刪了 **39 個檔案**。原因很簡單：刪碼會讓你每次追上游時都要重解衝突，這個成本會隨時間指數上升，第一次 rebase 就足以殺死專案。

正確做法是**加 `#if` 與 gating，然後把它推上游**。Collabora 自己就是這樣做的 —— 上面引用的兩個 commit（`2601d05bfc26`、`9f18735b173e`）都帶 `Reviewed-on: https://gerrit.libreoffice.org/...`，走的是上游 code review。

### 7.1 階梯式路線（由低風險到高）

#### 第 0 階：選對起點

用 `distro-configs/CPLinux-LOKit.conf`，**不要**用 `LibreOfficeOnline.conf`。

前者是 Collabora 產品線實戰過的；後者是上游的示範設定，少了 `--disable-randr`、`--disable-lotuswordpro`、`--without-templates`、`--enable-symbols`、`--disable-librelogo` 等。

```sh
./autogen.sh --with-distro=CPLinux-LOKit
```

或者複製一份改：

```sh
cp distro-configs/CPLinux-LOKit.conf distro-configs/LiteCore.conf
# 編輯 LiteCore.conf
./autogen.sh --with-distro=LiteCore
```

> ⚠️ **照抄之前，先拿掉 `--enable-symbols`。**
>
> `CPLinux-LOKit.conf` 是 Collabora 的**產品設定**，不是精簡設定。裡面有幾項是為了營運線上服務而存在，對 lite core 反而是負擔：
>
> | 項目 | Collabora 為什麼要 | 對你 |
> |---|---|---|
> | `--enable-symbols` | 線上服務崩潰時要能分析 backtrace | **體積殺手**，可佔數 GB。[8.6](#86-體積效益的實際排序) 排第 1 名 |
> | `--enable-sal-log` | 營運時要能開 `SAL_LOG` 追問題 | 有體積與執行期代價 |
> | `--enable-symbols` 之外的品牌項<br>（`--with-vendor`、`--with-branding`、`--disable-community-flavor`） | Collabora 的產品識別 | 你要換成自己的或直接拿掉 |
> | `--with-lang=`（38 種語言） | 服務全球客戶 | 你多半只需要 2 種 |
> | `--with-package-format=deb rpm` | 出貨要打包 | 開發階段可用 `--without-package-format` 省時間 |
>
> **這是最容易被忽略、效益卻最大的一項** —— 因為「用 Collabora 實戰過的設定當起點」這個建議本身是對的，錯的是連產品營運需求一起繼承。第 1 階會再列一次移除清單。

**風險：無。這只是換設定。**

#### 第 1 階：零程式碼成本的加碼

在你的 `LiteCore.conf` 加上：

```
--enable-mergelibs=more          # 合併更多函式庫
--with-lang=en-US zh-TW          # 只留兩種語言（原本 38 種）
--with-theme=colibre             # 只留一套圖示（原本兩套）
```

並**移除**（前兩項在[第 0 階](#第-0-階選對起點)已提醒，這裡是完整清單）：

```
--enable-symbols                 # ★ 除錯符號，體積殺手，效益排序第 1 名
--enable-sal-log                 # 執行期日誌
--with-docrepair-fonts           # ⚠️ 只有在你不做 OOXML 版面還原時才移除
--enable-noto-font               # 若目標系統已有字型
--with-package-format=deb rpm    # 開發階段改用 --without-package-format 省建置時間
```

**風險：低。純設定變更，不動程式碼。**

#### 第 2 階：關掉已有 gating 的功能模組

```
--disable-database-connectivity  # HAVE_FEATURE_DBCONNECTIVITY，27 檔案
--disable-avmedia                # HAVE_FEATURE_AVMEDIA，42 檔案
--disable-scripting              # HAVE_FEATURE_SCRIPTING，78 檔案 ⚠️ 見下
```

⚠️ `--disable-scripting` 要特別測試：OOXML 的 VBA 巨集、部分精靈、部分濾鏡會用到 BASIC 引擎。若出問題，退而求其次只用 `--disable-scripting-beanshell --disable-scripting-javascript`。

**風險：中。gating 已經寫好了，但這三個都標註「work in progress」，要跑完整的濾鏡測試。**

#### 第 3 階：砍冷門格式濾鏡

複製 `configure.ac:3350` 附近的 WASM pattern。**機制說明**：這些外部函式庫是用 `libo_CHECK_SYSTEM_MODULE([libxxx],...)` 宣告的，該巨集（定義在 `m4/libo_externals.m4`）會去讀一個叫 `test_libxxx` 的 shell 變數 —— 註解寫得很清楚：

```
#  - test_$1: set to no, if the feature shouldn't be tested at all
```

所以只要在 configure 的適當位置設 `test_libxxx=no`，該函式庫就完全不會被建置。

**WASM 區塊已經關掉的（直接抄）**：

```sh
test_libfreehand=no      # Adobe FreeHand
test_libmspub=no         # Microsoft Publisher
test_libpagemaker=no     # Adobe PageMaker
test_libqxp=no           # QuarkXPress
test_libvisio=no         # Microsoft Visio
test_libzmf=no           # Zoner Callisto/Draw
```

**還可以再加的（`configure.ac` 有 `test_` 支援，但 WASM 區塊沒關）**：

```sh
test_libcdr=no           # CorelDRAW
test_libetonyek=no       # Apple Keynote/Pages/Numbers
```

⚠️ **這四個上游完全沒有關閉開關**（`configure.ac` 裡沒有任何 `test_` 賦值，永遠會建）：

| 函式庫 | 格式 | 註記 |
|---|---|---|
| `libwpd` | WordPerfect Document | `configure.ac:10238` |
| `libwps` | Microsoft Works | `configure.ac:10242` |
| `libabw` | AbiWord | `configure.ac:10262` |
| `libstaroffice` | StarOffice 舊格式 | `configure.ac:10270` |

由於巨集本身支援 `test_$1`，你**可以**在自己的分支加上 `test_libwpd=no` 等來關閉 —— 這是一個乾淨、值得推上游的小改動。但要注意 `libwpd` / `libwps` 是 `writerperfect` 模組的相依項，關掉前先確認 `writerperfect/Library_wpft*.mk` 的連動。

**這是投報率最高的一步之一** —— `external/` 底下這些函式庫加起來體積可觀，而且絕大多數使用情境永遠用不到。

**風險：中低。要確認你的使用情境真的不需要這些格式。**

#### 第 4 階：LOK 路線的話 —— cherry-pick `lok-always-active`

```sh
git cherry-pick 2601d05bfc2607a87e21430ef36a64245c9b749a
```

然後加上 `--enable-lok-always-active`。

只動 4 個檔案、28 行，衝突風險極低。**如果你的 lite core 只服務 headless/嵌入情境，這可能是單一效益最高的改動。**

**風險：低（程式碼層面）。但這會讓你的 build 無法用於桌面 GUI 情境 —— 是單向門。**

#### 第 5 階：接手 native-code.py 的元件白名單

這是**投報率最高、也最需要動手**的一步。

目前 `native-code.py` 只在靜態建置用。但它的 `-r` 模式（裁剪 `services.rdb`）**不需要靜態連結**。做法：

1. 在 `postprocess/` 加一個步驟，用 `native-code.py -r` 裁剪產生的 `services.rdb`
2. 用 `-g core -g writer`（或你需要的組合）
3. 沒被註冊的元件，即使 `.so` 還在，也不會被載入 → 啟動變快、記憶體變少
4. 進一步：讓建置系統據此**不連結**那些函式庫 → 體積真的變小

同時，把 `9f18735b173e` 的模式推廣開來 —— 把清單裡更多項目改成 `(名字, "#if HAVE_FEATURE_XXX")` 的形式，讓第一層的 feature 旗標能穿透到第三層。

**風險：高。需要理解 UNO 元件系統，且要有完整的回歸測試。但這是「真正的蒸餾」。**

#### 第 6 階：建立你自己的 `ENABLE_LITE_*`

沿用 `ENABLE_WASM_STRIP_*` 已經證明可行的 `#if` 落點，建立一組平行的旗標，讓它們在**原生動態建置**也能生效（目前被 `cross_compiling = yes` 擋住）。

優先順序建議：

1. `STRIP_SWEXPORTS` / `STRIP_SCEXPORTS` — 若只需要讀不需要寫，或只需要 ODF 不需要 OOXML，**濾鏡層是最大的一塊肥肉**
2. `STRIP_RECOVERYUI`、`STRIP_RECENT`、`STRIP_PINGUSER`、`STRIP_SPLASH` — headless 情境完全用不到，且落點乾淨
3. `STRIP_ACCESSIBILITY` — ⚠️ 這個要想清楚，無障礙功能可能是法規要求
4. `STRIP_BASIC_DRAW_MATH_IMPRESS` / `STRIP_CALC` / `STRIP_WRITER` — 若你的情境只需要其中一兩個應用程式

**風險：高。但這是 Collabora 和 allotropia 已經走過的路，`#if` 的位置都已經標好了。**

### 7.2 一句話總結

> 材料都在上游樹裡。第 0～3 階是「把旋鈕轉對」，第 4～6 階是「把已經存在的機制推廣到你的建置情境」。
> 全程都不需要 fork 去刪碼。

---

## 第 8 章：WASM、前後端分離與 UI 精簡

> 本章回答的問題：**能不能自己用 JavaScript 做一個極簡前端，把 LibreOffice core 當後端，做出像 Markdown editor 一樣輕的編輯器？**
>
> 比對基準：`libreoffice-26-2/`（分支 `libreoffice-26-2-5`，`co-26.04-branch-point-724`）對照 `libreoffice-25-2/`。

### 8.1 先講結論

1. **26-2 的 WASM 支援確實有進展，但幅度比想像中小** —— `static/` 只改了 5 個檔案、+454 行。
2. **「自己寫 JS 前端」是可行的，有三種架構，只有一種成熟。**
3. **前後端分離不會讓應用「變輕」，只會把重量搬到伺服器。** 這點必須先接受。
4. **體積要靠 configure 旗標與元件裁剪，跟前後端怎麼切完全無關。** 效益排序見 [8.6](#86-體積效益的實際排序)。
5. 曾評估「關掉 `.ui` 對話框資源」，**已否決** —— 理由記在 [8.5](#85-評估後否決關掉-ui-對話框資源)，避免日後重走。

### 8.2 26-2 的 WASM 進展

`static/` 目錄在 25-2 → 26-2 之間的全部變動：

```
static/CustomTarget_emscripten_fs_image.mk | 312 +++++++++++-
static/README.wasm.md                      |  48 ++--
static/config/wasm-accelerators.xcu        |  95 +++++++
static/emscripten/script.js                |  14 ++
static/source/embindmaker/embindmaker.cxx  |  26 +--
5 files changed, 454 insertions(+), 41 deletions(-)
```

#### 最有意義的變化：`--with-wasm-module`

25-2 的 `--with-main-module` 只能二選一；26-2 改名為 `--with-wasm-module` 並支援複選（`configure.ac:2266`）：

```sh
# 25-2
--with-main-module=writer|calc

# 26-2（預設值是 'calc writer'）
--with-wasm-module="writer calc impress"
```

而且它現在**直接驅動** strip 旗標（`configure.ac:4311-4342`）—— 先全部關掉，再按需要打開：

```sh
ENABLE_WASM_STRIP_ACCESSIBILITY=TRUE
ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS=TRUE
ENABLE_WASM_STRIP_CALC=TRUE
ENABLE_WASM_STRIP_WRITER=TRUE
for i in $with_wasm_module; do
    case "$i" in
    calc)    ENABLE_WASM_STRIP_ACCESSIBILITY=; ENABLE_WASM_STRIP_CALC= ;;
    writer)  ENABLE_WASM_STRIP_WRITER= ;;
    impress) ENABLE_WASM_STRIP_ACCESSIBILITY=
             ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS= ;;
    *)       AC_MSG_ERROR([Unknown --with-wasm-module "$i"])
    esac
done
if test "$ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS" = TRUE; then
    test_libcdr=no;  test_libetonyek=no;  test_libfreehand=no
    test_libmspub=no; test_libpagemaker=no; test_libqxp=no
    test_libvisio=no; test_libzmf=no
fi
```

> **注意最後那段** —— 就是[第 7 章第 3 階](#第-3-階砍冷門格式濾鏡)建議你手動加的 `test_lib*=no`，26-2 已經內建了。這印證了那個做法的方向正確，也代表**上游願意接受這類 patch**。

#### 仍未改變的限制

主開關的條件（`configure.ac:4306-4308`）跟 25-2 完全一樣：

```sh
if test "$cross_compiling" = "yes"; then
    if test "$enable_dynamic_loading" != yes -a "$enable_wasm_strip" = yes; then
        ENABLE_WASM_STRIP=TRUE
```

**原生 Linux 動態建置依然吃不到這組旗標。** [第 7 章第 6 階](#第-6-階建立你自己的-enable_lite_)的建議不變。

#### 官方對成熟度的自我評價

`static/README.wasm.md` 談 embind 的原文：

> *"Right now there's a very rough implementation in place. With lots of different bits unimplemented. And it **might be leaking memory**. i.e. Lots of room for improvement!"*

`configure.ac:2267` 的註解：

> *"Don't include impress by default. Debug builds become too large for Chromium with 'calc impress writer' enabled. (buffer source exceeds maximum size)"*

**三個模組一起編，Chromium 載不動。** 這是官方註解，不是推測。

#### 26-2 的其他相關變化

| 變化 | 說明 |
|---|---|
| `accessibility` 模組**消失** | 併入 `vcl`（commit `9283da858506` "a11y: Merge accessibility module into vcl"）。程式碼現在在 `vcl/source/accessibility/`。**模組數從 120 減少 1。** |
| 新增 `rust_uno/` | UNO 的 Rust 綁定（`rustmaker`、`Cargo.toml`）。與精簡無關，但顯示上游在擴展語言綁定。 |
| 新增 `README.yrs` | 用 Yjs CRDT（`y-crdt` 的 Rust 實作 yrs）做 Writer **註解**的即時協作。高度實驗性 —— 原文要求 `EDIT_COMMENT_IN_READONLY_MODE=1`、唯讀模式開檔、走硬編碼的 pipe，且「切到可編輯模式會必然崩潰」。相關程式碼在 `config_host/config_collab.h` 巨集後面。 |

### 8.3 「前後端分離」的三種架構

這是最容易混淆的地方。三種都叫「前後端分離」，但性質完全不同。

| | 架構 | core 跑在哪 | 前端能自己寫嗎 | 渲染怎麼來 | 成熟度 |
|---|---|---|---|---|---|
| **A** | LOK + JS 前端 | 伺服器（原生） | ✅ 完全可以 | core 渲染 tile，透過 WebSocket 送圖 | ✅ 成熟，Collabora 產品化多年 |
| **B** | WASM + Qt5 GUI | 瀏覽器 | ❌ UI 是 LibreOffice 的 | Qt5 編進 WASM 自己畫 | ⚠️ 可跑，但那就是 LibreOffice 的介面 |
| **C** | WASM headless + embind | 瀏覽器 | ✅ 可以 | **沒有現成路徑** | ❌ 官方標「very rough」 |

#### 架構 A：LOK + 自己的 JS 前端

這是 Collabora Online 的模式。LibreOffice 以原生二進位跑在伺服器，透過 LibreOfficeKit 把文件渲染成 **tile（圖磚）**，前端 JS 收圖片、送滑鼠/鍵盤事件回去。

- 前端可以完全自己寫，想多簡就多簡
- 相關設定見[第 3 章](#第-3-章旗標大全逐一解釋)的 `CPLinux-LOKit.conf`
- 核心 API 在 `include/LibreOfficeKit/`（244 種 `LOK_CALLBACK_*` 事件）

#### 架構 B：WASM + Qt5

`static/README.wasm.md` 的前半部講的就是這個。需要 Qt 5.15.2 + Emscripten 4.0.10，而且要用 allotropia 打過 patch 的 Qt fork（`github.com/allotropia/qt5`，分支 `5.15.2+wasm`）。

產出是 `qt_soffice.html`，跑起來就是 LibreOffice 的完整介面，只是在瀏覽器裡。**與「自製輕量前端」的目標無關。**

#### 架構 C：WASM headless + embind ← 使用者通常想要的

`README.wasm.md` 後半段「Building headless LibreOffice as WASM for use in another product」講的就是這個。設定範例（官方原文）：

```
--disable-debug
--enable-sal-log
--disable-crashdump
--host=wasm32-local-emscripten
--disable-gui
--with-wasm-module=writer
--with-package-format=emscripten
```

**embind 是什麼**：Emscripten 提供的 C++ ↔ JavaScript 綁定機制。LibreOffice 用 `static/source/embindmaker/embindmaker.cxx` 這支工具，從 UNO 的 IDL 定義自動產生綁定程式碼：

```make
# static/CustomTarget_unoembind.mk
embindmaker uno  bindings_uno.cxx  bindings_uno.hxx  bindings_uno.js \
    +$(udkapi) +$(offapi)
```

輸入是 `udkapi` + `offapi` —— **全樹共 4344 個 `.idl` 檔**，也就是整個 UNO API 面都會被綁定。

JS 側的膠水在 `static/emscripten/uno.js`（提供 `Module.uno_init`、`Module.unoObject`、例外轉換等）。官方使用範例：

```js
Module.uno_init.then(function() {
    const css = Module.uno.com.sun.star;
    let xModel = Module.getCurrentModelFromViewSh();
    const xTextDocument = css.text.XTextDocument.query(xModel);
    const xText = xTextDocument.getText();
    const xTextCursor = xText.createTextCursor();
    xTextCursor.setString("string here!");
});
```

> ⚠️ **記憶體要手動管理**。注意範例裡到處是 `.delete()` —— embind 沒有 GC 整合，每個 UNO 物件都要手動釋放。README 自承 *"it might be leaking memory"*。

> ⚠️ **架構 C 沒有渲染路徑。** README 的所有範例都是操作**文件模型**（插字、改段落顏色、列舉段落），沒有一個是把文件畫出來。你拿得到 model，但顯示要自己解決。Collabora 的 COWASM 是把 LOK 的 tile 渲染一起編進 WASM 才解決這件事 —— 那等於把架構 A 的後端整包搬進瀏覽器。

> ⚠️ 執行環境限制：因為用了 `-sPROXY_TO_PTHREAD`，LO 主執行緒在 **web worker** 裡。要在瀏覽器 console 測試上面的範例，必須切到第一個 worker 的 console，不是主頁面的。

### 8.4 輕量化：誠實的評估

**核心問題：前後端分離能讓應用變輕嗎？**

**不能。它只能搬動重量。**

| 架構 | 客戶端重量 | 總重量 |
|---|---|---|
| A（LOK + JS 前端） | 輕（數百 KB JS） | **不變** —— 後端仍是完整 LibreOffice，且每個編輯 session 要一個 process |
| C（WASM + JS 前端） | **更重** —— 使用者要下載 `.wasm` + `soffice.data` | 更重（WASM 通常大於原生二進位） |

**更根本的問題：LibreOffice 的「重」不在 UI，在 core 與資源。**

一個 ODF/OOXML 排版引擎本質上就是複雜的：

- Writer 的 layout engine（`sw/source/core/layout/`）
- 字型 shaping（HarfBuzz）、i18n 斷行（ICU）
- 幾十種格式濾鏡（見[第 3.3 節](#33-c-組檔案格式濾鏡--體積肥肉的所在)）
- 樣式模型、修訂記錄、欄位、表格、繪圖物件……

**這些沒有一項能靠「換掉 UI」減少。** 把前端換成自己的 JS，core 一克都沒輕。

#### 與 Markdown editor 的本質差異

Markdown editor 之所以精簡，**是因為 Markdown 的資料模型極簡**（段落、標題、清單、行內強調、程式碼區塊 —— 十幾種節點類型就結束），不是因為它前後端分離。

LibreOffice core 的價值恰恰是 **ODF/OOXML 的完整保真度**，而那個保真度就是體積的來源。這兩件事無法兼得。

> **決策點**：
> - **不需要 ODF/OOXML 保真度** → LibreOffice core 是錯的工具。用 ProseMirror / Tiptap / Lexical 之類的編輯器框架，體積差三個數量級。
> - **需要保真度** → 走架構 A，並接受「輕只發生在客戶端」。

### 8.5 評估後否決：關掉 `.ui` 對話框資源

> **結論：不值得做。** 這一節保留是為了避免日後重新發現同一個「機會」再走一次冤枉路。

#### 觀察到的現象（屬實）

`solenv/gbuild/UIConfig.mk` 裡完全沒有任何 `DISABLE_GUI` / `ENABLE_WASM_STRIP_*` / `gb_Helper_optional` 的 gating：

```sh
$ grep -n "DISABLE_GUI\|WASM_STRIP\|gb_Helper_optional" solenv/gbuild/UIConfig.mk
（無輸出）
```

意思是即使 `--disable-gui` 做 headless 建置，全樹 **1254 個 `.ui` 對話框定義檔**還是全部被打包。乍看是個沒人補的缺口。

#### 為什麼實際上不值得做

**理由一：省下的量太小。** 實測 1254 個 `.ui` 合計只有 **30.4 MB**（平均 24.8 KB/檔），而且是 XML，壓縮後大約只剩 5–8 MB。跟同樣會被打包、卻**有現成開關**的資源相比是小頭：

| 資源 | 體積 | 現成開關 |
|---|---|---|
| `icon-themes/`（全部） | 420 MB | `--with-theme=colibre` → 約 21 MB |
| `extras/source`（圖庫、範本） | 76 MB | `--with-galleries=no --without-templates` |
| **`.ui` 對話框定義** | **30 MB** | 無（但不值得補） |
| `i18npool/source/localedata` | 5 MB | 部分 |

**理由二：省不到程式碼。** `.ui` 只是資料檔，實作對話框的 C++ 一行都不會少：

| 部位 | 行數 | 關掉 `.ui` 後 |
|---|---|---|
| `cui` | 104,968 | 照編 |
| `sw/source/ui` | 83,197 | 照編 |
| `vcl/source/window`（含 `builder.cxx` 3,961 行） | 61,618 | 照編 |
| `vcl/source/control` | 39,015 | 照編 |
| `svx/source/dialog` | 38,308 | 照編 |
| `sfx2/source/dialog` | 21,530 | 照編 |

光「純對話框」的 `cui` + `svx/source/dialog` + `sfx2/source/dialog` 就約 **165,000 行**，全部留著。關掉資料檔而留著程式碼，執行期的結果通常是**崩潰**而不是變輕。

**理由三：程式碼砍不掉，耦合太深。** 實測耦合度：

```
引用 <vcl/weld.hxx> 的檔案數：      825
呼叫 SfxAbstractDialogFactory 的：   30
```

`SfxAbstractDialogFactory` 那 30 處是乾淨的接縫，可以切。但 `weld::` 這層抽象滲透到 825 個檔案，其中：

- `sfx2/source` 有 **83 個檔案**用 `weld::` —— 而 sfx2 是文件框架層，不可能不要
- `sw/source/core` 12 個、`sc/source/core` 4 個 —— **連排版核心都會彈對話框**（錯誤訊息、密碼提示、格式警告）

要真的砍掉，得把這些呼叫點逐一改成 callback 或失敗路徑。**這是數個月的工作量，換 5–8 MB。**

**理由四：做前後端分離反而更需要 `.ui`。** Collabora Online 的 jsdialog（`vcl/jsdialog/`，4,070 行；白名單在 `enabled.cxx`，634 行）正是**讀 `.ui` 序列化成 JSON** 送給瀏覽器。也就是說「自己寫 JS 前端」這件事本身，並不會讓你有資格砍 `.ui` —— 只有「連對話框功能都完全不要」才有資格，而那時你面對的是上面理由三的耦合問題。

#### 這一節的教訓

「找到一個沒人補的缺口」不等於「找到一個值得補的缺口」。判斷順序應該是**先量效益，再看難度**，而不是反過來。正確的優先順序見 [8.6](#86-體積效益的實際排序)。

### 8.6 體積效益的實際排序

> ⚠️ 以下排序依原始碼與資源體積推估，**不是實測二進位大小**（本研究未進行建置）。實際數字需要建置後量測。

| 順位 | 動作 | 為什麼 | 對應章節 |
|---|---|---|---|
| 1 | 移除 `--enable-symbols` | Collabora 開著是為了線上服務除錯；除錯符號可佔數 GB | [3.7](#37-g-組開發與除錯) |
| 2 | `--with-lang=en-US zh-TW` | 從 38 種語言降到 2 種 | [3.4](#34-d-組資源與語言) |
| 3 | `--with-theme=colibre` 只留一套 | 420 MB → 約 21 MB | [3.4](#34-d-組資源與語言) |
| 4 | 砍冷門格式濾鏡（`test_lib*=no`） | 26-2 已內建範本可抄 | [7.1 第 3 階](#第-3-階砍冷門格式濾鏡) |
| 5 | `--enable-mergelibs=more` | 連結期跨函式庫死碼消除 | [2.4](#24-額外一層mergelibs連結策略) |
| 6 | `--enable-lok-always-active` | 數千處 `if (isActive())` 的 else 分支被消掉 | [6.3](#63-唯一的-collabora-獨有精簡機制) |
| 7 | `native-code.py` 元件白名單 | 真正的元件級裁剪 | [第 5 章](#第-5-章native-codepy--元件白名單) |
| — | ~~關掉 `.ui`~~ | **否決** —— 30 MB 資料，程式碼一行不減 | [8.5](#85-評估後否決關掉-ui-對話框資源) |

**注意第 1 項。** Collabora 的 `CPLinux-LOKit.conf` 裡有 `--enable-symbols`，那是**產品需求**（線上服務崩潰要能分析 backtrace），不是精簡設定。直接照抄他們的設定檔會把這個一起抄進來 —— 這大概是最容易被忽略、效益卻最大的一項。

### 8.7 本章對路線圖的補充

在[第 7 章](#第-7-章蒸餾-lite-core-的建議路線)的階梯上，本章新增一項修訂：

| 階段 | 動作 | 風險 |
|---|---|---|
| **第 3 階（更新）** | 若基準改用 26-2，`test_lib*=no` 那批**已內建**於 `--with-wasm-module` 路徑，可直接參考 `configure.ac:4334-4341` 抄到原生建置 | 低 |

**架構選擇建議**：

- 做產品 → **架構 A**（LOK + 自製 JS 前端）。唯一成熟的路。
- 做研究 → 架構 C 可以玩，但不要排進產品時程。官方自評 rough、疑似漏記憶體、三模組 Chromium 載不動。

**但要清楚一件事**：選架構 A 不會讓總體積變輕（見 [8.4](#84-輕量化誠實的評估)）。體積要靠上面 [8.6](#86-體積效益的實際排序) 那七項，那跟前後端怎麼切是兩件獨立的事。

---

## 附錄 A：查證指令

以下指令在 `collabora-25.04/` 目錄執行，可重現本文的所有數字。

```sh
# 兩個 worktree 的關係
git worktree list

# 分歧點
MB=$(git merge-base distro/collabora/co-25.04 libreoffice-25-2)
git log --oneline -1 $MB

# 各自的 commit 數
git rev-list --count $MB..distro/collabora/co-25.04   # 3463
git rev-list --count $MB..libreoffice-25-2            #  621

# patch-id 比對（哪些 CO commit 已在 25-2）
git cherry libreoffice-25-2 distro/collabora/co-25.04 | grep -c '^-'   # 550
git cherry libreoffice-25-2 distro/collabora/co-25.04 | grep -c '^+'   # 2913

# 刪除/新增的檔案數（排除非程式碼目錄）
EXC=":(exclude)translations :(exclude)helpcontent2 :(exclude)extras :(exclude)dictionaries :(exclude)icon-themes"
git diff --diff-filter=D --name-only $MB..distro/collabora/co-25.04 -- . $EXC | wc -l   # 39
git diff --diff-filter=A --name-only $MB..distro/collabora/co-25.04 -- . $EXC | wc -l   # 951

# 各模組的新增檔案分布
git diff --diff-filter=A --name-only $MB..distro/collabora/co-25.04 -- . $EXC \
  | awk -F/ '{print $1}' | sort | uniq -c | sort -rn | head -20

# feature 巨集的覆蓋範圍
for m in HAVE_FEATURE_UI HAVE_FEATURE_SCRIPTING HAVE_FEATURE_DBCONNECTIVITY \
         HAVE_FEATURE_AVMEDIA HAVE_FEATURE_XMLHELP; do
  printf "%-35s %s\n" "$m" "$(grep -rl "$m" --include='*.cxx' --include='*.hxx' \
    --include='*.mk' --include='*.h' . | wc -l)"
done

# 有 gating 的模組
grep -oE 'gb_Helper_optional,[A-Z0-9_]+' RepositoryModule_host.mk | sort -u

# 所有 WASM strip 旗標
grep -rhoE 'ENABLE_WASM_STRIP_[A-Z_0-9]+' . --include='*.mk' --include='*.ac' \
  --include='*.cxx' --include='*.hxx' | sort -u

# 某個 strip 旗標實際落在哪些檔案
grep -rl "ENABLE_WASM_STRIP_ACCESSIBILITY" --include='*.mk' --include='*.cxx' \
  --include='*.hxx' . | grep -v workdir

# 查任何 configure 旗標的官方說明
grep -A5 'AS_HELP_STRING(\[--disable-gui' configure.ac

# 某個外部濾鏡函式庫有沒有關閉開關
grep -n "libo_CHECK_SYSTEM_MODULE(\[libwpd\]" configure.ac   # 宣告處
grep -c "^ *test_libwpd=" configure.ac                       # 0 = 沒有關閉開關
# 巨集如何讀 test_* 變數
grep -n "test_\$1" m4/libo_externals.m4

# 列出所有可用旗標
./autogen.sh --help    # 或 ./configure --help
```

### 第 8 章（WASM / 前後端分離）相關

在 `libreoffice-26-2/` 目錄執行：

```sh
# static/ 在兩版之間改了什麼
git diff --stat libreoffice-25-2..libreoffice-26-2-5 -- static/

# --with-wasm-module 的完整邏輯
sed -n '4306,4350p' configure.ac

# WASM strip 主開關的條件（確認仍限 cross-compile）
grep -n "ENABLE_WASM_STRIP=TRUE" -B4 configure.ac

# WASM 檔案系統映像裡各類資源的數量
grep -oE '/[a-z_]+\.(ui|xcd|rdb|png|svg)' static/CustomTarget_emscripten_fs_image.mk \
  | awk -F. '{print $NF}' | sort | uniq -c | sort -rn
#   1028 ui / 13 xcd / 3 svg / 2 rdb / 1 png

# .ui 檔的數量與實際體積（見 8.5：評估後否決）
find . -name '*.ui' -path '*/uiconfig/*' -printf '%s\n' \
  | awk '{s+=$1;n++} END{printf "%d 檔, %.1f MB\n", n, s/1048576}'   # 1254 檔, 30.4 MB

# UIConfig.mk 沒有任何 gating（無輸出）— 屬實，但不值得補
grep -n "DISABLE_GUI\|WASM_STRIP\|gb_Helper_optional" solenv/gbuild/UIConfig.mk

# 對話框耦合度（為什麼砍不掉）
grep -rl '#include <vcl/weld.hxx>' --include='*.cxx' --include='*.hxx' . | wc -l  # 825
grep -rl 'SfxAbstractDialogFactory' --include='*.cxx' . | wc -l                   # 30
grep -rl 'weld::' sfx2/source --include='*.cxx' | wc -l                           # 83

# 資源體積對照（為什麼 .ui 是小頭）
du -sm icon-themes extras/source i18npool/source/localedata

# embind 綁定的 UNO API 規模
find offapi udkapi -name '*.idl' | wc -l                  # 4344

# embind 產生器的呼叫方式 / JS 側膠水
cat static/CustomTarget_unoembind.mk
cat static/emscripten/uno.js

# accessibility 模組去哪了
git log --oneline -1 -- accessibility                      # 9283da858506
```

---

## 附錄 B：名詞對照

| 名詞 | 說明 |
|---|---|
| **core** | LibreOffice 的主 repository（`LibreOffice/core.git`），約 120 個模組、數百萬行 C++。 |
| **gbuild** | LibreOffice 自製的 GNU Make 建置框架，位於 `solenv/gbuild/`。取代一般專案的 CMake。 |
| **Module** | gbuild 的概念，對應一個頂層目錄（`sw`、`sc`、`vcl`）。清單在 `RepositoryModule_host.mk`。 |
| **Library** | gbuild 的概念，對應一個 `.so`/`.dll`。清單在 `Repository.mk`。 |
| **UNO** | Universal Network Objects，LibreOffice 的元件物件模型（類似 COM）。所有功能都以 UNO 元件形式組裝。 |
| **UNO component** | 一個實作了某些 UNO 介面的模組，執行期用名字查表取得。 |
| **services.rdb** | UNO 元件的註冊表（XML）。決定執行期有哪些元件可用。 |
| **LOK / LibreOfficeKit** | LibreOffice 的嵌入 API（`include/LibreOfficeKit/`）。讓外部程式把 LibreOffice 當函式庫用 —— 載入文件、渲染圖磚、送滑鼠/鍵盤事件。Collabora Online 的基礎。 |
| **tile / 圖磚** | LOK 的渲染單位。文件被切成固定大小的方塊分別渲染，瀏覽器端拼起來。 |
| **jsdialog** | 把 LibreOffice 原生對話框（`.ui` 檔）序列化成 JSON 送給瀏覽器渲染的機制。位於 `vcl/jsdialog/`，**上游與 Collabora 都有**。 |
| **VCL** | Visual Class Library，LibreOffice 的跨平台 GUI 與繪圖抽象層（`vcl/` 模組）。 |
| **headless** | 沒有圖形介面的執行模式。VCL 的 headless 後端用 Cairo 畫到記憶體 bitmap。 |
| **mergelibs** | 把多個小函式庫合併成單一 `libmerged.so` 的建置策略。 |
| **distro-config** | `distro-configs/*.conf`，預先寫好的 configure 參數組合。用 `--with-distro=NAME` 套用。 |
| **cherry-pick** | 把某個 commit 的變更套用到另一個分支。Collabora 用它把上游 master 的修正回填到 25.04 分支。 |
| **merge-base** | 兩個分支的最近共同祖先 commit。 |
| **patch-id** | commit 內容的雜湊（不含 metadata）。用來判斷兩個 hash 不同的 commit 是否其實是同一個修改。 |
| **Gerrit** | LibreOffice 的 code review 系統（`gerrit.libreoffice.org`）。GitHub 上的 repo 只是唯讀鏡像。 |
| **WASM / Emscripten** | 把 C++ 編譯成 WebAssembly 在瀏覽器執行的技術。`ENABLE_WASM_STRIP_*` 那組旗標為此而生。 |
| **DCE / dead code elimination** | 編譯器移除永遠不會執行到的程式碼。`--enable-lok-always-active` 就是為了觸發它。 |
| **LTO** | Link-Time Optimization，連結期跨編譯單元最佳化。體積與效能有益，但建置成本高。 |
| **embind** | Emscripten 提供的 C++ ↔ JavaScript 綁定機制。LibreOffice 用它把 UNO API 暴露給瀏覽器裡的 JS。**沒有 GC 整合，物件要手動 `.delete()`。** |
| **embindmaker** | `static/source/embindmaker/`，從 UNO IDL 自動產生 embind 綁定的工具。輸入是 `udkapi` + `offapi`（共 4344 個 `.idl`）。 |
| **`.ui` 檔** | GTK Builder 格式的對話框定義（XML），放在各模組的 `uiconfig/` 下。全樹 1254 個、合計 30.4 MB。VCL 讀它建出對話框；jsdialog 讀它序列化成 JSON。 |
| **UIConfig.mk** | `solenv/gbuild/UIConfig.mk`，負責把 `.ui` 檔打包進安裝目錄。目前沒有條件開關 —— 但[評估後認為不值得補](#85-評估後否決關掉-ui-對話框資源)。 |
| **weld::** | VCL 的現代對話框抽象層（`include/vcl/weld.hxx`），把原生 widget 包成與後端無關的介面。**全樹 825 個檔案引用**，是對話框程式碼難以移除的主因。 |
| **soffice.data** | WASM 建置產生的「記憶體檔案系統映像」，內含執行期需要的所有資源檔（`.ui`、`.xcd`、`.rdb` 等）。清單定義在 `static/CustomTarget_emscripten_fs_image.mk`。 |
| **CRDT / Yrs** | Conflict-free Replicated Data Type，讓多人同時編輯不需中央仲裁的資料結構。Yrs 是 Yjs 的 Rust 實作。26-2 用它做 Writer 註解的實驗性協作（`README.yrs`）。 |
| **PROXY_TO_PTHREAD** | Emscripten 選項，把程式主執行緒移到 web worker（而非瀏覽器主執行緒）。LibreOffice WASM 有用，所以在瀏覽器 console 測試要切到 worker 的 console。 |
