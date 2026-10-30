# Owner-only v28 link (the 083 path: a one-position-back fallback judged by the LAST block)

Spec: `specs/SPEC-M3-v28-last-line-fallback.md` (pinned `b1241e3dd`, append-only). Ruling: `findings/evidence/176/RULING-fable-2026-10-30-d.md` (ruling 4). Native evidence: `findings/evidence/176/native-q52/`.

This is one fresh product link of a new identity, `e2-editor-v28`. It does not touch DDEV, a host, LibreOffice core, any frozen profile or the count chain.

## 0. Before handing over (agent)

All green and committed (`findings/evidence/v28-083/pre-link/README.md`, `../u-v28/README.md`, `../pl1/`):

- [x] Spec pinned before any implementation (`b1241e3dd`), after one adversarial review.
- [x] U-v28 (shell: `fallback-readback-refused` -> review, its own sentence) red first, then green.
  - Shell 565/566. The one red predates this: L-select-all-u2-pins-v26-profile.
  - E1-C intact before and after.
- [x] E1/E2 red first (20 FAILs on the v27 inc), then green; 8 mutations red.
- [x] E3: the inc tests one by one; `test-v27-first-block-static` green; `test-e2-c-static` has no new red (the pre-existing ones are named).
- [x] E4:
  - v27's 18 rows are unchanged under the v28 define;
  - 26 tool-closed fallback rows agree with the saved documents.
- [x] V0-v28 against 3a6998b33: v23/v24/v25/v27 preprocess unchanged (16/16), with a positive control.
- [x] S: `-fsyntax-only` is clean with the v28 define, and both controls behave.
- [x] W1 / W2: the v28 worker is the archived v27 worker plus the closed list. The fallback projection is last in the object and never carries the markup.
- [x] `make test-v28-last-block-static` exit 0.
- [x] M1-1: red on exactly E2_V28's objects, then green with its carrier.
  - It also caught a mangled define while the Makefile block was being derived; fixed.
- [x] L:
  - `what_the_link_ships`: only `probe_engine`, 9 .cpp hunks;
  - `check_v28_ships_confined.py`: CONFINED_V28_HOLDS. 15 declared groups; stripping them gives v27's link source byte for byte. Two red cases.
- [x] PIN:
  - 11 core files agree between the link core and the native core (both 671c848b), with a one-byte red case;
  - the v27 archive verifies 5/5;
  - the frozen set is recorded (2,862 files);
  - no v28 build directory, profile or log exists;
  - `make -n` of the command below prints only v28's four compiles and one guarded link.
- [x] **PL-1-v28: PL1_V28_HOLDS 6/6.** On the shipped v27 product (generation 81 as dist/ serves it), the 083 recipe (two paragraphs, click below the text, Enter, bullet) reaches the fallback's trigger in Chrome and Firefox, N=3: `select-text-returned-none`, collapsed, dispatched, `selectionResultSeen` true. Self-test 6/6 (`findings/evidence/v28-083/pl1/`).

Re-verify on the day: `cd wasm_sdk_probe/build/archive/e2-editor-v27-c089dfd6-worker-8152448a && sha256sum -c SHA256SUMS`.

Before starting, check that nothing else is building or measuring: `uptime`, `pgrep -a make`.

## 1. Owner command

From Bash. It takes about 3-5 minutes (v27's same-shaped link was 14:19 with four small objects, one full WASM link, packaging and one make job).

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/link_v28_last_block_owner.sh
```

What the helper does:
- It refuses if `build/e2/editor-v28`, `dist/profiles/e2-editor-v28` or `build/link-v28-last-block-01.log` already exists.
- It unsets the build overrides and runs exactly `make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v28/sdk-manifest.json`, with the full stream in `build/link-v28-last-block-01.log` (pipefail).
- It checks the real log, the manifest, the exports and the binary bindings, and prints the artifact hashes.

**Report that final JSON**, or the complete error with the log.

Expected in the JSON:
- `profile: "e2-editor-v28"`, `abiVersion: 6`, `typedInsert: "document-sdk-insert-typed-text"`;
- `selectAll: ["collapsed", "range-single", "range-cross"]`, 23 actions;
- **`withheld: []`**;
- a `wasmSha256` that is new (not `c089dfd6...`).

On failure: do not clean, retry or rerun an old target; preserve the partial directory and the log. `ALLOW_FROZEN_RELINK=1` is for this one target only.

## 2. After the link (agent, spec 7.3; mirror only, no DDEV)

1. **P-v28.**
   - The five artifact hashes; `check_v28_last_block_contract.py`; exports equal v27's.
   - The real log: four fresh compilations with all the feature defines, `-DOXSDK_E2_V27_FIRST_BLOCK` and `-DOXSDK_E2_V28_LAST_BLOCK` included, and one link.
   - Frozen set: no existing file changed, and the only new files are v28's four profile files.
   - Archive at once: `build/archive/e2-editor-v28-<wasm8>-worker-<worker8>/`.
2. **Cutover.** The page gets the v28 worker URL and wasm pin.
   - Generation 82 differs from 81 by the page and the client (a tool-computed closed list).
   - The exclusion list is 81's plus `sdk/v28-last-block-worker.js`.
   - The bundle line is red, then green, then red again when pointed back.
3. **S4-a..e** (`tools/check_v82_last_line_bullet.py`, new): both browsers, N=3, generation 81 as the counterexample.
   - S4-a: the multi-paragraph last line, verified, with the marker typed after the press.
   - S4-b: the other four actions.
   - S4-c: the blank document, unchanged.
   - S4-d: a table before the last line: review with the new sentence, no rollback; typing after it leaves the table cell's text intact.
   - S4-e: two Enters.
   - `fallback.restoreConfirmed` N/N wherever the fallback read something.
4. **Freeze generation 82**, then F3-82 (no declared move), F4-82, V0′-82, E1-C.
5. **Host 0.2.44** (spec 7.4) needs the owner's DDEV slot. Then the owner's hand tests (a)-(d).

Any check not run, NE, or with an undeclared move: 0.2.44 is not sent for install (spec 7.3 default).
