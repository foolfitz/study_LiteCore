# R1 reader verified, four product arms PASS; S5 oracle decision pending

Supersedes `HANDOFF-2026-10-27c-v23-ruling-4-witness-bound-r1-prep-passes.md`. Checkpoint on 2026-10-27, about 12:00 +0800. Evidence head before this handoff: `431bce12`; product runner code is `6c1640f6`. Nothing started by this task remains running. The tree is clean except the unrelated untracked `codex-claude-code-delegation.md`; preserve it.

The owner alternates Codex and Claude Code on this project. In this session the owner authorized **Astra consultation for difficult decisions only**, not routine delegation; one narrowly scoped consultation was used. Its advice is not a fable ruling. The previous session's fable decision delegation was explicitly session-scoped and has not been renewed. The owner granted unrestricted execution access after sandbox failures; personal prohibitions on sudo/root modifications and the default owner-run compiling make still apply. No build/link, native execution, shell generation, host/DDEV change or upstream submission occurred.

## 1. Completed: the 27c test failures and R1 ruling 1 C1-C4

- Reproduced all 22 preserved-page failures and the native-deletion assertion's TypeError. `b3fca864` skips witnessed empty-mark rows in the native-deletion assertion; `56b33914` adds only the explicit `emptyMark: null` / `emptyMarkWitness: null` expected defaults to historical S5 inspections. Every other field still compares exactly; non-default values are not ignored.
- Added a bound re-read of all 24 R1 prep-01 pages, including decompressed receipt SHA verification. All 12 Chrome and 12 Firefox pages remain PASS; only `staleFields: []` is added.
- `a58e49d0`: mutation census `r1-source/reader-mutation-sweep.ruling-1.output.json` gives **ALL_KILLED 62/62**: 56 AST-enumerated conditions and 6 defining expressions. The new stale check is in the census. The old 61-mutation output remains preserved.
- `230ea150`: `r1-source/check-stale-controls.py` replays C1 literally against the archived reader at `2b561678`: actual pre-move candidate caret, actual old range selection, actual pre-move control caret, missing candidate state. All four are false PASS on the old reader; current results are FAIL, FAIL, NE, NE with the prescribed reasons. No browser observation is claimed by these model controls.
- `r1-source/VERIFICATION-ruling-1.md` contains commands/results. Reader SHA remains `d77ec17418c1c27ead7aa2c809038df039202863330ba13e51bec06a38c6f4a3`; test SHA remains `bcd9421592e50e097f33c10bbebeb505a4b2d49ec5e4f5ae1a238607db4a4560`. The mutation output's bindings were checked again at the end.

Final integrated-source host checks all pass: selection 50, R1 50, native S5 type/boundary 12; four-arm host tests 49; original product mutation static tests 10; Node observer cases 11. A sandboxed Node run exposed only a file-level wrapper plus stream-fd errors and was not credited as the 11-case proof. After access was granted, all 11 internal cases ran explicitly.

## 2. Completed: measurements for the two order-dependent S5 cells

`s5-order-prep-01/` is a preserved setup failure: the sandbox prohibited the local server socket, zero browser cells. The approved outside-sandbox run uses the separate `s5-order-prep-02/` name, with two cells in each browser:

- `shift-Home@heading-mid/backspace-twice`
- `shift-Home@list-mid/backspace-twice`

All **4/4 remain NE `native save not order-independent`** under the existing ruling 4. Their saved inspections have not been reclassified. Both browsers establish single-line witnesses and original-document native comparability. Every candidate equals the bound every-member-settled native save under ruling 2's native comparator (`strip_ffd(reduce_content(...))`) and its fresh settled-WASM arm under full reduction; every candidate differs from queued native. Heading differs in paragraph/heading structure; list has equal paragraph text but `list-item` versus `list-header` structure. A text-only comparator is not sufficient.

Reproducible evidence: `feature-protocol/s5-order-oracle-review/read-prep.py`, `comparison.json`, `BRIEF.md`. The reader verifies browser-arm bindings, the original 336-cell native witness validation, direct candidate-original versus witness-own-before comparability and the non-collapse guard. It censuses all 336 cells' member timestamps; all pass. For each member, key-up return precedes its read and every non-final read completes strictly before the next key-down. Native setup/save lifecycle is **source-bound**, not independently timestamped. Four browser observations share two native witnesses; they are not four native repetitions. No new native run was needed or performed.

### Pending decision — do not silently implement A

The owner has been presented with A/B/C; **no answer has arrived at this checkpoint**. Granting execution access did not select an oracle. Ruling 4 still applies, so these cells remain NE and counted S5 cannot close.

**A, recommended by Astra:** use the same cell's bound every-member-settled native before/after pair for the tool-derived non-empty-mark, order-dependent partition. Keep original comparability, reduction non-collapse, structural comparison, Home/End single-line premise and overlap requirements. Label the distinct native schedule. Missing/invalid witness defaults to NE; no fallback to queued native or WASM merely to obtain a PASS. Membership must come from the generated native-capable population and native disagreement, never two hardcoded IDs or agreement with the candidate.

**B:** settled-WASM reference, explicitly narrowing these cells to ordering/self-consistency.

**C:** retain NE and leave S5 blocked here.

Astra's advice is summarized in `BRIEF.md`; it is advisory, not an authorized fable ruling. Agreement of every-member-settled native and Shift-only-settled WASM does not prove schedule equivalence. Two identical Backspaces cannot explain the difference merely by swapping them; no responsible layer or reordering cause has been established.

If A is selected, existing native files suffice under the disclosed source-bound lifecycle, but a proper plan/reader change and red controls are still required. Bind the settled witness's **own** before/after saves; validate exact sequence/posts, every step, finite non-boolean times, non-capped settles, inter-member policy, source/receipt/core/environment/fixture/raw/save hashes. Red controls must include missing/bad witness/save/hash, capped/wrong/interleaved steps, wrong own-before, queued heading/list results used as candidates (FAIL, including structure-only list difference), emptyMark handed to native (refusal), and a new generated member without its witness (refusal). Preserve historical configs' NE and old pages; append the owner decision and the exact replacement of ruling 4's condition 1, and append S-CASES. No count is carried from prep or counted-01.

`0d97a584` registers ruling 4's other named limitation in `s5-order-oracle-review/GUARD-ATTRIBUTION.md`: behavior exists, but no external guard has been demonstrated red for "caret deletion after a no-op Shift removes two units." The scoped source inspection does not claim an exhaustive absence of guards. No mechanism was added. Do not credit the ordered-delete route/model tests as that specific causal proof without evidence.

## 3. Completed: four-arm integration and the first qualifying population

The original pending patch is integrated (`c6213c85`); **do not apply it again**. The host integration test now reads the actual runner rather than applying a preparation patch to it.

The first integrated Chrome attempt stopped at boot: observer entry HTTP 404. It is preserved as `product-four-arms-integration-01/patched-chrome.json` plus a read-only CDP diagnostic. `build_mirror()` materialized only overrides already present in the source tree. The new host test first showed both new observer files missing; `6c1640f6` materializes all overrides after the walk, including new files, without writing the original tree. This is the new execution-forced instrument fix in this checkpoint.

Two-stage sequence from `product-four-arms-source/README.md` was followed:

1. **Compatibility preparation** `product-four-arms-integration-01/`: unpatched and corrected patched runner once per browser; source-bound independent comparison gives **UNCHANGED for all 42 original outcomes in each browser**. Its separate four-arm preparation gives 24/24 PASS. The failed boot and all original outcomes are retained.
2. **Fresh qualifying cohort** `product-four-arms-counted-01/`: declared/committed `cohort.json` before execution, then distinct fresh runs in Chrome and Firefox. Independent `aggregate-judge.json`: **24 rows, zero problems, all four arms PASS**. Each arm has six PASS rows (three per browser). Both complete reports reach 096 after neutral restoration. The raw page, identity, table, rows and 26 ODT saves are preserved.

`post-inputs.json`: all 24 Python import-closure files and the served identity unchanged. Prerequisite hashes still match the declaration; actual row population exactly matches the generated declared population. `commands.json` records invocations, timestamps, report hashes and statuses. Aggregate SHA: `3b9f09d66971c2d64f0e928bbafe2373f9353003eec1d95c86a191e7c4dca11c`. Evidence commit: `431bce12`.

The original full product outcomes remain red/NE: baseline Chrome 36 PASS / 3 FAIL / 3 NE; Firefox 29 PASS / 2 FAIL / 11 NE. Qualifying reports add four PASS checks: Chrome 40/3/3, Firefox 33/2/11. Runner exit 1 is therefore expected; the independent four-arm judge exits 0. This establishes only the four prescribed ABI6 arms, not overall product acceptance. Firefox 096 B2/B4 are not closed.

Re-read from `wasm_sdk_probe/`:

```bash
python3 -I tools/judge_v23_product_four_arms.py ../findings/evidence/link-batch-v23/feature-protocol/product-four-arms-counted-01/chrome.v23-four-arms ../findings/evidence/link-batch-v23/feature-protocol/product-four-arms-counted-01/firefox.v23-four-arms
```

## 4. Next, after the owner's S5 decision

1. Implement only the selected oracle decision, with its required red controls and append-only gate amendments. No changes to type oracle run-03 or empty-mark membership are implied.
2. Run S5 prep-05 with the final plan and current R1-merged page: both browsers, representative emptyMark cells, non-emptyMark before-and-after, native type, settled-WASM, plus both order-dependent cells if A/B changes their route. Suggested existing cases from 27c remain valid. No S5 prep-05 has run here.
3. Refresh the R1 mutation output if the shared judge changes (the current 62-case output binds the old exact full-file hash), then re-read prep-01 / preserved S1-S5 pages and run the affected suites. Four-arm source remains fixed and its already-established scope is documented above.
4. Only after the shared plan/instrument is final: counted R1, full 72 × two browsers, and fresh counted S5-02, 588 × two browsers, following the detached launcher pattern in `s5-counted-01.launch.sh` with new output names. Required R1 pre-red: `../findings/evidence/link-batch-v23/feature-pre-red/counted-05/report.json`. No filters, keep-going or preparation-only for a qualifying R1 run. No import-closure edits while either counted run is in flight; serialize browser/native measurements.
5. Finding 166 unipoll and finding 167 desktop-Writer remain work items; no new evidence for those layers was collected.

No counted R1 or fresh S5-02 has started. Profile `e2-editor-v23`, ABI 6, WASM `fe1f99cd…`, worker `3fd3e1e6…`, page `c25b11c4…`, generation 76 remain unchanged. Remaining named inputs, host/DDEV and K acceptance remain unclosed.
