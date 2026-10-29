# F3: the product-path checks on v25 against v24's T4, criterion A (2026-10-29)

Spec `specs/SPEC-M3-link-batch-v25.md` section 16 (owner's choice A, pinned and committed `55b3acc59` before this run). Local mirror, no DDEV. Wrapper `wasm_sdk_probe/tools/run_v25_f3.py` (T4's wrapper with the shell rebound to generation 78 before the runner is imported; `run-01/*/shell-manifest-override.json`: default v76, used v78, the runner took it). Reader `wasm_sdk_probe/tools/read_v25_f3.py`; its pre-run exercise is `reader-pre-run/`.

## run-01 (chrome 15:57:43-16:07:19, firefox -16:17:10 +0800): **F3_RED** (`read-01.json`, exit 1)

Totals: Chrome 42 PASS / 2 NE / 2 FAIL; Firefox 35 PASS / 10 NE / 1 FAIL (v24 T4 run-02: Chrome 34/7/5, Firefox 29/15/2). Runner exit 1 in both (some checks non-PASS), as on v24.

- **P (six DISPOSITIONS product cells): all PASS.** Chrome `bulleting-a-blank-line-does-not-demand-a-rollback`, `every-inline-format-reaches-the-document`, `clear-format-removes-every-inline-format`, `an-inline-format-reaches-a-selection`; Firefox `bulleting-…`, `every-inline-…`.
- **Improved, named** (same-or-pass group): Chrome `editing-a-long-document-stays-responsive` FAIL -> PASS (the baseline run-02 had the recorded ink-race intermittent; DISPOSITIONS row 9); Firefox `clear-format-removes-every-inline-format` NE -> PASS (172's family outside the nine cells, as section 15 item 9 predicted).
- **The red, both browsers: `notice-action-recovers-the-session` [no-regression]: v24 PASS -> v25 NOT_ESTABLISHED.** Nothing else is red.
- Chrome wire (recorded, not a rule): 41 `insertText` requests (23 `paste`, 18 `uno-insert-text`), every one with a route, one ok reply, `method` equal to its route; observer lost nothing.
- `read-01-self-test.json`: all seven mutations `F3_RED`; `selfTest: FAIL` only because the base itself is `F3_RED` (the self-test requires a holding base).

## What the red cell is (read from the reports, not inferred)

`notice-action-recovers-the-session` is the designed sentinel of CLAUDE.md section 3. Its own `why` in the v25 report: it and `bulleting-a-blank-line-does-not-demand-a-rollback` "are two reads of one moment, and they are anti-correlated by construction": if the blank-line bullet does not block the queue, bulleting PASSes and there is no recovery notice to press, so this check abstains (NE); if it does block, bulleting FAILs and this check is judged. The runner records the pair as `recoveryPairing` in every report:

| Report | bulleting | noticeAction | held |
| --- | --- | --- | --- |
| v24 T4 run-02 Chrome | FAIL | PASS | true |
| v24 T4 run-02 Firefox | FAIL | PASS | true |
| v25 F3 run-01 Chrome | PASS | NOT_ESTABLISHED | true |
| v25 F3 run-01 Firefox | PASS | NOT_ESTABLISHED | true |

v24's PASS here was produced by finding 171 (the bullet put the session into `recoverable-error`, so the notice was offered and pressed). `../../host-0.2.39/k-nine-cells/README.md` had already recorded this check as NE on v21 and v22 (the 0.2.26 anchor) and PASS on v24, in both browsers. v25 returns it to the anchor's reading. The F4 runs (`../f4/`) show the same NE in both browsers.

So criterion A, pinned against v24's T4, cannot be met by a v25 that fixes 171: one baseline PASS was manufactured by the defect being fixed, and its partner rule makes the fix force the abstain. This is the criterion's red, not a product regression -- but the rule says RED, and it is not reinterpreted here (CLAUDE.md sections 8-9). A correction, if any, must be decided by the owner or a ruling, written before a run-02 that counts under it (T4 Correction 1 is the precedent).

## run-02 under correction 1 (chrome 18:07:19-18:16:54, firefox -18:26:45 +0800): **F3_HOLDS** (`read-02.json`, exit 0) -- F3's verdict

Spec 16.1 was written and committed (`b3c6fea46`) after run-01 and before this run; the reader was exercised beforehand (`reader-correction-1/`).

- **Every check's outcome equals run-01's**, both browsers (no cell moved between the runs). Totals as run-01: Chrome 42 PASS / 2 NE / 2 FAIL; Firefox 35 / 10 / 1.
- P: six cells PASS. Recovery pairing: `notice-action-recovers-the-session` NE with `recoveryPairing` held, consistent with both checks, bulleting PASS, in both browsers. No-regression and same-or-pass groups: no problem. Improved (named): the six P cells, Chrome `editing-a-long-document-stays-responsive` FAIL -> PASS, Firefox `clear-format-removes-every-inline-format` NE -> PASS.
- Remaining non-PASS on v25, all equal to v24's T4: Chrome `the-enter-key-reaches-the-document` FAIL (I-enter-raw-substring), `a-boundary-arrow-press-does-not-cost-the-work` FAIL (I-worker-inducer-single-shot), `a-refused-action-is-reported-and-changes-nothing` NE; Firefox `an-inline-format-reaches-a-selection` FAIL and nine NE as on v24.
- `read-02-self-test.json`: base `F3_HOLDS`; all eleven mutations `F3_RED` -> `selfTest: PASS`.
- Chrome wire (recorded): 41 `insertText` (23 `paste`, 18 `uno-insert-text`), every route equal to its ok reply's `method`; nothing lost.

With F1, F2, F3 and F4 holding, DISPOSITIONS rows 1-6 are fixed and re-measured on v25 (mirror). K itself has not run.
