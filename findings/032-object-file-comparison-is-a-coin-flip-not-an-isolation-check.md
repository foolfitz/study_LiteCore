# 032 — 用目的檔逐位元比對驗證隔離是擲硬幣，不是檢查

| | |
|---|---|
| **狀態** | **已確認（同源同旗標 8 次重編，兩種輸出各 4 次）／我已用它做過三次錯誤保證** |
| **Bugzilla** | — |
| **發現日** | 2026-08-11 |
| **嚴重度** | 一般偏高（不影響產品；但讓一個被反覆引用的驗證方法失效，且我已據此下過保證） |
| **可重現** | 100%（重編就會擲一次） |
| **是否上游** | **未確認**（emscripten／LLVM 的最佳化階段；本輪未定位，也未回報） |

## 摘要

本專案（含我本輪）多次用「關掉旗標重編，目的檔與既有的逐位元相同」來證明某個改動被
`#ifdef` 隔離乾淨、凍結 artifact 不受影響。

**這個檢查不可靠。** 同一份原始碼、同一組旗標、同一台機器連編 8 次，得到**兩種**目的檔，
各出現 4 次，差異固定是 **37 個 byte、固定落在 offset 23963**，檔案長度相同。

也就是說：**檢查通過與否有一半是運氣。** 我先前兩次「逐位元相同」的通過報告，
各自只是擲中了同一面。

## 重現

```bash
cd wasm_sdk_probe
for i in 1 2 3 4 5 6 7 8; do
  ../wasm-lite/tools/emsdk/upstream/emscripten/em++ \
    -DLOK_USE_UNSTABLE_API -I../libreoffice-26-8/include \
    -I../wasm-lite/build-headless-probe/config_host \
    -I../wasm-lite/build-headless-probe/workdir/UnoApiHeadersTarget/udkapi/comprehensive \
    -I../wasm-lite/build-headless-probe/workdir/UnoApiHeadersTarget/offapi/comprehensive \
    -I../wasm-lite/build-headless-probe/workdir/UnpackedTarball/boost \
    -Oz -pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm \
    -DOXSDK_EDITOR_DISCOVERY -DOXSDK_FINDING_016_SELECTION_BARRIER \
    -c src/probe_engine.cpp -o /tmp/o$i.o
done
sha256sum /tmp/o*.o | sort | uniq -c -w 12
```

實測：

```text
4  a47a8cb2c4c3…
4  d57e5069ea55…
```

那組旗標**就是 `Makefile:420-422` 給 `$(E1_B_BUILD)/%.o` 的旗標**，不是我自己拼的特殊組合。

差異位置逐次相同，內容是 WASM 指令位元組（不是字串、不是路徑、不是時間戳）：

```text
A: … \x10\xd5\x81\x80\x80\x00 \x01A\xd0\x01j …  ("\x06@" 之前少一個 block)
B: … \x10\xd5\x81\x80\x80\x00\x06@ \x01A\xd0\x01j …
```

看起來是最佳化階段的分支／區塊順序在兩個等價形式之間跳，**未定位到哪一個 pass**。

## 這推翻了什麼

**我在本輪（2026-08-11）用這個方法下過三次保證，全部要降級**：

1. finding 030 的派送形式修正——「`OXSDK_E2_FORMAT_BARRIER` 關閉時 E1-B 目的檔逐位元不變」。
2. finding 031 的 locale profile——同上。
3. 本輪 readback barrier——同上（這次擲到另一面，**才因此發現**）。

三次的**結論仍然正確**（見下），但**當時給的理由不成立**。

E2-A 10.6 節記載的
「`OXSDK_MAINLOOP_ENGINE` 區塊以旗標關閉時 E1-B 組態目的檔逐位元不變驗證」
是同一個方法，**同樣要降級**。該次結論本身未受本單影響，但它的證據力只有一半。

## 正確的檢查是比對前置處理後的翻譯單元

隔離要證明的是「在那個組態下，編譯器看到的原始碼一模一樣」。那正是
`-E -P` 的輸出，而它**不受 codegen 不確定性影響**：

```bash
em++ <同一組 -I 與 -D，去掉 -Oz/-c> -E -P src/probe_engine.cpp -o now.i
git show HEAD:wasm_sdk_probe/src/probe_engine.cpp > src/__head.cpp   # 要放在 src/ 底下，
em++ … -E -P src/__head.cpp -o head.i                                # 相對 include 才找得到
cmp head.i now.i
```

本輪 readback barrier 以此驗證：**4,355,327 bytes 逐位元相同**。
這比目的檔比對**更強**（直接證明的就是隔離本身），而且可重複。

`-P` 會去掉行號標記，所以純行號位移不會誤報——這正是我們要的，
因為行號位移本來就不影響隔離。

## 未驗證（不要當成已知）

- **連結後的 profile 雜湊會不會也跳。** 本單只量了目的檔。若會跳，
  「重編凍結 artifact 應得到相同 hash」這條紀律要重新檢討；若不會（連結器把差異吸收掉），
  那影響僅限於目的檔層級的檢查。**這一項沒量，不要憑本單推論。**
- 其他翻譯單元（`sdk_api.cpp` 等）是否也有同樣現象。
- 是哪一個最佳化 pass、是否與 `-Oz`／`-fwasm-exceptions`／`-pthread` 有關。
- emscripten／LLVM 版本相關性；本輪只有一個工具鏈（`wasm-lite/tools/emsdk`）。
- **是否為上游缺陷。** 未確認前不送。

## 量測紀律

**一個有一半機率通過的檢查，比沒有檢查更糟**——它會產生「已驗證」的紀錄。
判斷一個驗證方法可不可靠，最便宜的方式是**對已知不變的輸入跑兩次**：
同輸入兩次結果不同，那它量的就不是你以為的東西。
本專案已有一條相近的紀律（「不能印出不同值的探針不是探針」），
本單是它的反面：**對相同輸入印出不同值的檢查，也不是檢查。**

## 相關

- [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)、
  [031](031-styleapply-postcondition-compares-a-localized-ui-name.md)——本輪被降級的三次保證。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 10.6 節——更早的同方法保證。
