<!--
LANGUAGE NOTE (do not "fix" this into English): this file is deliberately
zh-TW, as an explicit exception to AGENTS.md's "handoff/** is English" rule.
That rule exists because handoff/** is normally read by the next agent; this
one file's sole reader is the owner, who reads Chinese and does not read
handoff/**. Same exception, same reason, as
`handoff/RUNBOOK-operator-T4-manual-round.md`.
-->

# 093 選項 B 操作手冊 —— 逐段幾何要付的到底是什麼

寫於 2026-09-08。這份是**唯讀調查的產物**：樹沒有被動過，沒有編譯、沒有連結、
沒有寫任何 `dist/`。目標是讓你打開這一份就能決定要不要開工、以及開工之後你自己
要跑哪幾行，**不用回頭讀 finding 093 或任何別的東西**。

---

## 1. 一頁的結論

### 1.1 擋門的那一題：**不需要重編 LibreOffice core**

你裁定 B 的時候寫下的那一題是——

> `XAccessibleComponent` 在目前這顆 WASM core 裡有沒有被連進去？

**答案：有。而且不只「連得到」，它現在就已經在出貨的那顆 `probe.wasm` 裡面。**

所以 B 的價碼是**探針引擎重編 ＋ 一次重新連結**，屬於 agent 的範圍。
**不是**那趟 40 分鐘的核心重編。

### 1.2 證據（五條，每一條你都可以自己重跑一行確認）

**（a）符號真的在連結線上的 archive 裡，是「已定義」不是「未定義」**

```
cd wasm-lite/build-a11y-gate0/instdir/program
llvm-nm-19 --defined-only libcomphelper.a | grep OAccessible9getBounds
    →  _ZN10comphelper11OAccessible9getBoundsEv          T
llvm-nm-19 --defined-only libswlo.a | grep SwAccessibleContext13implGetBounds
    →  _ZN19SwAccessibleContext13implGetBoundsEv         T
```

`T` ＝ 已定義的程式碼。這兩個 archive 都在連結線上（`soffice.js.linkdeps`，
310 個 `-l` 項裡有 `-lcomphelper` 與 `-lswlo`）。

**（b）繼承鏈是原始碼上的，不是推測的**

- `comphelper::OAccessible` 繼承
  `WeakComponentImplHelper<…, XAccessibleExtendedComponent>`
  （`libreoffice-26-8/include/comphelper/OAccessible.hxx:38-44`）
- `XAccessibleExtendedComponent : XAccessibleComponent`
  （`offapi/com/sun/star/accessibility/XAccessibleExtendedComponent.idl:38`）
- `OAccessible::getBounds()` 是 `override final`，實作在
  `comphelper/source/misc/OAccessible.cxx:263-266`，轉呼叫 `implGetBounds()`
- `SwAccessibleContext::implGetBounds()` → `getBoundsImpl(true)`
  （`sw/source/core/access/acccontext.cxx:716`）

也就是說：**每一個 `OAccessible` 天生就是一個 `XAccessibleComponent`**，
而走訪現在拿到的每一個段落節點都是 `OAccessible` 的後代。

**（c）出貨的位元組裡已經有它**

`dist/profiles/e2-editor-v12/probe.wasm` 裡同時有 UNO 型別名的 ASCII 字串
`com.sun.star.accessibility.XAccessibleComponent`、RTTI 名
`N3com3sun4star13accessibility20XAccessibleComponentE`，以及
`21SwAccessibleParagraph N4cppu21ImplInheritanceHelperI19SwAccessibleContextJ…`。

**（d）呼叫端不會產生任何一個新的外部符號**

- `Reference<XAccessibleComponent>(xCtx, UNO_QUERY)` 走的是 header 裡的
  `cppu::UnoType<>`，最終呼叫 `typelib_static_interface_type_init`——
  那個函式在 `libcppu` 裡，而**現在的走訪查 `XAccessibleText` 已經在用它了**。
- `getBounds()` 是純虛擬呼叫，走 vtable，**連結期不需要任何符號**。

所以這次改動與 2026-08-23 那次不同：那次要新增三個外部符號（
`SfxViewShell::Current()`、`vcl::Window::GetAccessible()`、
`OAccessible::getAccessibleContext()`，記在
`findings/evidence/aria-projection/REACHABILITY.md`），**這次一個都不用**。

**（e）需要的 header 已經產生在磁碟上**

```
wasm-lite/build-a11y-gate0/workdir/UnoApiHeadersTarget/offapi/comprehensive/
    com/sun/star/accessibility/XAccessibleComponent.hpp        (14,968 bytes)
    com/sun/star/accessibility/XAccessibleExtendedComponent.hpp (5,679 bytes)
```

而且那顆核心建置樹是完整的：`wasm-lite/build-a11y-gate0`，5.9 GB，
310 個 `-l` 項全部在 `instdir/program` 或 `-L` 搜尋路徑底下解析得到，
`ENABLE_WASM_STRIP_ACCESSIBILITY 0`。**它不用重編。**

### 1.3 那趟核心重編如果真的要跑要多久（這次用不到，寫在這裡只為了對照）

`handoff/RUNBOOK-a11y-gate0-core-rebuild.md:112-113` 預估 **40–80 分鐘**
（writer-only 的前例是 35 分 42 秒，`-j12`）；實際那一趟
`handoff/a11y-gate-0/README.md:16` 記的是 **40 分鐘，含一次 finding 003 的重試**。
**這次不需要跑它。**

---

## 2. 座標空間：這是 B 唯一真正的未知數

**這一整節是讀原始碼推出來的，不是量到的。**照 AGENTS.md §7（驗宣稱不要驗代理、
能看就不要推），下面的步驟 1 就是去把它看一遍——而且那一步**不是單向門**。

### 2.1 `getBounds()` 回的是什麼

- 型別是 `com::sun::star::awt::Rectangle`。
- 值來自 `GetMap()->CoreToPixel(aLogBounds)`
  （`sw/source/core/access/acccontext.cxx:777-820`），而 `CoreToPixel` 是
  `pWin->LogicToPixel(rect, aMapMode)`（`sw/source/core/access/accmap.cxx:2896-2909`）。
- ⇒ **單位是輸出裝置的像素**。**不是 twips，也不是 1/100 mm。**
  （這一點我特別點出來，因為一支外包 agent 依一般 UNO 慣例回報成 1/100 mm，
  是錯的；我讀了 Writer 的實作。）
- 那個 MapMode 是 `MapUnit::MapTwip`
  （`sw/source/uibase/docvw/edtwin.cxx:5618`，`SwEditWin` 自己設的），
  所以 pixel = twips × DPI ÷ 1440。**那個 DPI 在這顆 wasm build 上沒有人量過。**

### 2.2 原點：是絕對的，不是相對於 parent 的

`getBoundsImpl(true)` **只有在 `!pParent->IsRootFrame()` 時**才會扣掉 parent 的
位移（`acccontext.cxx:810-815`）。而——

- 那個 `GetParent()` 與 `getAccessibleParent()` 用的是**同一個函式**
  （`acccontext.cxx:625` 對 `acccontext.cxx:781`）；
- 而已經量過的樹形是**扁的**：root `DOCUMENT_TEXT` ＋ 133 個段落全部在 depth 1，
  中間沒有節點（`findings/evidence/aria-projection/TREE-SHAPE.md`）。

⇒ 段落的 parent **就是 root frame** ⇒ 那個扣位移的分支不會走
⇒ **回傳的是文件絕對座標**。這是 B 能成立的關鍵，也是最該在步驟 1 驗掉的一句。

### 2.3 頁面現有的幾何路徑：**全程 twips，中間零轉換**

新矩形應該騎在這條路上，不要另開第二條。

| 站 | 位置 | 做什麼 |
| --- | --- | --- |
| LOK 契約 | `include/LibreOfficeKit/LibreOfficeKitEnums.h:120-130` | 明文寫「document coordinates, in twips」 |
| 引擎收 | `src/probe_engine.cpp:2391-2409` | `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` → `gEditorState.caret` |
| 引擎解析 | `src/probe_engine.cpp:1048-1064` | `sscanf("%d,%d,%d,%d")`，**零算術** |
| 引擎序列化 | `src/probe_engine.cpp:1116-1126` | 原數字寫成 JSON |
| worker | `sdk/sdk-worker.js:302-309` | allowlist，原樣搬 |
| 頁面繪圖 | `web/e2-editor-app.js:676-681` | `scaleX = canvas.width / document.widthTwips`（backing px） |
| 頁面定位 | `web/e2-editor-app.js:722-735` | `moveSinkToCaret`，用 `clientWidth`（CSS px） |

**建議的形狀（給 agent，不是給你）**：探針在**同一個 OutputDevice** 上把像素轉
回 twips（`PixelToLogic(rect, MapMode(MapUnit::MapTwip))`）再吐出去。那是同一個
裝置的精確反運算，**DPI 這個未知數就整個消失**，而且新矩形跟 caret 同空間，
頁面端直接沿用 `moveSinkToCaret` 那三行算式。

---

## 3. B 比你裁定當時假設的**便宜**兩件事

**（a）不用重編 core。**你裁定時寫的是「沒連進去 → 需要一次核心重編，那是擁有者
手動跑的長作業」。那一半不會發生。

**（b）它不會過期——而「會過期」正是 S3′ 被否決的唯一理由。**

- 引擎的 outline **每一次 state read 都重算整棵樹**。這不是我猜的，
  `src/probe_engine.cpp:1177-1182` 的註解逐字寫著：
  「Emitted on every state read rather than only when the structure moved,
  and that is a MEASURED choice rather than a lazy one」。
  ⇒ **編輯不會讓它過期。**
- 若幾何以 twips 交付，`layoutCanvas()`（改視窗寬度）改的是 CSS 比例，
  不是 twips。⇒ **視窗縮放也不會讓它過期。**

S3′ 缺的那個性質，B 是天生就有的。**這一點強化了你的裁定，不是削弱它。**

---

## 4. B 比假設的**貴**四件事（都要在動手前知道）

**（a）連結要跑多久，全樹沒有任何紀錄。**
`wasm_sdk_probe/*.time` 那 11 個檔全是 2026-08-01 的小探針（1.64–4.34 秒），
不是 profile 連結。所有 relink 手冊都沒寫時間。`probe.wasm` 是 135 MB。
**代價未知——照這棵樹的規矩，我不編一個數字給你。**

**（b）`e2-editor-v12` 從來沒有被 archive 過。**
`build/archive/` 有 26 個目錄，**沒有 v11 也沒有 v12**。v12 的 worker
（`03f5b69a…`）與 manifest 只活在 `dist/` 裡。這是既有的洞，不是 B 造成的，
但 B 會把它變成損失——所以步驟 2 是補做它。

**（c）要動 `Makefile`，而 finding 042 說改 Makefile 會讓每個 profile 的 `.o`
全部過期。**好消息是 `refuse_unasked_relink`（`Makefile:873-891`）會**擋下來並
退出**，不會靜默重連結：

```
refusing to relink a frozen profile: <target>
a new link mints a new artifact and unbinds that (findings 027, 036).
```

代價是：改完 Makefile 之後**只能 build 新目標**，不要跑任何裸 `make`。

**（d）頁面端有一個會靜默復發 088 的陷阱。**
`web/e2-editor-app.js:308-310` 的 `signature` 是 `[role, level, text]`；
signature 一變就整批 `replaceChildren`。**幾何絕對不可以進 signature**，
否則每次捲動／編輯都重建整棵樹，088 就回來了——而 **088 是你用耳朵發現的，
沒有任何儀器會報它**。

---

## 5. 你要跑的步驟（依序）

> **總則**：只有步驟 4 是你的。其餘每一步都是 agent 的，但都列在這裡，
> 這樣你知道等的是什麼、以及卡住時卡在哪。
> **步驟 1 沒有給出乾淨答案之前，不要跑步驟 4。**

### 步驟 0 —— 你的授權（一句話）

現在什麼都還沒動。開工前請明確說一句「開始 093 B」。理由是這棵樹的規矩：
連結是單向門，而 agent 不得自行走進去。

### 步驟 1 —— native 校準（agent；**不是單向門**，最重要的一步）

**問題**：§2 整節是讀原始碼推的。單位、原點、以及「跟 LOK 的 caret rect 對不對
得上」，三題都沒有量過。

**做法**：在 `build-native-26-8`（原生 26.8 建置，**已經有無障礙**——
`libswlo.so` 裡找得到 `SwAccessibleParagraph`，而且它就是
`tools/check_core_build_provides.py` 用的正對照）上寫一支 native 探針，
對同一份 fixture 問 `XAccessibleComponent::getBounds()`，回答：

1. 回傳值的**單位**是不是像素、以及那顆裝置的 DPI 是多少；
2. 原點是不是**文件絕對座標**（§2.2 的推論對不對）；
3. 把它換算成 twips 之後，**跟 LOK 給的 caret rect 對不對得上**（同一段落、
   同一行，y 應該落在同一個帶狀區域內）。

**為什麼一定要先做這一步**：native build 可重建、**不鑄造任何 wasm 身分、
不動閘門、不作廢任何證據**。這棵樹已經有一整批 `tools/*_native_*.cpp` 的前例。
花小錢先看清楚門後面是什麼，正是「重編是單向門」那條規矩的意思。

**如果步驟 1 的答案是「對不上」**：停手回報，不要進步驟 3。那代表 B 的形狀要重
設計（例如改用 `getLocationOnScreen()` 相減），而那是一個新的裁定，不是一個補丁。

### 步驟 2 —— 補 archive `e2-editor-v12`（agent）

照 `build/archive/` 的慣例，目錄名是
`e2-editor-v12-<wasm16>-worker-<worker16>-manifest-<manifest16>`，
內容比照最完整的那一份（`e2-editor-v8-4a2710bb-worker-070229cd-manifest-d70481cb`）：
`ATTRIBUTION.md`、`SHA256SUMS`、`SHA256SUMS.shared`、`probe.js`、`probe.wasm`、
`sdk-worker.js`、`sdk-manifest.json`，加上 v12 特有的三個資料包
（base／cjk／fallback）。

**理由**：一顆 profile 是**五個綁定身分**——profile 名、`probe.js`、`probe.wasm`、
`sdk-worker.js`、`sdk-manifest.json`（v12 再加上頁面與三個資料包）。
v3 那次「archive 的名字綁錯東西」就是這樣付過一次錢的。

### 步驟 3 —— 落地改動（agent）；**先做紅案，再做綠燈**

改動面共四處：

| 檔案 | 改什麼（形狀，不是程式碼） |
| --- | --- |
| `src/a11y_tree_probe.cpp:252-345` | 走訪迴圈裡多一次 `Reference<XAccessibleComponent>(xCtx, UNO_QUERY)`，取 `getBounds()`，**在同一個 OutputDevice 上換算成 twips**，加進每一段的 JSON。**這個 TU 已經是 `-DLIBO_INTERNAL_ONLY`，不用新增任何編譯旗標。** |
| `sdk/sdk-worker.js:383-401` | allowlist 多搬四個欄位（x／y／width／height）。**這是 allowlist：沒加就永遠到不了產品。** |
| `tools/build_e2_editor_v4_profile.py:485-491` | 比照 `caretParagraphText`／`documentOutline` 的形狀，新增一個宣告欄位（例如 `documentOutlineGeometry`），**綁在旗標上、不無條件宣告**——那個檔案自己的註解寫著無條件宣告就是 2026-08-22 付過錢的「describes but does not constrain」。 |
| `web/e2-editor.html` ＋ `web/e2-editor-app.js:255-410` | `#a11y-doc` 要能承載子節點的絕對定位（`.a11y-only` 目前是 `width:1px; height:1px; overflow:hidden`），每個投影節點依自己那一段的 twips × `moveSinkToCaret` 的比例定位。**幾何不進 signature**（§4d），要用就地改 `style`。 |

**落地前先做出紅案**（AGENTS.md §6）：至少要有「引擎沒吐幾何時頁面怎麼樣」、
「幾何吐了但 worker 沒搬」兩個紅案，各自證明它會紅。

**同時落地一道讀幾何的檢查**——這件事 finding 093 已經論證過資格，而且**窗口只在
soak 計數為 0 時開著，現在正好是 0**。不做的話，069 的故事會第三次發生：
修好第二個元素，而那個形狀依然沒有人守。

驗收判準沿用已經先釘死的那一份，不要新寫：
`findings/evidence/093/ORACLE-fix-shape.md`（commit `8edd7cf8`，寫在探針存在之前），
儀器是 `tools/probe_093_fix_shape_oracle.py`。**目標是 133 段的長文件上
browse 與 focus 兩臂都 3/3**——S3′ 已經量到那個成績，B 至少要打平。

### 步驟 4 —— **連結（這一步是你的）**

先確認 agent 回報三件事都綠了：步驟 1 的校準、步驟 3 的紅案、以及
`check_relink_queue.py` 報 `p1Complete: True`。然後：

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v13/sdk-manifest.json
```

- **新名字是 `e2-editor-v13`**，不是覆寫 v12。v10 的手冊第一句就是
  「This link mints a NEW name」。
- `ALLOW_FROZEN_RELINK=1` 是**守衛的價錢，不是在描述你在重連結凍結的東西**——
  那個守衛無條件坐在每一條連結配方裡。
- **打包的旗標一個都不能漏**，漏了就是在一次跟它無關的連結上悄悄縮限產品
  （v8 手冊為了 `--inline-range-gestures all` 專門寫過這件事）：

```
--profile e2-editor-v13 --paragraph-text --document-outline \
--inline-range-gestures all --core-data ../wasm-lite/build-a11y-gate0 \
--split-core-data
```

`--split-core-data` 是 v12 之所以是 v12 的那一半（base／cjk／fallback 三個包）；
漏掉它，新 profile 就不是對 v12 的單一變因比較。

**看輸出**：builder 會印五個身分。任何一個是空的就停手。

### 步驟 5 —— 連結之後、量任何東西之前（agent）

1. **記下五個 hash**；
2. **立刻 archive**：`build/archive/e2-editor-v13-<wasm16>-worker-<worker16>-manifest-<manifest16>/`；
3. **repoint**：`web/e2-editor-app.js` 的 `workerUrl` 與 `PINNED_WASM_SHA256`
   **兩行一起改**，`dist/` 的副本也要——「一頁只改一行，就會釘住一個 artifact
   而載入另一個」；
4. 凍新的 shell generation、重跑靜態測試與產品路徑；
5. 然後才是 `tools/probe_093_fix_shape_oracle.py` 的驗收。

### 步驟 6 —— 閘門重來（你與 agent）

見下一節。

---

## 6. 什麼會死、什麼要重賺

### 6.1 會移動的身分

profile 名、`probe.wasm`／`wasmSha256`、`sdk-manifest.json` 的摘要、
`sdk-worker.js`（步驟 3 會改它）、`web/e2-editor-app.js` 的 `PINNED_WASM_SHA256`
與 `workerUrl`、`candidateCutover.pageSha256`、`servedShell.servedSha256`／
`entrypointSha256`、以及一個新的 shell bundle generation。
**`probe.js`（loader）可能不動**——v8 那次就沒動——這正是 archive 目錄名要帶
三個 hash 的原因。

機制只有一條：`tools/run_e2_c_product_path.py:428-439` 從新 manifest 讀
`editorContract.wasmSha256`，改寫頁面裡的 `PINNED_WASM_SHA256`
⇒ 頁面位元組變 ⇒ `pageSha256` 變 ⇒ 而頁面又是 shell bundle 的 entrypoint
⇒ `servedSha256` 也變。**六個 pin 裡有五個一次全倒**，只有 `completedAt` 活著。

### 6.2 會死的證據

- **soak：已經是 0 of 12**（你的 D-c 裁定，`ed1ea02a`）。所以 B 在 soak 上的
  邊際成本是零——但它讓那個歸零**從裁決變成機械的**。
- **條件 3 與 4b 的判斷半**（你 2026-09-08 凌晨那一輪）：綁在頁面 `9b29e39b…`，
  **頁面一動就不存活**。要重做一次人工輪。
- **條件 4a**（`tools/check_4a.py` 的第 1 項就是 Identity，比對 `pageSha256`）。
- **條件 2 的三趟診斷跑**、**ODT 來回**、**revert 演練**。

前例是實打實的：這棵樹已經因為身分變更作廢過 **22 趟** run，分四次
（v11→v12 五趟；頁面移動兩次 7＋10 趟；判準移動 2 趟）。每一批都**原地保留**，
配一份 `WHY-THESE-ARE-VOID.md`，**不改寫、不搬走**。

### 6.3 一個機械上的陷阱

`tools/check_soak_bank.py` 用 glob 枚舉，而**未分類的檔案是紅的，不是被忽略**。
作廢的 run 必須**實體離開計數目錄**，否則 `every-run-clean` 永遠 false。
存活的 run **不重新編號**（目前的 bank 是 03–08，沒有 01／02，那個缺口就是重啟
的紀錄）。

### 6.4 不會死的

`dist/profiles/resources/`（34 個 profile 共用，v11／v12 自帶影像沒碰它）、
所有已凍結的前代 archive、以及 `findings/evidence/` 底下的一切
——**證據原地保留，永不改寫**。

---

## 7. 這份文件沒有回答的三件事（不要被上面的綠燈蓋過去）

1. **§2 全部是讀原始碼推的，不是量到的。**單位、原點、與 caret 對不對得上，
   三題都要步驟 1 去看。**能看就不要推**，而步驟 1 是免費的。
2. **連結的 wall-clock 未知。**樹裡沒有紀錄，我沒有編一個給你。
3. **`getBounds()` 每段一次的成本沒有量過。**outline 是每次 state read 重算整棵樹，
   133 段就是每次多 133 次 UNO 呼叫。可能無所謂，但那是**要量的，不是要假設的**。

另外兩件仍然獨立、仍然未裁定，**不要因為 093 有處置就順手一起處理**：
頂端邊界的焦點逃逸（`leaving panel`），以及 finding 095（最後一行按 ArrowDown
之後點畫布放不了游標）。

---

# 追記（2026-09-08）：步驟 1 做完了，§2 的三題全部量到

**這一段是 append，上面一個字都沒有改。**它更正的是 §7 第 1 點——「§2 全部是讀
原始碼推的，不是量到的」——那句話從現在起只適用於 wasm 那一側。

證據：`findings/evidence/093/step1-native-geometry/`（`RESULT.md`、
`VERDICT.json`、`run/`）。判準先釘死在 `ACCEPTANCE.md`（commit `bcb7caf4`，
寫在探針存在之前）。儀器 commit `ca78f998`。

**只跑 native（`build-native-26-8`）。wasm 那一側一個位元組都沒有動。**

| 題 | 答案 | 數字 |
| --- | --- | --- |
| 單位（§2.1） | **輸出裝置像素**，如手冊所讀 | raw/twips ＝ 0.0666764 對 `dpi/1440` ＝ 0.0666667，差 0.015% |
| DPI（§2.1 說「沒有人量過」） | **這顆 native svp 裝置是 96**，三種讀法互相同意 | 96 / 96 / `LogicToPixel(1440 twips)` ＝ 96 |
| 原點（§2.2） | **文件絕對座標**，推論成立 | 114 段的 parent 都是走訪 root；y 走到 96,240 而視窗只有 7,440 |
| 對應（§2.3） | **20/20 對得上** | `dTop` −14..0 twips，一個像素是 15，判準是 552 |

**停止規則沒有觸發**，所以 §5 步驟 1 的「對不上就停手」不適用。

順帶結清兩件本來要在步驟 3 猜的事：

1. §2.3 建議的 `PixelToLogic(rect, MapMode(MapUnit::MapTwip))` 與
   `CoreToPixel` 的精確反運算（用裝置自己的 MapMode）在 114 段上**每一段都
   同值**——那顆裝置的 MapMode 就是 MapTwip、原點 (0,0)、縮放 1。
2. §5 步驟 1 提到的備案「改用 `getLocationOnScreen()` 相減」**不需要**：
   它與 `getBounds()` 的差是單一常數 (0, 64) px，資訊量為零，只是每段多一次
   UNO 呼叫。

**§7 的另外兩點原封不動**：連結的 wall-clock 仍然未知；每段一次 `getBounds()`
的成本仍然沒有量過（這次量的是座標，不是時間）。

**仍然待辦**：步驟 2（補 archive `e2-editor-v12`）、步驟 3（落地改動，先做紅案）。
步驟 4 的連結仍然是你的。

---

# 追記（2026-09-08）：步驟 3 做完了，而**步驟 4 的那行指令現在跑不起來**

**這一段是 append，上面一個字都沒有改。**它更正的是 §5 步驟 4，並補上兩件在
落地過程中量到、而原文沒有的事。

貨載：commit `c2a7abad`（引擎＋worker＋builder）、`18eefcce`（頁面＋殼層
generation v49）、`72f8de7f`（第 41 道檢查＋兩筆突變）、`f17a5de5`（閘門 amendment
與證據）。證據在 `findings/evidence/093/step3-source-landing/`。
**沒有連結、沒有產出 wasm、`dist/profiles/**` 一個位元組都沒動。**

## 更正一：`make … e2-editor-v13/sdk-manifest.json` **沒有這條規則**

實測：

```
$ make -n dist/profiles/e2-editor-v13/sdk-manifest.json
make: *** No rule to make target 'dist/profiles/e2-editor-v13/sdk-manifest.json'.  Stop.
```

原因是 **v11 與 v12 都不是連結出來的**。`E2_V11_DIST` 那條規則是拿
`build/archive/e2-editor-v10-4ec1e389-…/` **重新打包**，而 v12 連 Makefile 規則
都沒有（它是直接跑 `build_e2_editor_v4_profile.py` 打包的）。核對過：
`dist/profiles/e2-editor-v12/probe.wasm` 的雜湊是 `4ec1e389…`，**就是 v10 那顆**。

所以 B 需要的是一組**新的建置＋連結規則**（比照 `E2_V10_*` 那三條：`%.o`、
`a11y_tree_probe.o`、`probe.js`），因為引擎真的改了、必須重編重連。那要**動
Makefile**，而 §4(c) 已經寫了它的代價（finding 042：每個 profile 的 `.o` 全部過期）
——所以改完之後**只 build 新目標，不要跑任何裸 `make`**；`refuse_unasked_relink`
仍然坐在每一條連結配方裡，會擋下沒有 `ALLOW_FROZEN_RELINK=1` 的連結。

這條規則**沒有由這一輪寫**：工單的改動面是四個檔案並且明說「盡量不要動 Makefile」，
而寫它的人應該是要按下連結那一鍵的人。

## 更正二：打包旗標**少了一個**，而少了它這趟連結會白做

§5 步驟 4 的旗標清單要再加一個：

```
--profile e2-editor-v13 --paragraph-text --document-outline \
--document-outline-geometry \
--inline-range-gestures all --core-data ../wasm-lite/build-a11y-gate0 \
--split-core-data
```

`--document-outline-geometry` 是這一輪新加的旗標，**預設關**。它跟
`--document-outline` 分開，是因為 2026-09-08 之前連結的每一顆 profile 都是
「有 outline、沒有幾何」，由前者推後者會讓 v10／v11／v12 的 manifest 宣告它們的
位元組沒有的東西。

**漏掉它的後果是靜默的**：引擎會吐幾何，manifest 不宣告，頁面讀不到宣告就走
「誠實降級」那條路（`data-geometry="absent"`），投影還是全部疊在紙張頂端，而
產品路徑那道新檢查**會過**——因為那條路正是它要保護的合法狀態。你會得到一顆
新身分、五個 pin 全倒、而行為跟連結前一模一樣。這就是 v8 手冊為
`--inline-range-gestures all` 專門寫過的那件事，同一個形狀。

## 補充：步驟 5 之前先看兩個 DOM 屬性

連結完、repoint 完之後，最快的「這趟連結有沒有生效」是讀
`#a11y-structure` 的 `data-geometry`：

- `present` ＝ 宣告了而且酬載有幾何，**這是要看到的**；
- `absent` ＝ manifest 沒宣告（多半是更正二漏了旗標）；
- `declared-but-missing` ＝ 宣告了但一個都沒到（引擎沒吐，或 worker 的 allowlist
  沒搬）——產品路徑的新檢查會**紅**在這一格。

驗收仍然是 `tools/probe_093_fix_shape_oracle.py` 對
`findings/evidence/093/ORACLE-fix-shape.md`，目標 133 段的長文件兩臂 3/3。
**連結之前量不到 3/3**：今天用同一支儀器對落地後的頁面跑 `--shape S0
--fixture a11y-long`，兩臂都 0/3，重疊 0px、捲動比例 0.0000。

## 更正三：§1.2(d)「呼叫端不會產生任何一個新的外部符號」是錯的

實測 43 個未定義符號變 47 個，多的四個是 `vcl::Window::GetOutDev`、`MapMode` 的
建構與解構、`OutputDevice::PixelToLogic`。原本的論證涵蓋了 `UNO_QUERY`（header-only）
與純虛擬的 `getBounds()`，兩者都成立，**但沒有涵蓋換算本身**——而換算正是 B 真正
加上去的東西。四個都在 `libvcllo.a` 裡是 `T`，`-lvcllo` 在連結線上，所以 §1 的
**結論**（不用重編 core、連得起來）不受影響，被更正的是它的論證。
細節與重跑方式在 `findings/evidence/093/step3-source-landing/new-undefined-symbols.txt`。

## 更正四：§6.3 那個陷阱有第二層

§6.3 說作廢的 run 必須實體離開計數目錄，否則 `every-run-clean` 永遠 false。對，
但 `check_soak_bank.py --self-test` 的 `clean_sources()` 讀的是**活的** bank，
把它清空會讓那支判官再也證明不了自己會說不（`SystemExit`）。所以那次搬移要排在
**第一趟連結後的乾淨執行入庫之後**，不是之前。同一段還記著：D-c 的歸零從來沒有
像 R-1 那次一樣套進 glob，2026-09-07 那六趟今天仍然被判官算成乾淨。三個常數
（`EXPECTED_PASS` 38→39、`DEFAULT_SHA`、`DEFAULT_SERVED_SHELL`）要在步驟 4 之後
一起動。理由寫在 `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` 2026-09-08
的 amendment。
