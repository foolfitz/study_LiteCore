# Finding 128 — evidence: after a Delete/Backspace the deleted character stays on screen for about 120 ms after the caret has moved

Reported by the owner in the hand test of host 0.2.12 (2026-10-12): "delete / backspace 刪去文字的時候會有殘影". Reproduced the same day on the host (`litecore` 0.2.12 `b245ae7`, served page `8909564e…`, shell v61 `f48df85b…`, engine v19; each report's `static` block), with `wasm_sdk_probe/tools/probe_hand_test_0212.py` (not a counted runner; no product byte touched). The owner's document (`PMPC指南.odt`, the production-UI runner's gitignored copy, sha256 `7b336879…`) was uploaded as `probe-hand-0212.odt`; desk 1850 × 980 CSS px, devicePixelRatio 1, canvas 900 px wide, document 22,257 rows, the canvas window 4,092 rows = 4 bands of 1,023.

## Files

| File | What |
|---|---|
| `chrome-1.json` | Chrome, arms `high`, `low`, `selection`, `shift` (2026-10-12 01:37–01:39 UTC). Written by the probe before the Worker trace was added (the instrument is the same; the later versions only add the trace and `window.__h_t0`) |
| `chrome-trace-3.json` | Chrome, arm `high` with the Worker message trace (`trace`), the paint's region and the failed reply's error object (01:44–01:45 UTC) |
| `firefox-1.json` | Firefox 157.0.1, arms `high`, `low`, `selection`, `shift` (01:46–01:47 UTC). No Worker trace: it is injected with CDP `Page.addScriptToEvaluateOnNewDocument` |

Probe at the time of `chrome-trace-3` and `firefox-1`: sha256 `c0c1d54b…`.

## The reading

State, not pixels. `#canvas[data-bands]` lists each cached band as `index:top:rows:label`, where `label` is the page's change counter when the band was asked for; the page writes it right after painting a band (`publishWindow` after `paintBand`). `#canvas[data-changes]` is the counter. The sink rides the caret. Per key: `caretMovedMs` (keydown → the sink moved), `caretBandFreshMs` (keydown → the band under the caret carries a label at least the counter's value once that key's operation was done), and their difference `staleAfterCaretMs` — the time the old text is drawn with the caret already moved: the ghost the owner saw. Arms: `high` = the caret in the first band under the view (row 229, band 0); `low` = the caret in the second band under the view (row 1338, band 1, band 0 also visible). Each arm types eight letters, then four single Backspaces (each allowed to settle), then four Backspaces 50 ms apart.

## Results

| | Chrome high | Chrome low | Firefox high | Firefox low |
|---|---|---|---|---|
| caret moved after keydown | 44–55 ms | 39–45 ms | 45–59 ms | 46–63 ms |
| single keys, `staleAfterCaretMs` | 122–125 | 131–133 | 126–128 | 134–143 |
| rapid keys, `staleAfterCaretMs` (max) | 125 | 139 | 129 | **283** |
| type eight, delete eight: view pixels before vs after | 0 of 738,000 differ | 0 of 738,000 | 0 of 750,600 | 0 of 750,600 |

So the ghost is **transient** — nothing is left on the canvas once the keys stop — and it lasts about 120–140 ms per key in both browsers, up to 283 ms under rapid keys in Firefox when the caret is in the second band of the view.

## The cause, read from the Worker trace (`chrome-trace-3.json`, 4 of 4 keys)

For each Backspace:

1. 0.6–0.9 ms: `editorActionV2` (`delete-backward`) is posted.
2. 34.6–35.5 ms: the engine emits `document-invalidated` **before** the action has returned; the page's `onEvent` starts a repaint pass at once and posts `paint` for band 0.
3. 39.0–43.7 ms: the paint is answered `ok: false`, `{"code":"BUSY","message":"a verified selection delete is still in flight","operation":"selection-barrier"}`.
4. 44.0–44.5 ms: the caret's state update arrives and the overlay moves the caret left — over the character that is still drawn.
5. 44.6–45.2 ms: `editorActionV2` returns (a second `document-invalidated` just before it); `run()` bumps the counter and asks for a repaint, but a pass is still marked as running, so it only sets `renderAgain`.
6. `renderDocument`'s BUSY branch waits a **fixed 120 ms** (`wasm_sdk_probe/web/e2-editor-app.js:1238`, `setTimeout(resolve, 120)`) with `rendering` still set. Measured: the next `paint` is posted 120.2–120.4 ms after the BUSY reply, with no Worker traffic in between and no long task on the main thread (a `longtask` PerformanceObserver recorded none).
7. The next pass's first `paint` is posted at 159.3–164.1 ms; the four bands then come back in 6.5–12 ms each.

So about 110 of the ~125 ms are the page waiting out a back-off for a barrier that had already finished. The engine's paint itself is not slow.

Not measured here: whether typing (insert-text, which goes through no selection barrier) ever meets the same BUSY; whether a Delete key (forward) behaves the same (its action is boundary-capable and goes through the same session path — expected, not run).

## Positive controls

- The reading moves when the thing it reads moves: the band labels advance after every key (e.g. 23 → 32 → 35 in `chrome-1.json` `high.rapidLog`), and `low`'s fresh band is index 1 while `high`'s is index 0.
- The persistent-ghost comparison is not vacuous: each snap covers the visible rows (738,000 pixels in Chrome), and it was taken with the caret back at the same place, so a difference in the caret area would have counted.
- H2 (band order: the caret's band waits behind the bands above it) was the hypothesis written into the probe before the run; it predicts `low` ≫ `high`. Measured: `low` is 8–15 ms longer per single key, not a band's worth — H2 is not the cause of the ~120 ms. It may contribute under rapid keys (Firefox low 283 ms), not separated here.
