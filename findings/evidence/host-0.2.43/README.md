# Host 0.2.43 preparation: Writer on profile e2-editor-v27 with shell generation 81 (finding 176)

## Declared before packaging, 2026-10-30

Spec `specs/SPEC-M3-v27-finding-176.md` 7.4. A relink: `e2-editor-v27` is the owner's 14:19 link (wasm `c089dfd6…`, archive `build/archive/e2-editor-v27-c089dfd6-worker-8152448a`). The page pin is `c089dfd699d646e3`.

**Live predecessor** (read-only): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **93b1ebc** (0.2.42), clean. Its engine is the 0.2.42 archive `host-0.2.42-engine-01e6c3fb62626d16`.

**Candidate.** Isolated worktree `wasm_sdk_probe/build/host-0.2.43/litecore`, branch **host-0.2.43**, commit **ae8240d** (from 93b1ebc). The only source change is `appinfo/info.xml` 0.2.42 -> 0.2.43.

**Expected delta against 0.2.42** (`prepare-release.py` refuses anything else; `check-delta.py` re-derives it from the two archived MANIFEST files):
- changed, exactly one: `e2-editor-app.js`;
- added, exactly four: `profiles/e2-editor-v27/{probe.js,probe.wasm,sdk-manifest.json,sdk-worker.js}`;
- removed, exactly four: the same four under `profiles/e2-editor-v26/`. It is checked first that `e2-editor.html` is the only page of the 0.2.42 package on v26.
- All four added files differ from the removed ones. v27's `probe.wasm` equal to v26's would mean no new engine, and is a refusal.

**Evidence gate.** 0.2.42's gate is unchanged: v24 counts carried over; v25 F1-F4 and the section 9 reader; spec v79; spec v26 with F3-80 under append 2.

Spec v27's is added, every file under `findings/evidence/v27-176/` and checked for existence first:
- U1 and the shell suite;
- E1-E4, V0-v27 with its positive control, S, the static target, M1-1 red and green, L, PIN;
- PL-1 and its self-test;
- P-v27: both contract checks, I1, the frozen set;
- S3, its self-test and its three mutations; S2′ and its self-test;
- F3-81: reading 2 `F3_81_DECLARED_ONLY` with its self-test, and reading 1 **exactly** `F3_RED` with the four declared problems, written out in the script;
- F4-81 24/24; V0′-81; E1-C.

No gate requires `recoveryPairing.held: true` (spec 8 item 3).

**Scripts.** Each is derived from its 0.2.42 counterpart, which is not edited; the closed list of differences is in each docstring or header:
- `prepare-release.py`;
- `check-delta.py`;
- `offline-package-check.py` (docstring only);
- `install-0.2.43.py` (docstring and candidate path only);
- `rollback-package.sh` (exact 0.2.42 engine; label stays 0.2.43);
- `capture-after.py` (docstring only; the inherited named limit stays).

Files workflow: the unchanged `wasm_sdk_probe/tools/run_calc_editor_host.py`.

## Offline results (2026-10-30 ~15:49-15:55 +0800)

- **`prepare-release.py`** (`package-run-01.*`, exit 0, 154 s). Engine **741afd80a36e673b**.
  - Against 0.2.42: 41 records unchanged; changed exactly `e2-editor-app.js`; added the four v27 files; removed the four v26 files; all four profile files differ (`release.json` `profileSuccessor`).
  - Every v25, v79, v26 and v27 gate holds (`release.json` `v27Gates`, `f3_81Verdicts`).
  - Archive `wasm_sdk_probe/build/archive/host-0.2.43-engine-741afd80a36e673b` (not in git), bound by `archive.sha256`.
- **`check-delta.py`** -> `check-delta.json`: **DELTA_HOLDS**, no problems. All eight red cases are red: more, fewer, added, removed, v27 wasm = v26's, v27 worker = v26's, another old page on v26, the editor still on v26.
- **`offline-package-check.py`** -> `offline-package-check.json`: **PACKAGE_HOLDS**, zero problems, **22/22** red cases red.
- **`install-0.2.43.py --offline-only`** -> `offline-install-preflight.json`: **OFFLINE_INSTALL_READY** (parent 93b1ebc, candidate ae8240d, `liveMutation: false`).

**Next.** A slot (`slot.json`, with an explicit no-site answer and shared-DDEV coordination). The owner wrote at ~15:50: "如果要用到ddev，可以把其他ddev關掉". Then:
1. `install-0.2.43.py --preflight-only`, then `install-0.2.43.py`;
2. the Files workflow, then `capture-after.py <install-dir> <workflow-dir>`;
3. the owner's hand tests:
   - (a) a document with text, an empty line with a paragraph after it, bullet -> no toast, the strip shows the time;
   - (b) a new blank document, bullet -> 083's sentence in the normal style, the strip says 「待確認」;
   - (c) after (a), Ctrl+Z -> the list is undone.
