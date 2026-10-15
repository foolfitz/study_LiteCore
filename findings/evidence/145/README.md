# Finding 145 — evidence: the page's delete accounting leaks across a refusal's reopen

Source of the reading: the 0.2.23 count's merge step (chain `20261015T025837Z`, `../release-0.2.23/merge-m2/`). `judge_counted_m2.py --profile e2-editor-v20` read `VERDICT FAIL: ['chrome M2-1', 'chrome M2-3', 'chrome red', 'firefox M2-1', 'firefox red']; NOT DONE: ['chrome M2-2', 'firefox M2-2']`.

## What the reports show

The same 36 of 60 M2-1 records fail in both browsers, in both the instrumented and the control (uninstrumented) runs. The control's `afterKey` revision equals the counted run's in every one of 78 records (`model-readings.txt`, last section). The fixtures, click points and engine carets equal v19's X7 run, which passed. There are two shapes:
- **no response**: the key never reached the engine (`response: null`, `keyTrace: []`, revision 0);
- **too many deletes**: one key, revision 2 or 3.

## The mechanism, read from the page source (`web/e2-editor-app.js` at `ccb67a52…`)

- `settleDelete` (`:2732–2739`) returns at `if (send.document !== session?.document) return;` **before** `deletesUnanswered -= 1`.
- A refused delete reopens the document (`reopenAfterBoundaryRefusal`, `:1912`). Per the page's own comment at `:258`, "the reopen after a refusal" makes a new DOCUMENT object. So a refused delete's settle never decrements, and from then on `deletesUnanswered > 0` for the rest of the page's life.
- `holdsDelete(action, unanswered, inFlightAction)` (`:2712`) then holds every press whose key equals the last sent one (`heldDeletes.count += 1`, `:2774–2776`).
- The next press of the other key is sent. `dispatchDelete` sets `heldDeletes.action` to that key (`:2753`), and its answer runs `releaseHeldDelete` (`:2722–2729`), which re-sends every held press **as that key's action**.
- Introduced by `2b647fcb` (task 10-14o, finding 141's fix), first shipped in host **0.2.21** (`187b36d`). Present in 0.2.21, 0.2.22 and 0.2.23.

## The model check (`leak_model.py`)

A replay of exactly those four functions, with one assumption: a refused delete's settle is lost. It walks the records in run order and predicts each one's outcome (held / refused / boundary no-op / answered) and how many deletes reach the engine (1 + the presses released).

| report | match | mismatch |
|---|---|---|
| `counted-chrome`, `counted-firefox` | 78 / 78 | 0 |
| `m2-1b-chrome`, `m2-1b-firefox` (no refusal in the mode) | 20 / 20 | 0 |
| `red-chrome`, `red-firefox` (v8 refuses C01 and C02; C03 is held, so "not red") | 3 / 3 | 0 |
| counter-model `leak_model_counter.py` (a refused delete settles normally) on `counted-chrome` | 42 | **36** |
| the model on v19's X7 `counted-chrome` (page before `2b647fcb`) | 39 | **39** |

The model predicts the exact extra-delete counts: D04 and the next round's C01 delete 3 times after two held presses, and C11, C14 and C08 twice after one. It also places the first failure right after the round's three refusals (C15–C17).

## Not established

- **The user's path.** The trigger is any refused delete. On engine v20 the document's two ends no longer refuse (C), but refusals remain, e.g. Delete at a table cell's end (finding 136).
- Inferred, not measured: after one refusal, the user's next presses of the refused key do nothing until the other key is pressed, and then all of them are replayed as that key.
- No production-UI arm induces a refusal on v20 (SPEC-M3-link-batch §17.3: B3x withdrawn, A1-2′ R's rescue across a refusal registered as unguarded). This count's merge cases C15–C17 are the only refusals it ran.
- A hand test or probe on the host is the next measurement.
