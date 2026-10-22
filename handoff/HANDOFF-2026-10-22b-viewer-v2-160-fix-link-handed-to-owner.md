# Handoff, 2026-10-22b: viewer v2 on the fallback core -- e96e01ec linked and measured, E6's leak half withdrawn (fable ruling 1), V2-160 failed and its cause found; the 160-fix link is the owner's next command

**First line, in SPEC-M3-link-batch-v22 §13.1's shapes:**
- **(a) installed:** unchanged -- ddev runs host **0.2.31** on package `1b4d6a1fc905fb8a`.
- **(b) built and archived, uncounted:** `ods-viewer-v2` **`e96e01ec`** on `build-a11y-gate0` (fallback F; archived `wasm_sdk_probe/build/archive/ods-viewer-v2-e96e01ec-worker-9c85043a/`); `a6390eef` stays archived as 158-B's diagnostic. The next link (160's fix) will replace `dist/profiles/ods-viewer-v2/`.
- **(c) bound / counted:** nothing. Nominal shipped version still 0.2.26; K batched.
- **(d) accumulated-uncounted list:** unchanged.

Spec: `specs/SPEC-M4-viewer-v2.md` §7.2-§7.7 and **§8 (the 160 fix, pinned before the link)**; SPEC-M4 addendum 12 (E6); SPEC-M3-production-ui §17.27-§17.28 (launcher). Previous handoff: `HANDOFF-2026-10-22-…`.

## What happened (all on 10-22, CST)

| when | what | record |
| --- | --- | --- |
| 09:15-09:18 | owner's fallback core build: K-2a/b/e true, K-2c false as required; `config_host.mk` differs only in PATH order (read, harmless); five sw objects recompiled from HEAD sources (mtimes touched by lo-submit's tdf#173931 apply/revert) | spec §7.2, `fallback-core/` |
| 09:30-09:40 | pre-link gates redone on gate0; Makefile `ODS_VIEWER_V2_CORE` default -> gate0; owner deleted the stale dist/objects (my `rm -rf` was refused) | `4cad469c`, `fallback-pre-link/` |
| 09:46 | **owner linked `e96e01ec`**; all §7.2 readings hold (no form-controls, bits 30771, base 6f7424a1, OFormsCollection 0, gzip 47,972,953) | §7.3, `fed4cc8b` |
| 10:04-10:12 | no desktop session after the 08:04 reboot -> Phase E refused on the wallet; owner chose B: **`ChromeSession` gets `--password-store=basic`** (W0: default flags stall 25 s on the D-Bus timeout, the flag 0.31 s; W1/W2 mirror-only witnesses hold); the six ODS tools record the wallet instead of refusing | §17.27/17.28, `b9a76b8a`, `aede0889`, `findings/evidence/launcher-password-store/` |
| 10:10 | targeted Phase E on e96e01ec: everything PASS; five control files refused (158-A); **tdf138507 opens**; 159's two green | §7.4 |
| 10:13-10:23 | E6's B = 0; the first counted E6 is red (one-cell-a1's reopen tail +8 KB x2); ten repeats: v2 3/7, v1 2/7, same shape -> **fable ruling 1** (owner asked): A7.1's leak sentence withdrawn, E6 = peak + shape + series recorded; finding 164; owner agreed | §7.5-7.6, SPEC-M4 addendum 12, `e6-repeat/RULING-fable-1.md` |
| 10:24-10:54 | full corpus x3: all pass except E3's registered `L-no-basic-udf` and **V2-160 FAIL** (unconfirmed 0, 2, 1; each waited 10 s) | §7.7 |
| 10:54-11:03 | finding 164's 20-cycle diagnostic: no counting segment on either link (yield rule); default wording kept | `0c314580` |
| ~11:00 | **160's cause from the existing reports**: every unconfirmed SelectAll (5/5, v1 and v2) has LOK's `Failed to dispatch .uno:SelectAll` in the worker's stderr, no other read does -- the command was never dispatched (doc_postUnoCommand dispatches to the Desktop's active frame; inferred) | finding 160, `e7694378` |
| 11:09-11:17 | native probe (`tools/probe_160_native.cpp`): 0/2,410 unconfirmed, control 1,515/1,515 -> N3, wasm-only (or far rarer natively); nothing upstream | `160-native/`, `ec3960af` |
| ~11:20 | owner chose **B: fix 160 before v2 ships**; fix written and gated (engine only: re-post a SelectAll LOK did not dispatch, 50 ms pauses, 10 s deadline); V2-160-D added; readings pinned | spec §8, `d7ead71d` |

## Next, in order

1. **Owner:** `bash ~/LibreOffice/study_LiteCore/handoff/ods-viewer-v2/link-gate0.sh` (same script; objects rebuild because `src/` changed).
2. **Mine, right after (runbook G2):** frozen set (`160-fix-pre-link/frozen-set-before.sha256`, 1,543 files) -- only the six files of `dist/profiles/ods-viewer-v2/` may change; manifest = e96e01ec's shape (bits 30771); the wasm carries `oxsdk part-text: .uno:SelectAll not dispatched`; v2 markers, OFormsCollection 0, stack PASS, E1-C intact; archive `build/archive/ods-viewer-v2-<sha8>-worker-9c85043a/`.
3. **Phase E from zero** on the new identity: targeted run (as `fallback-phase-e/run1`'s `--only` list), E6 with `--profile ods-viewer-v2` and **no `--bound`** (addendum 12) plus B, full corpus x3 judged by V2-160 and **V2-160-D** (compute from each case's `messages`: LOK's failed-dispatch lines == the engine's counts; files with such lines all confirmed; no `never dispatched`). Read per §8.3's four readings. Always pass `--out` (the runners' defaults are v1's counted directories).
4. Then a new package and Phase H in an owner-named ddev slot. The first host Chrome runner there is also the witness for §17.27's residual 1 (host runners under `--password-store=basic`).
5. Still open: H7 (owner clicks `three-sheets-distinct.ods` in Files on 0.2.31); 158-B as its own work item (finding 158); finding 164's intra-open growth work item.

## Hazards

- The E6 tool's and Phase E runner's default `--out` are v1's counted directories.
- Four Chrome launchers do not go through `ChromeSession` (`validate_e1/r7/r8_preflight`, `v21_network`): no flag there.
- `build-ods-viewer-v2` (6.0 GB) is now only 158-B's starting point; nothing defaults to it.

## §34.4

- This stretch: because of execution **+1** (the launcher, §17.27: W0 + today's refusal), because of review **+0**. The criterion withdrawal (addendum 12) and V2-160-D are criteria, not check repairs. Running total since 10-14b: **46 / 27.**
- New tools, unreviewed: `tools/probe_160_native.cpp` (a probe, judges nothing), `e6-repeat/cycles-20/classify.py` and `launcher-password-store/compare_w2.py` (one-off comparators with their own red cases), `run_ods_viewer_e6_leak.py --profile` (an option, not a judge change).
