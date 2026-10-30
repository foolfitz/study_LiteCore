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

## Live installation (owner slot `slot.json`, 2026-10-30 16:01-17:01 +0800)

**The slot.** The owner was asked: 「可以現在安裝嗎？…這段時間請不要開 litecore 站台」. The answer was **「A 現在裝（建議）」**. Earlier, unprompted, the owner had written 「如果要用到ddev，可以把其他ddev關掉」. Only litecore was running before and after (`ddev-before.json`, `ddev-after-slot.json`), so nothing was stopped.

**Live preflight** (`live-preflight.*`, `install-20261030T160144+0800/before.json`): `LIVE_PREFLIGHT_READY`.
- One lock row was present: `oc_files_lock` id 5412, `file_id 25890` = `LiteCore Calc 手動驗收 2026-10-25 203756/empty.odt`, created 2026-10-30 10:38:08, ttl 1925 s.
- It was expired for about 5 hours and not being refreshed, unlike 0.2.42's first slot, so it could not move during the install.

**Install** (`install.*`, `install-20261030T160214+0800/`): **`CANDIDATE_INSTALLED`**.
- Host main fast-forwarded 93b1ebc -> **ae8240d**; the engine was rsynced from the 0.2.43 archive; `occ upgrade`.
- `installed_version` 0.2.43.
- `preservedDocumentsAndLocks: true`: the installer's own before and after snapshots, bracketing the mutation, are equal, the stale lock row included.
- `globalLockWrites: false`; the three routes answer 401 unauthenticated.

**Files workflow** (`files-workflow-01/`, the unchanged `run_calc_editor_host.py`, Chrome and Firefox): **52/52 PASS**, `ok: true`.
- Cleanup: no owned unlocks, share removed, temporary user removed, folder 204.

**`capture-after.py install-20261030T160214+0800 files-workflow-01`** (absolute paths) -> `post-install-identity.json`: **`holds: false`**.

These items hold:
- host ae8240d clean; installed_version 0.2.43; buildId 741afd80a36e673b; engine equals the archive;
- the protected documents equal the installer's after-state;
- the workflow is ok, 52 checks, none failed;
- owned folder 404; temporary user absent; no global lock-table writes.

**The only false item is `lockRowsEqualInstallAfter`.** The stale row 5412 was present in the installer's after-state and is gone now (`oc_files_lock` empty). What was measured about its removal:
- None of our steps deleted it. The installer and capture-after only read the lock table. The Files workflow never clears it, and its `ownedUnlocks` is `[]`.
- The two lock background jobs last ran on 2026-10-25 (`oc_jobs`: `OCA\FilesLock\Cron\Unlock`, `OCA\Files\BackgroundJob\CleanupFileLocks`), so they did not remove it. `core.lastcron` moved during the window.
- Nextcloud's files_lock deletes an EXPIRED lock row whenever any request looks the file's lock up:
  - `apps/files_lock/lib/Service/LockService.php:141-155`: `getETA() === 0` -> `removeIds`;
  - `:337-339`: `getLockFromFileId` deletes it, "lock is ignored and deleted as being too old".
  The row had been expired since about 11:10.
- Which request looked it up was not measured. It is not claimed here.

So the red is capture-after's comparison of the FULL lock table across a window in which Nextcloud itself may lazily delete an already-expired row. It is not a change to any document or live lock. Named: **L-capture-after-expired-lock-lazily-deleted**. It is recorded, not fixed: the tool is a derived copy kept byte-for-byte, and redesigning its lock clause would be new mechanism. The verdict stays `holds: false` as written.

Not done yet: the owner's hand tests (a)-(c). The decision whether 0.2.43 replaces 0.2.42 as the daily uncounted candidate goes to the owner, with this red named. The rollback is prepared (`rollback-package.sh`: the exact 0.2.42 engine; the label stays 0.2.43).
