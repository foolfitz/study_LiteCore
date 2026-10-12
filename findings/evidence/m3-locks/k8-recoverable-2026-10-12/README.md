# K8 `frozen` ends in `recoverable-error` on 0.2.13 (finding 133)

## What stopped the count

The 0.2.13 count chain (`findings/evidence/m3-production-ui/runs-0.2.13/chain-2026-10-12.out`) stopped at the `locks` shakedown: 21 of 22 cells passed, **K8 `frozen` (Chrome) 0/1** (`../shakedown/2026-10-12T113020+0000.json`). After the page had been frozen (`Page.setWebLifecycleState frozen`) for about 330 s and thawed, the session was in `recoverable-error`; the save the arm presses was refused (`EDITOR_NOT_READY`), and no PUT reached the server (`serverAfter` = `serverBefore`). No counted run started.

History: K8 had run 27 times since 2026-09-28 (counted and shakedown, every page up to 0.2.12, and this morning's witness on the pre-fix 0.2.13 page `c7f904fa…`), always ending `ready` with the save landed.

## Probe

`wasm_sdk_probe/tools/probe_k8_frozen_recovery.py` runs the locks runner's own `run_arm("frozen", "chrome", …)` unchanged and adds CDP logpoints (conditional breakpoints whose condition is `console.log(...), false`; they never pause) at: `editor-session.js` `_blockQueue` / `_enterRecovery`, `state-machine.js` `transition`, `document-sdk.js` request start / response / `failAndCancel`, the tile scheduler's render `.catch`, and the page's `autosaveNow`. Each logpoint's source line is checked before the run (a moved line stops the probe). No product byte and no check changed. Host 0.2.13 `e028517`, page `d761f1ce…` (same as the chain).

Report: `probe-2026-10-12T121440+0000.json` (3 runs). The probe's call to `score_arm` raised `KeyError: 'original'` (the probe's report lacks the runner's `original` block); the cell is read from `save1State.state` instead, which is what the runner's K8 check reads first.

Positive control: every run logs the open and the edit (`transition`, `req`/`resp` for `editorGetStateV2`, `click`, `editorActionV2`, `paint`), so an empty log would have meant the logpoints did not take; all eight resolved (`logpointsInstalled[*].locations` non-empty).

## Result: 2 of 3 runs reproduce it, with one mechanism

Times are ms from the host's `started` (the same clock as `freezeAt` / `thawAt`).

| run | freezeAt | thawAt | what happened at thaw | end state |
|---|---|---|---|---|
| 1 | 3425 | 333805 | `fail save 18 TIMEOUT "save timed out after 180000 ms"` at 333987 → `blockQueue recoverable-error editor-recovery` | `recoverable-error` |
| 2 | 3496 | 333864 | `resp save 18 ok` at 334135 → ready; auto save landed, then the manual save | `ready` |
| 3 | 3416 | 333828 | `fail save 18 TIMEOUT` at 334016 → `blockQueue recoverable-error` | `recoverable-error` |

In all three runs, 1–2 ms after `freezeAt`:

```
autosaveNow  "hidden"  {"state":"ready","pending":0,...,"savesUnsettled":0}
transition   ready -> busy
req          save 18
```

So:

1. Freezing the page through CDP first makes it `hidden`. 0.2.13's autosave rule "save at once when the page goes to the background" (SPEC-M3-autosave §9.2, finding 127) starts an engine save, and request 18 (`save`, timeout 180000 ms) is posted to the Worker.
2. The page is then frozen for about 330 s. The request's timeout is a `setTimeout`, so at thaw it is about 150 s overdue. The Worker appears to be frozen with it (inference, not measured: in run 2 the reply came about 270 ms after thaw, not at once, as a reply queued during the freeze would).
3. At thaw the overdue timer and the Worker's reply race. When the timer wins (runs 1, 3; about 180 ms after thaw) the request fails with `TIMEOUT`. `TIMEOUT` is in `RECOVERY_ERRORS` (`editor-shell/editor-session.js:15`, "a ... TIMEOUT means the engine thread is already dead"), so the drain blocks the queue into `recoverable-error`. When the reply wins (run 2; about 270 ms after thaw) the save completes and everything passes.

Why it never happened before 0.2.13: nothing started a request at the moment of freezing, so nothing was in flight across the freeze. This morning's witness K8 on `c7f904fa…` (same autosave code) shows the same `hidden` auto save at thaw; there the reply won.

## What the user is told

With no checkpoint, the page's recovery notice reads (`e2-editor-app.js` around :749, decided by `recovery-notice.js`): 「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。」 That the engine was not dead is inferred from run 2 only (it answers about 270 ms after thaw): in runs 1 and 3 a late reply to the cancelled request cannot be seen, because the `resp` logpoint sits at `document-sdk.js:236`, after `:234 if (!entry) return;` (correction from fable's ruling, `../../133/ruling/fable-ruling.md` §4). Whether the restart actually loses the edit was **not measured**; by the notice's own wording the page says it does.

## Not measured

- How often a real user reaches this. It needs a save in flight when the page is frozen or the machine stops: for example, closing a laptop lid or switching away right before the system sleeps. Chrome's own freezing of background tabs happens minutes after hiding, long after a 0.5–0.7 s save. Whether a 180 s `setTimeout` is overdue after OS suspend depends on the platform clock. **Not measured on any platform.**
- Firefox: K8 is Chrome-only (CDP).
- The frequency beyond 2/3 + 1/1 (the chain's run) + 0/1 (the witness) = 3 of 5 on 0.2.13's pages.

## Corrections (2026-10-12, from fable's ruling §4)

- "1–2 ms after `freezeAt`": run 3 is 5 ms (3416 → 3421).
- The race is not only reply speed: at thaw the overdue timers are released in one batched wake-up (the 30 s idle-autosave timer and the 180 s save deadline fire within 2 ms of each other: 333985/333987, 334014/334016; run 2's batch at 334659, after the reply at 334135), phases +182 / +188 / +795 ms against a reply at about +271 ms. So a green K8 on an unfixed page is the timer losing, not evidence of health.
- The K8 expectation change is `65e90f62`; `ce758882` holds the witness re-score outputs.
