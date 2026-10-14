# Host 0.2.22: finding 144 fixed on the page (task 10-14q)

Task: `handoff/tasks/TASK-2026-10-14q-fix-144-held-depth-counts-held-presses.md` (U1–U3, N1, H1 pinned there before any run). Finding 144 (`findings/144-…md`): on 0.2.21 a held Backspace/Delete inside text deleted 27–29 characters after the key came up (K3c, `findings/evidence/host-0.2.21/k3/`), because finding 141's hold kept `deletesInFlight` at one and finding 132's depth cut (`dropsHeldRepeat`, keydown, depth 2) never fired. The owner chose A; rulings on the owner's behalf are the appended 裁決 in `findings/144-…md` and the 裁決補記 in `findings/141-…md` (what 10-14o's test set missed). English here. No host change, no freeze, package, link, `occ upgrade` or `--write`; the only make `e2-c-assets`; N1 is no-host, the owner's instance was not used.

## The change (`wasm_sdk_probe/web/e2-editor-app.js`)

1. **The depth counts the held presses.** `skipHeldRepeat` now gives `dropsHeldRepeat` `deletesInFlight + heldDeletes.count` (the parameter is renamed `deletesOutOrHeld`; `HELD_DELETE_DEPTH` stays 2). During a hold: the press is sent (1 out), the first flagged repeat is held (1 held), from the second on the keydown is dropped (1 + 1 ≥ 2); each engine answer releases one held press and the next repeat is held again. At the key-up at most one delete is unanswered and one press held: 132's 「放開之後最多再刪 2 字」.
2. **A held press is released by a direct call, not a synthetic event.** 0.2.21 re-dispatched an `InputEvent("beforeinput")` on the sink, which every `beforeinput` listener saw: the frozen adapter traced it and 132-B's instrument counted it (`beforeinputs` 102 against 52 keys), so its clause (c) `beforeinputs == deleted` read red for the count alone. The send is now `dispatchDelete(action)`, called by the listener for a press nothing held and by `releaseHeldDelete` for a held one; the form sent (121's shape, 131's collapsed form while a delete is out) is decided at the moment of sending, as before. `DELETE_INPUT_TYPE_OF` is gone.

Finding 141's boundary behaviour is unchanged (an unflagged burst at a C boundary is still one request; U1c, N1). Named residual, as before 141: a flagged hold at a C boundary still costs one no-op per 2.25 s window (10-14n's `hold-3s` shape); 141's "remember the last no-op" was not added, the engine-side answer at the boundary (§10.5 `waitedMs`) stays the next-link item.

**Bytes.** `web/e2-editor-app.js` `2d6c4580e8beaac7…` (0.2.21) → **`aa50cd20e975954a…`**; `dist/e2-editor-app.js` the same after `make e2-c-assets`; `editor-shell-v2/narrow-editor-v2-session.js` `f47c80ec…` unchanged; `editor-shell/` untouched. `tests/test_product_path_mutations.py`: 10/10 OK, no mutation anchor moved (`u/product-path-mutations.txt`).

## U1 — red first on 0.2.21's page, then green (`u/`)

`editor-shell-v2/tests/page-held-depth.test.mjs` compiles the keydown guard, the listener and its helpers from the page source and drives them as a browser does: a keydown reaches the sink's keydown listeners first and the `beforeinput` follows only if none called `preventDefault`; the fake engine answers one action at a time on mocked time (a verified delete at 66 ms + a 10 ms repaint, a boundary no-op at 2,250 ms); the hold is 132-B's: the press, then a flagged repeat every 30 ms from 500 to 2,000 ms, key-up at 2,015 ms. `PAGE_SOURCE=` selects the page copy.

| test | 0.2.21 page `2d6c4580…` (`held-depth-page-0.2.21-2d6c4580.tap`) | the changed page (`held-depth-new-page.tap`) |
|---|---|---|
| U1: flagged hold inside text, deletes after the key-up ≤ 2 | **red**: 23 deletes after release, the last at +1,565 ms (the host measured 27–29, +1.8 s) | green: ≤ 2; `beforeinput` count == verified deletes == revision; ≥ 20 deletes during the hold; fewer than the 52 keydowns |
| U1b (control, 131): the same 52 keydowns unflagged | green (52 deletes) | green (52 deletes) |
| U1c (control, 141): a flagged hold at a C boundary | green (1 request, nothing deleted) | green (1 request, nothing deleted) |
| U1d: the keydown guard drops a flagged repeat with one delete out and one press held | **red** | green |

## U2, U3

- U2: finding 141's eight tests (`page-held-deletes.test.mjs`) and the 121/131/132/134 tests (`page-delete-and-sink.test.mjs`): **22/22** green (`u/u2-141-131-132-134-tests.tap`). Three substring pins moved with the code they pin, each with its reason in the file: 131's "counted before the call, released in finally" and 121's "asks the engine's current selection" now read `dispatchDelete()` (the handler calls it), 134 U-B4's rejection pin likewise; 132 U4's and 141 T4's harnesses declare `heldDeletes` (the guard reads it); 132 U6's harness slices `dispatchDelete` and no longer needs a synthetic-event sink; 141's harness slices `dispatchDelete`. No clause changed.
- U3: `node --test editor-shell-v2/tests/*.test.mjs` **364 / 364** (360 + 4; `u/suite.tap`); `check_e1_c_bundle_intact.py` **`intact: true`** (`u/e1c-intact.json`). Recorded as seen: in one of three full-suite runs `place-caret-second-pass.test.mjs` "defect 2" (real timers against the engine's 250 ms deadline) was red once; alone 3/3 green, the suite 2/2 green afterwards; read as intermittent and unrelated to this change, not re-run until green.

## N1 — no host, both browsers (`n1-nohost-v20/`), and the red witness (`n1-red-page-0.2.21/`)

The dist mirror (symlinks to `dist/` with the changed page `aa50cd20…`, profile `e2-editor-v20`, `web/serve.py`), the 60-page fixture through the page's file input, the 10-14o probe plus one arm: `hold-2s-in-text` holds Backspace for 2 s with the caret inside page 1's text, the repeats **flagged** as WebDriver/CDP send them (the desk's 500 ms delay, 30 ms interval: 52 keydowns), and the summary counts the engine's verified deletes answered after the key-up. The red witness is the same arm on a mirror carrying 0.2.21's page (`2d6c4580…`). Judge: `judge_n1.py --dir n1-nohost-v20 --red-check n1-red-page-0.2.21` (`n1-judge.txt`).

| arm | Firefox 157 | Chrome 151 | the 0.2.21 page, Firefox (red witness) |
|---|---|---|---|
| `burst-1s` at the document start | (a) **1** request / 1 no-op; (b) ready at **2,258.0 ms**; generation 1, no toast — PASS | (a) **1** / 1; (b) **2,260.1 ms** — PASS | — |
| `burst-1s-in-text` (unflagged, 131) | 18 keydowns → 18 requests, 18 verified deletes — PASS | 18 → 18 / 18 — PASS | — |
| `hold-2s-in-text` (52 keydowns, 51 flagged, key-up at 2.02–2.13 s) | (d) deletes after the key-up **2**, the last +48.6 ms; (e) `beforeinput` 35 == deletes 35; (f) 33 deletes during the hold — PASS | (d) **1**, the last +31.4 ms; (e) 33 == 33; (f) 32 — PASS | (d) **14** after the key-up, the last +827 ms — FAIL; (e) `beforeinput` **96** ≠ deletes 48 (the re-dispatched events) — FAIL; (f) 34 — PASS |

`judge_n1.py` VERDICT PASS, its red check on the 0.2.21 page red on (d) and (e) (fewer after-release deletes than the host's 27–29 because this mirror's engine answered faster than the installed one; the shape is the same: every repeat held, drained one per answer after the key-up).

## Files

`probe_10_14q.py` (the 10-14o probe + `hold-2s-in-text` + deletes-after-release in the summary + its own name in the preflight exclusion), `judge_n1.py`, `u/` (U1–U3 witnesses, the mutation census output), `n1-nohost-v20/` and `n1-red-page-0.2.21/` (reports, logs, screenshots), `n1-judge.txt`.

## For the freeze and the release

Re-pin the page to `aa50cd20e975954a…` (v71); the identifiers added in 10-14o remain (`deletesUnanswered`, `heldDeletes`, `deleteStateOf`, `boundaryNoopStands`, `holdsDelete`, `dropHeldDeletes`, `releaseHeldDelete`, `settleDelete`, `editorAction(action, { onResult })`), `dispatchDelete` is new and `DELETE_INPUT_TYPE_OF` is gone. Release text: a held delete key inside text stops within two characters of the key-up again (as on 0.2.18–0.2.20); at a document boundary the first press still waits about 2.25 s and further presses or a held key cost nothing more. H1 (132-B and K3 on the installed 0.2.22) is the binding host check and is a later task.
