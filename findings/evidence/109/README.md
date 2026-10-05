# Finding 109 — evidence

Reported by the owner on 2026-10-05 (`owner-screenshot-2026-10-05.png`: `PMPC指南.odt` on the dev instance, status bar `restart-required`, `檢查點 無`, `上次操作 ⌦ 前刪 失敗`, notice 「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。」). Reproduced the same evening.

**Setup.** Dev instance `https://litecore.ddev.site:8443`, host `litecore` 0.2.5 (`7420418`), the shipped product page; Chrome 151.0.7922.169 driven over CDP by `probe.py` (the M3 harness's login and page helpers; real keys through `Input.dispatchKeyEvent`). Each arm opened its own copy of the owner's document (`repro-109-a..d.odt`, copied over WebDAV; the owner's own file, which was open in their browser, was not touched). Clicks are fractions of the canvas (900 × 18551 CSS px): `(0.5, 0.0115)` is inside the first body paragraph, `(0.693, 0.00728)` is the blank right of the heading 「一、序言」 (caret at the end of that paragraph), `(0.127, 0.00927)` is the first-line indent of the first body paragraph (caret at its start).

| arm | steps | result |
| --- | --- | --- |
| a | click in text, type `xy` (revision 0 → 2, unsaved), click end of heading, toolbar `delete-forward` (「⌦ 前刪」) | `restart-required`, checkpoint 「無」, toast `EDITOR_BOUNDARY_UNSUPPORTED：one Writer unit did not produce a safe single-line text selection; no mutation was dispatched; start a fresh Worker`; the paragraph separator left selected (`arm-a-after.png`, the same highlight as the owner's screenshot). This arm's file had been opened by a calibration run just before, whose lock had not expired, hence the host's "open in another window" bar in the screenshot; arms b–d used fresh copies. |
| b | as a, but the keyboard **Delete** key | the same (`⌦ 前刪 失敗`, `restart-required`, checkpoint 「無」) |
| c | type `xy`, **Backspace** mid-paragraph (positive control: revision 2 → 3 in 87 ms), click start of the paragraph, **Backspace** | the control deletes; the boundary Backspace gives `⌫ 刪除 失敗`, `restart-required`, checkpoint 「無」 |
| d | as a, then press 「儲存 ODT」 | refused: `EDITOR_NOT_READY：editor operation save is unavailable in restart-required`; no toolbar button is disabled in that state. The notice offers only 「重新開啟」, which reloads the last saved bytes: the unsaved `xy` is gone. |

Each `arm-*.json` holds every step's status-bar state as the page shows it.

**Where.** The engine refuses before mutating and says so (`wasm_sdk_probe/src/probe_engine.cpp`, the selection barrier's `EDITOR_BOUNDARY_UNSUPPORTED`, ~:3396), but asks for a fresh Worker because the barrier's selection is left in place. The shell maps every `EDITOR_BOUNDARY_UNSUPPORTED` to "restart" (`editor-shell-v2/paragraph-editor-session.js`, `recoveryFor`) and blocks the queue as `restart-required` (`editor-shell/editor-session.js`, ~:319); a save is then refused. A checkpoint is taken before boundary-capable **moves** (`narrow-editor-v2-session.js`, `BOUNDARY_CAPABLE_MOVES`), not before deletes, so a user who placed the caret with the mouse has none.

Not measured: Firefox; the a11y core; whether the worker could still serialise the unchanged document at that point.
