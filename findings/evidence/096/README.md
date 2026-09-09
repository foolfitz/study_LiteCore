# 096 — boundary arrow press: reproduction and discrimination

**Protocol**: `handoff/tasks/TASK-2026-09-09-096-which-profiles-kill-the-session.md`
(commit `a0f098b5`), registered before the probe was written. Its
`## Execution record` carries the three changes the shakedown forced, all made
before the first counted attempt.

**This directory names no cause.** It answers one question — does the session
enter a dead state after an arrow key pressed at a document boundary, and on
which of three engines — and banks what the engine said while it happened.

## Files

| file | what it is |
| --- | --- |
| `probe_096_boundary_arrow.py` | the instrument. Real key events over CDP, the caret placed by a canvas pointerdown, the owner's own document handed to the product's `#file` input. |
| `boundary-arrow-e2-editor-v13.json` | arm A, the candidate |
| `boundary-arrow-e2-editor-v12.json` | arm B, the previous candidate's engine |
| `boundary-arrow-e2-editor-v8.json` | arm C, **the shipped bytes** |
| `boundary-arrow-armD-pre093-page-e2-editor-v8.json` | arm D, the page from before 093's page half on the shipping engine. Its page source is not committed here because it already is: `git show 18eefcce^:wasm_sdk_probe/web/e2-editor-app.js`, sha256 `df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143`, fed to the probe with `--page-from`. |
| `summarise.py` | reads whatever `boundary-arrow-*.json` files are present and prints the matrix and every attempt |
| `RESULT.md` | the verdict, against the outcomes registered before the run |

## What is held constant, and what varies

`repointed_page()` rewrites exactly two things in `web/e2-editor-app.js`: the
one worker URL and the one pinned wasm hash. So **the page source is the same in
all three arms** — the current one, which already carries 093's page half
(`18eefcce`). The triple therefore isolates the **engine**; it cannot by itself
attribute anything to the page change. Arm C's page is byte-identical to the
shipped `dist/e2-editor-app.js`.

| arm | page sha256 | probe.wasm |
| --- | --- | --- |
| A — `e2-editor-v13` | `31787584290e42bd…` | `0fe25650bec1bac5` |
| B — `e2-editor-v12` | `db2ed393f3433e2e…` | `4ec1e389aaab3b03` |
| C — `e2-editor-v8` | `1ec7baf9fb53c808…` | `4a2710bba1ef07d9` |

Arm A's page sha256 is the number the owner's round was banked against
(`findings/evidence/manual-round-v13-31787584/notes-owner-T4.md`).

All three manifests offer `move-line-up` and `move-line-down`, so the page's
`keydown` handler takes the key on all three — the arms are comparable at the
key path, and that was checked before the run rather than assumed.

## The document

`~/Documents/SLAT/e20-專訪瓦特老師.odt`, sha256
`63bf89cb5d7eb8913fd2e691f5d93b0d42d8715ca9ef8c61cd331048831c53d5` — **the
owner's own file, the one they used in the T4 round**, not a built fixture.
Finding 086 is on record as a defect that a real document exposes and the built
fixtures did not.

"Longer than the viewport" is measured per attempt, not assumed: every attempt
records `#desk`'s `scrollHeight` and `clientHeight` and is void if the document
fits on one screen. Viewport fixed at 1920x1080.

## The gesture

- keys: CDP `Input.dispatchKeyEvent`, `rawKeyDown` then `keyUp`, virtual key
  code 38 / 40. Not a synthesised `KeyboardEvent`, not `session.action(...)`,
  not a toolbar button. **The owner pressed real arrow keys**, and this tree has
  twice measured a path nobody walks.
- caret: a canvas `pointerdown`/`pointerup`, the only thing that moves the caret
  in this page, which focuses `#sink` on the way.
- document: `DOM.setFileInputFiles` on the product's own `#file` input.
- **up arm**: click the first row of text ink, then ArrowUp.
  **down arm**: click the last row of text ink, then ArrowDown.

## The predicate

Read from the product's own decision fields, never from its wording:

- **DIED** — `#state-pill`'s `data-state` in `{recoverable-error,
  restart-required, expired}` within 90 s of the press.
- **REPRODUCED** — DIED **and** `#notice` shown **and** `data-rescue == "none"`,
  which is the product's own decision that there is no checkpoint. The rendered
  sentence is banked too and compared to the owner's quote, as evidence rather
  than as the predicate.
- **DIED_WITH_CHECKPOINT** — DIED with a checkpoint offered. A different, less
  severe shape; **not** a reproduction of 096.

## What is banked from the engine side

`#s-latency`, the state ball and the toast are the **page's** observations. Each
attempt therefore also carries, raw:

- `cdpEvents` — every CDP event on the page target, verbatim. `ChromeSession.call`
  discards every message whose id does not match while it waits for its own;
  this probe buffers them instead.
- `cdpEventsFromWorker` / `workerTargets` — the document worker's own console and
  uncaught errors, reached through `Target.setAutoAttach`. **Opening a document
  replaces the worker**, so the console is enabled again after the open;
  without that the banked console would be a worker nobody was using.
- `workerLiveness` — one `Runtime.evaluate` addressed to the live worker's own
  CDP session after the verdict. "The worker's JS thread is blocked" and "the
  worker is idle and something behind it never answered" are indistinguishable
  at the page.
- `toasts` — every toast, via the MutationObserver `INSTALL` puts on `#toast`,
  not `#toast.textContent`, which the next message overwrites. `run()` renders
  `${code}：${message}` from the SDK's own error object, so the toast carries
  the engine's error **code**.
- `transitions` — the state-pill trace, recorded by a MutationObserver in the
  page, so the ordering carries page timestamps rather than poll times.
- `pageErrors` — `window.onerror` and `unhandledrejection`. The page's own
  handlers swallow rejections, so a rejection that never reaches a toast would
  otherwise leave no trace.

## What this does not measure

- **Why.** Naming a cause is out of scope; 040 and 089 are the precedents.
- **The other two things the owner recorded.** The viewport not following the
  caret during ordinary arrow movement, and (with a screen reader) the caret not
  following the browse cursor, are registered by 096 as possibly-separate. They
  are not measured here and must not be merged with this.
- **Finding 095** (after ArrowDown at the last line, the next canvas click
  places no caret) is a different shape on a different fixture size and stays
  separate.
- **A physical keyboard.** These keys are injected at the renderer. See
  `RESULT.md` for what that leaves open.
