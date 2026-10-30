# Handoff: finding 176 batch -- PL-1 holds, v27 mechanics green, the link is the owner's

Checkpoint **2026-10-30 ~14:05 +0800**. Supersedes `HANDOFF-2026-10-30f-v27-spec-pinned-engine-step-done.md`; that file still holds for whatever it says that is not superseded here.

Study HEAD **fb3f495e2** plus this file's commit. The tree is clean apart from three untracked files, all to be kept:
- `codex-claude-code-delegation.md` -- not ours; preserve it;
- `findings/evidence/176/native/build-01/f176-native` and `build-02/f176-native` -- native harness binaries, deliberately not committed.

**Nothing is running.** `dist/` still serves generation 80 / profile v26.

## Owner state

Waiting on the owner for one command (the relink), handed over in this session's last message:

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/link_v27_first_block_owner.sh
```

Runbook: `handoff/RUNBOOK-relink-v27.md`. About 3-5 minutes.

Expected final JSON:
- `profile: "e2-editor-v27"`, `abiVersion: 6`, 23 actions;
- `selectAll: ["collapsed","range-single","range-cross"]`;
- **`withheld: []`** (select-all has been granted since v26; anything else means stop);
- a new `wasmSha256`.

DDEV is used by another session. Nothing before host 0.2.43 needs it, and that install needs the owner's slot. Judgement calls go to the owner as A/B/C, and to fable when the owner says so.

## Done this session

**1. S3's document** (`findings/evidence/v27-176/fixture-two-plain/`, `0be1119ac`). `two-plain.fodt` was saved once as ODT by the native core (`soffice --convert-to`, buildid `671c848b`). Output `two-plain.odt`, `56bc01b0...`, receipt kept. S3 must pin the same bytes.

**2. PL-1, the relink gate** (`findings/evidence/v27-176/pl1/`, tools `0be1119ac`, evidence `8259ed388`): **PL1_WOULD_VERIFY 12/12**.
- Run: Chrome and Firefox x F3's list-contexts cell and S3's recipe x N=3, on v26 in the mirror.
- Every engine record is 046's cell (`multi-block-readback`, collapsed, dispatched) and passes v27's collapsed rule in the engine's order. The page shows finding 176 exactly as on 0.2.42.
- Reader `read_v27_pl1.py`: a clause table with a mutation per clause; self-test 68/68 red.
- **Observer, Chrome**: v25 F1's CDP attach, installing into every `sdk-worker.js` target. No served byte changes.
- **Observer, Firefox**: a mirror-only diagnostic worker, the archived v26 worker byte for byte plus an appended `JSON.parse` wrapper posting on `BroadcastChannel`. It is appended, not prepended, because the worker opens with `"use strict"`. Identity-checked; evidence class `diagnostic`. The product page and worker do not check the worker hash at run time.
- **S3's click point is (0.80, 0.0894) of `#paper`.** `#paper` includes LOK's 284-twip border, so 900 x 1256 px = 22 x 30.7 cm. The first value, 0.0757, landed in the top margin and was judged red by the reader's `is-046-cell` / `recipe-cell` clauses.

**3. Mechanics** (spec 5, `fb3f495e2`). Everything is in `findings/evidence/v27-176/pre-link/README.md`:
- **Makefile and static target.** The Makefile v27 block; `test-v27-first-block-static` (exit 0).
- **Contract and builder.** `check_v27_first_block_contract.py`; `build_e2_v27_first_block_profile.py`. The builder's dry run on v26's own binaries gives v26's manifest with exactly profile, sdkVersion and workerSha256 changed.
- **Owner script.** `link_v27_first_block_owner.sh`, `bash -n` only.
- **Profile test.** `tests/test_v27_first_block_profile.py`, 7 tests.
- **M1-1.** Red on exactly E2_V27's three objects, then green with the carrier (39 rules / 151 objects).
- **L.**
  - `what_the_link_ships --variant link-batch-v27`: only probe_engine changes, two .cpp hunks.
  - `check_v27_ships_confined.py`: **CONFINED_V27_HOLDS**. A new check D strips the v27 groups and requires `9d7fb9e7c` byte for byte, with the groups exactly the seven declared hunks.
  - Three red cases. Two of them only D catches.
- **PIN.**
  - `source-pin.json`: spec 10's six files agree in both cores (git `671c848b`), with a one-flipped-byte red case.
  - Frozen set: 2,757 files.
  - v26 archive: 5/5.
  - `make -n` of the owner's command: only v27's four compiles and one guarded link, whose line equals v25's with the directory renamed.
- **`make -k test-e2-c-static`.** Exit 2 on three unit tests that predate this session; M1-1 inside it is green. Named in the README:
  - the shell bundle test closes at generation 81's freeze;
  - `copy-lies` is L-copy-lies-pattern-stale;
  - the liveness count is 4 != 3 since `c6213c854`, and the runner is bound.

## Next (spec 7.3, then 7.4)

1. **After the owner's JSON: P-v27.**
   - Recompute the five hashes and copy the log in as evidence.
   - Run the contract check on the real manifest and confirm exports equal v26's.
   - Check the frozen set against `pre-link/frozen-set-before.sha256`: only the four v27 profile files are new.
   - Archive `build/archive/e2-editor-v27-<wasm8>-worker-<worker8>/` with `SHA256SUMS` and `ATTRIBUTION.md`.
   - v25's post-link README is the template, including I1 with `check_profile_identity.py` and its red cases.
2. **Cutover.** Page worker URL and `PINNED_WASM_SHA256` to v27. Generation 81 is minted only after every shell change; exclusion list = v80's + `sdk/v27-first-block-worker.js`.
3. **S3** `tools/check_v81_blank_line_bullet.py` (new; reuse PL-1's recipe code) and **S2′** `tools/check_v81_blank_bullet.py` (derive from `check_v80_blank_bullet.py`, which is bound: do not edit it).
4. **Freeze 81** -> F3-81 (declared moves only), F4-81, V0′-81, E1-C.
5. **Host 0.2.43** (owner's DDEV slot) -> Files flow -> capture-after -> owner hand test (a)-(c).

## Cautions

- **Cross-session.** Another session uses DDEV; do not touch it or the owner's desktop processes.
- **Owner-only.** The relink. Single-file g++ harnesses and `-fsyntax-only` / `-E` checks are the agent's (AGENTS.md); check `uptime` / `pgrep -a make` first.
- **Bound tools.** `run_e2_c_product_path.py`, `check_v79_blank_bullet.py` and `check_v80_blank_bullet.py`: derive, never edit.
- **F3-81 by design.** It will report `ok:false` (`recoveryPairing.held` false) and reading 1 `F3_RED`, both declared in spec 8. Do not "fix" them.

## Section 34.4 this round

- Fixed-by-execution: **3**.
  - S3's click fraction left out the LOK document border (shakedown; the reader judged it red).
  - The builder printed v5's pre-swap `withheld` (dry run).
  - The hunk reader's D first compared the untracked `src/*.o` files.
- Fixed-by-review: **0**.
- Fable rulings: **0**.

## Language

- Replies to the owner: Taiwan Traditional Chinese, A/B/C for options.
- Evidence and `handoff/**`: English.
- Specs and findings: zh-TW.
