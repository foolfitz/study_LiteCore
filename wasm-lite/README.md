# LibreOffice 26.8 WASM Lite Core — 建置規劃

目標：把 `libreoffice-26-8/` 編成一個**只有 Writer、用 LibreOffice 自己的 Qt5 UI、跑在瀏覽器裡**的精簡 WASM 核心。

> 基準分支從 26-2 改成 26-8，理由見 [§5.5](#55-為什麼用-26-8-而不是-26-2)。

> ## ⚠️ 這份文件有三節已被實測推翻（2026-07-31）
>
> 這是**建置前**寫的規劃。實際編出來、跑起來、除完錯之後，其中三節已知有誤：
>
> | 節 | 問題 |
> |---|---|
> | [§3.5](#35-體積--除錯) | `--disable-symbols` 標成「效益第一名」，**實際上它會讓程式啟動即死** |
> | [§3.6](#36-拿掉用不到的東西) | 那批旗標**幾乎全是白工**，Emscripten 上本來就預設關閉 |
> | [§5.4](#54-為什麼不用-qt6雖然官方策略指向-qt6) | Qt5/Qt6 的權衡前提已不成立 —— Qt5 完全無法輸入中文 |
>
> **請以 [`../DEVLOG-2026-07-31-wasm.md`](../devlog/DEVLOG-2026-07-31-wasm.md) 為準。**
> 這三節之所以還沒改寫，是因為 §5.4 怎麼寫取決於 Qt5/Qt6 路線的決策，而那還沒做。

對應腳本：[`build-wasm-lite.sh`](build-wasm-lite.sh)
背景研究：[`../litecore-analysis.md`](../litecore-analysis.md)

---

## 目錄

- [0. 你的四個要求，實際落地情況](#0-你的四個要求實際落地情況)
- [1. 這條路線是什麼](#1-這條路線是什麼)
- [2. 精簡從哪裡來](#2-精簡從哪裡來)
- [3. 完整旗標清單與理由](#3-完整旗標清單與理由)
- [4. 三個必要的原始碼修改](#4-三個必要的原始碼修改)
- [5. 前置條件](#5-前置條件)
- [6. 怎麼跑](#6-怎麼跑)
- [7. 時間、空間、風險](#7-時間空間風險)
- [8. 還可以再砍的（本次沒做）](#8-還可以再砍的本次沒做)

---

## 0. 你的四個要求，實際落地情況

| 你的要求 | 狀態 | 說明 |
|---|---|---|
| `--enable-noto-font` | ⚠️ **這個旗標在上游不存在** | 它是 **Collabora 專屬**的。上游 26-8 沒有 `AC_ARG_ENABLE(noto-font)`，Noto 系列由 `--with-fonts`（預設開）無條件安裝。腳本改用 `--with-fonts`，**結果相同甚至更完整**。詳見 [3.4](#34-字型) |
| `--enable-lto` | ❌ **實際上從未跑過** | 腳本支援（探針 + `gb_LTOPLUGINFLAGS=` 繞過），但**實際建置時因為當時 swap 不足而用 `LITE_LTO=0` 跑**，所以 LTO 至今未經驗證。而且 emscripten#13665 指出 wasm 例外處理在 LTO 下會失效 —— 若 [001](../findings/001-wasm-configmgrwriter-crash.md) 的機制假設成立，LTO 很可能是同一類地雷。（swap 現在有 64 GB 了，可以重試。）詳見 [7.3](#73-lto-的兩個真實風險) |
| 語言：英文 + 繁中 | ✅ 有做，但**需要改一個檔案** | `--with-lang="en-US zh-TW"` 只負責「編出來」。WASM 的 `soffice.data` 檔案清單是**寫死 en-US 的**，不改就打包不進去。詳見 [4.1](#41-讓-sofficedata-收錄-zh-tw-語言包) |
| 只要 Writer | ✅ 有做 | `--with-wasm-module=writer`。預設值其實是 `'calc writer'`，所以這一項真的有省到 |

還有一件你沒問但會踩到的事：

> ⚠️ **上游 LibreOffice 沒有內建任何 CJK 字型。**
>
> `external/more_fonts/` 有 30 幾套字型，一套中日韓都沒有。WASM 的檔案系統是封閉的，抓不到系統字型。所以**不額外塞字型的話，繁中介面與繁中文件會整片豆腐字（□□□）**。腳本會處理，詳見 [4.2](#42-塞一套-cjk-字型進去)。

---

## 1. 這條路線是什麼

`static/README.wasm.md` 講了 WASM 有兩條路：

| | 路線 A：Qt5 GUI | 路線 B：headless + 自製前端 |
|---|---|---|
| UI | LibreOffice 自己的（VCL → Qt5 → canvas） | 你自己寫 JS |
| 成熟度 | LO 的原始 WASM 移植目標，一直有人維護 | 官方自評 "very rough"、"might be leaking memory" |
| 你選的 | ✅ **這條** | ❌（你說來不及做） |

選 A 是對的。B 目前沒有渲染路徑，embind 綁定也還在很早期，不是趕時間該碰的東西。

代價：**必須先有一份為 wasm 編好的 Qt5**。這是整條路上最大的前置成本（約 1 小時無人值守編譯），腳本會處理。

---

## 2. 精簡從哪裡來

四層，由粗到細：

### 第 1 層：`--enable-wasm-strip`（自動開啟，最大的一刀）

`configure.ac:1280` — 只要 `--host=wasm32-local-emscripten`，這個就自動是 `yes`。它一口氣關掉：

```
avmedia  libcmis  coinmp  cups  database_connectivity  dbus  dconf
dynamic_loading  extensions(×3)  gio  gpgmepp  ldap  lotuswordpro
lpsolve  nss  odk  online_update  opencl  pdfimport  randr
report_builder  scripting  sdremote(×2)  skia  xmlhelp  zxing
galleries  templates  X11
```

並定義 8 個 `ENABLE_WASM_STRIP_*` 巨集（ACCESSIBILITY / EXTRA / PINGUSER / PREMULTIPLY / RECENT / RECOVERYUI / SPLASH）。

**這一層你什麼都不用做，選了 WASM 就送你。**

### 第 2 層：`--with-wasm-module=writer`（你要的那一刀）

預設是 `'calc writer'`（`configure.ac:2317`）。改成 `writer` 之後：

| 變數 | 值 | 效果 |
|---|---|---|
| `ENABLE_WASM_STRIP_WRITER` | 空 | 保留 Writer |
| `ENABLE_WASM_STRIP_CALC` | `TRUE` | **砍掉 sc、scfilt、Calc 的 .ui 與 .xcu** |
| `ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS` | `TRUE` | 砍掉 basic、sd、starmath、draw |
| `ENABLE_WASM_STRIP_ACCESSIBILITY` | `TRUE` | 砍掉無障礙層（選 calc 或 impress 會把這個關掉，選 writer 不會） |

順帶把 8 個外部圖形匯入庫關掉：`libcdr` `libetonyek` `libfreehand` `libmspub` `libpagemaker` `libqxp` `libvisio` `libzmf`。

### 第 3 層：手動旗標

見 [第 3 節](#3-完整旗標清單與理由)。~~重點是 `--disable-symbols`（體積殺手第一名）。~~

> ⚠️ **已過時**：`--disable-symbols` 會讓程式啟動即死，見 [§3.5](#35-體積--除錯) 的警告。
> 而且這一層的多數旗標其實沒有效果，見 [§3.6](#36-拿掉用不到的東西)。
> **體積的真正槓桿是字型（佔 `soffice.data` 的 71.7%），這一層反而是最不重要的。**

### 第 4 層：`soffice.data` 檔案清單

`static/CustomTarget_emscripten_fs_image.mk`（1833 行）逐檔列出要打包進虛擬檔案系統的東西，已經按 `ENABLE_WASM_STRIP_*` 分區塊 gate 好了。**這一層不用你動**——除了語言與字型那兩處（[第 4 節](#4-三個必要的原始碼修改)）。

---

## 3. 完整旗標清單與理由

### 3.1 平台骨幹（來自 `distro-configs/LibreOfficeWASM32.conf`）

```
--host=wasm32-local-emscripten     # 決定一切。觸發第 1 層自動精簡
--enable-qt5                       # LibreOffice 自己的 UI（你要的）
--disable-gen                      # 砍掉 X11 fallback VCL backend
--disable-scripting                # Basic/腳本引擎（wasm-strip 也會關，明寫較清楚）
--with-package-format=emscripten   # 產出 workdir/installation/LibreOffice/emscripten/
```

### 3.2 模組範圍

```
--with-wasm-module=writer          # ★ 只要 Writer（預設是 calc writer）
```

### 3.3 語言

```
--with-lang=en-US zh-TW
```

會讓 configure 把 `translations` 列進 `GIT_NEEDED_SUBMODULES`，並要求 `msgfmt` / `msguniq`（gettext）。腳本會自動 init submodule。

### 3.4 字型

```
--with-fonts                       # 預設就是 yes，明寫以免誤解
```

`configure.ac:14620` → `WITH_FONTS=TRUE` → `BUILD_TYPE += MORE_FONTS` → `external/more_fonts/Module_more_fonts.mk` 安裝 30 幾套字型，其中 **Noto 佔 14 套**：

```
noto_kufi_arabic  noto_naskh_arabic  noto_sans  noto_sans_arabic
noto_sans_armenian  noto_sans_georgian  noto_sans_hebrew
noto_sans_lao  noto_sans_lisu  noto_serif  noto_serif_armenian
noto_serif_georgian  noto_serif_hebrew  noto_serif_lao
```

fs image 那邊 `ifeq ($(WITH_FONTS),TRUE)` 就會把 `ooo_fonts` 整包塞進 `soffice.data`。

> **這就是為什麼上游沒有 `--enable-noto-font`**：Collabora 加那個旗標是為了讓自己能**多裝**一批額外 Noto；上游是全部都裝。你要的效果（有 Noto）預設就成立。

### 3.5 體積 / 除錯

> ## ⚠️ 已過時 —— `--disable-symbols` 不能用
>
> 實測結果：**帶 `--disable-symbols` 的 WASM 建置啟動即死**，`configmgrWriter` 執行緒
> 逸出未捕捉的 `RuntimeException`，整個 app 停在白畫面。已用五個 build 隔離到這個單一變因。
>
> 詳見 [`../findings/001-wasm-configmgrwriter-crash.md`](../findings/001-wasm-configmgrwriter-crash.md)。
>
> **目前唯一可用的替代**：`--enable-symbols=Executable_soffice_bin`
> （只有最終可執行檔帶符號，其餘照舊；代價是 `soffice.wasm` 從 125 MB 變 183 MB）。
> 但這會踩到 [`004`](../findings/004-emscripten-install-partial-symbols.md) ——
> 打包步驟會失敗，產物本身沒問題，直接從 `instdir/program/` 跑即可。
>
> 下面這段「效益第一名」的說法**請忽略**。

```
--enable-release-build
--disable-debug
--disable-dbgutil
--disable-symbols                  # ★ 效益第一名
--disable-sal-log
--disable-assert-always-abort
--disable-crashdump
--disable-breakpad
--disable-pch                      # ★ 不加會 configure 失敗，見下
```

> ⚠️ `--disable-pch` **不是可選的**。`configure.ac:6832`：
> ```
> if test "$enable_pch" != no -a "$_os" = Emscripten; then
>     AC_MSG_ERROR([PCH currently isn't supported for Emscripten ...])
> ```
> 因為 native EH（`-fwasm-exceptions`）下 clang 缺 Sj/Lj 支援。

`--disable-symbols` 為什麼是第一名：symbols 開著時 `emscripten-install` 還會多複製 `soffice.wasm.debug.wasm` 與 `.dwp` 兩個檔（`instsetoo_native/CustomTarget_emscripten-install.mk:23-24`），而且 `configure.ac:5397` 明講「full symbols 且記憶體 < 16GB 不支援」。

### 3.6 拿掉用不到的東西

> ## ⚠️ 已過時 —— 這批旗標幾乎沒有效果
>
> 事後比對 lite build 與上游預設 build 的 `config_host.mk`，**下面這批旗標對結果毫無影響** ——
> 它們在 Emscripten 上本來就是預設關閉的（`--enable-wasm-strip` 會自動處理，見 §2 第 1 層）。
>
> 真正產生差異的只有四個變數：`ENABLE_SYMBOLS_FOR`、`ENABLE_WASM_STRIP_CALC`、
> `ENABLE_WASM_STRIP_ACCESSIBILITY`、`ENABLE_RELEASE_BUILD`。
>
> 留著它們不會壞事（只是冗長），但**別以為是靠它們瘦下來的**。
> 體積的真正槓桿是字型 —— 佔 `soffice.data` 的 **71.7%**，見 DEVLOG。

```
--without-help                     # 說明檔（helpcontent2 submodule，很大）
--without-helppack-integration
--without-myspell-dicts            # ★ 見下
--without-java
--without-doxygen
--without-export-validation
--disable-python
--disable-cve-tests
--disable-odk
--disable-online-update
--disable-firebird-sdbc
--disable-postgresql-sdbc
--with-theme=colibre               # emscripten 預設值，明寫
```

> `--without-myspell-dicts` 的理由不是「不想要拼字檢查」，而是**字典根本沒被打包進 `soffice.data`**——fs image 的清單裡沒有 `dictionaries`，`ooo_fonts` 是唯一被 autoinstall 進去的包。所以編字典＝純浪費時間，還多一個 submodule 要抓。
>
> （hunspell 本身還是有編進去的：`ENABLE_WASM_STRIP_HUNSPELL` 在 `configure.ac:3501` 是被註解掉的。）

### 3.7 建置速度

```
--enable-ccache
--with-build-platform-configure-options=--enable-ccache
```

第二行很重要：cross build 會**先編一份 native 的 build-side 工具鏈**（idlc、cppumaker⋯），那一份是獨立 configure 的，不傳這個就沒有 ccache。

---

## 4. 三個必要的原始碼修改

腳本的 `patch` 子命令會做，`unpatch` 可還原（就是 `git checkout --`）。

### 4.1 讓 `soffice.data` 收錄 zh-TW 語言包

`static/CustomTarget_emscripten_fs_image.mk` 第 1685、1688、1689 行把語言**寫死成 en-US**：

```make
$(INSTROOT)/$(LIBO_SHARE_FOLDER)/registry/Langpack-en-US.xcd \
$(INSTROOT)/$(LIBO_SHARE_FOLDER)/registry/res/fcfg_langpack_en-US.xcd \
$(INSTROOT)/$(LIBO_SHARE_FOLDER)/registry/res/registry_en-US.xcd \
```

改成用 gbuild 既有的語言變數：

```make
$(foreach lang,$(gb_Configuration_LANGS),$(INSTROOT)/.../Langpack-$(lang).xcd) \
$(foreach lang,$(gb_Configuration_LANGS),$(INSTROOT)/.../res/fcfg_langpack_$(lang).xcd) \
$(foreach lang,$(gb_Configuration_LANGS),$(INSTROOT)/.../res/registry_$(lang).xcd) \
```

`gb_Configuration_LANGS`（`solenv/gbuild/Configuration.mk:64`）＝ `en-US` + 你 `--with-lang` 指定的其他語言。這正是 `postprocess/Package_registry.mk` 拿來裝進 instdir 用的同一個變數，所以檔案保證存在、名字保證對得上。

**不改的話**：zh-TW 的 .xcd 會被編出來、會被裝進 `instdir/`，然後**不會進 `soffice.data`**，瀏覽器裡永遠只有英文。

### 4.2 塞一套 CJK 字型進去

同一個檔案末尾加一段：

```make
ifneq ($(LITE_EXTRA_FONTS_DIR),)
lite_extra_font_names := $(notdir $(wildcard $(LITE_EXTRA_FONTS_DIR)/*.tt[fc]) ...)
gb_emscripten_fs_image_files += $(foreach f,$(lite_extra_font_names),$(INSTROOT)/.../fonts/truetype/$(f))
# ...外加一條把檔案 cp 進 instdir 的規則
endif
```

字型來源優先序（腳本 `fonts` 子命令）：

1. 你用 `LITE_CJK_FONT_FILES=/path/a.otf:/path/b.otf` 指定的
2. 系統既有的 `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`（你這台有，19.5 MB）
3. 從 GitHub `notofonts/noto-cjk` releases 下載 TC 專用 OTF（約 9 MB，比 TTC 小一半，因為不含 JP/KR/SC）

> 體積提醒：TTC 那份 19.5 MB 會**原封不動**進 `soffice.data`（file_packager 不壓縮）。真正在乎大小的話用第 3 種，或用 `pyftsubset` 依常用字表子集化到 3–5 MB。README 末段有指令。

### 4.3 （非修改）`translations` submodule

`libreoffice-26-8/` 的三個 submodule 都還沒 init（`git submodule status` 前面都是 `-`）。`--with-lang` 非 en-US 時 `Makefile.in:271` 會擋下來。腳本會 `git submodule update --init --depth 1 translations`。

`dictionaries` 與 `helpcontent2` 因為 [3.6](#36-拿掉用不到的東西) 的旗標而不需要。

---

## 5. 前置條件

### 5.1 host 套件（Debian/Ubuntu）

```bash
sudo apt install build-essential git ccache autoconf automake libtool \
  pkg-config flex bison gperf gettext python3 python3-dev zip unzip \
  nasm libxml2-utils xsltproc perl
```

### 5.2 Emscripten SDK

`README.wasm.md` 指定 **4.0.10**；`configure.ac:1525-1527` 的最低要求是 3.1.46。腳本裝 4.0.10。

### 5.3 Qt 5.15.2+wasm

**必須用 allotropia 的 fork**（`https://github.com/allotropia/qt5.git`，branch `5.15.2+wasm`）。上游 Qt 5.15 LTS 不公開維護，WASM 的重大 bug 修正都在這個 fork 裡 cherry-pick。

configure 參數（照 `README.wasm.md`）：

```
-opensource -confirm-license -xplatform wasm-emscripten -feature-thread
QMAKE_CFLAGS+=-sSUPPORT_LONGJMP=wasm QMAKE_CXXFLAGS+=-sSUPPORT_LONGJMP=wasm
```

> **不要**加 `-fwasm-exceptions` 到 Qt 的 `QMAKE_CXXFLAGS`。README 明講會跟 `simulate_infinite_loop` 衝突。

### 5.4 為什麼不用 Qt6（雖然官方策略指向 Qt6）

> ## ⚠️ 已過時 —— 結論的前提已不成立
>
> 本節的結論（「走 Qt5」）建立在一個假設上：兩條路線功能等價，差別只有風險與成本。
>
> **那個假設是錯的。** 實測發現 **Qt5 的 WASM 版本完全無法使用輸入法** ——
> Qt 5.15 的 wasm platform plugin 沒有 input context 實作，只註冊了原始的
> `keydown`/`keyup`，不監聽 composition 事件。fcitx 打中文一個字都進不去。
> 而 Qt6 的 wasm plugin 有 `qwasminputcontext.cpp`，設計上有解。
>
> 詳見 [`../findings/005-qt5-wasm-no-input-context.md`](../findings/005-qt5-wasm-no-input-context.md)。
>
> 對繁中編輯器來說這是硬性阻斷，其他優化都沒有意義。
> **Qt6 因此從「風險太高不值得賭」變成「唯一可能的選項」**，儘管它那條路
> 已經 18 個月沒人維護。
>
> 下面對 Qt6 現況的技術盤點（管線停更、預設模式壞掉、必須自編 Qt、sed 脆弱⋯）
> **仍然全部有效且已查證**，只是「所以選 Qt5」那個結論不再成立。
>
> 路線決策尚未做出，見 DEVLOG 待辦第 1 項。

這節有點反直覺，所以講清楚。

**TDF 官方的方向確實是 Qt6 + WASM。** 2026-05-27 的[新網頁與行動策略](https://blog.documentfoundation.org/blog/2026/05/27/new-web-and-mobile-strategy-for-libreoffice/)把「enhancing and polishing our functional prototype based on **Qt 6 and WebAssembly**」列為 2026 年目標之一。背景是 TDF 決定重啟停擺的 LibreOffice Online，Collabora（Michael Meeks 同時是 TDF 董事）公開反對，隨後 TDF 會員委員會投票移除所有 Collabora 員工與夥伴的會員資格。TDF 現在要走一條不經過 Collabora Online 的路，那條路就是 Qt6 + WASM。

**但那個未來還沒抵達可用狀態。** 用 git 歷史查證：

| 事實 | 證據 |
|---|---|
| Emscripten+Qt6 的專屬管線最後一次更新是 2025-02-11 | JSPI / proxy-to-pthread ersatz / qtloader sed 三處，至今無新 commit |
| Qt6 的**預設模式是壞的** | `--enable-emscripten-proxy-to-pthread` 預設 `yes`，但 commit `364508802571` 自陳 Qt6 要支援它需要「excessive and unrealistic」的 Qt hack |
| 唯一可行的 Qt6 模式仍是實驗性 | 同一 commit：`--enable-qt6 --enable-emscripten-jspi --disable-emscripten-proxy-to-pthread`，且「known to occasionally hang and crash」 |
| Qt6 **不能**用預編 binary | JSPI 需要 `-feature-wasm-jspi -feature-wasm-exceptions`，Qt 官方文件明講必須從原始碼建置。所以 Qt6 不但沒省那一小時，還要編到 6.10+ |
| 沒有文件 | `static/README.wasm.md` 從頭到尾沒有一行講 Qt6 怎麼建 |
| configure 對 Qt6 的檢查較鬆 | Qt5 會撈 `libQt5Gui.a` 的 `emscripten_longjmp` 符號擋掉錯誤的 Qt（`configure.ac:14145`）；Qt6 那段（`14294-14300`）只檢查檔案存在，錯了會拖到 link 才炸 |
| `qt_soffice.html` 綁死 Qt 版本 | `solenv/gbuild/platform/unxgcc.mk:190` 用一行 `sed -z` 改 Qt 的 `wasm_shell.html`，依賴 `@APPNAME@` / `@APPEXPORTNAME@` / `@PRELOAD@`（Qt 6.6 才有）與結尾 `});`。Qt 改樣板它會**靜默失效**，不報錯 |

唯一的利多是瀏覽器端：JSPI 從 **Chrome 137 / Firefox 139 起已預設開啟**，2025-04 由 W3C WebAssembly CG 完成標準化。Bergmann 當年測試時它還躲在 `chrome://flags` 後面。阻塞理由消失了一年多，但 LO 這邊沒人跟進。

**結論**：Qt6 缺的是文件與驗證，不是工時 —— 這跟你有多少時間無關。腳本走 Qt5；想試 Qt6 就設 `LITE_QT=6` 並自備 `QT6DIR`。26.8 正式版落地後值得重新評估一次。

### 5.5 為什麼用 26-8 而不是 26-2

原本的規劃基準是 26-2。改成 26-8 的理由是**原生 Qt 對話框的覆蓋率**（`tdf#130857`，Michael Weghorn 主導，該人正是 TDF 策略文件點名的網頁/行動開發成員之一）：

```
                        26-2      26-8      master
原生 Qt 對話框 (.ui)      221       463        582
```

以 `vcl/qt5/QtInstanceBuilder.cxx` 的白名單行數計。這條線總共 1460 個 commit，最近 12 個月 784 個，幾乎全部出自同一人。它把對話框從 VCL 自繪換成原生 Qt widget，是「讓 LO 能在 Qt6 上跑行動裝置與瀏覽器」的前置工程 —— 也就是 TDF 策略的本體。26-8 拿到 master 的 80%，而且是一條正在收斂的分支。

第二個理由是 26-8 多了 **7 筆純 WASM build fix**（2026-02 ~ 2026-06，Xisco Fauli / Julien Nabet / Stephan Bergmann）。其中 Julien 那筆標題裡的「WASM TB」是 tinderbox —— 有機器在自動編 WASM、有人在追紅燈。這些修的是 26-2 切出去（2025-12-03）之後 master 上新長出來的破口，**不代表 26-2 編不起來**，但代表 26-8 的 WASM build 這半年有人證明過，26-2 的沒有。

分支時程：

```
切出點        2026-06-16   （= beta1 tag）
RC1           2026-07-13   libreoffice-26.8.0.1
QA 徵求測試    2026-07-22
正式版         2026 年 8 月底
```

**前置需求完全相同** —— 兩條分支的 `README.wasm.md` 都是 Qt 5.15.2 + emsdk 4.0.10，§4 的兩個原始碼修改也原封不動適用（patch 是內容比對不是行號比對；四個錨點在 26-8 各出現一次，已實測）。所以換分支不需要重做任何前置作業。

要退回 26-2：

```bash
LO_SRC=/home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-2 ./build-wasm-lite.sh doctor
```

> 若之後要送 patch 上游，注意 LibreOffice 的規矩是**一律先進 master、再 backport**。26-8 適合當「跑起來 + 報 bug」的基地，改東西最後仍需要一份 master worktree。

---

## 6. 怎麼跑

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm-lite

./build-wasm-lite.sh doctor      # 檢查環境，不改任何東西 ← 先跑這個
./build-wasm-lite.sh all         # 全自動：emsdk → qt5 → submodule → 字型 → patch → configure → build
```

或分階段（建議第一次這樣，比較好抓問題）：

```bash
./build-wasm-lite.sh emsdk       # ~10 分鐘
./build-wasm-lite.sh qt5         # ~60 分鐘（無人值守）
./build-wasm-lite.sh submodules  # ~5 分鐘
./build-wasm-lite.sh fonts       # ~1 分鐘
./build-wasm-lite.sh patch       # 秒
./build-wasm-lite.sh configure   # ~10 分鐘
./build-wasm-lite.sh build       # ~4-8 小時
./build-wasm-lite.sh report      # 印出各檔案大小
./build-wasm-lite.sh serve       # emrun 起本機伺服器
```

常用環境變數：

| 變數 | 預設 | 用途 |
|---|---|---|
| `LITE_LTO` | `1` | 設 `0` 關掉 LTO |
| `LITE_JOBS` | `nproc` | 平行度 |
| `LITE_LANGS` | `en-US zh-TW` | 語言 |
| `LITE_BUILDDIR` | `wasm-lite/build` | out-of-tree 建置目錄（保持 git worktree 乾淨） |
| `LITE_CJK_FONT_FILES` | 自動偵測 | 冒號分隔的字型路徑 |
| `LITE_QT` | `5` | `6` 則改用 `QT6DIR` |

建置是 **out-of-tree** 的（`$LITE_BUILDDIR`），只有 [4.1/4.2](#4-三個必要的原始碼修改) 那一個檔案會動到原始碼樹。

---

## 7. 時間、空間、風險

### 7.1 這台機器

```
CPU     12 核
RAM     30 GB          ← 見 7.3
Disk    256 GB 可用    ← 夠，但不寬裕
```

### 7.2 預估

| 階段 | 時間 | 空間 |
|---|---|---|
| emsdk | 10 分 | 3 GB |
| Qt5 wasm | 60 分 | 8 GB |
| translations submodule | 5 分 | 1 GB |
| LO configure | 10 分 | — |
| LO build | 4–8 小時 | 60–90 GB |
| **最後 link soffice.wasm** | **20–90 分（單執行緒）** | **峰值 RAM 見下** |

### 7.3 LTO 的兩個真實風險

**風險 A：`emar --plugin LLVMgold.so` 可能不吃。**

`solenv/gbuild/platform/com_GCC_defs.mk:189-196` 在 clang + LTO 時設 `gb_LTOPLUGINFLAGS := --plugin LLVMgold.so`，`unxgcc.mk:211` 拿去餵給 `$(gb_AR)`。Emscripten 下 `AR=emar`（包 `llvm-ar`），而 `llvm-ar` 對 `--plugin` 的空格形式支援跟 GNU ar 不同。Linux + clang 之所以沒事，是因為那邊 `AR` 通常解析到 GNU ar。

> 順帶一提，那段的 `ifeq (,$(index,iOS MACOSX,$(OS)))` 是個 typo（`$(index,...)` 不是 make 函式，永遠展開成空字串），所以這個條件恆真。

**腳本的處理**：`configure` 前先跑一個真實探針（編一個 `.o`、試著 `emar --plugin LLVMgold.so -rsu`），失敗就在 make 命令列加 `gb_LTOPLUGINFLAGS=` 覆蓋掉。命令列變數在 GNU make 裡優先於 makefile 內的賦值，所以不用改原始碼。

**風險 B：link 期記憶體。**

`README.wasm.md` 說 LO WASM link「可能需要 64GB RAM」。你有 30GB。加上 ThinLTO（bitcode 物件 + link-time codegen）只會更吃。

**腳本的處理**：`doctor` 會檢查 swap，不足時建議：

```bash
sudo fallocate -l 48G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
```

真的過不去就 `LITE_LTO=0` 重跑（只需重新 configure + relink，物件檔 ccache 還在）。

### 7.4 其他已知坑

- **瀏覽器要 COOP/COEP header**（`Cross-Origin-Opener-Policy: same-origin`、`Cross-Origin-Embedder-Policy: require-corp`），否則 SharedArrayBuffer 不給用、pthread 全掛。`emrun` 有處理；自架 nginx 要自己加。
- **開新分頁測試，不要重新整理**。README.wasm.md 特別提醒過，快取會讓你以為改的沒生效。
- LO 用巢狀 event loop 跑 dialog，在瀏覽器上驅動不了。這是 Qt5 路線的已知結構性限制，不是你設定錯。

---

## 8. 還可以再砍的（本次沒做）

| 項目 | 省多少 | 為什麼沒做 |
|---|---|---|
| `ENABLE_WASM_STRIP_CHART` | 中 | `configure.ac:3499` 是**被註解掉**的，也沒有對應的 configure 旗標。要砍得自己改 configure.ac。而且 Writer 內嵌圖表會壞 |
| `ENABLE_WASM_STRIP_HUNSPELL` | 小 | 同上，`configure.ac:3501` 註解掉。反正字典沒打包，只剩程式碼 |
| CJK 字型子集化 | **大（19.5 → 3~5 MB）** | 需要 `pip install fonttools`，見下 |
| 四個沒被 gate 的 filter library | 小 | 見 `../litecore-analysis.md` 第 3 章 |

字型子集化（真的在乎首載大小時做）：

```bash
pip install fonttools brotli
pyftsubset NotoSansCJK-Regular.ttc \
    --output-file=NotoSansTC-Subset.ttf \
    --font-number=0 \
    --unicodes="U+0020-007E,U+3000-303F,U+4E00-9FFF,U+FF00-FFEF" \
    --layout-features='*' --drop-tables+=DSIG
```

然後 `LITE_CJK_FONT_FILES=$PWD/NotoSansTC-Subset.ttf ./build-wasm-lite.sh fonts`。
