# Owner-only v27 link (finding 176: the collapsed route judges a two-paragraph readback by its first block)

Spec: `specs/SPEC-M3-v27-finding-176.md` (pinned `ce782b9af`, append-only). Rulings: `findings/evidence/176/RULING-fable-2026-10-30.md` (ruling 2) and `RULING-fable-2026-10-30-c.md` (ruling 3).

This is one fresh product link of a new identity, `e2-editor-v27`. It does not touch DDEV, a host, LibreOffice core, any frozen profile or the count chain.

## 0. Before handing over (agent)

All green and committed (`findings/evidence/v27-176/pre-link/README.md`, `../pl1/README.md`):

- [x] Spec pinned before any implementation (`ce782b9af`).
- [x] U1 (shell item) red first, then green; shell suite green.
- [x] E1/E2 red first, then green; E3 (three inc-text tests, one by one) green; E4 (production parser on the native arm's recorded markup, 18 rows) green.
- [x] V0-v27: v23/v24/v25 preprocess unchanged, with a positive control.
- [x] S: `-fsyntax-only` clean with the v27 define; both controls behave, the guard's control on `editor_api.cpp`.
- [x] W1 / W2: the v27 worker is the archived v26 worker plus the closed list.
- [x] **PL-1 (the relink gate): PL1_WOULD_VERIFY 12/12** on v26's own WASM records, in Chrome and Firefox.
- [x] `make test-v27-first-block-static` exit 0, including the builder's dry run on v26's binaries: v26's manifest with exactly profile, sdkVersion and workerSha256 changed.
- [x] M1-1: red on exactly E2_V27's three objects, then green with its carrier.
- [x] L: `what_the_link_ships` (only `probe_engine`, two .cpp hunks) and `check_v27_ships_confined.py` CONFINED_V27_HOLDS. Every difference is inside the v27 blocks, the blocks are exactly the seven declared hunks, and stripping them gives v25's link source byte for byte. Three red cases.
- [x] PIN:
  - the six core files of spec 10 agree between the link core and the native core (both `671c848b`);
  - the frozen set is recorded (2,757 files; v25's 2,453 unchanged);
  - the v26 archive verifies 5/5;
  - no v27 build directory, profile or log exists;
  - `make -n` of the command below prints only the four v27 compiles, one guarded link, two `cp` and the manifest build.

Re-verify on the day: `cd wasm_sdk_probe/build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae && sha256sum -c SHA256SUMS`.

Before starting, check that nothing else is building or measuring: `uptime`, `pgrep -a make`.

## 1. Owner command

From Bash. It takes about 3-5 minutes: v25's same-shaped link took 14:14-14:17, with four small objects, one full WASM link, packaging and one make job.

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/link_v27_first_block_owner.sh
```

What the helper does:
- It refuses if `build/e2/editor-v27`, `dist/profiles/e2-editor-v27` or `build/link-v27-first-block-01.log` already exists.
- It unsets the build overrides and runs exactly `make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v27/sdk-manifest.json`, with the full stream in `build/link-v27-first-block-01.log` (pipefail).
- It checks the real log, the manifest, the exports and the binary bindings, and prints the artifact hashes.

**Report that final JSON**, or the complete error with the log.

Expected in the JSON:
- `profile: "e2-editor-v27"`, `abiVersion: 6`, `typedInsert: "document-sdk-insert-typed-text"`;
- `selectAll: ["collapsed", "range-single", "range-cross"]`, 23 actions;
- **`withheld: []`**. Unlike v24/v25, select-all has been granted since v26. If `withheld` names `select-all`, the builder took the wrong leaf: stop and report.
- a `wasmSha256` that is new (not `44cb15ea...`).

On failure: do not clean, retry or rerun an old target; preserve the partial directory and the log. `ALLOW_FROZEN_RELINK=1` is for this one target only.

## 2. After the link (agent, spec 7.3; mirror only, no DDEV)

1. **P-v27.**
   - The five artifact hashes; `check_v27_first_block_contract.py` (leaves equal v26's, only three hashes and two names changed); exports equal v26's.
   - The real log: four fresh v27 compilations with all four feature defines, one link.
   - Frozen set against `pre-link/frozen-set-before.sha256`: no existing file changed, and the only new files are v27's four profile files.
   - Archive at once: `build/archive/e2-editor-v27-<wasm8>-worker-<worker8>/` (five files, `SHA256SUMS`, `ATTRIBUTION.md`).
2. **Cutover.** `web/e2-editor-app.js` gets the v27 worker URL and wasm pin.
   - Generation 81 is frozen only after every shell change of the batch is in.
   - It differs from 80 by the page only (tool-computed closed list).
   - The exclusion list is v80's plus `sdk/v27-first-block-worker.js`.
   - The bundle line is red before the change, green after it, and red again when pointed back at 80.
   - `make -n e2-c-assets` prints one `cp`.
3. **S3** (`tools/check_v81_blank_line_bullet.py`, new) and **S2′** (`tools/check_v81_blank_bullet.py`, derived from v80's).
   - Both browsers, N=3, generation 80 as the counterexample.
   - S3 pins `findings/evidence/v27-176/fixture-two-plain/build-01/two-plain.odt` (`56bc01b0...`) and clicks the first line's end at (0.80, 0.0894) of `#paper`: PL-1's measured point.
   - S3 runs three mutations: `press-list-none`, `hide-review-toast`, `cosmetic-review`.
4. **Freeze generation 81**, then:
   - **F3-81**, with the declared moves of spec 8: bulleting PASS->FAIL with `state ready` and an empty toast; `recoveryPairing.held` false; reading 1 `F3_RED` exactly;
   - **F4-81**: 24/24 in both browsers;
   - **V0′-81**;
   - **E1-C** intact.
5. **Host 0.2.43** (spec 7.4) needs the owner's DDEV slot. Then the owner's hand test (a)-(c).

Any check not run, NE, or with an undeclared move: 0.2.43 is not sent for install (spec 7.3 default).
