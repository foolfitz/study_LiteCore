# Host 0.2.44 preparation: Writer on profile e2-editor-v28 with shell generation 82 (the 083 path's last line)

## Declared before packaging, 2026-10-30

Spec `specs/SPEC-M3-v28-last-line-fallback.md` 7.4. A relink: `e2-editor-v28` is the link the agent ran at the owner's request on 2026-10-30 ~20:34 (wasm `13f674e4…`, archive `build/archive/e2-editor-v28-13f674e4-worker-a5df83db`). The page pin is `13f674e498a56c8a`.

**Live predecessor** (read-only): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **ae8240d** (0.2.43), clean. Its engine is the 0.2.43 archive `host-0.2.43-engine-741afd80a36e673b`.

**Candidate.** Isolated worktree `wasm_sdk_probe/build/host-0.2.44/litecore`, branch **host-0.2.44**, commit **a97724f** (from ae8240d). The only source change is `appinfo/info.xml` 0.2.43 -> 0.2.44.

**Expected delta against 0.2.43** (`prepare-release.py` refuses anything else; `check-delta.py` re-derives it from the two archived MANIFEST files):
- changed, exactly two: `e2-editor-app.js` and `editor-shell-v2/paragraph-editor-client.js` (spec 7.4 corrects ruling 4's "exactly 1": 0.2.43's package carries the client, review item 20);
- added, exactly four: `profiles/e2-editor-v28/{probe.js,probe.wasm,sdk-manifest.json,sdk-worker.js}`;
- removed, exactly four: the same four under `profiles/e2-editor-v27/`. It is checked first that `e2-editor.html` is the only page of the 0.2.43 package on v27;
- all four added files differ from the removed ones; v28's `probe.wasm` equal to v27's is a refusal.

**Evidence gate.** 0.2.43's gate is unchanged (v24 counts carried over; v25; spec v79; spec v26; spec v27). Spec v28's is added, every file under `findings/evidence/v28-083/` checked for existence first:
- U-v28 red first (`exit 1`), the three page tests red first, the shell suite with exactly one failing test, the named L-select-all-u2-pins-v26-profile;
- E1 red first, E1/E2 green, E3's six green receipts, E4, V0-v28 with its positive control, S, W1 green and its red case, W2, `test-v28-last-block-static`, M1-1 red and green, L, PIN with the v27 archive check;
- PL-1-v28 and its self-test;
- P-v28: the link's three "v28 preconditions hold" lines, the frozen-set delta;
- S4 `S4_HOLDS`, its self-test, its six mutations caught (press-list-none from its re-run, `s4/README.md`);
- F3-82: reading 2 `F3_82_EQUAL` with its self-test, and reading 1 **exactly** F3-81's `F3_RED` with the four problems, written out in the script;
- F4-82 24/24; V0′-82; E1-C at U-v28 (before and after), the cutover, the freeze and the put-back.

**Scripts**, each derived from its 0.2.43 counterpart (not edited), by `../v28-083/derive/derive_host_0244.py` and `derive_host_0244_prepare.py` (each replacement must match its count); the closed list is in each docstring or header:
- `prepare-release.py`;
- `check-delta.py` (one more red case: the client reverted);
- `offline-package-check.py` (docstring only);
- `install-0.2.44.py` (docstring and candidate path only);
- `rollback-package.sh` (exact 0.2.43 engine; label stays 0.2.44);
- `capture-after.py` (docstring only; the inherited limits stay, L-capture-after-expired-lock-lazily-deleted included).

Files workflow: the unchanged `wasm_sdk_probe/tools/run_calc_editor_host.py`.

Installing needs the owner's slot (DDEV is shared): `slot.json` with an explicit no-site answer. No slot, no install; 0.2.43 stays the daily uncounted candidate (spec 7.4).

## Offline results (2026-10-30 ~23:09-23:16 +0800)

- **`prepare-release.py`**
  - package-run-01 (exit 1) never started: the generated script had a syntax error. The E1-C fix's `'\n'` had passed through two string layers in `derive_host_0244_prepare.py` and become a real newline. Fixed by execution in the derivation; the script was regenerated and parsed before run-02. Nothing was written by run-01.
  - package-run-02 (`package-run-02.*`, exit 0, 163 s): engine **dacdfa20fd4ff1ea**.
  - Against 0.2.43: 40 records unchanged; changed exactly `e2-editor-app.js` and `editor-shell-v2/paragraph-editor-client.js`; added the four v28 files; removed the four v27 files; all four profile files differ (`release.json` `profileSuccessor`).
  - Every v25, v79, v26, v27 and v28 gate holds (`release.json` `v28Gates`, `f3_82Verdicts`: `F3_RED` / `F3_82_EQUAL`).
  - Archive `wasm_sdk_probe/build/archive/host-0.2.44-engine-dacdfa20fd4ff1ea` (not in git), bound by `archive.sha256` (94 members).
- **`check-delta.py`** -> `check-delta.json`: **DELTA_HOLDS**, no problems; all nine red cases red (more, fewer, fewer_client, added, removed, wasm_same, worker_same, another old page on v27, the editor still on v27).
- **`offline-package-check.py`** -> `offline-package-check.json`: **PACKAGE_HOLDS**, zero problems, **22/22** red cases red.
- **`install-0.2.44.py --offline-only`** -> `offline-install-preflight.json`: **OFFLINE_INSTALL_READY** (parent ae8240d, candidate a97724f, `liveMutation: false`).

**Next.** The owner's slot (`slot.json`: an explicit no-site answer, shared-DDEV coordination). Then:
1. `install-0.2.44.py --preflight-only`, then `install-0.2.44.py`;
2. the Files workflow, then `capture-after.py <install-dir> <workflow-dir>`;
3. the owner's hand tests (spec 7.4):
   - (a) a document with text whose last line is empty, bullet -> no toast;
   - (b) a new blank document, bullet -> the same sentence as now;
   - (c) after (a), Ctrl+Z -> the list is undone;
   - (d) (optional) a document ending in a table, bullet on the line below it -> the new sentence, no 「回到檢查點」, 「復原」 undoes it.
