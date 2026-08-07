# LibreOffice 26.8 QA 參與指引

寫給：有能力自己編 LibreOffice、母語繁中、手上有 26-8 worktree 的人。
也就是說，這份文件刻意**不寫**通用的 QA 入門，只寫「以你的條件，投入哪裡回報率最高」。

相關文件：[`wasm-lite/README.md`](wasm-lite/README.md)（WASM lite build 規劃）、[`litecore-analysis.md`](litecore-analysis.md)（core 精簡研究）

---

## 0. 先把兩條線分開

| | QA 線 | 專案線 |
|---|---|---|
| 目的 | 幫 26.8 正式版把關 | 你自己的 WASM lite core |
| 載具 | 官方 RC binary，或接近預設的自編 build | `wasm-lite/build` 的 lite build |
| 產出 | Bugzilla 上的 bug report | 你自己的筆記 |

**這兩條不能混。** 原因見下一節。

---

## 1. 不要用 lite build 報 bug

`wasm-lite` 的 configure 長這樣：

```
--with-wasm-module=writer --disable-symbols --disable-pch --disable-scripting
--without-help --without-myspell-dicts --disable-python --disable-odk ...
```

這是一個**沒有任何人跑過的組合**。在上面發現的異常，QA triager 的第一個問題必然是「官方 build 能重現嗎」，答不出來就會停在 NEEDINFO 然後過期關掉。這不是刁難 —— 他們沒有資源追每個人的自訂 config。

所以：lite build 上看到的問題，**先在官方 build 或接近預設的 build 上重現過**，再決定要不要報。重現不了就是你自己的組態問題，記在專案筆記裡就好。

---

## 2. 起手式：triage（零門檻，先做這個）

QA 真正的瓶頸不是「沒人回報」，是 **UNCONFIRMED 佇列沒人確認**。

做法：挑一個 UNCONFIRMED 的 bug、照步驟試、回一句結果。

```
可重現 / 不可重現
Version: 26.8.0.1 (build id: ...)
OS: Linux (你的發行版)
VCL plugin: qt6
```

半小時能做好幾個，零門檻，而且是熟悉 Bugzilla 流程最快的路。先做 10 個 triage 再開始報自己的 bug，你會少踩很多格式上的坑。

入口：<https://wiki.documentfoundation.org/QA/GetInvolved>

---

## 3. 主戰場：Welded widgets 的 A/B 測試

**這是我認為你投報率最高的地方。**

### 3.1 這是什麼

`tdf#130857` 這條線在把 LibreOffice 的對話框從「VCL 自繪」改成「原生 Qt widget」。26-8 已經轉換 **463 個 `.ui`**（master 是 582）。它是 TDF 網頁與行動策略的前置工程 —— 要讓 LO 跑在 Qt6 上（行動裝置、瀏覽器），對話框層必須先原生化。

規模：`tdf#130857` 累計 1460 個 commit，最近 12 個月 784 個，幾乎全部出自 Michael Weghorn 一人。

### 3.2 為什麼這裡沒人測

**它預設是關的。** 見 `vcl/qt5/QtInstance.cxx:862-876`：

```cpp
bool QtInstance::noWeldedWidgets()
{
    static const bool bNoWeldedWidgets = (getenv("SAL_VCL_QT_NO_WELDED_WIDGETS") != nullptr);
    return bNoWeldedWidgets;
}

bool QtInstance::isQtWeldingEnabled()
{
    if (noWeldedWidgets())
        return false;
    // for now, require explicitly enabling use of QtInstanceBuilder via SAL_VCL_QT_USE_WELDED_WIDGETS
    static const bool bUseWeldedWidgets = (getenv("SAL_VCL_QT_USE_WELDED_WIDGETS") != nullptr);
    return bUseWeldedWidgets;
}
```

也就是說：**這 463 個對話框在 26.8 正式版發佈前，實質上只有寫的人測過。**

### 3.3 完美的 A/B

上面那兩個環境變數是一組對照：

```bash
# A：新的原生 Qt 對話框
SAL_USE_VCLPLUGIN=qt6 SAL_VCL_QT_USE_WELDED_WIDGETS=1 soffice --writer

# B：強制關閉，走舊的 VCL 自繪
SAL_USE_VCLPLUGIN=qt6 SAL_VCL_QT_NO_WELDED_WIDGETS=1 soffice --writer
```

**同一個 binary、同一個對話框、只差一個環境變數。** 兩邊行為不同就是 bug，而且重現步驟乾淨到無法爭辯 —— 這是 triager 最喜歡的格式。

報告時務必寫清楚「A 會、B 不會」，並在標題帶上 `qt weld:` 之類的字樣，讓它直接落到對的人手上。

### 3.4 檢查清單

按 CJK 命中率排序。**第一層先做完再往下**。

#### 第一層：CJK 直球對決（最可能中）

這些對話框只有在啟用亞洲語言支援時才會出現完整樣貌，海外開發者幾乎不會碰：

| `.ui` | 在哪 | 看什麼 |
|---|---|---|
| `cui/ui/charnamepage.ui` | 格式 → 字元 → 字型 | **最關鍵**。繁中 locale 下這頁有「西方文字 / 亞洲文字 / CTL」三組字型選擇器。welded 版有沒有把三組都畫出來？字型名稱下拉選單顯示中文字型名正常嗎？ |
| `cui/ui/asiantypography.ui` | 格式 → 段落 → 亞洲式排版 | 這個分頁只在亞洲語言啟用時存在。checkbox 有沒有全部在？ |
| `cui/ui/textflowpage.ui` | 格式 → 段落 → 換行和分頁 | 含亞洲文字的斷行規則 |
| `cui/ui/breaknumberoption.ui` | 工具 → 選項 → 語言設定 → 亞洲語言排版 | 禁則處理字元清單，是一個吃 CJK 字串的輸入框 |
| `cui/ui/positionpage.ui` | 格式 → 字元 → 位置 | 旋轉/縮放，中文直排相關 |
| `cui/ui/effectspage.ui` | 格式 → 字元 → 字型效果 | 強調標記（著重號）是 CJK 專屬功能 |

#### 第二層：文字輸入與輸入法

welded 的輸入元件是真的 `QLineEdit` / `QComboBox`，跟 VCL 自繪的完全兩回事。用**新酷音或你慣用的輸入法**打中文進去：

- preedit（未上屏的組字區）顯示正常嗎？會不會被吃掉？
- 打到一半按 Esc / Tab 會怎樣？
- 候選字視窗位置對嗎？
- 貼上長中文字串會不會爆版？

重點對象：`cui/ui/namedialog.ui`、`cui/ui/objectnamedialog.ui`、`modules/swriter/ui/addentrydialog.ui`、`modules/swriter/ui/createauthorentry.ui`、任何有 entry 的對話框。

#### 第三層：版面被中文撐爆

中文字比英文寬。VCL 自繪跟 Qt layout 的算法不一樣，所以「英文正常、中文截斷」是很典型的 welded bug：

- label 有沒有被切掉（顯示成 `字型效...`）
- button 文字有沒有超出邊框
- 對話框有沒有變得異常寬或異常窄
- 快捷鍵底線（mnemonic）在中文標籤上怎麼呈現

#### 第四層：Writer 核心功能廣度掃描

26-8 的 welded 清單裡 Writer 相關佔比：

```
cui/ui              128   （共用：字元、段落、選項⋯）
modules/swriter     106
sfx/ui               27
svx/ui               26
filter/ui            12
vcl/ui                8
uui/ui                4
```

挑常用的走一遍：`characterproperties.ui`、`bulletsandnumbering.ui`、`columndialog.ui`、`fielddialog.ui`、`footendnotedialog.ui`、`captiondialog.ui`、`contentcontroldlg.ui`。

完整清單自己撈：

```bash
grep -o 'u"[A-Za-z0-9/_-]*\.ui"' \
  libreoffice-26-8/vcl/qt5/QtInstanceBuilder.cxx | sed 's/^u"//; s/"$//' | sort -u
```

---

## 4. bibisect：指出兇手

TDF 一直說這是瓶頸 —— 回報的人多，能指出**哪個 commit 弄壞的**人少。

bibisect repo 是預編好的上百到上千個版本，`git bisect` 幾秒鐘就能收斂，**你連編都不用**。但懂編譯的人做這件事效率高很多，因為 bibisect 顆粒度太粗時，你能接著在 source 上直接 `git bisect` 補完。

一份附上 `first bad commit = abc123` 的 bug report，被修的機率跟一般回報差一個量級。

說明：<https://wiki.documentfoundation.org/QA/Bibisect>

---

## 5. Bugzilla 實務

帳號：<https://bugs.documentfoundation.org>，一個 email 就好。

- **報之前先搜。** 重複回報是 triager 最大的時間黑洞。
- **一個 bug 一張單。** 三個問題塞一張會整張卡住。
- **版本字串貼完整的。** `說明 → 關於` 有複製按鈕，整段貼上，不要只寫「26.8」。
- **一定要寫 VCL plugin**（`gtk3` / `qt5` / `qt6` / `gen`）。這個欄位常被漏掉，而它決定 bug 派給誰。用 welded widgets 測的話，把兩個環境變數也寫進去。
- 附最小重現檔。`.odt` 越小越好。
- 步驟寫成編號清單，一步一個動作，最後寫「預期 / 實際」。

---

## 6. 測試載具

### 最快：官方 26.8 RC

抓 .deb/.rpm 裝到 `/opt`（跟系統的 LibreOffice 並存，不會打架）。裝完先確認有 Qt plugin，沒有的話第 3 節那組 A/B 開不起來：

```bash
ls /opt/libreoffice26.8/program/libvclplug_qt*
```

### 最準：從同一個 worktree 再開一個 native build

WASM build 是 out-of-tree 的，所以 `libreoffice-26-8/` 可以同時當 native build 的來源（`wasm-lite` 的 patch 只動 emscripten 的 fs image，native build 根本不讀那個檔）。

```bash
mkdir -p ~/LibreOffice/study_LiteCore/wasm-lite/build-native
cd ~/LibreOffice/study_LiteCore/wasm-lite/build-native
~/LibreOffice/study_LiteCore/libreoffice-26-8/autogen.sh \
    --enable-qt6 --enable-release-build --disable-symbols --enable-ccache
make -j$(nproc)
```

好處：版本號跟你報的 bug 完全對得上，而且以後要在 source 上 bisect 現成。
代價：2–4 小時，而且**別跟 WASM build 同時跑**，會搶 CPU。

---

## 7. 時程

```
2026-07-13   RC1
2026-07-22   QA 徵求測試
2026-08 底   26.8 正式版
```

現在到八月中是最有效的窗口。之後報的東西只能進 26.8.1。
