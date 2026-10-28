# 170：原生 M1 harness 寫完最後一筆紀錄後以 exit 1 結束，stderr 留一行 `Unspecified Application Error`

| | |
|---|---|
| **狀態** | 已觀察（2/2）／成因**未查** |
| **Bugzilla** | — |
| **發現日** | 2026-10-28（第一次在 M1 run-01，重跑 run-02 重現） |
| **嚴重度** | 小——只在原生 harness 的程序收尾；所有紀錄與存檔都完整、讀取工具判 `M1_PASS` |
| **可重現** | 2/2（同一個 binary、同一套程序） |
| **是否上游** | **未確認**——可能是 LOK 在沒有 `destroy` 的程序結束路徑上的行為，也可能是這支 harness 自己的收尾；沒有追到呼叫者之前不能說 |

## 現象

`wasm_sdk_probe/tools/f168_native_insert_text_m1.cpp`（M1：對原生 LOK 26.8 用 `bNotifyWhenFinished=true` 送 `.uno:InsertText`，記錄 `UNO_COMMAND_RESULT`）跑完 3 回 × 38 臂、印出最後一筆紀錄之後，程序以 **exit 1** 結束，`native.stderr` 最後一行是 `Unspecified Application Error`（整個檔案只出現這一次）。harness 的 `main` 只會回傳 0（全部成功）或 5，所以這個 exit 1 不是 harness 自己回的。

同一天其他四次原生執行、以及原生 run-03（別的 harness，沒有用 notify 模式送 `.uno:InsertText`）都是 exit 0，也沒有這一行。

## 證據

- 第一次：`evidence/link-batch-v23/feature-protocol/s5-type-route-ruling/m1-run-01/`（`completion.json` `exitCode: 1`；裁決 1 的 M1 結果段當時記為「異常，未調查」）。
- 重跑：`evidence/link-batch-v24/pre-count/m1-rerun/run-02/`，同一個 binary（`62860ff0…31b5`）：`exitCode: 1`、125 筆紀錄、228 份存檔，`m1-reader-02.json` 判 `M1_PASS`。

## 分析（只讀碼）

- `Unspecified Application Error` 是 `SalAbort` 在錯誤訊息為空時印的字（`libreoffice-26-8/vcl/source/app/salplug.cxx:348`），所以是有東西以空訊息呼叫了 `Application::Abort`。
- harness 從頭到尾沒有呼叫 `kit->pClass->destroy`，`main` 直接回傳，LOK 在靜態解構／程序結束時自己收尾。
- 這支 harness 是第一支用 `bNotifyWhenFinished=true` 送 `.uno:InsertText` 的；兩者是否有關**不知道**。

## 對本樹的影響

- 不影響任何已記錄的量測：每一筆紀錄與存檔都驗過雜湊，判讀結果兩次都是 `M1_PASS`。
- 產品（WASM，unipoll）不會這樣拆掉 LOK，所以不擋 v24。
- **在引擎於關閉時依賴 notify 模式的結果之前**，要先查出是誰在結束時呼叫了 `Abort`（例如讓 harness 在回傳前呼叫 `destroy` 做對照，或在 `SalAbort` 下中斷點看呼叫堆疊）。
