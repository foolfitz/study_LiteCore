# v19: X2-X7 (before the runs)

Written 2026-10-08 after the owner's link (19:42 +0800), the archive, X1 and the binding (`8da777d7`; `post-link/README.md`), and before any v19 browser run. The criteria are spec SPEC-M3-paragraph-merge §31.4 as corrected by §32-§34; this file states the expected readings, which lines are criteria, and how each part is read. Labels: X2-X7 are §31.4's. Sub-labels (X5.P1 etc.) are local to this file.

Identities the round is about: v19 wasm `1aafd4f9…`, worker `00882139…`, manifest `902111fa…`; shell generation v56 (`b256fe04…`); page source `web/e2-editor-app.js` `a7d8ffa1…`; candidate page (repointed to v19) `e00ab76a…` (`build_cutover_page.py --profile e2-editor-v19`, no `--write`); runner sha256[:16] `73b2e9ff4b1e6fbe` (the reader's `RUNNER_SHA`). `chain.sh` hashes the profiles, packs, page, shell manifest and tools at start and end (`identity-at-start.txt`, `identity-at-end.txt`); the two must agree, or the round is not evidence about v19.

## Order and stop rule (`chain.sh`)

1. X2 M1-1 (no browser). 2. X3 W3/W5 probes (Chrome). 3. X7 counted M2, Chrome then Firefox: `counted`, `counted --control`, `--pair`, `m2-1b`, `m2-4`, `m2-1-red` on v8. 4. X5 product-path net, v8/v19 interleaved, 3 rounds × Chrome/Firefox. 5. X4 counted corpus comparison, v19 vs v18. 6. X6 the owner's document (Chrome; diagnostic only, §34.8).

Nothing aborts the chain; every exit code is logged first; each part is judged from its own reports, and a missing or unreadable report means that part was not done. The readers run after the chain. Spec §34.1: no tool under `tools/` is edited from the bind commit until X7's verdict is read; the only exceptions are §34.1 (a) and (b).

## X2 — `x2-m1-1/run.sh` (the pre-link script, unchanged except its output directory)

- **Criterion:** `green` exit 0 with `carriers [E2_V15, E2_V19]`, 25 rules, 100 objects, `different` 2; `red-only-v15`, `red-inject-v8`, `red-v8-as-carrier` each exit 1.
- Expected: the green JSON line equal to `post-link/m1-1-after-link.txt`.

## X3 — `x3-w3-w5/run.py`, reader `x3-w3-w5/judge.py` (v18's, session names changed; `--selftest` PASS, `selftest-output.txt`)

- **Criterion:** W3 PASS and W5 PASS with v19 in v18's place.
- Expected: K1 answered `Noto Sans Mono CJK KR`, 21 conf.d, the E10 path scanned; on the probe every 細明體/MingLiU answer equals the control's, 8 bands, every band top difference 0.
- Descriptive: v19's sessions equal v18's committed `../v18/w3-w5/sessions.json` readings (same answers, same band tops). The engine change is in the merge path only, so nothing in font resolution is expected to move; a difference is recorded (finding 036: the wasm is not a function of the source, which is why this is measured at all).

## X7 — `x7-counted-m2/`, reader `tools/judge_counted_m2.py --dir findings/evidence/v19/x7-counted-m2` (no `--uncounted`)

- **Criterion:** reader exit 0 and its last line `VERDICT PASS` naming both browsers (§33.1). Every report carries runner `73b2e9ff4b1e6fbe` and served exactly `BINDING` (the red case: all but wasm, worker and page).
- Expected per browser:
  - **M2-0** true on every fixture the reader requires.
  - **M2-1** 20 cases × 3 rounds = 60 records, all `verified-key-undo`, comment and `restorePresses` 0 as native, generation unchanged, documents equal native after reduction, no toast.
  - **M2-3** 5 × 3 = 15 refusals: C15/C16 `key-deadline` with `keyPosted:true`; C17 `anchor-mismatch`; C29/C30 `nothing-selected`; generation +1 at close and after 90 s.
  - **Barrier** G01 × 3 `verified-selection-delete`.
  - **Control:** the pair 0 differ; the number of documents compared is printed by `--pair` and the reader.
  - **M2-1b** Y01, Y02 × 10 = 20, each passing every M2-1 clause; no refusal, no reopen.
  - **M2-2:** every runner latency and every engine `keyToUndoMs` < 1000 ms (the 60 counted M2-1 completions and the 20 M2-1b ones).
  - **M2-4** 105 of 105 `verified-key-undo`, comment `Delete paragraph`, `restorePresses` 0, generation unchanged, `actionsAfter` reaches 100 by press 100 and stays, no toast (finding 118's watch), final `content.xml` and paragraph text equal native press 105 (`60087d94…`), and §31.2: every press runner latency and engine `keyToUndoMs` < 1000 ms.
  - **Red case** on v8: C01, C02, C03 each placed and refused (not `verified-key-undo`), generation +1.
- **Predictions (§31.4, not criteria):**
  - M2-4: every press's engine `keyToUndoMs` < 300 ms (v18: 102 presses at 2001-2002 ms).
  - Y01/Y02: engine `keyToUndoMs` in the 28-49 ms band of untyped merges (v18: about 628 ms).
- **Recorded (§33.4):** the minimum engine `keyToUndoMs` (the reader prints M2-4's `engineMs` [min, median, max]). §31.5's clock-guard argument rests on "two presses cannot fall in one whole millisecond"; it is re-read against this number. Expected ≥ 2 ms; below that the argument is registered as broken (a finding, not a criterion).

## X5 — `x5-product-path/`, reader `x5-product-path/judge.py` (v17's, page constants changed; on v18's committed run it gives P2 MISS, `selftest-output.txt`)

The verdict is the `SUMMARY` line (§34.7); the reader exits 0 on a MISS.

- **X5.P1 (precondition):** 12 reports, `complete: true`, `liveness.lastState: ready`, `pageErrors: null`.
- **X5.P2 (precondition):** v8 serves `a7d8ffa1…` (v56's page, still pinned to v8: since the freeze `dist/` serves it); the v19 reports read `candidateSource.page` `web/e2-editor-app.js`, `sha256BeforeRepoint` `a7d8ffa1…`, `restOfShellEqualsSource` true, served entrypoint = `candidateCutover.pageSha256` = `e00ab76a…`.
- **X5.P3 (the criterion, §23):** 0 red cells of 84.
- **X5.P4 (descriptive):** per-cell counts equal v18's run (`../v18/product-path/`), except the cells that already varied between rounds there (Firefox `clear-format-removes-every-inline-format`, `recovery-returns-what-the-product-promised`); Firefox `an-inline-format-reaches-a-selection` FAILs 3 of 3 on both arms again. Note: v18's v8 arm served the older page `e97d6e03…`; this round's v8 arm serves v56's, so the two arms now differ in the engine only.

## X4 — `x4-layout-corpus/`, reader `x4-layout-corpus/judge.py` (v18's, profiles and the not-measured reference changed; red/green in `selftest-output.txt`)

- **Criterion (§28.5's reading):** reader exit 0 and `VERDICT: PASS`; the not-comparable sets of the two arms identical; the not-measured set equal to v18's counted run's (23 documents). A STOP (exit 2) is not done.
- Expected: not comparable 5 in both arms; not measured 23, the same set; measured 48.
- Descriptive: every measured document differs by 0 px (v19 and v18 share packs, worker and export list; the engine change is in the merge path only).

## X6 — `x6-v5/`, reader `../v18/v5/judge.py --report findings/evidence/v19/x6-v5/shakedown-chrome-v19-v5.json --private-docs wasm_sdk_probe/build/merge-wasm-private/shakedown-chrome-v19-v5.docs --profile e2-editor-v19 --page e00ab76a…` (diagnostic; blocks nothing)

- Expected, as v18's O1-O3: caret height, x and y equal native in all 11 cells (E01 348, E02 521, E05 521, E10 348, T01 463, E12/P27/E13/E15/P62/P63 348 twips), `keyed` false, no `placement-mismatch`; 26 of 26 synthetic cases pass, `reducedBytesEqual` true on all three fixtures; E02's `afterKeyBytes` stays red with the same 4 of 15 soft page breaks (finding 115). The report carries no paragraph text.

## What a miss means

- A criterion miss (X2, X3, X4, X5.P3, X7): look at the request, the answer and the report first. No threshold or criterion is adjusted (§34.6). A FAIL that a committed honest report shows to be a reader error goes through §34.1 (b); anything else stands.
- X7 voided by a page or shell red: freeze v57, never overwrite v56 (§31.4).
- A missed prediction or descriptive line is recorded as a miss and is not a criterion.
- An honest crash (traceback, no report) is §34.1 (a): fix, re-run that step only.
