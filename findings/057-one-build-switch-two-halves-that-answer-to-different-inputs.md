# 057 — 同一個開關的兩半接到不同的輸入:`--with-wasm-module` 改得動物件,改不動巨集

| | |
|---|---|
| **狀態** | **已確認（configure.ac 窮舉閱讀）／未修** |
| **Bugzilla** | —（**是上游**;但送出作業暫停中,見 `upstream-submissions-on-hold`） |
| **發現日** | 2026-08-17(追查 finding 056 的機制時掉出來的) |
| **嚴重度** | **中**——它讓 056 的處方失效:照著 configure 的說明去開 accessibility,開不起來 |
| **可重現** | 窮舉閱讀 `configure.ac`(符號全樹只出現 5 次) |
| **是否上游** | **是**（`libreoffice-26-8`,未改動的上游原始碼） |

## 現象

`ENABLE_WASM_STRIP_ACCESSIBILITY` 在建置系統裡有**兩個獨立的存在**:

| | 決定什麼 | 由誰決定 |
|---|---|---|
| **Make 變數** | accessibility 的**物件編不編** | `--with-wasm-module`(`configure.ac:4372/4379/4386`) |
| **C++ 巨集** | accessibility 的**呼叫端編不編** | `--enable-wasm-strip`(`configure.ac:3498`) |

兩者同名,但接到**不同的輸入**,而且沒有任何一行讓它們互相同步。

窮舉:這個符號在 `configure.ac` 裡總共只出現 5 次——

```
3498:    AC_DEFINE(ENABLE_WASM_STRIP_ACCESSIBILITY)      <- C++ 巨集,唯一一次
4372:        ENABLE_WASM_STRIP_ACCESSIBILITY=TRUE        <- Make 變數
4379:                ENABLE_WASM_STRIP_ACCESSIBILITY=    <- calc 清掉
4386:                ENABLE_WASM_STRIP_ACCESSIBILITY=    <- impress 清掉
4413:AC_SUBST(ENABLE_WASM_STRIP_ACCESSIBILITY)           <- 只導出 Make 變數
```

`AC_DEFINE` 只有一次,而且在 `if test "$enable_wasm_strip" = "yes"`(`:3458`)
底下。4371–4392 那個 module 迴圈**一行 `AC_DEFINE` 都沒有**——它只指派 shell 變數。

## 後果:一個編了東西進去卻用不到的組態

`--with-wasm-module` 的**預設值就是 `'calc writer'`**(`configure.ac:2322-2326`)。
在那個預設值下:

- `calc` 走到 `:4379`,把 **Make 變數**清掉 → `sw/source/core/access/` 的 26 個物件
  **會被編進去**
- 但 `enable_wasm_strip` 在 Emscripten 上於 `:1280` 被**無條件指派為 `yes`**,
  所以 `:3498` 的 `AC_DEFINE` 照樣執行 → **C++ 巨集是 1**
- 於是 `SwEditWin::CreateAccessible()`(`sw/source/uibase/docvw/edtwin.cxx:6532-6542`)
  仍然直接回 `{}`

**編進去了,而且永遠不會被呼叫。**

`:1280` 是無條件指派,不是「使用者沒指定才給預設」,所以命令列上的
`--disable-wasm-strip` 在 Emscripten 上**會被覆蓋掉**。也就是說:

> **在 26.8 的 Emscripten 上,沒有任何 configure 旗標組合能讓 Writer 的 LOK
> accessibility 真的運作。**

## 這對 056 的意義

原本我以為 056 的處方是「把 `calc` 加回 `--with-wasm-module`」。**那是錯的**,
而且是這一格把它擋下來的:加 `calc` 只會讓物件被編進去,呼叫端仍然被巨集拿掉,
換來的是體積,不是能力。

真正的處方是**改原始碼**:讓 `AC_DEFINE` 跟著 module 決策走(或把
`:1280` 改成「使用者沒指定才預設」),然後**重編 core**。

## 判準與極限

- **這一格是窮舉閱讀出來的,不是量測出來的。** 這台機器上三個 wasm build 全都是
  `--with-wasm-module=writer`,兩半**一致**(都是 strip),所以分歧本身**沒有被
  觀測到**。
- **否證條件**:跑一次 `--with-wasm-module='calc writer'` 的 configure,若產出的
  `config_wasm_strip.h` 是 `0`,這一格就不成立。**還沒跑。**
- 之所以敢用「已確認」:符號在 `configure.ac` 全檔只出現 5 次,五處都讀過,
  中間是直線 shell,沒有分支能讓 `AC_DEFINE` 被撤銷。這是閱讀能給的最強形式,
  但它仍然不是一次 configure 執行。

## 相關

- [[056]] —— 這一格是追 056 的機制時掉出來的;056 說「兩邊不一樣」,這一格說
  「為什麼照說明去修會修不好」
- 對抗性審查由 codex 做(2026-08-17)。**這一格是 codex 找到、而我原本判錯的**:
  我原本主張「上游預設的 `calc writer` wasm build 有 Writer a11y」,codex 指出
  `AC_DEFINE` 不受 module 迴圈影響。經我自己窮舉核對後成立。
