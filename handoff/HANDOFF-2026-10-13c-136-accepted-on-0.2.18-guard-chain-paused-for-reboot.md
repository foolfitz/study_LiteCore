# Handoff, 2026-10-13c — finding 136 and the restore flash fixed in page `b24d754a…` (host 0.2.18, accepted); the condition-5 guard chain was paused for the owner's reboot before its first round

The owner was away and said 「我授權fable帶我裁決」, and later 「今天不受token軟上限的限制」. All forks this round went to fable as subagent rulings (ruling-2, ruling-3 with addenda 1–6). Then the owner said they may need to reboot; the guard chain was stopped before any round finished. **Nothing is half-written: every finished step is committed.** The previous handoff is `HANDOFF-2026-10-13b-134-fixed-0.2.16-uncounted-candidate.md`; read its State for 0.2.16.

## After the reboot (the owner, or the next session)

1. `cd ~/Projects/Nextcloud_Apps/litecore && ddev start` (no sudo needed in previous rounds). Check:
   - `ddev occ app:list | grep litecore` → **0.2.18**;
   - `git status --short` → only ` M appinfo/info.xml` (0.2.18, uncommitted on purpose);
   - `diff -rq engine ~/LibreOffice/study_LiteCore/wasm_sdk_probe/build/archive/host-0.2.18-engine-d6d04880f56e31da` → only `ATTRIBUTION.md`.
2. In `study_LiteCore`: `sha256sum wasm_sdk_probe/{web,dist}/e2-editor-app.js` must both be `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678`. `dist/` is not in git; if it differs, `make e2-c-assets` (it only copies the page).
3. **Run the guard chain:** `handoff/tasks/TASK-2026-10-13d-136-guard-chain.md`, G0–G6. It already targets `b24d754a…`, buildId `d6d04880f56e31da`, host 0.2.18.
   - Hand it to a sonnet subagent, as with the two previous chains (about 1.5 h).
   - Then verify the judges yourself.
   - `findings/evidence/136/guard/132-b-aborted-for-reboot/` is the stopped first attempt (no report). Ignore it, and do not write into it.
4. If the chain passes:
   - freeze shell **v66** (`wasm_sdk_probe/tools/build_e2_c_shell_bundle.py`: bump `MANIFEST` to v66 with a comment like v65's, then `--write --frozen-date <date>`);
   - `make test-e2-c-static` must exit 0;
   - commit host 0.2.18 (`info.xml` only), with a message in the shape of `f5b34f0`;
   - append the results to `specs/SPEC-M3-held-key.md` as §17;
   - set finding 136 → fixed (uncounted candidate) and close L-134-restore-flash (ruling-3 condition 8);
   - re-issue the owner's hand-test list for 0.2.18 (condition 7: add "Delete at the end of a table cell, then type" and "Delete at the document end, then watch the view").
5. The full count stays batched with the next engine-changing release (SPEC-M3-autosave §9.21). It now carries 127–136.

## What this round did (commits, oldest first, abbreviated)

| commit | what |
|---|---|
| `5f06354b`…`efd8f3aa` | Measurements while the owner was away (predictions committed before each run):<br>• restore window — text typed inside it lands at the restored caret, 6/6;<br>• C2 key-10 spike repeats;<br>• table refusals — run-1 had a probe focus bug; run-2/3 found **finding 136**: D put the caret in the next cell after a refused Delete at a cell end. |
| `8e08b84c`, `dcce345b`, `ff13f918` | **Ruling-2:** C2 A/B through the probe's mirror (`dist/` never written). It came out **VOID** by the rule fixed in advance (0.2.16 0/10), and 0.2.15 showed the same stall once.<br>**Finding 135** registered: the worker is silent for about 200 ms after key 9. C2's single-run gate is luck at about 30 %. G4's PASS stands; §15 says the cell is not safely under its gate. |
| `2eabcd98` | Collabora prior art (owner's hint): COOL's Writer reconnect saves the scroll offset, ignores the first-paragraph caret, clicks the saved caret, then restores the offset. |
| `9b70e8fb`…`b2b488c0` | **Ruling-3 (A″):** fix 136 and the flash in one page change.<br>• Addendum 1: harness stubs.<br>• Addenda 2–3: flash gated at `updateState`'s call site; `followCaret` byte-identical.<br>• First mechanism: a send-time FIFO, page `aebef525`. |
| `53f7aff5`…`e264b527` | Probes and judge extended (`kj` control, `wvy` after-mark, `scrollTop` judged, tool-closed over both probes' ARMS). Pre-fix baseline on 0.2.16 matched every prediction. |
| `36445d15`, `37f8ef3f`, `b40710b7` | 0.2.17 (FIFO, page `aebef525`) acceptance: **start-hold 4/4 FAIL**. Review 1 (opus) independently predicted it as BLOCKING B1: under H2 the refused key is sent before the previous one is processed, so the send-time caret is one character stale. **0.2.17 is retired, never committed or released.** |
| `fa5aa31b` | **Addendum 4:** D restores to the last caret the engine pushed with **no range selected** (`noteCollapsedCaret` in `updateState`). FIFO removed; `editorAction` is back to the `6470dec0` text. Page **`b24d754a…`**. |
| `becd0370`, `adec542a`, `95b0ddf5`, `60655ab5` | New arm `cell-start-hold`. The engine refuses it as `nothing-selected` (addendum 6 switched the control); on `aebef525` it was 4/4 one character off.<br>Judge: S1 (each press-type arm's control pinned to its paragraph) and N1 (`scrollTop` judged to the end of the log), each with a synthetic red. |
| `d624e29d`, `96e719d3`, `952a7e18` | Host **0.2.18** packaged (buildId `d6d04880f56e31da`, archived read-only). **Acceptance on 0.2.18: both judges exit 0, every arm, both browsers** (the main session re-ran both). 130-U identical. |
| `d1f51c05` | Guard-chain task retargeted to 0.2.18. Not run (paused). |

## Named limits and open items

- **Residual of rule (iii), registered** (ruling-3 addendum 4): stages raised after Escape #1 and before Escape #2 (`return-mismatch`, `restore` from `postMergeReturn`) leave the caret one unit off. The document is unchanged. Unmeasured.
- **Engine items for the link batch** (beside C in spec §14/§16):
  - no refusal exit may leave a selection behind;
  - a refusal should carry the pre-barrier caret.
- The page's 「這裡目前還不能這樣刪除」 toast cannot tell `anchor-mismatch` from the other unchanged stages. A backward hold into `anchor-mismatch` has no instance on the table fixture.
- **Finding 135** follow-ups belong to the owner:
  - repeat semantics for the C2 cell before the next count;
  - a worker-side timestamp shim;
  - gap-200 ×10 to separate a time-locked cause from a position-locked one.
- The owner's hand test is pending; its target is now 0.2.18.

## §34.4 (this round)

- 因執行而修 **2**: the stub lists of `page-boundary-text.test.mjs` and of `narrow-editor-v2-session.test.mjs` "B1 (page)". Each was edited twice, with witnesses identical per test on `6470dec0` (`findings/evidence/134/unit/*witness*`).
- 因審核而修 **1**: the judge's S1/N1 edit (`95b0ddf5`).
- The probe focus bug (table run-1) was in a measurement probe, not a check.

## Subagents (not reachable from a new session)

- fable: ruling-1 to ruling-3 plus addenda.
- opus: probe/judge implementer, and reviewers.
- sonnet: guard chains.

Their outputs are all in the files above.
