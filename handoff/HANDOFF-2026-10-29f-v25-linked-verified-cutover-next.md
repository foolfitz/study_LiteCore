# Handoff: v25 linked, verified and archived; page cut-over next

Checkpoint **2026-10-29 afternoon +0800**. Supersedes 10-29e (and its Addendum) as the entry point.
Study HEAD **a48e6b865**. Tree clean except the unrelated untracked `codex-claude-code-delegation.md`
(preserve it). **Nothing is running.** Another session is using DDEV: anything that needs DDEV must be
scheduled with the owner first (queue). Every step up to the host package below is offline.

## State

- **v25 is linked** (owner, `bash tools/link_v25_feature_owner.sh`, log 14:14-14:17): profile
  `e2-editor-v25`, `abiVersion` 6, `typedInsert: "document-sdk-insert-typed-text"`, 23 actions,
  `withheld: ["select-all"]`. wasm `44cb15ea8d36f0e0191e007179769b6bcb468e3d084cb260c645e6127630d193`,
  loader `ed1d9a55…`, worker `75557b22…`, manifest `e7780061…`, exports `f5b21630…` (= v24's; no new
  export, no new leaf). Source: `findings/evidence/link-batch-v25/post-link/README.md`, spec v25 section 14.
- **Section 6.2 all PASS** (`post-link/`, commit `a48e6b865`): `check_v25_feature_contract.py` on the real
  log and on the manifest -> `v25 preconditions hold`; X1 `VERDICT PASS` against v24 with only
  `--declared-worker 75557b22…`; three red cases each red on its own clause only (abi 7 -> `manifest`,
  undeclared leaf `formatProof` -> `manifest`, extra export -> `exports`); frozen set 2,453 files verify,
  only the four `dist/profiles/e2-editor-v25/` files are new; `ScDocShell` 0 (positive control 11 in
  `ods-editor-v2`, `ods-viewer-v3`); E1-C `intact: true`.
- **Archive**: `wasm_sdk_probe/build/archive/e2-editor-v25-44cb15ea-worker-75557b22/` (read-only, not in
  git): five artifacts, `SHA256SUMS` 5/5, `ATTRIBUTION.md`; copies in `post-link/archive/`.
- **Pre-link 6.1 all held** (`pre-link/README.md`): native R1/R2/D1/D2 (`tests/test_ordered_format_v25.py`,
  every mutation red), `V0_V25_HOLDS`, `S_V25_HOLDS`, W1/W2, M1-1 red then green, `ships.*`,
  `make test-v25-feature-static` exit 0. **Not yet measured anywhere**: the JSON serialisation of
  `dispatched` and `witness` (spec v25 section 13 item 4) -- F1/F2 are its first measurement.
- **Page still points at v24**: `wasm_sdk_probe/web/e2-editor-app.js:50` `PINNED_WASM_SHA256 =
  "276158084a602178"`, `:3749` `workerUrl: "./profiles/e2-editor-v24/sdk-worker.js"`.
- **Section 9 decided: carry over** (owner, 「沿用」, spec v25 section 14): the v24 S5/R1/S1-S4 counts are
  not re-run on v25; F3 and F4 still run. **Owed before any K**: the tool-closed reader (step 4 below).
- **Host**: owner's DDEV runs engine exact 0.2.38 (`5ad1f70a8c5f7d2f`) under host label 0.2.39 (host source
  `4a8b3cd`), rolled back today (`e78e8786f`); 0.2.39's engine archive is intact. **Nominal shipped host
  is still 0.2.26.** K has not run; it needs its own 8-10 h no-site window.

## Commits today (`git log --oneline -12`)

`f95ad1d52` K protocol ruling; `6b849569f` nine cells localized; `e78e8786f` engine rollback to 0.2.38;
`de7af5ac3` findings 171/172 + DISPOSITIONS; `f30acd0e6` fable ruling on the v25 fixes; `152cb6ad9` spec
v25 pinned; `cd60b7d61` handoff 10-29e; `9d7fb9e7c` engine fixes + native red cases; `58a2f5ddf` v25
worker; `d860a898a` build mechanics + pre-link checks; `cbcd7ac9e` link handed to owner; `a48e6b865`
post-link verified, archived, section 9 carry-over recorded.

## Next steps (spec v25 sections 8 and 6.3)

1. **Page cut-over** (spec v25 4.4; precedent `63ea44daa`, spec v24 4.4 + section 15,
   `findings/evidence/link-batch-v24/cutover/README.md`). Only two lines change: workerUrl ->
   `./profiles/e2-editor-v25/sdk-worker.js`, pin -> `44cb15ea8d36f0e0`; the `typedInsert` requirement added
   in v24 stays as is. Use `python3 -I tools/build_cutover_page.py --profile e2-editor-v25` (without
   `--write` it writes nothing and prints the sha256), then `--write --expect-sha256 <that>`; `node --check`;
   diff must show only those two lines. Dist copy: `make e2-c-assets` -- v24 first confirmed its `make -n`
   printed exactly two `cp` lines (page, `sdk/document-sdk.js`), then `cmp` each copy with its source.
   v24 also ran a V0′ after its cut-over (`cutover/v0/`: restore the shell files, re-read v23's completion);
   spec v25 names none -- decide whether the carried-over v24 count readers need the same and record it.
2. **Freeze shell generation 78 only after all shell changes** (spec v25 4.4). Precedent `be13e0b54`
   (`link-batch-v24/pre-count/freeze-77/README.md`): `tools/build_e2_c_shell_bundle.py --manifest
   e2/editor-shell-v2-bundle-v78.json --write --frozen-date …` with every `--exclude` explicit. v77
   excludes seven (`sdk/sdk-worker.js`, `reader-shell/reader-session.js`, `reader-shell/state-machine.js`,
   `sdk/v23-diagnostic-worker-tail.js`, `sdk/v23-diagnostic-r2-worker-tail.js`, `sdk/v23-feature-worker.js`,
   `sdk/v24-feature-worker.js`); by spec v24 4.4's precedent `sdk/v25-feature-worker.js` would be the eighth
   (spec v25 does not list it -- record the reason). Expected: only `web/e2-editor-app.js` differs from v77
   (`sdk/document-sdk.js` is unchanged, spec v25 4.3). `Makefile:4843` moves to `--manifest …v78.json` with
   red-before / green-after / red-on-v77. **Do not "fix" the bundle tool's default `MANIFEST` (v76)**: it
   stays v76 by design. `make test-e2-c-reachability` as a whole is red at Makefile:4804 since v21
   (pre-existing; freeze-77 README). Order note: spec v25 section 8 step 6 freezes 78 before 6.3 and F3
   says "v78 rebinding", whereas v24 froze 77 after its 6.3 preparations (spec v24 section 15). If 6.3
   then forces a shell change, that is generation 79, never an overwrite of 78.
3. **Section 6.3 on the local mirror, no DDEV**:
   - **F1**: `findings/evidence/host-0.2.39/k-nine-cells/diag-format/diag_format.py` with v25 as a third
     product. Expect the bullet scenario `ready` + `dispatched:true`; saved ODT `MKAFTERCLEAR` not italic,
     `MKITALAGAIN` italic (= v22). **Trap**: its `v24` product is "`dist/` as served (page b15a6d8e)"
     (`diag_format.py:6`, `:177`); after the cut-over `dist/` serves v25, so that arm would silently
     measure v25. Serve v24 from its own bytes (page `b15a6d8e`, wasm `27615808`). Write to a new run dir;
     run-01/02 stay as produced; mirrors under `wasm_sdk_probe/build/` or the scratchpad, never evidence.
   - **F2**: new `tools/check_v25_clear_format_noop.py`: clear-format on plain text -> four `ok`, toast
     「已清除…」, state `ready`. **Must be red on v24** (the natural counterexample; no mutant engine).
     Same v24-serving trap as F1.
   - **F3**: product-path plain arm, T4's method with the v78 rebinding, both browsers, one round each.
     DISPOSITIONS rows 1-6 must PASS on v25; the other 40 cells equal v24's T4 (row 8, I-enter-raw-substring,
     is a Chrome FAIL on every v24 product-path report, spec v24 section 17 item 3). The runner (`7ba30235`)
     is frozen; plain runs bind v76 and NE the four arms -- rebind in-process like `run_v24_four_arms.py`.
   - **F4**: A4 four arms via a new wrapper derived from `tools/run_v24_four_arms.py` (which rebinds
     `build_e2_c_shell_bundle.MANIFEST` before importing the runner, default v77), rebinding to v78; both
     browsers. Do not edit the v24 wrapper.
4. **Section 9 reader (before any K)**: a small tool-closed reader (CLAUDE.md section 1, form 2) proving
   every changed preprocessed hunk in `findings/evidence/link-batch-v25/pre-link/ships.stdout.txt` lies
   inside `#ifdef OXSDK_E2_V25_FORMAT_PROOF` blocks. Make it red first (CLAUDE.md section 6): a hunk outside
   a block -> red; zero hunks found -> red (non-vacuity). Until it exists "only the declared hunks differ"
   is read by eye (spec v25 section 13 item 3 / section 14), not tool-judged.
5. **Then** a host package 0.2.40 candidate carrying v25, and a DDEV slot agreed with the owner (queue
   behind the other session). K later, in its own 8-10 h no-site window.

## K reading, already pinned (do not re-derive)

`findings/evidence/host-0.2.39/k-protocol-ruling/RULING.md` (revision 1 anchors on the 0.2.26 v21 records)
plus `k-nine-cells/DISPOSITIONS.md` and its correction: rows 1-6 product (171/172), RED until fixed and
re-measured on v25; row 7 **I-worker-inducer-single-shot** (PASS only if B1-B3 true every round and the
inducer record has exactly the single-shot shape; default RED); row 8 **I-enter-raw-substring** (must be
applied explicitly); row 9 Q4 (N = K's three rounds per browser; at most one exact **I-ink-trigger-race**
signature per browser; default RED, nominal stays 0.2.26). Source: `RULING-v25-fixes.md` Q3/Q4.

## Not in v25 (spec v25 section 2, 10)

Page clear-format continue-on-error (ruling Q1 (c)); finding 038 not reproducing on the ordered engine
(finding candidate); a successor to `induce_worker_failure` (two inducers per CDP connection); the native
N=5 arm for **L-noop-trusts-last-state-item** (owed, not blocking; v22 has the same hole); K itself.
Findings 171/172 tables still say 未修 (unfixed) -- update their status only after F1/F2 measure the fix.

## Cautions (each bit this week)

- Regression baselines are the **last shipped/counted product**, never an unshipped intermediate (T4 was
  compared against unshipped v23; 10-29e item 3). F3's other 40 cells compare with v24's T4 (v24 was
  counted and shipped in 0.2.39); K anchors on the 0.2.26 v21 records.
- A new check's first red can be the **check's own setup**. Two today: the S guard control aimed at
  `probe_engine.cpp`, which does not include `editor_api.h` (spec v25 section 13 item 1,
  `s-v25-run01-wrong-control-tu.json`); X1 red-case scratch dirs not named `e2-editor-v25`, so the
  `profile` clause also failed (`post-link/i1/*.run01-scratch-dir-misnamed.*`).
- v24's E1 (`tests/test_v24_typed_insert_engine.py`) is red by construction on the live tree;
  `test-v24-feature-static` runs it on v24's link source `1f95a9fca` via `V24_E1_SRC` (spec v25 section 13
  item 2). Do not "repair" the test.
- Never edit frozen tool bytes: v23/v24 instruments, the product-path runner `7ba30235`, the live bound
  set (spec v24 section 17), generation 76/77 manifests, `inlineFormatArgumentResolved`'s v23/v24
  preprocessing (guarded by V0-v25).
- `rm` with shell variables is blocked; write `rm -rf -- "${VAR:?}"`.
- Evidence runners may overwrite committed evidence: point outputs at a scratch dir first, then
  `git status`.
- Compiling `make` / relink stays the owner's; em++ `-fsyntax-only`/`-E` checks and single-file native
  harnesses are the agent's (AGENTS.md; check `uptime` and `pgrep -a make`, `taskset -c 0`, receipts).

## Section 34.4 this round

Fixed-by-execution **2**: the S control translation unit (spec v25 section 13 item 1); X1 scratch-dir
naming (a red-case setup error, not a tool change; post-link README). Fixed-by-review **2**: K ruling
revision 1 anchor; DISPOSITIONS row 7 cause (the two spec v25 section 11 records; section 11's execution 1,
`capture-after.py`'s buildId, belongs to the 10-29e round).

## Language

Replies to the owner: Taiwan Traditional Chinese (A/B/C for options). Evidence, upstream text and
`handoff/**`: English. `devlog/`, `research/`, `specs/`: zh-TW (specs are append-only once pinned).
