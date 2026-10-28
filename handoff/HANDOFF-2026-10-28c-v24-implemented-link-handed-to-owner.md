# Handoff: v24 typed-insert route pinned, implemented, pre-link green; link handed to the owner

Supersedes `HANDOFF-2026-10-28b-f168-route-ruled-m0-m1-pass-v24-spec-next.md`. Checkpoint 2026-10-28 ~10:45 +0800. **Nothing is running.** Tree clean except the unrelated untracked `codex-claude-code-delegation.md` (preserve it). Commits this session: `ceaa2770` (spec pinned + ruling 2), `9b224a60` (implementation + pre-link evidence), `e141bf38` (em++ checks + standing rule). No engine make/relink, browser run, native run, DDEV, host or upstream action. Frozen v23 (ABI6, WASM `fe1f99cd…`, worker `3fd3e1e6…`, generation 76) unchanged and re-verified.

## Decisions made this session

- **Owner**: the ABI question goes to fable (chose C); **v24 carries only the typing route** (chose A).
- **fable ruling 2** (`findings/evidence/link-batch-v23/feature-protocol/s5-type-route-ruling/RULING-2-abi.md`, brief `BRIEF-2-abi.md`): **editor ABI stays 6**; ruling 1's "ABI 6→7" withdrawn (the editor ABI versions the action allowlist; the new export is document-level, like page-rectangles/paste-markdown). Declaration leaf `editorContract.typedInsert: "document-sdk-insert-typed-text"`. Condition: the v24 worker refuses init (`DECLARED_EXPORT_MISSING`) when a declared export is missing from the binary — the stale-wasm protection ABI 7 would have given (the page pin only checks the manifest's claim). `featureExtendPermitted`'s profile term must name v24.
- **Ruling 2 follow-up** (same file): "no silent paste on v24" lives on the **v24 page** (requires the leaf at open, `PAGE_BUILD_MISMATCH` otherwise), not in the SDK, because `sdk/document-sdk.js` is shared by ~28 pages whose profiles never declare the leaf. On a leafless manifest the SDK ignores metadata entirely (byte-identical request, no new error); `INSERT_ORIGIN_UNKNOWN` only on a declaring manifest, where every insert carries `route`. T2 tightened to per request (`route` and `method` both `uno-insert-text`, `completion: uno-command-result`).
- **Standing rule (owner, AGENTS.md)**: em++ checks that emit no object (`-fsyntax-only`, `-E`-based `check_merge_key_undo_scope.py`, `what_the_link_ships.py`) are agent-run with `uptime`/`pgrep -a make`, `taskset -c 0`, receipts, and a positive control for syntax checks. Object-producing builds stay owner-run.

## What is in the tree

Spec `specs/SPEC-M3-link-batch-v24.md` (zh-TW; criteria table §6, corrections §14). Evidence `findings/evidence/link-batch-v24/pre-link/README.md` (English, full list).

- Engine: `oxsdk_document_insert_typed_text` → `handleInsertTypedText` under `OXSDK_E2_V24_TYPED_INSERT`: refuses invalid UTF-8/NUL/LF/CR with `dispatched:false` before dispatch; `expectOrderedUno(".uno:InsertText")`; `postUnoCommand(…, true)`; reply at the first poll on the result's **presence** → `{type:"inserted", method:"uno-insert-text", completion:"uno-command-result", resultPayload}`, absent → `proof-absent-at-poll:UNO_COMMAND_RESULT`. Revision advances in the composer (as undo/format); the page repaints on the reply's revision (`editor-session.js:306/600`), so the callback stamp is not relied on — M2 measures it.
- Worker `sdk/v24-feature-worker.js` = archived v23 worker + 13 labelled hunks (`tests/v24-worker-delta.json`). **Sixth item found during implementation**: the `inserted` reply projection is a whitelist (`{method, revision}`), so `completion`/`resultPayload` had to be forwarded (spec §14.1).
- SDK `sdk/document-sdk.js`: `INSERT_ROUTE_BY_SOURCE`, `TYPED_INSERT_DECLARATION`, `route` only on a declaring manifest.
- New tools (v23's bound tools imported, never edited): `tools/check_v24_feature_contract.py`, `tools/build_e2_v24_feature_profile.py`, `tools/link_v24_feature_owner.sh`; Makefile v24 block, `test-v24-feature-static`, M1-1 carrier `E2_V24`, `what_the_link_ships` variant `link-batch-v24`.
- **The page is not cut over** (it pins v23; adding the leaf requirement now would refuse v23). All page changes happen at cutover after the link (spec §14.4).

## Established pre-link (all with red cases first)

T3/U1, W1, W2/(d′)/(viii)/init presence (6 causal controls), E1, identity reds (abi 7, leaf absent, etc.), S3-v24 (`make -n -B` both sides; 12 differing lines inside the closed five classes), dry-run log reader, syntax-only ×4 with positive control, M1-1 red→green (only E2_V24's three objects; its three guard variants refused), what_the_link_ships (`ok: true`, no drift, only `sdk_api`/`probe_engine` changed), frozen set (2,348 files), v23 archive 5/5. Shell node tests 517/517, `tests/*.test.mjs` 111/111.

**V0 was wrong as written and is now V0′** (§14.2): v23's `config()`/`identity()` (`tools/v23_feature_selection_cases.py:484-500`) requires the live shell files to equal generation 76, so any staged shell change makes the live re-read red by construction. V0′ holds: with only `sdk/document-sdk.js` restored to its v76 bytes, `read-completion.py` exits 0 (R1 144/144, S5 stopped 401+1 as recorded); native run-03 re-read identical to `reader-03.json`; E1-C intact. After cutover, the declared change set also includes `web/e2-editor-app.js`.

One test was green for the wrong reason (E1's red cases first exited 0 because the edit adding the scratch override never landed); caught by the red cases themselves, fixed before any record. §34.4 this batch: +0/+0.

## Next

1. **Owner links** (runbook `handoff/RUNBOOK-relink-v24.md`, all prerequisites checked): `cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/link_v24_feature_owner.sh` (~3–10 min). Expected final JSON: `e2-editor-v24`, `abiVersion: 6`, `typedInsert` declared, 23 actions, `withheld: ["select-all"]`.
2. Agent, link day (spec §6.2): L1 (real log), I1-v24 via X1 with exactly `--declared-worker`, `--declared-new-leaf .editorContract.typedInsert=…`, `--declared-export _oxsdk_document_insert_typed_text`, no changed leaf, plus reds (a)(b); frozen set; archive `build/archive/e2-editor-v24-<wasm8>-worker-<worker8>/`.
3. Cutover: page worker URL + wasm pin + leaf requirement; finish shell changes; mint generation 77.
4. Before any count (§6.3): (vi) v24 manifest + v23 wasm → `DECLARED_EXPORT_MISSING`; (vii) page refusal + positive control; **J-red** (write the v24 S5 judge as a wrapper — v23's judges hard-code `PROFILE`/ABI and are byte-bound, so new files only); M2 over 84 type cells × 2 browsers; T5 with real CDP keys incl. the 169 Ctrl+V control; (i); T4.
5. Counted: fresh S5 (T1, T2) in a new directory, R1 144, S1–S4 234, four arms; then host, BINDING, K (this is the engine change the batched count was waiting for; ledger base `research/2026-10-25-count-batching-and-next-work.md`, ask the owner for the DDEV slot).
6. Optional, cheap: rerun M1 once to see whether the exit-1 teardown recurs (native, agent-run).

Constraints unchanged: no sudo; object-producing builds owner-run; never overwrite frozen v23; v23's records do not transfer; repository evidence/handoff in English, conversation and specs zh-TW.
