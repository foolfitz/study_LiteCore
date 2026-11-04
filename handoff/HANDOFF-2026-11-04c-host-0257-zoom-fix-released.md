# Handoff: host 0.2.57 released -- Writer zoom on documents with comments fixed live; the owner's re-test passes

Checkpoint **2026-11-04 16:45**. Supersedes `HANDOFF-2026-11-04b-hand-test-0256-zoom-comment-fix.md`. One handoff for this session.

## The owner's decisions this session

- "我首先要修掉白畫面": taken as an early hand-test slot for the zoom fix alone (CLAUDE.md cadence item 1): freeze, one generation, one
  release regression, one host version.
- Generation 90's Writer chain: the owner ran it (B, "give me the command").
- Re-test of the 0.2.56 hand test's item 1 on 0.2.57: **"縮放OK了"** -- passes.

## Done

- **PLAN 3.1 tool slimming, before the freeze** (`f2ebcbb99`): `wasm_sdk_probe/tools/four_arms_identity.py` reads
  `wasm_sdk_probe/e2/generations/generation-NN.json`; `judge_product_four_arms.py`, `run_four_arms.py`, `run_f3_clipboard.py` and
  `v0_prime.py` take `--generation`. No more `vNN_*` copies. `run_f3_clipboard.py` records the bound runner's sha instead of pinning it.
  Unit test `tests/test_four_arms_identity.py` (generation 89's file equals `v89_four_arms_identity.py`'s constants).
- **Generation 90 frozen**: 89 + the page fix (page `0749bb91`, shell `2ee72a9a`, bundle `e2/editor-shell-v2-bundle-v90.json`, Makefile
  line rebound); E1-C intact before and after. Evidence `findings/evidence/zoom-comment-loop/gen-90/`.
- **V0' 90** (`gen-90/v0/`): `V0_PRIME_HOLDS`, two stages -- F4-89 re-read byte for byte by the parametrised reader with 89's page
  restored (and red on the 90 tree; this is also the witness that the new tools read a generation as the old copies did); K 0.2.45's
  `read_k.py` unchanged; put back holds.
- **Release regression** (`gen-90/chain-90.sh`): P5, P4, S1, P1 hold; Z holds on t3 and on l1; F3 `F3_83_EQUAL`, self-test `ALL_RED`;
  F4 refused at 15:03 (foreign CPU: another session's `make ... CppunitTest_editeng_core ...`), re-run alone (`f4-rerun.sh`,
  `f4-90-r2/`): 24/24 PASS. Calc nets not run (no Calc-served byte changed).
- **Host 0.2.57** (`findings/evidence/host-0.2.57/`, `1f43514bb`): host `f56a66e` (version bump) on `6def1da`, engine `2b1a095e`; served
  delta 1 changed (`e2-editor-app.js`), 45 the same; gate 16/16, `DELTA_HOLDS`, `PACKAGE_HOLDS`, installed 16:04; Files 52/52; capture
  `holds: true` (lock rows equal this time).
- **New arm on the host**: `zoom_host2.py` (unchanged) read by `host-0.2.57/read_z_host.py`: `Z_HOST_RED` on live 0.2.56 (blank at
  100/125/150 percent), `Z_HOST_HOLDS` on 0.2.57 in Chrome and Firefox.
- `host_release.py` changed: a page whose module changes without a profile move is checked against `inputs.pages`; `writerIdentity`
  may name `four_arms_identity` + generation. Witness: `delta` on 0.2.56 reproduces the committed result (`host-0.2.57/tool-witness-0.2.56/`).
- Finding 185 status: page workaround released in 0.2.57.

## Next, in order

1. **Ask the owner** whether to delete the fixture folder `手測-0.2.56/` on admin (12 files: fixtures and the owner's Save As outputs).
   My DAV DELETE was refused by the auto-mode classifier; the folder is untouched. The owner can delete it in Files, or allow it.
2. The next features are the owner's pick (memory `demo-to-colleagues-goal`: zoom done; Calc sheet tabs/scrollbars; Microsoft files done).
3. Later-slot candidates, not started: finding 130's queue depth (Firefox loses keys past 8 in a burst); the 5 expired lock rows from
   0.2.56's diagnostics (none appeared in 0.2.57's runs).
4. The next freeze: write `generation-NN.json` (copy 90's, change page/shell/bundle/frozenCommit, add `f4` after F4 runs), freeze with
   `freeze/argv.json`'s argv (manifest name and date changed), rebind the Makefile line, run `v0_prime.py --generation NN` with the K
   arguments from `gen-90/v0/v0-prime.json`.

## Cautions

- `zoom_host2.py` with Firefox needs `TMPDIR` outside `/tmp` (snap Firefox; `Failed to set preferences`). It creates `zoom-diag/` on admin
  before opening the browser and does not delete it when the browser fails to start: delete it before the next run.
- Do not use `pgrep -f <pattern>` inside a command whose own text contains the pattern: it killed my shell once this session (no other
  process was hit). Use `pgrep -x`.
- F4's pre-run check refuses on foreign CPU: other sessions' CppunitTest makes run here often; check `pgrep -a make` before a chain.
- Unchanged from the last handoff: four Writer mutations in `run_e2_c_product_path.py` have no anchor on the page;
  `test_v21_shakedown_common.py::test_the_real_mirror_reproduces_the_round_identity` red from before; submissions on hold; never check out
  a candidate in the host repo's working copy (it is the live app).

## Appended after the re-test (owner's requests)

- `手測-0.2.56/` deleted on the owner's word (DAV 204); admin's trash bin emptied (`occ trashbin:cleanup admin`), so it cannot be restored.
- Disk cleanup (owner chose A-D): identical files in `wasm_sdk_probe/build/archive` hardlinked (`hardlink -t -m 1048576`, 8.54 GiB, all
  3900 sha256 unchanged) -- **never write an archive file in place**, it would change every linked copy; old host candidates removed
  (worktrees 0.2.54 / 0.2.55, clone 0.2.56; stale worktree records pruned; branches and archives kept; 0.2.45 and 0.2.57 kept).
  Docker **not** touched: the stopped containers and unused images are the owner's other projects (some hold state, e.g.
  `modaodfweb-rhtest` 3.1 GB writable layer; many images are built locally). Free space 49 -> 58 GB.

## Section 34.4

Checks changed because of review: 0.
