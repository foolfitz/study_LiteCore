# Handoff: 0.2.39 installed then rolled back; findings 171/172; v25 spec pinned

Checkpoint **2026-10-29 ~11:40 +0800**. Supersedes 10-29d as the entry point. Study HEAD **152cb6ad9**.
Tree clean except the unrelated untracked `codex-claude-code-delegation.md` (preserve it).
**Nothing is running.** Another session is using DDEV: anything that needs DDEV must queue behind
the owner (ask first). Everything in the next steps below is offline (mirror, native tests, em++).

## What happened today (all committed)

1. **0.2.39 installed** in an owner slot (`e6e704d9a`): guarded installer, Files workflow 52/52.
2. **K protocol ruled** (`f95ad1d52`, spec v24 section 23, `findings/evidence/host-0.2.39/k-protocol-ruling/RULING.md`):
   modified A; revision 1 anchors product-path tolerance on the committed 0.2.26 **v21** records.
3. **Nine cells localized** (`6b849569f`, `k-nine-cells/`): same tools (runner `7ba30235`), same
   browsers, consecutive runs on shipped products via `make_tree.py` (git archive + dist symlink
   mirror + decoded package): v21 == v22 on all 46 checks; v24 regresses 8. v23 never shipped, so
   **0.2.39 was the first package to ship them**. Process lesson recorded: regression baselines must be
   the last shipped/counted product (T4 compared against unshipped v23).
4. **Owner chose rollback** (`e78e8786f`): engine is exact 0.2.38 (`5ad1f70a8c5f7d2f`), host label
   stays 0.2.39 (host source `4a8b3cd`), Files workflow 52/52 on the old build, DDEV states restored.
   0.2.39's engine archive is intact for later reinstall.
5. **Findings 171/172** (`de7af5ac3`), measured with `k-nine-cells/diag-format/diag_format.py`
   (v22 package vs v24 dist side by side, Worker observer, saved ODTs):
   - 171: ordered format path never sets `barrier.stage`; worker derives `dispatched:false`;
     blank-line bullet blocks the queue (`recoverable-error`). v22 `dispatched:true`, v24 `false`.
   - 172: v23 gate `if (!gOrderedProof.stateItems.count(unoCommand)) return false;` in
     `inlineFormatArgumentResolved` (`probe_engine.cpp:2211`, commit `9b6d4a6fb`) rejects no-op
     requests; clear-format's first no-op answers `LOK_COMMAND_FAILED` and the page loop stops.
6. **fable ruling on fixes** (`f30acd0e6`, `k-nine-cells/RULING-v25-fixes.md`), verified:
   172 = (a′) same reply as a change plus `witness` (frozen `editor-client.js:84-90` forbids
   `changed:false`); 171 = set stage before dispatch AND serialize `dispatched`; cell 7 =
   I-worker-inducer-single-shot (finding 038 no longer reproduces on v24, so the recovery check
   spends the single-shot inducer); cell 9 criterion pinned. `DISPOSITIONS.md` has the per-cell table
   and the correction (row 7's first cause was wrong).
7. **v25 spec pinned** (`152cb6ad9`): `specs/SPEC-M3-link-batch-v25.md`; ordered-commands spec
   section 23 amends 15.2/16.4 (no-op proof). Append-only from now on.

## Next steps (spec v25 section 8)

1. Engine under new define `OXSDK_E2_V25_FORMAT_PROOF` (requires V24): 171 in
   `src/ordered_format.inc` + `FormatStateBarrier` fields + `appendFormatBarrierDetails`; 172 in
   `src/ordered_engine_reply.inc` `composeOrderedUno` with a new helper (do not edit
   `inlineFormatArgumentResolved`). Reading done: no live v23 code reads `stage`
   (2235/2256/5981-6081 are `#ifndef OXSDK_E2_V23_LINK_BATCH`; deadlines need `stageDeadlineArmed`).
   Tests: extend the native fake-LOK pattern of `tests/ordered_format_test.cpp`. Red cases first
   (R1/R2/D1/D2, V0-v25 preprocess identity for v23/v24 defines, em++ `-fsyntax-only` with a
   positive control, M1-1 carrier red then green). Agent may run em++ checks and native g++
   harnesses per AGENTS.md (check `uptime`/`pgrep -a make` first, `taskset -c 0`, receipts).
2. `sdk/v25-feature-worker.js` from the archived v24 worker (closed diff list, W1/W2).
3. Makefile v25 block, `build_e2_v25_feature_profile.py`, `check_v25_feature_contract.py`,
   `link_v25_feature_owner.sh`, `test-v25-feature-static`, `what_the_link_ships` variant.
4. Hand the link to the owner (`bash tools/link_v25_feature_owner.sh`; compiling = owner's).
5. Post-link: static checks, page to v25, freeze generation 78 only after all shell changes, then
   F1 (diag_format with v25), F2 (`check_v25_clear_format_noop.py`, red on v24), F3, F4.

## Open owner questions

- **Spec v25 section 9**: may the S5/R1/S1-S4 counts carry over to v25 given a tool-closed preprocess
  diff showing only the declared hunks? Default if unanswered: re-run all.
- K still needs its own 8-10 h no-site window, after v25.

## Frozen facts and cautions

- Nominal shipped host is still **0.2.26**. Owner's DDEV runs engine 0.2.38 under label 0.2.39.
- Do not edit frozen bytes: v23/v24 tools, the product-path runner (`7ba30235`), the 40-file live
  set, generation 76/77 manifests, `inlineFormatArgumentResolved`'s v23/v24 preprocessing.
- `make_tree.py` and `diag_format.py` are diagnostic tools in evidence dirs; their mirrors live under
  `wasm_sdk_probe/build/` or the scratchpad, never under evidence.
- DDEV 1.25.3 has no `pause`; `paused` means containers stopped (e.g. after reboot).
- section 34.4 this round: execution 1, review 2.

## Addendum (2026-10-29 afternoon): v25 implemented, link handed to the owner

Commits `9d7fb9e7c` (engine + native red cases), `58a2f5ddf` (worker), `d860a898a` (Makefile, builder,
contract checker, link script, M1-1, what_the_link_ships, v24 E1 on its linked source, frozen set).
Evidence: `findings/evidence/link-batch-v25/pre-link/README.md`. All of spec v25 section 6.1 holds;
spec section 13 records the four implementation-forced corrections (execution 1: the S guard control
aimed at the wrong translation unit).

**Owner step** (compiles; owner runs it):

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/link_v25_feature_owner.sh
```

It refuses if `build/e2/editor-v25`, `dist/profiles/e2-editor-v25` or `build/link-v25-feature-01.log`
exists; logs to `build/link-v25-feature-01.log`; runs both contract checks and prints the five hashes.

**Agent, after the link (spec 6.2, then 6.3):** L1 on the real log; X1
(`tools/check_profile_identity.py --candidate dist/profiles/e2-editor-v25 --reference
dist/profiles/e2-editor-v24`, declared worker only, no new leaf/export) plus red cases; frozen set
equal except the four new v25 profile files; archive `build/archive/e2-editor-v25-<wasm8>-worker-<worker8>/`.
Then page cut-over (workerUrl + PINNED_WASM_SHA256 prefix), freeze generation 78 only after all shell
changes, F1 (diag_format.py with v25 as a third product), F2 (new `check_v25_clear_format_noop.py`,
red on v24), F3, F4. Section 9 (carry over selection counts) still awaits the owner; default re-run.
