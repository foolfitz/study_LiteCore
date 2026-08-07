# 005 — Qt5 WASM 版本無法使用任何輸入法，CJK 輸入完全不可行

| | |
|---|---|
| **狀態** | 可送出（但根因在 Qt5，LO 這邊是「選了沒有 IME 能力的後端」） |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-07-31 |
| **嚴重度** | 嚴重（對 CJK 使用者等同無法輸入文字） |
| **可重現** | 100% |
| **是否上游** | 是（LO + Qt5 wasm plugin） |

## 現象

在瀏覽器裡開啟 LOWA、進入 Writer，用 fcitx 打中文完全沒有反應。英文字母正常。

## 分析

**根因：Qt 5.15 的 wasm platform plugin 沒有任何 input context 實作。**

### 1. 鍵盤事件只有原始按鍵，沒有組字

`qtbase/src/plugins/platforms/wasm/qwasmeventtranslator.cpp:394-395`：

```cpp
emscripten_set_keydown_callback(canvasSelector.constData(), (void *)this, 1, &keyboard_cb);
emscripten_set_keyup_callback(canvasSelector.constData(), (void *)this, 1, &keyboard_cb);
```

只註冊 `keydown` / `keyup`。**沒有註冊 `compositionstart` / `compositionupdate` / `compositionend` / `beforeinput`。**

而 fcitx（以及所有作業系統層的輸入法）在瀏覽器裡是透過那組 composition DOM 事件把組好的字送進頁面的。沒有監聽 = 組好的中文永遠不會抵達應用程式。

### 2. input context 只有殼，沒有 wasm 實作

`qwasmintegration.cpp:232-239`：

```cpp
QString icStr = QPlatformInputContextFactory::requested();
if (!icStr.isNull())
    m_inputContext.reset(QPlatformInputContextFactory::create(icStr));
...
QPlatformInputContext *QWasmIntegration::inputContext() const { return m_inputContext.data(); }
```

只有在 `QT_IM_MODULE` 明確指定、且該 IM plugin 有被編進 wasm 時才會建立 —— 兩個條件在 wasm build 都不成立。

而且這個 fork 的 wasm plugin 目錄裡**沒有任何 input context 檔案**：

```
qwasmbackingstore  qwasmclipboard  qwasmcompositor  qwasmcursor  qwasmeventdispatcher
qwasmeventtranslator  qwasmfontdatabase  qwasmintegration  qwasmoffscreensurface
qwasmopenglcontext  qwasmscreen  qwasmservices  qwasmstring  qwasmtheme  qwasmwindow
                                   ↑ 沒有 qwasminputcontext
```

**Qt 6 的 wasm plugin 有 `qwasminputcontext.cpp`** —— 它用一個隱藏的 `<input>` 元素接收 composition 事件，正是為了解決這個問題。Qt5 沒有回移。

### 3. LibreOffice 這邊其實準備好了

`vcl/qt5/QtWidget.cxx:579` 的 `QtWidget::inputMethodEvent()` 完整處理了 preedit / commit / 屬性範圍：

```cpp
void QtWidget::inputMethodEvent(QInputMethodEvent* pEvent)
{
    const bool bHasCommitText = !pEvent->commitString().isEmpty();
    ...
    aInputEvent.maText = toOUString(pEvent->preeditString());
```

`QtFrame.cxx:779` 也有 `m_pQWidget->setAttribute(Qt::WA_InputMethodEnabled)`。

**LO 側完全就緒，只是那些事件永遠不會被送出來。**

## 結論

這在 **Qt5 路線上無法修**，除非把 Qt6 的 `qwasminputcontext` 回移到 allotropia 的 `5.15.2+wasm` fork。

對任何以 CJK 為目標的 LOWA 應用來說，這是硬性阻斷 —— 使用者連字都打不進去。

## 這對 Qt5 / Qt6 選擇的影響

見 [`../wasm-lite/README.md`](../wasm-lite/README.md) §5.4。原本的判斷是「Qt6 缺文件與驗證，不值得賭」。
本項發現改變了權重：**Qt5 路線對繁中應用有一個無法繞過的功能缺口**，而 Qt6 的 wasm plugin
在設計上有解。若專案目標是中文編輯，Qt6 從「風險較高的選項」變成「唯一可能的選項」。

## 還缺什麼才能送

- [ ] 在 `build-stock`（純上游組態）上覆驗一次
- [ ] 實測 Qt6 wasm 是否真的能輸入中文（需要先讓 LO 的 Qt6-WASM 路徑跑起來，見 README §5.4）
- [ ] 搜尋 Bugzilla / bugreports.qt.io 是否已有重複
- [ ] 決定要報到 TDF 還是 Qt（或兩邊）

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | Writer（或 framework；送出前查證） |
| Version | 26.8.0.1 rc |
| Hardware / OS | All / All |
| Summary | WASM/Qt5: no input method support — CJK (and any IME-based) text input is impossible |

## 時間軸

- 2026-07-31 在 `build-t3` 的可用建置上實測，fcitx 打中文無反應；追到 Qt5 wasm plugin 缺 input context
