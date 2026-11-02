# 178：product path runner 的 `format_arm` 每臂按兩次格式鈕，v29 快到第二按會反向

> 狀態：**已定案**（2026-11-01）。缺陷在我們自己的 runner，不在產品，也不在上游。
> 證據：`findings/evidence/v29-177/f3-83/`、`findings/evidence/v29-177/t3/format-toggle/`

## 現象

切到 v29（第 83 代）後，F3 唯一移動的一格：Firefox `clear-format-removes-every-inline-format` 由 PASS 變 NOT_ESTABLISHED，4 次全中。Chrome 2 次沒事。每次壞的臂不同，形狀是「按之前快取已經是 `true`，於是 toggle 送出 OFF」。

## 成因〔實測〕

`tools/run_e2_c_product_path.py` 的 `format_arm` 在 `:6765` 與 `:6834` 各按一次格式鈕，相隔 3–10 ms。工具列的請求值來自快取（`enabled: formatStateFor(action) !== true`）：

- v28：回覆約 25 ms，第二按送出時快取還沒動，兩按都是 ON，沒有人看得出來。
- v29：回覆約 3 ms，第二按讀到新快取，送出 OFF，把第一按取消。

```
221968.6 set-italic true
221970.9 format-state [bold, italic]
221977.8 set-italic false     ← 第二按
```

第一按是 2026-08-23（`c82a64289`，finding 077 那輪）留下的，當時加了完成訊號與快取紀錄，舊的按鍵行沒有刪。藏了十週，靠的是引擎夠慢。

## 判定

**不是產品缺陷，不是 v29 退化。** 使用者一次只按一下。

決定性實驗：預測先 commit（`7aca664aa`），只在記憶體裡拿掉第一按，其餘不變。Firefox 3 次、Chrome 1 次，**46 格全部等於 F3-82**，13 臂全對；`read_v83_f3_equal.py` 為 `F3_83_EQUAL`，self-test `ALL_RED`。同一批位元組上，有第一按時 Firefox 4/4 紅，所以這也是這個結論的紅案。

## 繞過的路

這格我判錯兩次，記下來是因為下一次還會想走同一條路：

1. 我先認定是「runner 插進清除迴圈」，並 commit 了「不是 v29 退化」。那個競態是真的（`format-toggle/`），v28 上的發生率還更高，但**不是這一格的原因**：改掉等待後 Chrome 也紅了。結論碰巧對，理由是錯的，已在證據裡更正。
2. 我的重現工具跑了 720 臂都沒有重現，因為它是我**照著讀到的流程重打一遍**，而我把那行看成無關的舊碼沒抄。缺陷正好在沒抄的那行。把 log 放進真正的 runner 之後，第一次跑就看到一按送兩個請求。

## 處置

- 被綁的 `run_e2_c_product_path.py` 不改。第 83 代的 F3 讀法改走 `diag_single_press.py`（`SPEC-M3-v29-tick-pacing` 追加 4）。
- **下一份 K 規格必須帶這個單按替換**，否則 K7 在 v29 上會無故紅。
- 另一個競態仍在：runner 等「清除格式」標籤，第一步就滿足。v29 上自然發生率 2/120（Firefox）、0/120（Chrome），v28 是 8/120、4/120。下一份 K 規格一併改等 toast。產品面：按清除後緊接著按格式鍵，可能被清除迴圈蓋掉；長文件上這個窗口 v28 約 470 ms、v29 約 20 ms，人碰不到，不處理。

## 追加（2026-11-03）：v31 上同一個競態又讓 F3 移動一格

F3-86 run-01 的 Firefox `every-inline-format-reaches-the-document` 由 PASS 變 NOT_ESTABLISHED，`MKSTROFF` 的前置條件沒建立。這是本文件「另一個競態仍在」那一段，不是 v31 的缺陷。

- **直接證據**（`evidence/demo-batch-3/f3-86/race/natural-v31-firefox.json`，`MKSTROFF1`）：`set-bold false`（清除第 1 步）、`set-strikethrough false`（runner 的按鍵，快取還是 true）、`set-italic false`（第 2 步）、`set-strikethrough true`（受測按鍵）、`set-underline false`（第 3 步）。runner 按進了頁面自己的迴圈。
- **發生率沒變**：同一頁面、同一殼層換引擎，Firefox v31 1/120、v30 3/120（v29 當時 2/120），Chrome v31 0/120。清除迴圈寬度中位數 v31 53 ms、v30 56 ms。
- **原工具不是每次都紅**：同一批位元組 Firefox 4 輪 1 輪紅。所以「改等 toast 之後 4 輪全過」本身鑑別力不足（發生率 1/4 時連過 3 輪有 42% 是運氣），定案靠的是上面的請求序列，不是那 4 輪。
- **F4 看不到這格**：`f4-86/firefox` 同一格也是 NOT_ESTABLISHED，F4 只判四臂，所以仍是 24/24。這次是普查歷次報告才看到的。

**處置**：F3-86 的閘門讀 `diag-clear-wait/equal.stdout.txt`（等 toast），run-01 的紅留著。下一代的 F3 runner 直接帶等 toast 的替換，否則這格會隔幾輪就紅一次，每次都要重查。
