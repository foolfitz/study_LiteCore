# Prepare ABI 6 only after the diagnostic decision closes

Status: read-only preparation, not authorization to implement or link. The coordinator reports r2 audit/archive and corrected04018/18 plus the per-open/proof auditor passed. Bounded, W-D, S-init and required workload/timing obligations are not all closed. Start no feature source work until the declared hard diagnostic readers pass on the bound r2 identity; retain the separate record-only/NE treatment of metrics in `findings/evidence/link-batch-v23/diagnostic/remaining-obligations-map-2026-10-26.md`. A partial PASS is insufficient.

Authority: `specs/SPEC-M3-ordered-commands.md` sections6,9.3,10 and appended16–20; `handoff/PLAN-2026-10-20-ordered-commands-v23.md` with its appended ruling; current checkpoint `HANDOFF-2026-10-26-v23-r2-diagnostic-in-progress.md`. The earlier `SPEC-M3-link-batch.md` sections4.1/4.2 describe the exact six-move interface; its section18 corrects the old “ABI5” label to ABI6. Its withdrawn completion mechanisms must not be restored: ordered section16.4 controls the first-poll completion instead.

## Exact public contract delta

These are behavioral additions on existing action IDs, not six newly allocated IDs. Keep the complete inherited external action list1–23 and mapping unchanged. Allow the existing boolean `extend_selection`/`extendSelection` for all six rows, and permit unshifted moves from a range through the same action. Writer determines the actual collapse/landing; do not emulate it with a preliminary click.

| Existing action | External ID | Internal ID | ABI6 gesture list / mask |
|---|---:|---:|---|
| move-character-left | 1 | 1 | collapsed, range-single, range-cross / 7 |
| move-character-right | 2 | 2 | same / 7 |
| move-line-up | 16 | 3 | same / 7 |
| move-line-down | 17 | 4 | same / 7 |
| move-line-home | 18 | 5 | same / 7 |
| move-line-end | 19 | 6 | same / 7 |

Gesture bits are collapsed1, range-single2, range-cross4. The current gate is action-based, not extend-based: granting both range bits enables both shifted and unshifted range movement. Do not promise independently masked Shift grants. Remove `no-extend-selection` only from16–19;1/2 already accept the flag in C/worker/client, but their current manifest grants collapsed only and the page drops Shift.

`kMaxExternalAction` remains23 and `kMaxInternalEditorAction` remains25; preserve the static assertions and narrowing-only mask behavior. No external24+ or internal26+ allocation is needed. Keep document-start/end external22/23→internal24/25 collapsed-only/no-extend: Ctrl/Cmd+Shift+Home/End is not among the six authorized keys. Keep select-all21 present with `gestures: []`, mask0. Keep delete-selection20 range-only/mask6 and its existing table/note limitation; caret deletes3/4 remain collapsed-only. Other actions/grants, arbitrary-key/UNO rejection, typed boolean flags, positive uint32 request IDs and uint32 revisions retain their existing bounds. `enabled` remains restricted to inline formats.

ABI6 must be selected only for the feature identity; the original/r2 diagnostic identities remain ABI5. Keep accepted completion names, `changed:false` and unchanged document revision for moves; serialize post-flush state at the first poll. Do not resurrect extend waiters, timers, old staged merge attribution, or claim headless L-C is solved. The native Q bodies are already in the diagnostic engine. Ordered section16.1 corrects feature deletion scope to the client/judging half and required product arms.

## Cohesive implementation units after the gate

1. **ABI and manifest:** `src/editor_api.h/.cpp`, a new feature-specific builder using the existing v5/v4/c/b chain, and Makefile feature-only ABI selection. Expand `isMove` flag acceptance to the six rows, preserve numeric mappings/bounds, stamp ABI6, and make the six mask/limit edits explicit. Keep older preprocessed variants and original builders' default identities unchanged. The current v23 define is shared by ABI5 diagnostics, so it cannot alone select ABI6.
2. **Worker/SDK boundary:** successor product-worker source, based on an explicitly bound worker identity. Update the `editorActionV2` closed flag validator (currently permits extend only for `EDITOR_V1_MOVE_ACTIONS`), preserve exact manifest/runtime ABI handshake, public error projection and forbidden fields. Review the SDK method/type declarations; do not add a private diagnostic escape hatch to the public API. Remove all diagnostic entrances/events/exports from feature output, not merely from its advertised capabilities.
3. **Client/session/page:** `editor-shell-v2/narrow-editor-v2-client.js/.d.ts`, session only where needed, and `web/e2-editor-app.js`. Widen the six-move extend predicate and line-move options, keep every action in its existing move postcondition class, route six keydown keys with `shiftKey`, and replace range `moveFromPoint` fallback only for those six. Keep document-move fallback until separately authorized. Retain096's `CHECKPOINTED_MOVES` safeguard; do not remove checkpointing because C changes its rationale. Implement the specified retained-key/depth behavior using actual in-flight work, not fabricated selection state.
4. **Contract witnesses and shell identity:** add focused causal red cases for the actual ABI/worker/mask/page paths and the required product-route readers. Do not alter frozen old ABI enum tests to follow new code; add successor assertions. Check frozen E1-C dependencies before editing shared files. Freeze a new shell generation only after all shell changes and checks complete; never rewrite a frozen bundle to make a source fix appear deployed.

## Protocols to append before implementation

Ordered section9.3 requires per-cell protocols before feature wiring. Append, preserve earlier text, and cite the existing criterion rather than inventing a new population or tolerance:

- R1:129's42 cells plus L-129 wrap cells; S1–S5, corrected S2 sixteen v19 pre-red cells, S-12 retained Shift, and the three deferred product routes (insert→Shift, merge Backspace→Shift, ShiftRight held1second).
- Keep S-12's separately stated2second hold protocol distinct from the1second product arm. Use the prescribed release-time in-flight bound; do not substitute an arbitrary overshoot number.
- L-142 save→move→type, the identical-character-string product arm required by15.7, L-C-number-or-indent's three named product positions, fixed-question3 table/frame arms, and the page's retained-key criterion.
- For every product runner on the feature profile,096 `clausesExercised` must include a true B2. Missing/false B2 is a product failure. Do not edit that check, its mutations, `check_soak_bank.py` or `tests/test_product_path_mutations.py` to obtain green; observe the specified first-clean-count cutoff and section34 rules.

Carry forward the exact native/fixture/source provenance and postcondition meanings when writing those protocols. The old S2 read rules were corrected repeatedly; use the corrected sixteen-cell requirement and C first-poll rule, not an obsolete first-callback rule. No new browser repetition count, timeout or statistical threshold is assigned by this work order. The missing per-cell append is an outstanding prerequisite, not permission to infer its values during a run. Private diagnostic4–9 observations are not public Shift acceptance.

## Scope decisions to record, without inventing grants

- Confirm the inherited six-action representation above in the feature protocol. Existing sources support it directly; “new actions” in ordered section6 does not itself allocate new wire IDs. Distinct extend action names would require a new explicit interface decision, not silent24+ allocation.
- Choose the narrow feature-only ABI selector and successor worker isolation strategy before editing: current `sdk/sdk-worker.js` carries Calc changes, whereas diagnostics used frozen v22 bytes plus a private tail. Preserve installed Calc and frozen worker bytes; a new feature worker must implement the public validators and contain no diagnostic tail.
- Confirm the feature profile/build target spelling and complete the required per-cell protocols. Existing planning/checker uses `e2-editor-v23` / `build/e2/editor-v23`; there is currently no corresponding Makefile target, so no historical command is runnable yet. No new Ctrl+Shift document moves, select-all grant, or table/frame delete-selection grant is implied.

## Eventual owner-only link boundary

Prepare, but do not execute now, a new `dist/profiles/e2-editor-v23/sdk-manifest.json` target with fresh `build/e2/editor-v23` objects, ABI6, the established ordered engine and the same headless core. Require `OXSDK_E2_V23_LINK_BATCH` plus its mainloop/transitive dependencies, and exclude `OXSDK_E2_V23_DIAGNOSTIC`, diagnostic exports/tails, and diagnostic `STACK_OVERFLOW_CHECK=2` as the existing feature-build reader requires. Do not reuse r2 objects.

After protocol append, implementation, reviews, causal checks, source/core/worker binding, shell preparation and a checked dry-run, issue a fresh owner command equivalent to `make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v23/sdk-manifest.json` from `wasm_sdk_probe`, with a new preserved log and explicit environment hygiene. The owner performs this compiling make. Read actual feature log/bytes and archive the new identity before section9.3 execution. Host deployment and K still require their separate owner-designated window; this work order grants neither.
