# Handoff, 2026-10-07c — candidate measurements now read the cutover's page; merge WASM runner reworked and shaken down on Chrome; M2-1 population is 20 merges + G01; nothing counted yet

Picks up from `HANDOFF-2026-10-07b-v16-replaces-v15-merge-runs-on-wasm.md` (its "Next, in order" items 1-3 are done or superseded below; items 4-5 remain). Entry points: this file; `specs/SPEC-M3-paragraph-merge.md` **§21-25** (appended this session; §20 and earlier unchanged); `findings/114-wasm-lays-out-cjk-lines-with-latin-metrics-where-native-with-the-same-fonts-does-not.md`; `findings/evidence/v16-shakedown/{product-path-web-page,merge,layout-corpus}/`; `findings/evidence/merge-native/r0c-wasmfonts/{PREDICTION,RESULT}.md`. Tree clean at `fa44c830` before this file. Not pushed. **No browser, runner or probe was run while writing this handoff.** Everything below is from commits and committed evidence.

## Since the previous handoff (oldest first; 16 commits after `53fca19d`)

| Commit | What |
|---|---|
| `3ab4f04a` | **Owner chose A** for "how candidate measurements get the cutover's page". `run_e2_c_product_path.py --candidate-profile` now reads `CUTOVER_PAGE_SOURCE` (= `web/e2-editor-app.js`), the same constant `build_cutover_page.py` imports. Candidate mode builds a mirror first and refuses if the other shell modules or `e2-editor.html` in `dist/` differ from source. Report gains `candidateSource`. Mutation `slow-repaint` re-anchored (it found nothing in web's page). |
| `471cb072` | Prediction P1-P3 for the first product-path run on B's page, committed before it. |
| `5555e554` | Merge runner: keeps every saved document (for the M2-0 diff), text-frame expectation = N1 refusal, marker placed at the tested fixture's own caret. |
| `7e01c68c` | **Spec §21**: candidate page (A); how 20.3's tolerance T is set (below); prediction L1-L4 for the corpus dry run. |
| `a8511fb2` | **Spec §22**: dispositions of the merge runner's opus review (5 BLOCKING, each re-verified against source before acceptance). |
| `b622441e` `34e311da` | Runner reworked to §22: case list generated from `merge-native/r0c/eshape.json`, per-clause verdicts, toast window closed on the reopen's own last sentence, observer bounded and recording every failed editor action (requestId -> operation map), placement tied to the current worker, `--frame-cell`, `--control`, offline `--pair`. Tests `wasm_sdk_probe/tests/test_merge_wasm_clauses.py` (16, with mutation checks). §22.3: "no observer" is impossible (placement reads the observer's caret), so the control keeps only caret and size. |
| `59b3fb4c` | Product-path net on B's page, `e2-editor-v8` vs `e2-editor-v16`, same runner sha `e3190144…`, interleaved, 3 rounds x Chrome/Firefox (12 reports). |
| `c50c7789` | Two page fixes: repaint rejected with `ENGINE_DISPOSED` (the page disposing its own engine on restart/close) no longer toasts; a BUSY retry no longer lets two repaint loops run (review N4). Test `editor-shell-v2/tests/page-render-disposed.test.mjs`; `editor-shell-v2/tests` 155/155. |
| `8ef4c5f8` | `shell_lagging_source` shared by the product-path runner, the merge runner and `compare_layout_corpus.py` (review S3). `make` is the fix for lagging source; nothing substitutes it. |
| `17af21da` | **Spec §23**: M2-5 becomes a per-cell rule (below). |
| `04e2594c` | **Spec §24**: M2-0 reduction. |
| `99d07c82` | Merge WASM shakedown run 3 (Chrome, uncounted). |
| `cbba6411` | Paired control for run 3. |
| `b2b30f65` `fa44c830` | Owner chose B for the owner's document (native R0c with WASM's fonts); result -> **finding 114**; **spec §25** falls back to A. |

## What is established (and how far)

| Item | State |
|---|---|
| Candidate page | The product-path runner, merge runner and corpus tool all measure `web/e2-editor-app.js` (+ dist's rest of shell, required equal to source). v16's current page sha256 is **`b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d`** (after `c50c7789`). |
| Product-path net on B's page | Measured page was `3cf01330…`, i.e. **before** `c50c7789`. P1 hit (12/12 complete, ready, no page errors), P2 hit, **P3 missed one cell**: Firefox `clear-format-removes-every-inline-format`, v8 1 PASS/2 NE, v16 3 NE. Cause is the harness precondition `allOnWhenTyped` varying per round on **both** profiles (not a v16 effect). Chrome: 42/42 cells equal counts; Firefox 41/42. Firefox also has the same FAIL `an-inline-format-reaches-a-selection` on both profiles. |
| Spec §23 (M2-5) | Per cell, per browser: v8 all PASS -> v16 all PASS; v8 has FAIL -> v16 FAILs not more; v8 has NE and no FAIL -> v16 no FAIL (PASS/NE ratio listed, not judged). Limit: cells where v8 abstains say nothing about v16. If never run: no product-path verdict for v16. |
| Merge runner (Chrome run 3, uncounted, runner at `8ef4c5f8`, page `b003534c…`) | 20 synthetic M2-1 cases, G01 barrier, 5 M2-3 cases and 2 frame cells (F01, F02) **pass every clause**. No 重繪失敗 toast anywhere. Frame cells refuse `anchor-mismatch` with the marker surviving (N1 confirmed on WASM). |
| M2-0 (spec §24) | All four inputs' WASM no-edit saves differ from native in bytes, equal in text. Reduction = sort root `xmlns:*`, drop empty `office:forms`, drop `text:soft-page-break`; after it all four equal. No case collapses under the reduction (32 cases checked). **Spec §5's M2-0 prediction was wrong in two places** (synthetic documents also differ; the owner's document differs in forms and page breaks, not styles). |
| After-key documents | 19/21 byte-equal Writer's own key arm after the reduction. Y01/Y02 differ because the page typed `x` first: typed text goes through the page's insert path, so spec 12 (text only) applies; the runner marks `afterKeyBytes` NE for `typed-merge`. |
| Paired control (`--control`, Chrome) | 39 case pairs, 0 differ (generation transitions, toast sequences, paragraph text of 21+21+7 kept documents; not vacuous). **Proves only** that response recording and the `postMessage` wrap are inert; the caret listener is in both arms and is not covered (spec 22.3). |
| Owner's document | 11/11 `placement-mismatch` on WASM (no key pressed): WASM line heights are about 0.79 of native (348/276, 521/414 ... twips). Native R0c rerun with WASM's own 13 font files and fontconfig: W1 hit (11 `merge`, 0 KILL), **W2 missed** (carets identical to the twip), strace positive control (7 font files opened with the config, 363 without) shows the config was in effect. So the cause is on the WASM engine side: **finding 114**, undiagnosed. |
| Spec §25 | M2-1 population = 20 merges (boundaries 16 + indent 4) + G01; M2-3 unchanged (5). Owner's document is covered natively (R0c, W1) and on the host by R (`check_m3_production_ui.py` merge arm); `--owner-document` is diagnostic only. Limit: no per-junction WASM measurement of the owner's 11 junctions. |
| Corpus layout (§21.2, **not run**) | Per comparable document: same band count and every band's top edge differs by <= T. T = max edge difference of a v16-vs-v16 dry run (separate browser sessions) + 2 px (the 2 px is a glyph-shape allowance, not a measurement). Red case v16 vs v15 (one CJK family = the cause of 113): at least one document with `cjkCharacters > 0` must differ above T and every `cjkCharacters == 0` document must stay equal (a miss is a second variable to register); red case not red -> the criterion may not be used. T is appended to the spec and committed **before** the counted comparison. Prediction L1-L4 is in `v16-shakedown/layout-corpus/PREDICTION.md`. |

## Next, in order

1. **Re-run the product-path net on the current page `b003534c…`**, v8 vs v16, same runner sha, interleaved, 3 rounds x Chrome/Firefox; judge by spec §23. The `59b3fb4c` result measured the page before the two repaint fixes and may not be cited for the v56 freeze.
2. **Merge runner on Firefox**: instrumented run and `--control`, then `--pair`, with `--frame-cell`; use the tool-generated list (spec 25: two rounds, 26 cases), no `--cases`. Check **N2** (Firefox `keyToResponseMs` sanity) before trusting any latency. The runner changed in `fa44c830` (sha prefix now `c3f723b3be6eb4bf`, run 3's report says `c2c94578…`), so counted runs bind to the new one.
3. **Layout corpus**: `python3 tools/compare_layout_corpus.py --profiles e2-editor-v16 e2-editor-v16 e2-editor-v15 --out <dir>` (dry run + red case, Chrome, machine quiet); judge L1-L4 against the committed prediction; append T to spec §21 as a new section and commit; **then** the counted comparison v16 vs `e2-editor-v15-cjk-r5-ab`. The three non-zip documents are not comparable on either arm by design.
4. **Freeze shell generation v56** (the page and the two shell modules that differ from v55), `make` dist, pins; then counted M2 (3 rounds x 2 browsers, tool list). **Still unwritten in the runner: M2-1b (N >= 20 repeated merges), M2-2, M2-4 (105 merges)** — say so in the report, do not let a counted M2 imply them. Then host 0.2.8 (`check_m3_assets.py` Z2-2 and "Z2 D" hardcode `cjk-r5`; change to `cjk-sub-e5`, which is a new pin) and R. The page's `workerUrl` moves to v16 last (wasm pin value unchanged).
5. **Finding 114**: read the WASM font substitution path (why the same fontconfig yields Noto Sans CJK TC natively and Liberation line metrics on WASM); measure **v8** on the owner's document (113 says v8 behaves the same; never measured on this document).

## Open, not diagnosed

- **C30**: in shakedown run 2, C30's `beforeKey` checkpoint already read 「有（r2）」 on a freshly opened document (the previous case, C29, ended with r2). Stale indicator carried across cases, or a real pre-key checkpoint? Not looked at. Run 3's M2-3 clause "checkpoint revision = revision before the key" passed all five, so it may not matter, but nothing explains it.
- The Firefox `clear-format-removes-every-inline-format` instability (the precondition `allOnWhenTyped` varies per round on both profiles). Spec §23 routes around it; it is not fixed.
- Finding 113's Taiwanese-font-name item is now finding 114 (above).

## Waiting on the owner

- Size work beyond the CJK subset (unchanged: measure first, Brotli, base-pack `FS.open` census; ICU trim deferred to the next core rebuild).
- Nothing else is blocked on the owner. The owner's document decisions (B, then A by the pre-written rule) are done.

## Standing rules (carried, plus new)

- One runner at a time; native probe runs need a quiet machine; never `pkill -f` with a pattern matching your own command line.
- Never `rm -rf "$VAR/…"` — the harness refuses it; use literal paths or new directory names.
- The owner's `PMPC指南.odt` never enters the repository (read only from `wasm_sdk_probe/build/scratch-m3-production-ui/`); reports and evidence carry hashes and paragraph indexes, not paragraph text. Kept saves of it live under `wasm_sdk_probe/build/`.
- Typed-text documents compare by paragraph text, never bytes.
- `build_cutover_page.py --write` only at the cutover; candidate measurements use `--candidate-profile`.
- Anything packed into a profile is built deterministically (fontTools: `recalcTimestamp=False`) and verified table by table against what it replaces.
- Never write into a mirror subdirectory (they are symlinks into `dist/`), only the mirror root.
- `findings/evidence/**` and `handoff/**` English; specs, research, findings' prose zh-TW; specs append-only (corrections go after, naming what they supersede).
- **New:** a predicted-before-the-run file is committed before the run; a miss is reported as a miss and the pre-written fallback is taken (spec 25 did this).
- **New:** a candidate report is only evidence about the page it names; check `candidateSource` and `pageSha256` against `build_cutover_page.py` before citing it. The page changed after `59b3fb4c`.

## Lessons this stretch

- **A "nothing changed" arm needs a positive control.** Native R0c with WASM's fonts came out identical to the twip; that is only informative because `strace` showed the config really restricted the process to 7 font files. Without it "no change" and "config not applied" are the same line.
- **A mutant survived the toast-count test** until a red case that actually exercised the count was added (a doubled reopen sentence from two repaint loops, N4). A test that cannot fail on the mutation does not guard it.
- **The page a tool measures must be read from the same constant as the tool that ships it.** Two tools reading two files (`dist/` vs `web/`) produced two "candidate" reports of the wrong page; one shared constant plus a refusal on lagging source closed it.
- **WASM's typed text goes through the page's insert path**, so a typed arm differs from Writer's in bytes (rsid span vs automatic style) while the text is equal; spec 12 (typed -> text only) was confirmed on Y01/Y02, not merely assumed.
- **Predictions written first caught three of my own mistakes**: spec 5's M2-0 prediction (two parts wrong), P3 (one cell), W2 (the fonts were not the cause). Each miss changed a decision rather than being explained away.
- **A harness precondition that varies on both arms is not a profile difference.** The Firefox clear-format cell looked like a v16 regression until the precondition column was laid out for all six reports.
