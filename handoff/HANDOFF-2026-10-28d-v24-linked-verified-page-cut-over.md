# Handoff: v24 linked, verified and archived; product page cut over; generation 77 not frozen yet

Supersedes `HANDOFF-2026-10-28c-v24-implemented-link-handed-to-owner.md` (read it for the decisions and the pre-link record). Checkpoint 2026-10-28 ~11:20 +0800. **Nothing is running.** Tree clean except the unrelated untracked `codex-claude-code-delegation.md`. Commits since 10-28c: `008efd72` (link-day verification + archive), `63ea44da` (page cutover + spec §15).

## Established

- **Owner linked v24** (10:51–10:54): `e2-editor-v24`, ABI 6, `typedInsert` declared, wasm `276158084a602178…`, loader `64aaa8dc…`, worker `41041fe7…` (= `sdk/v24-feature-worker.js`), manifest `f9554e8c…`, exports `f5b21630…` (37 lines), 23 actions, `withheld: ["select-all"]`.
- **L1, I1-v24, archive** (`findings/evidence/link-batch-v24/post-link/README.md`): both contract checks hold on the real log and manifest; X1 `VERDICT PASS` with exactly the declared worker, leaf and export, `abiVersion` 6; reds (a) abi 7 → `manifest`, (b) leaf absent → `declared-leaf`, export list unchanged → `exports`; 2,348 frozen files unchanged, only the four v24 profile files new; `ScDocShell` 0; E1-C intact. Archive `wasm_sdk_probe/build/archive/e2-editor-v24-27615808-worker-41041fe7/` (5/5), receipts copied to `post-link/archive/`.
- **Cutover** (`cutover/README.md`): page requires `typedInsert` at open (else `PAGE_BUILD_MISMATCH`), repointed by `build_cutover_page.py --expect-sha256 b15a6d8e…`; page `c25b11c4…` → `b15a6d8e…`; `dist/` copied (`make e2-c-assets`, two `cp`). V0′ after cutover holds (SDK + page restored to v76 bytes → v23 completion re-read green; restored afterwards).
- **Spec §15**: generation 77 is frozen after the §6.3 preparations pass (ruling 1's order), not at cutover. Until then every report binds page `b15a6d8e…` + candidate shell digest `56ce44c78043220e…`. Freezing 77 needs explicit exclusions: v76's six + `sdk/v24-feature-worker.js` (the tool's frozen list lacks v76, so it would otherwise inherit v75's three); also add v76 to `FROZEN_MANIFESTS` and bump `MANIFEST` in `tools/build_e2_c_shell_bundle.py`.

Note: after the cutover the v23 product page is no longer what `dist/` serves; v23 can be re-read only with the two declared shell files restored (V0′) or from its archived checkout.

## Next (spec §6.3, then §6.4)

1. **v24 instruments, new files only**: v23's runner/judges (`tools/v23_feature_selection_cases.py` PROFILE/ARTIFACT_PINS/BUNDLE/PAGE_SHA256, `tools/judge_v23_feature_selection.py`, `tools/judge_v23_product_four_arms.py`) hard-code v23 and are byte-bound — wrap or derive. The v24 S5 judge adds T2 per request (`route` and reply `method` both `uno-insert-text`, `completion: uno-command-result`; missing `route` or any `method:"paste"` in a type cell = FAIL). J-red before use: (ii) synthetic proof-absent, (iii) v23 counted-02 `shift-Right@cell-end/type` page → FAIL naming the route, (v) guard removal.
2. **(vi)** v24 manifest + archived v23 `probe.wasm` → worker init `DECLARED_EXPORT_MISSING`; **(vii)** leaf removed → page refuses at open, zero `insertText` requests, plus positive control (leaf present → first typed char's request carries `route:"uno-insert-text"`). `showExpired` hides the paper and disables the toolbar but does not detach input — (vii) measures whether that is enough.
3. **M2**: 84 S5 type cells × 2 browsers (est. ~1 h; ask the owner: detached run vs owner-run), 0 proof-absent, every reply `uno-insert-text`, table2 = run-03. **T5**: real CDP keys, 3/3 per browser, table2 typed `x` → A1 ``/B1 `x`; Ctrl+V `x` → `…textx`/`…textx#`. **(i)** scratch SDK mapping beforeinput → paste → T2 red. **T4** on the product-path runner (careful: several evidence runners overwrite committed evidence by default — point outputs at the scratchpad first).
4. Freeze generation 77; then counted fresh S5, R1, S1–S4, four arms; host, BINDING, K.
5. Optional: rerun M1 to check the exit-1 teardown.
