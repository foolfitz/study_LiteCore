# v20 merge shakedown (task 2026-10-14e Part B): prediction, written before any run

Written 2026-10-14 before the first browser step of this directory. This is a **shakedown, not a count**: `BINDING` in `tools/run_merge_wasm_shakedown.py` still holds v19's values (runner sha256 `73b2e9ff4b1e6fbe`, unchanged since v19's count), so every report from `--candidate-profile e2-editor-v20` must say `"counted": false`. Nothing in `tools/`, `web/`, `dist/` or the host is edited by this task; every run is its own §34.4 witness the first time it runs on v20.

## What is run (precedent in brackets)

Per browser, Chrome first, then Firefox, one runner at a time (`chain.sh`):

1. `--candidate-profile e2-editor-v20 --frame-cell --rounds 2` in the default `shakedown` mode, which takes the tool-generated list (spec 22.1). [`findings/evidence/v18/chain.sh`, `merge/shakedown-B`; the last shakedown-mode full-list run in the tree]
2. The same with `--control` (spec 22.3). [`merge/control-B`]
3. `--pair` of 1 and 2. [`merge/pair-B`]
4. `--mode m2-1b` and `--mode m2-4`. [`findings/evidence/v19/chain.sh`, `x7-counted-m2/m2-1b-B`, `m2-4-B`; modes of the same runner, uncounted here because BINDING is v19's]

Not run: `--mode counted` (same list as step 1 at 3 rounds, no frame cell), `--mode m2-1-red` (v8 red case, only meaningful against a bound candidate), `--owner-document`.

## Identity the runs are about

Profile `dist/profiles/e2-editor-v20/`: wasm `313b08d5…`, loader `e6b8c74a…`, worker `478d0da1…`, manifest `50aade86…`. Page source (shell v67) `web/e2-editor-app.js` `7815e16c…`. Page served = the v67 page repointed to v20 = `build_cutover_page.py --profile e2-editor-v20` (no `--write`) = `53019168651b6b4686f1baaba9aa75e0b566d02a3e2cc8a8e8ed4339f360bfd7`. Every report's `candidate.pageSha256` must equal that, `candidate.workerSha256` must equal `478d0da1…`, and the report's `bound` must differ from `binding` in the profile-dependent values (that is why `counted` is false).

## Predictions (not criteria; this directory has no judge, and the runner's own `pass` field is read verbatim)

- **P-a. Every case except C29 and C30 behaves as on v19 and v18** (the runner's own expectation from R0c's decision): `verified-key-undo` for the M2-1 cases, C15/C16 `refused` / `key-deadline` / `keyPosted: true`, C17 and F01/F02 `refused` / `anchor-mismatch` / `keyPosted: false`, G01 `verified-selection-delete`, `pass: true`, in both browsers and both rounds. The runner's `expectation()` still maps R0c's `nothing-selected` to `("refused", "nothing-selected", False)`; it is not edited.
- **P-b. C29 and C30 (the document start and the document end) complete `verified-boundary-noop` under C** (spec §10.5; native R0c's `nothing-selected`), not `refused`. Both rounds, both browsers: 4 records per report. `generation` stays `[1, 1]` (v19: `[1, 2]`, a refusal reopens). The runner therefore records `pass: false` for these records, because its expectation is the v19-era refusal. This is the expected effect of C and is reported verbatim, with the failing clauses named. It is not a product red and not a reason to touch the runner (§34).
- **P-c. `--pair`:** 0 differ, `sameOrder: true`, exit 0 (v18 and v19 precedent: 56 pairs; the exit-1 in v19's counted pair was the KB-figure toast, fable ruling §35, a different cause that does not apply to a shakedown-mode list with the same fixtures unless a saved file again sits on a rounding edge). If the pair differs only in the `已存出 N KB` figure, that is v19's known cause and is recorded as such.
- **P-d. M2-4:** 105 of 105 `verified-key-undo`, per-press engine `keyToUndoMs` [min, median, max] near v19's [30, 32, 36] ms (Chrome) / [30, 32, 33] ms (Firefox); the engine change between v19 and v20 is not in the Delete-in-the-middle path. M2-1b: Y01/Y02 engine latency in the 30–42 ms band.
- **P-e. No `重繪失敗` toast and no `runner-error`** in any report; no leftover test-browser process after any step.

## What a miss means

A miss of P-a other than C29/C30, or of P-d/P-e, is recorded as a miss with the request, the answer and the report, and is a finding candidate. A step that crashes without a report is §34.1 (a): recorded, that mode stopped, reported to the caller; the runner is not edited here.
