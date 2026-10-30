# Handoff: finding 176 batch -- v27 spec pinned, shell item and engine step done; next: E4, worker, mechanics, PL-1, then the owner's link

Checkpoint **2026-10-30 ~13:10 +0800** (first written ~13:00; updated after the worker step). Supersedes `HANDOFF-2026-10-30e-host-0242-installed-f176-next.md`; that file still holds for whatever it says that is not superseded here.

Study HEAD **811a3d530** plus this file's update commit. The tree is clean apart from three untracked files:
- `codex-claude-code-delegation.md` -- not ours; preserve it;
- `findings/evidence/176/native/build-01/f176-native` and `build-02/f176-native` -- native harness binaries, deliberately not committed.

**Nothing is running.** `dist/` still serves generation 80 / profile v26 (only source changed).

## Owner state

The owner is awake. This session the owner said:
- "這跟ddev有關嗎？有別的session在用。如果跟ddev無關就發給fable": engine item C's design went to fable;
- "C 一併交 fable": the 083 path went to fable too.

DDEV is in use by another session. Nothing in this batch needs DDEV until host 0.2.43, and that install needs the owner's slot.

Default for the next session: judgement calls go to the owner as A/B/C, and to fable when the owner says so.

## The plan of record: `specs/SPEC-M3-v27-finding-176.md` (pinned `ce782b9af`, zh-TW, append-only)

One batch:
- engine `e2-editor-v27`, a relink, run by the owner;
- shell generation 81;
- host 0.2.43.

Read its §3 (decisions), §4 (design), §7 (criteria), §8 (declared moves) and §11 (order) first. The rulings it implements:
- `findings/evidence/176/RULING-fable-2026-10-30.md` (ruling 2: shell item, census);
- `findings/evidence/176/RULING-fable-2026-10-30-c.md` (ruling 3: the design, Q1-Q6).

The design in one line: on the ordered engine's collapsed route, a multi-block readback is judged by the existing first-block predicate, with no restore before the select (op "G").
- That applies to all five paragraph actions.
- The undo stack is recorded, not judged.
- The 083 path (last empty paragraph, one-paragraph blank document) stays a toast.

## Done this session (commits 5d11bd4de..3a6998b33)

**1. Native arm** (`findings/evidence/176/native/`, `5d11bd4de`): `WITNESS-FAILS` as registered in PREDICTION.md.
- Ruling 2's candidate, the `.uno:DefaultBullet` state item, is late in every cell (25/25, median 300 ms after the first poll).
- Recorded: the readback's first block equals the saved dispatch paragraph in every multi-block cell. `FN_SELECT_PARA` overshoots forward only.
- Recorded: the undo stack is synchronous.
- Harness: `tool/f176_native.cpp` (derived from N1's `oc_native.cpp`). Readers `read_cells.py` and `read_q63.py` both have self-tests.

**2. Fable ruling 3** and the **Q6.3 cells** (`3f9c130ef`): all five actions `IN-SCOPE`, 10 cells x 5 rounds. A counted correction: the heading fixture's initial state was checked directly.

**3. Spec pinned** (`ce782b9af`) after an opus adversarial review. 9 items and the nits were folded in; nit 12 was judged and the leaf not bumped. The census is saved: `findings/evidence/v27-176/census/`.

**4. Appends** to findings 046 (B案 superseded under the conditions) and 176 (`1cb8ca955`).

**5. Shell item** (`9fbbb9b93`): `run()` writes `${label}：待確認` on `review`.
- U1 `editor-shell-v2/tests/page-review-latency.test.mjs` was red first, on exactly the three review cases, then 8/8 green.
- Shell suite 559/559. Evidence: `findings/evidence/v27-176/u1/`.

**6. Engine step** (`3a6998b33`; spec 4.1), under `OXSDK_E2_V27_FIRST_BLOCK`:
- edits: the `editor_api.h` guard; `probe_engine.cpp` struct fields and serializer (`undo` inside `formatBarrier`); `ordered_format.inc`.
- `strip_v27(inc) == HEAD's inc`, byte for byte.
- E1/E2 (`tests/test_ordered_format_v27.py` + `tests/ordered_format_v27_test.cpp`) were red first (`pre-link/e1-red-before-inc-edit.txt`). Now green, with v25-behaviour and three mutations red.
- E3: `test_ordered_format.py`, `test_ordered_format_scope.py` (run with `PYTHONPATH=tests`) and `test_ordered_format_v25.py` all green.
- Not linked.

## Done after the first version of this file (`960efd567`..`811a3d530`)

- **E4** `tests/test_format_readback_v27.py`: the production parser and predicate agree with the saved documents on 18 recorded rows (F and G), and the red cases are reported.
- **V0-v27** `V0_V27_HOLDS`: 12 rows. The positive control makes exactly the three probe_engine rows differ.
- **S** `S_V27_HOLDS`, with both controls.
- **Worker** `sdk/v27-first-block-worker.js`: W1 byte for byte, with a red extra line; W2 in a vm sandbox, with four causal controls.
- Evidence and its README: `findings/evidence/v27-176/pre-link/`.

So steps 1-4 below are DONE. Start at step 5, the mechanics.

## Next, in the spec's order (§11 steps 5-7)

1. **E4**: the production parser on the recorded HTML.
   - Extract `FormatReadback`, `parseFormatReadback`, `formatTagIsStructural`, `formatTagIsBlock`, `formatDivIsFootnoteApparatus`, `formatBarrierReadbackSatisfied` (plus the structs) from `probe_engine.cpp` by regex, as `test_ordered_format_v27.py` does.
   - Feed it the `format.html` of the rows listed in spec 7.2 E4 (F and G rows, from `native/out` and `native/out-q63`).
   - Expected predicate result = whether the saved document's dispatch paragraph is in the target state; use `read_cells.saved_target` as ground truth.
   - Hand-pin n2, r6 and r5. One mutated expectation must be red.
2. **V0-v27**: derive `findings/evidence/link-batch-v25/pre-link/v0_preprocess.py`.
   - Compare against `9fbbb9b93`, the parent of the engine commit. Its `wasm_sdk_probe/src` is identical to `9d7fb9e7c`, v25's link source.
   - Cover every unit of `E2_C_SOURCES` under the v23, v24 and v25 rules.
   - Positive control required.
3. **S**: derive `s_syntax.py`; `taskset -c 0`.
   - Positive control: a v27-only error is caught with the define.
   - The v27-without-v25 `#error` control must hit the TU `editor_api.cpp`.
4. **Worker** `sdk/v27-first-block-worker.js` (spec 4.2): the archived v26 worker plus three items.
   - The profile name in `featureExtendPermitted`.
   - The `undo` projection: `{read, changed, actionsBefore, actionsAfter}`, never `top`.
   - The header.
   - Then W1 and W2.
5. **Mechanics** (spec 5): Makefile v27 block, `build_e2_v27_first_block_profile.py`, `check_v27_first_block_contract.py`, `link_v27_first_block_owner.sh` (agent runs only `bash -n` on it), `test-v27-first-block-static`.
   - M1-1 carrier red then green.
   - `what_the_link_ships --since 9d7fb9e7c --variant link-batch-v27`.
   - Hunk reader `check_v27_ships_confined.py`.
   - PIN: source pin of both core trees, frozen set, the v26 `SHA256SUMS`, and `make -n` of the owner's command.
6. **PL-1** (spec 7.2): this is the relink gate.
   - On the mirror, v26, no DDEV: use F1's in-worker `JSON.parse` observer (`tools/diag_format.py`) on S3's recipe and F3's list-contexts cell, 2 browsers x N=3.
   - `read_v27_pl1.py` must say "would verify" N/N.
   - Otherwise there is no relink hand-off.
7. Runbook `handoff/RUNBOOK-relink-v27.md` and a short one-line command for the owner. Archive first (the v26 archive exists).

Before any browser run: no other measurement serving `dist/`. Desk gate only for timing cells (none here).

## Cautions

- **Cross-session.** Another session uses DDEV. Do not touch DDEV, and do not signal the owner's desktop processes.
- **Owner-only.** The engine relink (`make`/link). Single-file g++ harness builds and the `-fsyntax-only`/`-E` checks are the agent's own (AGENTS.md); check `uptime`/`pgrep -a make` first.
- **Bound tools.** `run_e2_c_product_path.py`, `check_v79_blank_bullet.py` and `check_v80_blank_bullet.py` are bound: derive, never edit.
- **The scope checker** counts braces textually: keep each `#ifdef`/`#else` branch brace-balanced.
- **F3-81.** It will report `ok:false` by construction (`recoveryPairing.held` false). Reading 1 will be `F3_RED`. Both are declared in spec §8; do not "fix" them.

## Section 34.4 this round

- Fixed-by-execution: **4**.
  - The native reader's clock check.
  - The heading control's design.
  - The scope checker's brace balance.
  - W2's first form called `featureExtendPermitted` without its argument; the test was wrong.
- Fixed-by-review: **9 + nits**, the opus spec review, before pinning.
- Fable rulings: **1** (ruling 3).

## Language

- Replies to the owner: Taiwan Traditional Chinese, with A/B/C for options.
- Evidence and `handoff/**`: English.
- Specs and findings: zh-TW.
