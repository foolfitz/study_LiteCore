# Host 0.2.45 preparation: Writer on profile e2-editor-v29 with shell generation 83 and the icon toolbar

## Declared before packaging, 2026-11-01

Spec `specs/SPEC-M3-v29-tick-pacing.md` append 6. A relink: `e2-editor-v29` was linked on the owner's word on 2026-11-01 (wasm `e61e5890...`, worker `a5df83db...` = v28's bytes, archive `build/archive/e2-editor-v29-e61e5890-worker-a5df83db`).

**Live predecessor** (read-only): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **a97724f** (0.2.44), clean. Its engine is the 0.2.44 archive `host-0.2.44-engine-dacdfa20fd4ff1ea`.

**This is the first release on the own stack** (`specs/SPEC-M3-own-stack.md`). No owner slot: the slot existed because ddev was shared. The install checks instead that `ddev` is the adapter answering for the running stack.

**Candidate.** Isolated worktree `wasm_sdk_probe/build/host-0.2.45/litecore`, branch **host-0.2.45**, from a97724f. The only source change is `appinfo/info.xml` 0.2.44 -> 0.2.45.

**Expected delta against 0.2.44**, computed from `closure(dist)` against the archived MANIFEST (`prepare-release.py` refuses anything else; `check-delta.py` re-derives it from the two archived MANIFEST files):
- changed, exactly two: `e2-editor-app.js` and `e2-editor.html`;
- added, exactly four: `profiles/e2-editor-v29/{probe.js,probe.wasm,sdk-manifest.json,sdk-worker.js}`;
- removed, exactly four: the same four under `profiles/e2-editor-v28/`;
- `sdk-worker.js` the same bytes as v28's; the other three different. 0.2.44's scripts demanded all four differ and would have refused this.

**Scripts**, each derived from its 0.2.44 counterpart (not edited), by `../v29-177/derive/derive_host_0245.py` and `derive_host_0245_prepare.py` (each replacement must match its count); the closed list is in each docstring or header.

`p-contract.txt`: `check_v29_tick_pacing_contract.py --manifest ... --exports ...`, re-run here because the link's own receipt is not in the tree: `v29 preconditions hold`. `withheld` is empty, 23 actions, ABI 6.
