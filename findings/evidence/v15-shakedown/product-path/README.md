# v15 shakedown: product-path net, `e2-editor-v15` against `e2-editor-v8`

Runbook step: `handoff/RUNBOOK-relink-v15.md` section 4, step 2 ("v15 must not regress any cell").
This is a shakedown. It is not counted and nothing is bound to it.

Nothing in the tree was edited for this run. The only files created are in this directory
(12 reports, 12 `*.stdout.txt`, 12 `*.stderr.txt`, `chain.log`, this README). `git status`
after the last run showed only `findings/evidence/v15-shakedown/` as untracked.

## Commands

All from `wasm_sdk_probe/`, strictly sequential (one run at a time, driven by a small shell loop
that is not kept; `chain.log` has each start and end line with the exact command). `<N>` is 1, 2, 3.

```
# v8 baseline (shipped page, no candidate flag)
python3 tools/run_e2_c_product_path.py --browser chrome  --out <DIR>/e2-editor-v8-chrome-r<N>.json
python3 tools/run_e2_c_product_path.py --browser firefox --out <DIR>/e2-editor-v8-firefox-r<N>.json
# v15 candidate page (repointed worker URL and pinned hash, as build_cutover_page.py would produce)
python3 tools/run_e2_c_product_path.py --browser chrome  --candidate-profile e2-editor-v15 --out <DIR>/e2-editor-v15-chrome-r<N>.json
python3 tools/run_e2_c_product_path.py --browser firefox --candidate-profile e2-editor-v15 --out <DIR>/e2-editor-v15-firefox-r<N>.json
```

`<DIR>` = `/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v15-shakedown/product-path`.
Default `--timeout 300`; no other flags. `build_cutover_page.py` was not called. No `make`. No other runner ran.

Start of chain 2026-10-07 10:42:26 +08:00, end 12:07:26 +08:00. Every run completed (`complete: true`,
`liveness.lastState: ready`, `pageErrors: null`, no `knownRed`, no stale declaration). No run refused or aborted.

Environment: Google Chrome 151.0.7922.169; Firefox 157.0 (snap); runner `tools/run_e2_c_product_path.py`
sha256 `5900ce877146c7bc...`. Served shell in all 12 runs: bundle `e2/editor-shell-v2-bundle-v55.json`,
whose dist copies differ from the declared manifest in `editor-shell-v2/narrow-editor-v2-client.js` and
`editor-shell-v2/narrow-editor-v2-session.js` (the known "red by design" item of the runbook); the v15 runs
differ additionally in `web/e2-editor-app.js`, which is the repointed candidate entrypoint. The runner did not
refuse on this. v15 candidate: page sha256 `fd69d79144dda5ba...`, pin `4a2710bba1ef07d9` -> `ad3f68bb85f94589`.
The two profiles were served the same shell bytes, so the comparison is not confounded by the shell.

Desktop notes: the owner's own Firefox (pid 777820, up since Oct 6) was running throughout. The owner's own
Chrome (pid 1090372, no flags) appeared at 12:00:19, during `v15-firefox-r2`; it is not a runner process and was
not touched. The three v15 Firefox reports are identical in composition (28 / 2 / 12) before and after that moment.

## Runs

| report | started | completed | PASS | FAIL | NE | ok | complete | last state |
|---|---|---|---|---|---|---|---|---|
| `e2-editor-v8-chrome-r1.json` | 10:42:26 | 10:49:18 | 40 | 0 | 2 | True | True | ready |
| `e2-editor-v8-chrome-r2.json` | 10:49:18 | 10:56:09 | 40 | 0 | 2 | True | True | ready |
| `e2-editor-v8-chrome-r3.json` | 10:56:09 | 11:03:01 | 40 | 0 | 2 | True | True | ready |
| `e2-editor-v8-firefox-r1.json` | 11:03:02 | 11:11:04 | 29 | 1 | 12 | False | True | ready |
| `e2-editor-v8-firefox-r2.json` | 11:11:14 | 11:17:17 | 30 | 1 | 11 | False | True | ready |
| `e2-editor-v8-firefox-r3.json` | 11:17:27 | 11:23:30 | 30 | 1 | 11 | False | True | ready |
| `e2-editor-v15-chrome-r1.json` | 11:23:40 | 11:32:04 | 39 | 1 | 2 | False | True | ready |
| `e2-editor-v15-chrome-r2.json` | 11:32:05 | 11:40:32 | 39 | 1 | 2 | False | True | ready |
| `e2-editor-v15-chrome-r3.json` | 11:40:32 | 11:48:58 | 39 | 1 | 2 | False | True | ready |
| `e2-editor-v15-firefox-r1.json` | 11:48:58 | 11:54:56 | 28 | 2 | 12 | False | True | ready |
| `e2-editor-v15-firefox-r2.json` | 11:55:07 | 12:01:06 | 28 | 2 | 12 | False | True | ready |
| `e2-editor-v15-firefox-r3.json` | 12:01:16 | 12:07:16 | 28 | 2 | 12 | False | True | ready |

`ok: false` on every Firefox run (both profiles) comes from FAIL cells described below; Firefox here has no CDP, so
12 of the 42 checks abstain by design (`no CDP, so a real key cannot be delivered`, etc.).

## Every check, over 3 rounds each

Counts are over the 3 rounds. `NE` = NOT_ESTABLISHED (not a pass). Bold = the v15 cell; the last column flags every
row where the v15 count differs from the v8 count in that browser.

| check id | v8 chrome | v8 firefox | v15 chrome | v15 firefox | v15 vs v8 |
|---|---|---|---|---|---|
| `product-save-button-writes-a-real-odt` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `every-ime-commit-reaches-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `ctrl-c-asks-the-engine` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `product-insert-button-inserts-what-the-field-holds` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `product-undo-button-reverses-the-last-edit` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `product-redo-button-restores-what-undo-removed` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `bulleting-a-blank-line-does-not-demand-a-rollback` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `notice-action-recovers-the-session` | 3 NE | 3 NE | 3 NE | 3 NE |  |
| `backspace-and-arrows-reach-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-keyboard-reaches-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `ctrl-v-reaches-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-caret-is-drawn-where-it-was-placed` | 3 PASS | 3 PASS | 3 PASS | **3 FAIL** | **DIFF (firefox)** |
| `the-caret-lands-where-the-click-was` | 3 PASS | 3 PASS | 3 PASS | **3 NE** | **DIFF (firefox)** |
| `bold-can-be-turned-off-again` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `a-format-that-worked-is-not-reported-as-failed` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `a-failed-format-does-not-block-the-session` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `format-a-paragraph-changes-that-paragraph` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `cut-removes-the-selected-text` | 3 PASS | 3 NE | 3 PASS | 3 NE |  |
| `a-refused-action-is-reported-and-changes-nothing` | 3 NE | 3 NE | 3 NE | 3 NE |  |
| `every-inline-format-reaches-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `clear-format-removes-every-inline-format` | 3 PASS | 3 NE | 3 PASS | 3 NE |  |
| `formatting-survives-the-next-paragraph-break` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-toolbar-gives-the-keyboard-back` | 3 PASS | 3 NE | 3 PASS | 3 NE |  |
| `the-edit-buttons-do-what-they-say` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-open-button-opens-the-file-chooser` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `an-aborted-gesture-stops-selecting` | 3 PASS | 3 NE | 3 PASS | 3 NE |  |
| `caret-follows-the-text-you-type` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-vertical-arrows-move-the-caret` | 3 PASS | 3 NE | 3 PASS | 3 NE |  |
| `the-composition-you-are-typing-is-visible` | 3 PASS | 3 NE | 3 PASS | 3 NE |  |
| `the-document-region-says-why-it-is-empty` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-projection-is-placed-where-the-document-is` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `an-inline-format-reaches-a-selection` | 3 PASS | 3 FAIL | 3 PASS | 3 FAIL |  |
| `the-page-agrees-with-the-engine-about-the-selection` | 3 PASS | 3 NE | 3 PASS | 3 NE |  |
| `the-canvas-follows-a-window-that-changed-size` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-sample-picker-opens-a-second-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `product-opens-a-document-the-user-chose` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-enter-key-reaches-the-document` | 3 PASS | 3 NE | 3 PASS | 3 NE |  |
| `a-long-document-is-drawn-or-the-product-says-it-is-not` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `the-canvas-follows-a-document-that-grew` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `editing-a-long-document-stays-responsive` | 3 PASS | 3 PASS | 3 PASS | 3 PASS |  |
| `recovery-returns-what-the-product-promised` | 3 PASS | 2 PASS, 1 NE | 3 PASS | **3 PASS** | **DIFF (firefox)** |
| `a-boundary-arrow-press-does-not-cost-the-work` | 3 PASS | 3 NE | **3 FAIL** | 3 NE | **DIFF (chrome)** |

## Where v15 differs from v8

Four rows differ. Two are v15 doing worse by the report's own verdict (A, B); one is a v15 cell that is
NOT_ESTABLISHED where v8 passed (B); one is v15 not worse (C). By the criterion as written in the runbook
("v15 must not regress any cell") the net is **not** satisfied as measured: A and B are red on all 3 of 3 rounds
(deterministic, not intermittent), and the reports do not by themselves say whether the cause is the product,
the instrument, or the premise of the instrument.

### A. Chrome: `a-boundary-arrow-press-does-not-cost-the-work`, v8 3 PASS, v15 3 FAIL

The report's own failure text (identical in all three v15 rounds):

> the second inducer never fired, so B4 -- what comes back contains what was typed -- was not measured on this profile: auto-attach delivered no session for a document worker

What the report measured on v15 (`observed`): `verdict` B1 true, B2 true, B3 true, B4 null; `clausesExercised`
`["B1","B3","B2"]`; `theEngineAnsweredThePress: true`, `stateAfterPress: "ready"`, `checkpointAfterTheKey: "有（r1）"`;
`fallbackInducer: {name: INDUCE_WORKER_FAILURE, fired: false, why: "auto-attach delivered no session for a document worker", attachedTypes: []}`.
On v8 the same check passes by the other branch: the press is not answered (`theEngineAnsweredThePress: false`,
`stateAfterPress: "recoverable-error"`), the notice appears, the checkpoint is restored and `workCameBack: true`
(B4 true via `b4Inducer: "boundary-press"`). So v15 changes the shape of this cell in the way finding 096's engine half
intends (the press is now answered, the session stays `ready`); what v15 lacks is the B4 measurement.

Related fact measured in the same v15 Chrome runs, in the preceding check `recovery-returns-what-the-product-promised`
(PASS on both profiles): on v8 Chrome `finding038Reproduced: true` (3/3), the footnote inducer wedged the engine, and
`fallbackInducer` was null. On v15 Chrome `finding038Reproduced: false` (3/3) and the runner fell back to
`INDUCE_WORKER_FAILURE`, which fired. The derived drag for the footnote inducer also differs only on Chrome:
`drag` = [left, right, y] was `[0.10621, 0.74069, 0.06138]` on v8 and `[0.10621, 0.4, 0.07197]` on v15 (Firefox: right edge
0.74 on both profiles, and 038 reproduces on v15 Firefox 3/3). The runner's own comment says a wrong aim "reads exactly like
a fixed defect", so "038 stopped reproducing on v15 Chrome" is not established by this run; only that it did not reproduce
with this aim.

Pre-existing, documented behaviour that matches the failure text (not re-measured here):
`handoff/HANDOFF-2026-09-28b-099-reproduced-in-both-modes-and-v48-measured.md` lesson 1, "`induce_worker_failure` works once per
browser ... The product-path runner has two call sites and fires only one per run today; if it ever needs both, check 42 goes
loudly red (`B4: null`, its accepted cost), not silently green." On v15 Chrome both call sites fire in one run (the
recovery arm's fallback, then this arm's second inducer), and this arm is red with exactly `B4: null`. That is a
consistency observation, not a diagnosis: no diagnostic run was made to separate "the second `setAutoAttach` call finds no
worker" from any other cause. Also the comment above the `worker-crash-*` mutations assumes 038 reproduces "on either profile"
(measured on v8 and v14 in 2026-09); that assumption did not hold in these v15 Chrome runs.

### B. Firefox: `the-caret-is-drawn-where-it-was-placed`, v8 3 PASS, v15 3 FAIL; and `the-caret-lands-where-the-click-was`, v8 3 PASS, v15 3 NE

Same read of one moment (both use the same two clicks at line fraction 0.28 of `list-contexts.odt`).

- v15 Firefox (`observed`, identical in all 3 rounds): `inkLeft 101, inkRight 584, inkSpan 483`,
  `caretAfterClickNearStart: null`, `caretAfterClickPastEnd: 585`, `strokeGained 18`, `strokeLost 0`,
  `fractionNearStart: null`. The first check requires `strokeGained > 0 and strokeLost > 0`, so it FAILs;
  the second reports NE (`a column index that came from a tie-break is not a position`).
- v8 Firefox (PASS, 3/3): `inkRight 627, inkSpan 526`, `caretAfterClickNearStart 164`, `strokeGained 24`, `strokeLost 19`, `fractionNearStart 0.1198`.
- v15 Chrome passes both (`inkSpan 389`, `caretAfterClickNearStart 129`, `strokeLost 14`); v8 Chrome `inkSpan 423`.
- The ink span of the line sampled at 0.28 is about 8% narrower on v15 than on v8 in BOTH browsers (Firefox 483 vs 526;
  Chrome 389 vs 423), so the derived click columns and the line being measured differ between profiles. The report does not
  say why (the check's own LIMIT text warns that on Firefox the caret is adjacent to glyph ink and `strokeLost` can be small).
  Not diagnosed: whether the caret is not drawn at the near-start position on v15 Firefox, or is drawn and the detector
  cannot separate it from the ink at that column, cannot be read from these reports (they store counts and columns, not the
  pixels). Do not read this as a CJK-pack effect; no measurement here links the two.

### C. Firefox: `recovery-returns-what-the-product-promised`, v8 2 PASS + 1 NE, v15 3 PASS (v15 not worse)

On v8 Firefox round 1 the footnote inducer did not wedge (`finding038Reproduced: false`) and the fallback cannot fire
without CDP (`no CDP; a worker cannot be reached over WebDriver`), so the cell abstained; rounds 2 and 3 reproduced 038 and passed.
v15 Firefox reproduced 038 and passed in all 3 rounds. This is run-to-run variation on the baseline, listed only because the
counts differ.

## Cells that are not differences but are not clean either

- `an-inline-format-reaches-a-selection`: Firefox 3 FAIL on v8 and 3 FAIL on v15 (equal). `observed`: `selectedText: ""`
  after the drag (`bandsAvailable` 20-21), `wasBoldBefore: false`, and the saved text read back as `boldAfter` starting `KITALMKBOLD...`
  against `boldBefore` starting `MKBOLD...`. The report does not say more; the drag selected no text on the baseline either. Equal in both profiles, so not a v15 difference; it does mean that
  Firefox on this machine is not a clean baseline (v8 Firefox: 29-30 PASS / 11-12 NE / 1 FAIL, `ok: false`).
- Chrome NE set is identical on both profiles: `notice-action-recovers-the-session`, `a-refused-action-is-reported-and-changes-nothing`
  (3 NE each). Everything else on Chrome is 3 PASS on v8, and on v15 except row A.
- Firefox NE cells are identical between profiles except the caret row in B (the NEs listed in the table as 3 NE on both sides).
- No recent full Firefox product-path report was compared against: a quick search found only older, partial Firefox reports
  (for example `findings/evidence/sdk-e2/e2-c-validation/product-path/round-2-high-paths/baseline-firefox.json`, 6 checks), and the
  2026-09-28 H4 baselines (`findings/evidence/098/product-path/v52-*.json`) are Chrome. So "v8 Firefox" above is this run's
  own baseline, not a comparison with a known-good Firefox run; the search was not exhaustive.

## Not measured here

- Whether either red cell is a product regression: no diagnostic or mutation run was made (out of scope for this task).
- Anything about the A/B CJK tile comparison (runbook 2b), the WASM shakedown (step 1), or the freeze (step 3).
