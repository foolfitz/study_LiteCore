# Before binding v20: part P of task 10-15c (P1-P5)

Brief: `handoff/tasks/TASK-2026-10-15c-pre-binding-v20-prep-and-rulings.md` (commit `91de8867`). Executor: a fable, 2026-10-15. Commits `c8d53f39..` (eleven, listed per item below), each `git commit -- <paths>`; nothing pushed. Limits honoured: no browser, no ddev, no `make` but `test-e2-c-static`, no link, no freeze, no host change, no `--write`, `BINDING` of v20 not set (the main session's step). Host state read, not changed: `~/Projects/Nextcloud_Apps/litecore` HEAD `2ccf1a9`, `<version>0.2.23`, tree clean; `engine/MANIFEST.json` buildId `c3c22d9294de068a`, `e2-editor-app.js` `ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e`; `blank/MANIFEST.json` `e5cdb8e2f0311cc1…`. In the tree, `web/e2-editor-app.js` = `dist/e2-editor-app.js` = `ccb67a52…`; `editor-shell-v2/narrow-editor-v2-session.js` = `f47c80ec955397c4…`.

## Read this first: what this part did NOT do

- **Only the page pins moved (P4's scope).** Every M3 runner also carries host, session, build-id or shell-bundle constants that still name host **0.2.14 / shell v63**, and a counted run refuses on them until they are moved (the precedent binding commits `fb839ec1`, `3a6603de`, `05aa0c75` moved them in one commit each). The list, by name (line numbers shifted by the comment lines added above each pin): `check_m3_assets.py` `BUILD_ID eb3f9408…` (0.2.23 is `c3c22d9294de068a`); `check_m3_versions.py` `HOST_COMMIT 237f2cb`; `check_m3_same_second.py` `HOST_VERSION 0.2.14`; `check_m3_page_honesty.py` `SESSION_SHA256 62a2a20e…` (the served session is `f47c80ec955397c4…` since v68), `HOST_VERSION`, `HOST_COMMIT`; `check_m3_production_ui.py` `SESSION_SHA256`, `HOST_VERSION`, `HOST_COMMIT`, `SHELL_BUNDLE_SHA256 318b3bf2… (v63)` (v72's bundle file `e2/editor-shell-v2-bundle-v72.json` hashes `3ccbd1441806761e…` as a file, and the freeze commit `19c19543` names `4dc10507…`: check which the pin means before moving it); `check_m3_autosave.py` `SESSION_SHA256`, `HOST_VERSION`, `HOST_COMMIT`. These are the binding step's, with `m.BINDING` in the merge runner and `judge_counted_m2.py`'s `--profile` default (still `e2-editor-v19`; a v20 count must pass `--profile e2-editor-v20`, or the `profile` identity clause reads NOT DONE -- fail-closed, not silent).
- **Two of 10-13f's nine runners have no pin line** (`check_m3_versions.py`, `check_m3_same_second.py` import `check_m3_locks.py`'s), **one has none at all** (`check_m3_host_entry.py`: `PAGE` is a path, no binding constants), and **the product-path net's pin is not in the runner** (see P4). The brief's "nine pin lines" are eight physical lines, three of them the ones the brief named by kind (`FINAL_PAGE_SHA256`, the two judges' `PAGE`).

## P1. `judge_counted_m2.py` learns C (commit `c8d53f39`, with P2)

**What changed.** `expectation(decision, boundary_noop=False)`: with the keying, `nothing-selected` (C29, C30) expects `("M2-3", "verified-boundary-noop", None, None)`; without it, the refusal as before; nothing else moves. The keying is the runner's (`7e6c9acd`, `m.boundary_noop_declared`): the fragment the engine emits, `,"completion":"verified-boundary-noop"`, read from `PROFILES/<profile>/probe.wasm` (`dist/profiles/`, or `--wasm PATH`), and its sha256 must equal every non-red report's `bound.wasmSha256`, else the browser's reports are NOT DONE and nothing of them is judged ("C's expectation cannot be read from bytes that did not run"). A missing engine file stops the population. `noop_record` recomputes the no-op's clauses from the recorded fields and the kept `<case>-r<n>-after-key.odt`, tied by content to `afterKeyDocument.sha`/`.paragraphs`: `markerPlaced`, `placed`, `outcome`, `generation`, `revision` (`beforeKey.revision == afterKey.revision`, both read), `noToast` (`toasts == []`), `unchangedText` (original + marker), `markerOnce`, `caretUnchanged` (`caretAfterKey` against `place.engineCaret` and `place.caretGeneration`; **None when the record has no `caretAfterKey`**, never inferred). `kept_expected(cases)` makes the paired control's kept-document counts follow the keying: 63/63/15 without C, 69/63/9 with it. The population line now prints the keying: `keyed on <wasm> (<sha16>): C declared|not declared, nothing-selected expects …`. Served engines, read with `m.boundary_noop_declared`: v8 False, v18 False, v19 False, **v20 True**.

**Witness (§34.4, repaired because of execution): part B's eight reports**, `findings/evidence/link-batch/v20-shakedown/merge/` (runner `73b2e9ff4b1e6fbe`, every one bound to wasm `313b08d5cb085897`, which is `dist/profiles/e2-editor-v20/probe.wasm`). Staged under the counted names (`shakedown-B` → `counted-B`, `control-B` → `counted-control-B`, `m2-1b-B`, `m2-4-B`; no red report), judged `--profile e2-editor-v20 --uncounted`. Runner `73b2e9ff` took the refusal path on the no-ops, so the four C29/C30 records per shakedown and control report were mapped onto the no-op path's shape exactly as the committed re-judge (`v20-shakedown/merge/re-expectation/rejudge.py`) did: `toasts ← toastWindow.toasts`, the `-reopened.odt` kept as `-after-key.odt`, `afterKeyDocument ← reopenedDocument`; `caretAfterKey` stays absent. Nothing else edited. The HEAD judge (`94cbfcd7cfad18f1`, the one `judge-exit-rejudged.txt` names) and the edited judge (`4c231dc749c609cd`) on the same staged directory:

```
before (HEAD judge, exit 1), both browsers:
M2-3       FAIL     10 records (expected 15: 5 cases x 3 rounds); not passing: [('FAIL', 'C29 r1', ['checkpointRevision', 'generation', 'keyPosted', 'onlyTheReopenToasts', 'outcome', 'stage', 'toastWindowClosed']), ('FAIL', 'C30 r1', ['generation', 'keyPosted', 'onlyTheReopenToasts', 'outcome', 'stage', 'toastWindowClosed']), ('FAIL', 'C29 r2', [...same 7...]), ('FAIL', 'C30 r2', [...same 6...])] ...
VERDICT FAIL: ['chrome M2-3', 'firefox M2-3']; NOT DONE: [identity, reports, red, M2-1, barrier, M2-2, control x 2 browsers]

after (edited judge, exit 3), both browsers:
keyed on .../dist/profiles/e2-editor-v20/probe.wasm (313b08d5cb085897): C declared, nothing-selected expects verified-boundary-noop
M2-3       NOT DONE 10 records (expected 15: 5 cases x 3 rounds); not passing: [('NOT DONE', 'C29 r1', ['caretUnchanged']), ('NOT DONE', 'C30 r1', ['caretUnchanged']), ('NOT DONE', 'C29 r2', ['caretUnchanged']), ('NOT DONE', 'C30 r2', ['caretUnchanged'])] population: missing [(...round 3...)] extra [F01, F02 ...]
VERDICT NOT DONE: [identity, reports, red, M2-1, M2-3, barrier, M2-2, control x 2 browsers]
```

Every clause the old table had false presupposed a refusal and its reopen; under the keying the four records have nothing false and one open clause, `caretUnchanged`, which `73b2e9ff` could not record (part A's C1 arm measured the caret after the same no-op; cited, not substituted -- the runner since `7e6c9acd` records `caretAfterKey`). The rest of the staged run is NOT DONE for what it is: two rounds of three, `mode: shakedown`, F01/F02 present, no red report, not bound.

**v19's X7 reports re-judge unchanged.** `judge_counted_m2.py --dir findings/evidence/v19/x7-counted-m2 --profile e2-editor-v19` against the committed `judge-output-rejudged.txt` (the post-34.1(b) output): `diff` shows only the new `keyed on …/e2-editor-v19/probe.wasm (1aafd4f9da42fd83): C not declared, nothing-selected expects refused` line, the `all identity` line (`NOT DONE … off: ['thisRunner']`, this runner `d185cb50` against the reports' `73b2e9ff` -- by construction since `7e6c9acd`, P2's matter) and the final `VERDICT` line. **Every criterion line of both browsers is byte-identical**, M2-3 included.

**Tests** (`tests/test_judge_counted_m2.py`, 52 → 70, all green; the commit message says "50 → 70", the count before was 52). A second TEST AUTHORITY: a synthetic engine `FAKE_WASM` (no fragment) under a temporary `PROFILES`, the binding's `wasmSha256` = its sha256; `FAKE_WASM_C` adds the fragment. New: the keying names the served engine; a report bound to other bytes → NOT DONE `chrome reports`, nothing judged; no engine file → NOT DONE "cannot be read"; v18's refusals judged under C → M2-3 FAIL on exactly C29/C30 × 3 rounds (`outcome`); **a synthetic no-op under C passes** (both browsers, exit 0, kept counts `[69, 69] / [63, 63] / [9, 9]`, 15 M2-3 records); red: caret moved (`caretUnchanged`), another worker's caret, revision changed, a toast, marker lost (`markerOnce`), a refusal on a C profile (M2-3 and the pair); NOT DONE: no `caretAfterKey`, a document the report did not save; "everything but C29/C30 is as before" under C (M2-1, barrier, M2-2, M2-1b, M2-4, red, M2-0 all PASS; control open on the kept counts 63/15 vs 69/9, differ 0). Two existing identity tests now stop at the keying before `all identity` (`test_red_firefox_ran_another_candidate` now differs on the worker, not the wasm; `test_red_a_binding_of_another_schema` expects the two `reports` entries as well): fail-closed either way. `V20Witness` runs the staging above inside the suite on the real bytes (skipped unless the eight reports and the v20/v19 engines are present and the reports' bound wasm is the served v20): no longer red (4 × `['caretUnchanged']` per M2-3 line, no `'FAIL'`); red under the refusal table (`boundary_noop_declared` patched to False: 4 FAIL per line, `outcome`); keyed on v19's engine → nothing judged.

## P2. `V19Witness` re-judges at the run's commit (commit `c8d53f39`)

**Red before** (this tree before the commit, `python3 -m unittest tests.test_judge_counted_m2.V19Witness`, 2 of 4 failing by construction since `7e6c9acd`):

```
identity   NOT DONE runners ['73b2e9ff4b1e6fbe'] (this runner d185cb50029d76e6) pages ['e00ab76a550dc12f'] off: ['thisRunner']
FAIL: test_a_the_witness_passes       AssertionError: 3 != 0  (VERDICT NOT DONE: ['all identity'])
FAIL: test_c_one_arm_with_a_single_save_is_red
  AssertionError: Tuples differ: (1, "VERDICT FAIL: ['chrome control']; NOT DONE: ['all identity']") != (1, "VERDICT FAIL: ['chrome control']")
Ran 4 tests  FAILED (failures=2)
```

**The fix is in the test, not the judge's rule.** The class materialises the runner file as of the witness commit `b8324a85` (`git show b8324a85:wasm_sdk_probe/tools/run_merge_wasm_shakedown.py`, sha256[:16] `73b2e9ff4b1e6fbe`; the runner did not move between `b8324a85` and `7e6c9acd^`), requires it to be the hash every report names (else the class skips, with the two hashes in the reason), and patches `j.RUNNER_SHA` for the class. Only the identity is materialised; the functions the judge borrows from the runner are the live ones. `test_e_the_live_runner_is_still_the_rule` restores the live hash and gets `(3, "VERDICT NOT DONE: ['all identity']")`. **Green after:** 5/5 (`test_a` … `test_e`), inside the 70.

## P3. `check_m3_new_document.py` bound to host 0.2.23 (commit `004fcdd3`; a binding, not a repair)

| constant | was | now | basis |
|---|---|---|---|
| `HOST_COMMIT` | `afbaf3c` | `2ccf1a9` | host HEAD |
| `HOST_VERSION` | `0.2.19` | `0.2.23` | `appinfo/info.xml` |
| `MANIFEST_SHA256` | `e5cdb8e2…` | unchanged | `blank/MANIFEST.json` hashes the same; `git diff afbaf3c..2ccf1a9` touches only `appinfo/info.xml` and `templates/editor.php` |
| `ENGINE_BUILD_ID` | `None` | `c3c22d9294de068a` | `engine/MANIFEST.json` |
| `PAGE_SHA256` | `None` | `ccb67a52a3fe…` | the manifest's declared `e2-editor-app.js` |

`DELTA_HOST_VERSION` and the three `CONTROL_*` constants stay frozen with 0.2.19 (spec §7.5, DISPOSITION Q3). Tests 19/19 green; the two tests of the "not written" default (`test_the_delta_clauses_apply_only_to_0_2_19`, `test_moving_the_control_values_changes_nothing_on_a_later_host`) now set `ENGINE_BUILD_ID=None, PAGE_SHA256=None` themselves, since the module no longer defaults to None (they were red for exactly that reason after the edit; not a repair of the checker). `--red-cases` on the committed counted report `runs/2026-10-14T035226Z.json` (host 0.2.19): **39 RED, 0 MISS, 0 SKIP, 0 GREEN cases**; the baseline reads `RED base … problems=['binding hostCommit afbaf3c != 2ccf1a9', 'binding hostVersion 0.2.19 != 0.2.23']`, exit 1 -- by construction, DISPOSITION row 42 ("a binding rejects the earlier host; the tests patch to the report under test"). With the module's `HOST_COMMIT/HOST_VERSION/MANIFEST_SHA256` patched to that report's own (as the tests do): `GREEN base NEW-DOCUMENT WORKS …`, 39 RED, 0 MISS, exit 0. `--score` on the five committed reports: the three shakedowns and `runs/…034231Z` print as before (non-strict, or already NOT_ESTABLISHED on their own cells); the counted one moves WORKS → NOT_ESTABLISHED on the binding, which is what binding to a later host does. Not run against the real occ or ddev.

## P4. Page pins re-pointed to `ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e` (eight commits, one per pin line; old value kept in a comment above)

10-13f's nine runners, and where their page pin is:

| # | runner | pin | path | old → new | commit |
|---|---|---|---|---|---|
| 1 | M3 assets | `PAGE_SHA256` | `wasm_sdk_probe/tools/check_m3_assets.py` | `d761f1cee9d26c50…` → `ccb67a52…` | `773aa6de` |
| 2 | M3 locks | `PAGE_SHA256` | `wasm_sdk_probe/tools/check_m3_locks.py` | `d761f1ce…` → `ccb67a52…` | `9c211734` |
| 3 | M3 versions | imports #2 (`from check_m3_locks import … PAGE_SHA256`) | `wasm_sdk_probe/tools/check_m3_versions.py` | none of its own; reads `ccb67a52…` (checked by import) | -- |
| 4 | M3 same_second | imports #2 | `wasm_sdk_probe/tools/check_m3_same_second.py` | none of its own; reads `ccb67a52…` | -- |
| 5 | M3 host_entry | **no page pin, no binding constants** (`PAGE` is the path `web/e2-editor-app.js`) | `wasm_sdk_probe/tools/check_m3_host_entry.py` | -- | -- |
| 6 | M3 page_honesty | `PAGE_SHA256` | `wasm_sdk_probe/tools/check_m3_page_honesty.py` | `d761f1ce…` → `ccb67a52…` | `31012885` |
| 7 | production UI | `PAGE_SHA256` | `wasm_sdk_probe/tools/check_m3_production_ui.py` | `d761f1ce…` → `ccb67a52…` | `d5075093` |
| 8 | autosave | `PAGE_SHA256` | `wasm_sdk_probe/tools/check_m3_autosave.py` | `d761f1ce…` → `ccb67a52…` | `90fed007` |
| 9 | product-path net | **not in the runner**: `run_e2_c_product_path.py` hashes the page it serves and records `pageSha256`; the pin lives in the per-release judge copy (`findings/evidence/release-0.2.13/product-path/judge.py`: `--candidate-page` default `d761f1ce…` and `V8_REPOINTED fac708d0…`), created with the release's `PREDICTION.md` at count prep (precedent `3a6603de`). The 0.2.13 copy is that count's evidence and was not edited. | -- | the next copy must carry candidate page `ccb67a52…` and the v8 repoint **`49d1fd5f52e47a30d8c664758c803ed47498b2ddbf631727f0d12895f003bee3`** (computed now with the runner's own `repointed_page()` on `web/e2-editor-app.js`; pin before `313b08d5…`, v8 wasm `4a2710bb…`) | -- |

The three pins the brief named by kind, moved on the same rule:

| pin | path | old → new | commit |
|---|---|---|---|
| `FINAL_PAGE_SHA256` (129-B `--final`) | `wasm_sdk_probe/tools/probe_129_m4_wasm.py` | `7815e16c2cdfdebe…` (the v67/v68 candidate page; round-20261014T085633Z ran on it) → `ccb67a52…` | `af2527a4` |
| `PAGE` (`--page` default) | `findings/evidence/c-prime/c2/judge_c2.py` | `b24d754a426706bb…` → `ccb67a52…` | `af0ddacc` |
| `PAGE` (`--page` default) | `findings/evidence/typing-latency/judge_p2.py` | `b24d754a…` → `ccb67a52…` | `034d9a8c` |

**129-B: the pin moves; the runner is not marked retired.** SPEC-M3-link-batch §10.9 S-2 retires 129-B *in favour of R1*; §13.3 defers R1 to the ordered-commands batch, and handoff 10-13f records the consequence: "L-129 stands and 129-B stays". It ran on v20 as finding 140's C2 witness (task 10-14k, 54/54 both browsers) on the then-pinned page. Retiring it now would retire the only instrument of L-129 before its replacement exists. Other `--page` arguments found and left alone: `judge_132b.py`, `judge_held_into_refusal.py`, `judge_bubble.py`, `judge_p.py` (no default, passed per run); `v18/v5/judge.py`, `v18/merge/judge.py` (frozen v18 readers). Every committed C2/P2 report ran on an earlier page; re-judge them with `--page` or the judge from git history (noted in each file). `red_cases_c2.py` binds `--page` per report: `red cases: all as required`, exit 0, after the move.

## P5. After P1-P4

- `make test-e2-c-static`: **exit 0** (21.7 s; node suites pass, python `Ran 108 tests … OK`). Baseline before any edit: exit 0 (18.9 s).
- `python3 -m unittest tests.test_judge_counted_m2`: 70/70 (final run after every edit). `tests.test_check_m3_new_document`: 19/19.
- `check_m3_autosave.py --selftest`: `selftest: 0 failure(s)`. `check_m3_new_document.py --red-cases`: as in P3. `red_cases_c2.py`: as in P4. `py_compile` of all ten touched tools: ok. `check_m3_versions` / `check_m3_same_second` import the moved pin (`ccb67a52a3fe4b73`).
- Not run (no browser, no ddev): any runner or probe; `check_m3_{assets,locks,page_honesty,production_ui}.py --red-cases` need a report on the pinned page and none exists yet.

## §34.4

- **Repaired because of execution: 2.** P1 `judge_counted_m2.py` (witness: part B's eight reports; the four C29/C30 records per shakedown/control report). P2 `tests/test_judge_counted_m2.py::V19Witness` (witness: the committed v19 X7 reports, red since `7e6c9acd` moved the runner's hash). The test-expectation changes that follow P1 (two identity tests, three C tests written in this round) are inside P1's count.
- **Repaired because of review: 0.**
- **Binding updates, not repairs: P3 (5 constants, one commit) and P4 (8 pin lines, 8 commits).** The two new-document tests adjusted in P3 asserted the pre-binding `None` default and now set it up themselves.
