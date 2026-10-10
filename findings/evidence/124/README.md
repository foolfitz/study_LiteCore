# Findings 124 and 125: arrow keys on a long document (owner hand test, host 0.2.11, 2026-10-10)

The owner, hand-testing host 0.2.11 (2026-10-10), verbatim: "在長文件中，透過「下」方向鍵使游標往下移動時，畫面不會跟著捲動" and "使用方向鍵移動游標，「處理中」就會一直閃爍，但內容明明沒有變更".

Read before measuring (page `web/e2-editor-app.js` = dist `36c2b18b…`): the sink's keydown handler maps ArrowUp/Down/Left/Right/Home/End to engine actions (`KEY_ACTIONS`, :1998–2005) and calls `preventDefault()` (:2120, before `editorAction` at :2121), so the browser's own scroll-the-caret-into-view never runs; nothing in the page scrolls `#desk` (no `scrollIntoView`/`scrollTop` call outside comments). The state pill shows `處理中` for the session state `busy` (:616), and every engine command — a caret move included — passes through `busy`.

## Probe and predictions (written before the runs)

`tools/probe_124_125_arrows.py`: the shipped standalone page from `dist/` (no product byte changed; mirror only, no shim), the owner document (`PMPC指南.odt`, 22 pages), caret placed inside the first body paragraph (`0.5, 0.010373`, the production-UI runner's `IN_TEXT`), then **40 real ArrowDown presses** one at a time (Chrome CDP `Input.dispatchKeyEvent`, Firefox WebDriver actions), each followed by waiting for the page to be idle; then, as a control, **5 typed letters** the same way. After each press it reads `#desk.scrollTop`, the desk's and the sink's client rectangles, the revision and the pill; throughout, a MutationObserver logs every pill text change with its time.

Predictions, both browsers, default headless window:

- **124**: `#desk.scrollTop` is the same after every press as before the first; the sink's top moves down by about one line per press and leaves the desk's visible rectangle after roughly (visible desk height / line height) presses, about 10–25, and stays outside for the rest; the revision does not change during the 40 presses.
- **125**: each ArrowDown produces exactly one `處理中` → `就緒` pair on the pill (40 pairs, ±2 for a press that lands while the pill is still busy), each `處理中` lasting 10–80 ms; the revision does not change. Control: the 5 letters also produce one pair each and move the revision by +5 — the pill reports engine commands, not document changes.

If 124's prediction misses (the desk does scroll), the owner's report came from something this probe does not reproduce (window size, the host page) and is re-measured there before anything is changed.

## First run (Chrome, default window; `arrows-chrome.json`, exit 0)

- **125 as predicted**: 40 ArrowDown presses → 40 `處理中` flashes (31.7 / 34.9 / 42.1 ms min / median / max), revision 0 throughout; the 5 letters → 5 flashes and revision 0 → 5.
- **124 not testable in this window**: the headless default 800 × 600 leaves the desk 139 px tall (client rect 325.4–464; the standalone page's header and status rows take the rest), and the caret placed in the first body paragraph was already below it (sink top 530 > desk bottom 464) before the first press. `scrollTop` stayed 0 through the 40 presses and the 5 letters — so the view followed neither the arrows nor the typing — but "the caret leaves the view after 10–25 presses" could not happen. Not counted as a hit or a miss; the window is fixed below and the run repeated.

## Second run: `--window 1400x1000` (prediction written before the run)

Desk about 1000 − 325 − 136 ≈ 540 px tall (the same header and status rows), the caret line starting about 185 px into the paper, about 23 px per line: the caret is visible after the click and leaves the desk after about 10–20 presses; `scrollTop` stays 0 for all 40 presses; the letters typed while the caret is below the view do not scroll it either (as in the first run). 125 as before: 40 flashes, 5 for the letters. Both browsers.

### Second run results (2026-10-10, `arrows-{chrome,firefox}-1400x1000.json`, both exit 0; page `36c2b18b…`)

| | Chrome | Firefox |
| --- | --- | --- |
| desk `scrollTop` before / during 40 ArrowDown / after 5 letters | 0 / {0} / 0 | 0 / {0} / 0 |
| first press with the caret (sink) outside the desk | **15** | **12** |
| presses with the caret outside | 26 of 40 | 29 of 40 |
| revision during the presses / after the letters | 0 / 5 | 0 / 5 |
| `處理中` flashes during the 40 presses | **40**, 33.7 / 35.0 / 61.8 ms | **40**, 35.9 / 41.3 / 43.1 ms |
| flashes during the 5 letters | 5 | 5 |

Both predictions hit (124: the caret leaves after 10–20 presses and the view never moves; 125: one flash per press, 10–80 ms, revision unchanged). Every step was quiet before the next press; the sink kept focus throughout.

## How Collabora Online does it (`cool-26-04`, read 2026-10-10; prior art, no code taken)

- **Following the caret**: on each cursor invalidation, `_onInvalidateCursorMsg` (`browser/src/layer/tile/CanvasTileLayer.js` :1854–1922) compares the new cursor rectangle with the last one and calls `_onUpdateCursor(scroll = changed && caused by this view)`. `_onUpdateCursor` (:3082–3135) scrolls only when the rectangle's top-left or bottom-right is outside the displayed area, and `scrollToPos` (:3027–) works per axis: an axis on which the cursor is already visible does not move; otherwise the cursor is put in the **middle** of the view on that axis (cursor − half the view, clamped at 0). A state update that does not move the cursor never scrolls, so a user who scrolled away with the wheel is not pulled back until the cursor moves. Not during a "complex" selection (`_allowViewJump`, :3022).
- **Busy**: there is no per-command busy indicator. A busy popup exists only for long operations named by the caller (saving, downloading, uploading, reconnecting, core's status indicator; `showBusy` callers), and even then it opens **700 ms** after it is asked for and is cancelled if the operation ends first (`browser/src/control/Control.UIManager.ts` :644–689). A key press never shows anything.

## The probe extended for spec §17's 124-B / 125-B, and its red run on the P page (2026-10-11)

`probe_124_125_arrows.py` now also logs `#state-shown` (when present), reads which pill is shown, scrolls the desk back to the top with a real wheel event between the arrows and the letters (Chrome CDP `mouseWheel`, Firefox WebDriver wheel actions), and prints `verdict124B` / `verdict125B` as §17.4 words them. Run once on the P page (`dist/` = `36c2b18b…`) before any C′ page exists, as §17.5 requires — `v2-red-p-page-{chrome,firefox}-1400x1000.json`:

- **124-B FAIL in both browsers** (as required): the sink is outside the desk from press 14 (Chrome) / 11 (Firefox) on — "wholly inside" is one press stricter than the first run's "not overlapping" — and after the first letter. The wheel segment reads 0 / 0 / 0 here (the P page never scrolled), so it is exercised only on a page that follows the caret.
- **125-B FAIL in both browsers** (as required): no `#state-shown`. The positive control holds: `#state-pill` was written 處理中 85 times (the observer logs every write, including repeats of the same label, so this counts writes, not flashes; the requirement is ≥ 40).
