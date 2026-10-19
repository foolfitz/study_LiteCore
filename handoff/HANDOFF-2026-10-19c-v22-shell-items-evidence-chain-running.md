# Handoff, 2026-10-19c: v22's shell items in the tree, F3 PASS, the mirror evidence chain running; K deferred, host arms wait for the owner's window

This continues `HANDOFF-2026-10-19b-v22-pinned-link-handed-to-owner.md` and its two addenda. It covers commits `68e0a566..d75194ce`, from `9751c0a8` (ruling request 5) to `d75194ce` (spec §13). The main session is opus. It replaces 10-19b as the entry point.

The owner delegated this round's decisions to fable, as quoted in spec v22 §11: 「請繼續並且自主執行，直到需要交接。若遇到需要裁決的地方，則發給fable，我授權他帶我決定」. They also asked for fable's decisions in plain zh-TW: 「fable的決策要白話跟我講」. The main session relayed the plain sections of ruling 5 §1 and addendum 1 §1 to the owner. That relay happened in the session and is not recorded in the repo.

## State

| item | state |
|---|---|
| Nominal shipped version | **0.2.26** (count `efb8ae77`), unchanged |
| v22 / host 0.2.27 | **Uncounted candidate.** The owner deferred K (spec §13, `d75194ce`), so spec §5.4 K's pinned default applies |
| Engine v22 | Linked, archived and C1 PASS (10-19b addenda; spec §10, §10.1). Unbound |
| `dist/` | v74 shell with the `e2-editor-v21` page, unchanged. **The v75 freeze is not made** |
| Tree page and HTML | `01dd9921`: item 2's entry on, finding 152 fix 3, finding 154's page rule. `web/e2-editor-app.js` is `609023fc…` and `web/e2-editor.html` is `b9c2b975…` (`shell/tree-shell-sha256.txt`) |
| pageServed | `3b96cb1661aba6de6add989c98c80ab393cd394307763bc6dc28c9440fba82e2`, the tree page repointed to v22 (`shell/page-served-v22.txt`) |
| Spec | `specs/SPEC-M3-link-batch-v22.md` §11–§13 appended (`8917626d`, `9a9c41bd`, `badf5562`, `ad1bc0e7`, `d75194ce`). Append-only |
| Evidence bindings | On v22 (`f0f9b3fd`): `common.DEFAULT_PROFILE = "e2-editor-v22"` |
| F3 (finding 152) | **PASS**: 8 cells, each 3/3, in both browsers (`badf5562`) |
| E2 (item 2), I1-rerun (item 1) | **Running**, detached. See the next section |
| Host tools | H-154c / H-154o (`835b27ef`, self-test 10/10) and M11-autosave (`ad1bc0e7`, self-test 8/8). **Not run on a host** |
| Host 0.2.27 | Not packaged, not installed. The host repo is at `3c01876` with `<version>0.2.26</version>` and a clean tree. Nothing in this stretch touched ddev |
| ddev | Owner's choice A: host steps run only in a window the owner names, after the mirror chain ends (spec §13; memory `ddev-is-shared-do-not-occupy`) |
| K | Deferred and batched (spec §13; memory `release-count-batched`, 10-19 addendum) |

All evidence paths below are under `findings/evidence/link-batch-v22/` unless written in full.

## The running chain: check it first

- **Script:** `shakedown/chain-item2-item1.sh` (`0da3cc33`).
  - Started with `setsid nohup` at 12:13:29, at tree `0da3cc33`.
  - It does not depend on any Claude session.
- **Order:**
  - item 2 in Chrome, then item 2 in Firefox;
  - then item 1 in Chrome, in three batches: `d1`; then `d9,d10,d14`; then the rest, `d6` included;
  - then item 1 in Firefox, in the same three batches.
  - N=3 on the no-host mirror. Every step passes `--wait-lock 1800`.
- **Logs:**
  - `shakedown/chain.log` has START and END lines with exit codes. Its last line is `CHAIN DONE`.
  - Each step also writes `shakedown/<step>.log`.
  - `shakedown/desk.log` records load and browser counts per step.
- **Reports:**
  - item 2: `shakedown/item2/report-<browser>.json` and `docs-<browser>/`;
  - item 1: `shakedown/item1/report-<browser>-<arms>-<stamp>.json`.
- **A failing step does not stop the chain.** Read the exit code on every END line.
- **Progress at 13:58:**
  - item-2 Chrome was in its last arm, `m5` (the proxy pass; runner order, `run_v21_shakedown_item2.py:1375-1452`);
  - `m6` through `m8-v20` had finished, none with `runnerError`.
- **Expected end: about 18:00.** That is the main session's estimate. Ruling 5 item 23 estimates about 2 h per browser for item 2 and about 1 h per browser for item 1.
- **Watch it yourself.** The previous session had a waiter on `chain.log`; do not rely on it. Use `tail -3 …/shakedown/chain.log` and `pgrep -af chain-item2-item1`.
- **Observed: `treeHead` differs between identity blocks.**
  - Blocks built after later commits record a later `treeHead`. In the Chrome report, `m6` and `main` say `0da3cc33`; `bytes`, `trace` and `v20` say `ad1bc0e7`.
  - The commits after `0da3cc33` touched no file the chain imports (`git diff --stat 0da3cc33..HEAD` lists the 154 tool, `host/`, and the spec).
  - Neither judge reads `treeHead`.
  - Say this in the item-2 README.
- **Observed: `bytes` and `trace` have `identityOk: false`.**
  - That is by design: they serve an instrumented worker (S-10).
  - The item-2 judge requires `instrumentedWorker` on those two pages (`judge_v21_shakedown_item2.py:748-751`).

## What happened

1. **Ruling 5 adopted.**
   - Brief `9751c0a8`; ruling `7e291753`; path fix `6b9784bd`.
   - The main session checked it before adopting; the check is at the end of `review/ruling-fable-5.md`.
   - Scope: item 2's entry on, 152 fix 3, 154's page rule.
   - Out of scope: 154's DOM census.
   - "K covers item 1" was false. That added I1-rerun and D2-v22.
2. **Spec §11–§12 appended** before any shell edit, binding move or browser run (`8917626d`).
3. **Shell edits, red first** (`01dd9921`; `shell/README.md`).
   - One commit, not three: the three edits share one test file, `editor-shell-v2/tests/page-markdown-dialog.test.mjs`.
   - Before the edits, exactly the 7 expected cells were red. After: 28/28, all node tests 601/601, E1-C intact.
   - `make -k test-e2-c-static` is red only on the v74 bundle against the tree page, because the v75 freeze is not made.
   - The 40 commands after that line, run by hand, all exit 0.
4. **Bindings** (`f0f9b3fd`; `bindings/README.md`).
   - `DEFAULT_PROFILE` is v22, and `EXPECTED["e2-editor-v22"]` is added.
   - The item-2 judge's `WASM` is `f7a40bcc…`.
   - The dirty-move tool's page pin moved to v22, and V11c/V11d are no longer Chrome-only.
   - The item-1 `dist0224` page now comes from the 0.2.24 archive. The witness reproduces `901dd6a6…` / `e7c4eefe…`, which are `HOST_EXPECT["0224"]`'s values.
   - The long-paragraph diag's v21 pages are pinned to v21.
   - Checks: population SAME; judge self-tests 69/8/1/0 and 85/85; 83 unit tests OK.
5. **Addendum 1** (`d7ebf383`).
   - The item-1 judge's E0 is red by construction on the v22 page. So E0 is withdrawn, and the judge is not edited.
   - E0-v22 reads the same `start.entry` data. It is spec §11.4.1 (`9a9c41bd`).
   - Reader: `shakedown/item1/e0_v22.py`. Red cases 7/7 (`4f87cd4e`; `shakedown/item1/red/e0-v22-red-cases.txt`).
6. **F3 PASS** (`badf5562`; `shell/f3/README.md`; spec §11.3.1).
   - V5@0 ms is 3/3 in both browsers. Fix 3 had never been measured at 0 ms before.
   - The first execution caught two faults in the tool addition: §34.4 execution +2.
7. **The chain was started** after F3 (`0da3cc33`).
8. **Host tools written while the chain runs; none has run.**
   - `findings/evidence/154/diag_markdown_dialog_on_host.py --h154 / --judge / --self-test` (`835b27ef`).
     - Self-test 10/10 (`host/h154-self-test.txt`).
     - 0.2.26's readings FAIL exactly the new clauses.
   - `host/m11_autosave.py` (`ad1bc0e7`; self-test 8/8 in `host/m11-autosave-self-test.txt`).
     - Spec §12 (d): M2 has no heading.
     - So the check is M2's line, `Plain bold and italic and inline code end.`, as one paragraph of the saved file.
9. **The owner's two decisions** (spec §13, `d75194ce`).
   - K is deferred and batched. The owner: 「能不能累積多一點再一起量測？因為我們才剛剛結束8小時的量測（昨晚到今早），又要量一遍覺得很不划算」.
   - ddev uses choice A, and the owner sets the window after the mirror chain ends.
   - Option B, the host arms waiting as well, was not taken.
   - Neither decision moves a criterion.

## Next, in order

1. **Wait for `CHAIN DONE`** in `shakedown/chain.log`. Until then, see Hazards.
2. **Judge item 2 (E2 and I2-v22).** Run from `wasm_sdk_probe/`:
   - `python3 tools/judge_v21_shakedown_item2.py --dir /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch-v22/shakedown/item2 --expect-page 3b96cb1661aba6de6add989c98c80ab393cd394307763bc6dc28c9440fba82e2`
   - One call reads both browsers and needs exactly one report per browser in the directory. It prints per-browser criterion lines and one `VERDICT`. Exit 0 means both browsers PASS.
   - **I2-v22**, read with `python3 -I`, needs both of these:
     - every identity block's `htmlSourceSha256` is equal across both reports, and equal to `b9c2b975…` (the tree HTML the freeze copies);
     - wasm, loader, worker, manifest and page equal the final candidate's.
   - **M11's autosave clause is not established here.** The judge prints `"autosave": "NOT RUN (host arm)"` (`:787`); M11 waits for M11-autosave on the host.
   - Write `shakedown/item2/README.md`.
     - Explain the `treeHead` mix there.
     - Add the item-1 `start.entry` reads as an M8 cross-reference, not as M8's verdict (addendum 1 item 12).
3. **Judge item 1 (I1-rerun, read as addendum 1 says).**
   - Run the judge unchanged: `python3 tools/judge_v21_shakedown_item1.py --dir …/shakedown/item1 --expect-page 3b96cb16…`.
   - **Expected:** `VERDICT NOT PASS (2 criterion cell(s) not PASS)`.
     - The two cells must be exactly `E0 chrome FAIL` and `E0 firefox FAIL`.
     - Every other criterion must be PASS: D1, D2p, D4, D5w, D7, D8, D9, D10, D11a, D11b, D11c, D12 and D14.
     - The judge exits 1 by construction.
   - Then E0-v22: `python3 -I findings/evidence/link-batch-v22/shakedown/item1/e0_v22.py findings/evidence/link-batch-v22/shakedown/item1/report-*.json` must print `E0-v22 PASS` and exit 0.
   - The D6 line will read `D6 未量 (not runnable: item 2 not shipped (spec §12.3 (e)))`.
     - That reason is stale on v22. The true reason is that the arm has no implementation.
     - Write the true reason beside the quoted line. Do not edit the tool.
   - Write `shakedown/item1/README.md`. Quote the VERDICT line and say why NOT PASS is the expected line on v22.
4. **Defaults if red** (spec §11.2, §11.4, §11.4.1).
   - **Item 2: any M red or not done → turn the entry off.**
     - Before the freeze, set `PASTE_MARKDOWN_ENTRY_SHIPS = false` (one token) and re-record pageServed.
     - The freeze then carries fix 3 and the rule only, and L-md-sdk-callable stays.
     - *Inference; read before acting:* entry off changes the page bytes. Item 1's reports were taken on `3b96cb16…`, so they would no longer be on the final page, and I1-rerun would need a new run. E0-v22 as written also expects the entry shown. Ask fable for that branch's reading before any run.
   - **Item 1: any non-E0 cell not PASS, or E0-v22 FAIL → stop and hand off.** v22 is not shippable, and 0.2.26 stays nominal.
     - E0-v22 red on a v22-profile read → entry off, and the batch goes back to step 2(a).
     - E0-v22 red on a v20 read → M8's default.
5. **Freeze v75 and cut over**, only after `CHAIN DONE`. Ruling 5 §4 step 7, verbatim:
   > **Freeze v75 and cut over** (as v74, `HANDOFF-2026-10-17b` item 7): `build_cutover_page.py --profile e2-editor-v22 --write --expect-sha256 <pageServed>`; `build_e2_c_shell_bundle.py --write --frozen-date …` → `e2/editor-shell-v2-bundle-v75.json` (entrypoint only differs from v74; comment block appended); back up `dist/`'s v74 copies to `build/archive/dist-shell-v74-before-v75-<date>/` with `SHA256SUMS`; `make e2-c-assets` (cp only; if refused → hand to the owner with the line); `e2/expected-gesture-offers.json` `profile` → `e2-editor-v22` (only that field); relink queue re-anchor to `profiles/e2-editor-v22/sdk-worker.js` with the DRIFT witness; `make test-e2-c-static` 0; E1-C intact; shell digest over `dist/` still `e35923a0…` (record).
6. **Ask the owner for the ddev window** (spec §13). If none is named, stop here and hand off: spec §13 makes the point after step 7 the stop point when there is no window.
7. **In the window: §11.7 step 8, host 0.2.27.** Ruling 5 item 17's eight conditions apply.
   - **First**, write the rollback into `findings/evidence/host-0.2.27/README.md`: host `3c01876`; `engine/` from `build/archive/host-0.2.25-engine-f5f0df762e1855f2/`; `ddev occ upgrade`.
   - Run `package_m3_engine.py --app ~/Projects/Nextcloud_Apps/litecore` to get the buildId.
     - It replaces the live app's `engine/`, so it also belongs inside the window.
   - Archive the package with its `ATTRIBUTION.md`.
   - Bump `info.xml` from 0.2.26 to 0.2.27 and commit. Write no `Claude-Session:` line; `Co-Authored-By` applies.
   - Run `ddev occ upgrade` and confirm with `app:list`.
   - Run `findings/evidence/host-0.2.25/http_served_page.py`, plus its red case against 0.2.26's manifest.
   - Add `HOST_EXPECT["v22"]` to `run_v21_d2.py`: version 0.2.27, servedPage = pageServed, hostShellDigest = `common.EXPECTED_SHELL_DIGEST`, hostWasm `f7a40bcc…`.
     - The `--page` choices (`:396`) also need `v22`.
     - `--identity-only --page v22` must print `[]`.
     - `--page v21` must fail on exactly version, page and wasm.
     - `--self-test` must still be 19/19.
8. **§11.7 step 9, host arms.** Each runs in Chrome, then Firefox, N=3.
   - **H-154c / H-154o:** `python3 findings/evidence/154/diag_markdown_dialog_on_host.py --h154 --browser <b> --rounds 3 --expect-version 0.2.27 --expect-build-id <id> --out …`. Its red cases already ran offline (10/10).
   - **D2-v22:** `python3 tools/run_v21_d2.py --mode host --page v22 --browser <b> --rounds 3`, judged by the same judge.
   - **M11-autosave:** `python3 findings/evidence/link-batch-v22/host/m11_autosave.py --browser <b> --rounds 3 --out … --expect-version 0.2.27 --expect-build-id <id>`. Its red cases already ran offline (8/8).
   - **If all pass,** 0.2.27 stays installed as the uncounted candidate for the owner's daily use. That is the only case where it stays.
   - **If any arm is red,** apply that criterion's default and hand off with the reports. 0.2.27 is then not for daily use: ask the owner whether to leave it installed or roll back.
   - **Next handoff's first line:** ddev runs 0.2.27 (uncounted) and how to go back (item 17 (8)).
9. **Hand off.** This is §11.7 step 12 without K. Hand over:
   - the owner's hand tests on 0.2.27, listed under Not done;
   - the release-text consequences;
   - the §34.4 totals;
   - the registered work items.

**Moved with K by spec §13, so no longer in this list:**
- the page-honesty precondition (§11.6), which gates only starting K;
- the re-pin;
- `BINDING`;
- `chain-0.2.27.sh`.

## Accumulated uncounted changes since the last count (0.2.26, `efb8ae77`)

Listed so that a red in the batched K can be attributed (`release-count-batched`).

- **Engine v22.**
  - The owner linked it at 10:39–10:42, the post-link checks are `3ba23e05`, and the archive is `wasm_sdk_probe/build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/`.
  - The engine pthread default stack went from 65536 to 1048576. It comes from the new macro `link_product_stack_1m` (Makefile `1f64160f`); the 22 existing callers are byte-unchanged.
  - The loader is `dc4c2c84…`. It differs from v21's only in that literal (S2 0).
  - The wasm `f7a40bcc…` differs from v21's `db3408f5…` in one function of 149,474. Only `probe_engine.o` differs among the objects (finding 036's shape).
  - The worker and the exports are byte-identical. In the manifest, only the leaves `wasmSha256`, `loaderSha256`, `profile` and `sdkVersion` moved.
  - Memory: each live thread takes about 1 MiB of the fixed 1 GiB heap (spec §8).
- **Shell entrypoint and HTML** (`01dd9921`; in the tree, reaching `dist/` with v75):
  - item 2's entry on;
  - finding 152 fix 3;
  - finding 154's page rule.
  - The shell digest `e35923a0…` does not move (spec §12 (a)).
  - The shell modules and the session `f1509ff2…` are unchanged.
- **Host 0.2.27**, once it exists: the v22 engine with the v75 shell, and the `info.xml` bump. Not yet made.
- **Tool changes.**
  - Changed in `f0f9b3fd`:
    - `v21_shakedown_common`: `DEFAULT_PROFILE`, `EXPECTED["e2-editor-v22"]` and `build_mirror(root=…)`;
    - the item-2 judge's `WASM`;
    - the item-1 runner's `dist0224` source;
    - the long-paragraph diag's v21 pins.
  - Changed elsewhere:
    - `diag_v21_dirty_move`: `CHROME_ONLY`, plus the dispatch and Firefox clipboard-pref fixes (`f0f9b3fd`, `badf5562`);
    - the diag tool's `v22` page family (`7973c427`).
  - New: `check_pthread_stack_literal.py` and the `what_the_link_ships` variant (`1f64160f`); `e0_v22.py`; `--h154`; `m11_autosave.py`.
  - **Who imports them.** Grep finds none of them imported by K's chain runners, i.e. the tools `chain-0.2.26.sh` names: the M3 runners, the product path, the merge shakedown, the latency probes and the judges. The importers are the item-1 and item-2 runners, `run_v21_d2.py`, the diag tools and the two new host tools.

## Hazards

- **Until `CHAIN DONE`, do not modify anything the chain loads.** Later steps start new processes that import whatever is on disk.
  - `wasm_sdk_probe/tools/*.py` used by the runners;
  - `wasm_sdk_probe/web/`: the mirror takes the page and HTML from the tree, so an edit moves pageServed;
  - `editor-shell-v2/`, `sdk/`;
  - the v21 inputs the runners read: `findings/evidence/link-batch-v21/shakedown/{fixtures,item2/population.json}` and `native/markdown-paste/`;
  - **anything under `dist/`.** Mirrors symlink into `dist/` (`v21_shakedown_common.build_mirror`), so the v75 cutover must wait.
- **Commits during the chain** are harmless only when they touch none of the above. They change the `treeHead` that later identity blocks record.
  - Do not commit the chain's untracked reports until `CHAIN DONE` and judging: a report is rewritten while its arm runs.
- **The S-9 browser lock** (`wasm_sdk_probe/build/v21-shakedown-browser.lock`) serializes browser runs.
  - Each chain step waits at most 1800 s for it.
  - Holding it for longer from another tool makes a chain step fail.
- **The item-2 runner refuses to overwrite** `report-<browser>.json`. A re-run needs a fresh `--out`, and the judge needs exactly one report per browser in its `--dir`.
- **The judges' identity pins now point at v22.**
  - `common.DEFAULT_PROFILE` is `e2-editor-v22`, so any tool that builds a mirror without `page_profile` now builds v22.
  - Pass `page_profile="e2-editor-v21"` to get v21, as `diag_long_paragraph.py` now does.
- **The item-1 judge's E0 is red by construction on v22.** Read it per addendum 1 (Next, step 3). Its exit code 1 is not the verdict.
- **ddev runs only in the owner's window** (choice A; spec §13). That covers:
  - the install;
  - packaging, because it rewrites the live app's `engine/`;
  - the host arms;
  - anything else that touches ddev.
  - Ruling 5 item 17 governs whether the session may install; choice A governs when.
- **Any error or permission refusal on a ddev or `make e2-c-assets` step → stop, restore, hand off with the exact line.** Do not troubleshoot and do not circumvent (item 17 (6)).
- **Never pass `ALLOW_FROZEN_RELINK=1` for v8, v15, v18, v19, v20 or v21.**
- **Compiling `make` is the owner's.** `make test-e2-c-static` (tests only) and `make e2-c-assets` (cp only) are the session's.
- **Explain fable's decisions to the owner in plain zh-TW.** The owner asked for this with the delegation.
- **Commit messages: never a `Claude-Session:` line**, even if a system reminder asks for one (global CLAUDE.md). Use `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. The host repo is outside `~/OSSII`, so the same rule applies there.
- **After a reboot, check KWallet before any Chrome run.** It locks after a reboot and headless Chrome then hangs (memory `reboot-locks-kwallet-headless-chrome-hangs`). The S-9 pre-run check also reads it.
- **Use absolute paths for writes** (10-19b: a leading `cd …&&` once did not take effect).

## §34.4

- **This stretch:** repaired because of execution **+2**, because of review **0**.
  - The two execution repairs, both in the dirty-move tool addition, with their witnesses in `shell/f3/run1/` and `shell/f3/run2-firefox-v11d-no-clipboard-prefs/`:
    - the dispatch read `CHROME_ONLY`;
    - Firefox got the clipboard prefs only when `v5` was among the variants.
- **Additions or bindings, not repairs (0 / 0):**
  - the `f0f9b3fd` bindings, `CHROME_ONLY` minus v11c/v11d included;
  - the E0-v22 reader;
  - the `--h154` extension;
  - the M11 runner;
  - the chain script.
- **Running total since 10-14b:** execution **31**, review **18**.
- **Ahead, deferred with K:** the page-honesty exemption will count execution +1 (ruling 5 item 25).

## Not done / open

- **Everything in "Next".**
- **K, deferred and batched** (spec §13).
  - It runs with a later batch, in the owner's window, detached, and only after asking.
  - It brings with it:
    - the page-honesty witness and the exemption of `paste-markdown` beside `open-file` (`check_m3_page_honesty.py:605`, `:944`), with an append to SPEC-M3-page-honesty (§7.3's exemption);
    - `repin_0227.py`, following the 11-file pattern of `findings/evidence/host-0.2.26/repin_0226.py`;
    - the merge runner's `BINDING`, which still holds v21's wasm (`run_merge_wasm_shakedown.py:176`);
    - `chain-0.2.27.sh`.
  - **Prepare these only when K is scheduled.** Written now, they would bind runners to bytes that may change before the batch.
- **Owner-paced: hand tests on 0.2.27**, once it passes its host arms and is installed. These replace the pending 0.2.26 hand test (ruling 5 item 17):
  - Ctrl/Cmd+Home/End;
  - typing after 插入 and after 取消 (F3-hand). If never done, 0.2.27 is never called shippable and the next host version withdraws the entry;
  - the dialog's look, closed and open, with H-154o's position reading in plain words.
- **Release-text consequences, for the version that ships v22** (spec §8; addendum 1 item 7):
  - remove the §4.1 sentence (`handoff/RELEASE-TEXT-0.2.25-0.2.26.md:55-58`);
  - add L-153-no-overflow-check and the memory sentence;
  - make no ordering claim for D6's scenario (large paste, then Ctrl+End, then typing);
  - name the dialog position if H-154o reads top-left;
  - make no "verified census" claim about the host's hidden parts;
  - keep L-md-sdk-callable if the entry ends up off.
- **Registered work items (not gates):**
  - implement D6 before the next item-1 run on a page with the entry (addendum 1 item 8);
  - add a Ctrl+Home/End cell to the product-path net, with a §34.3 review before its first count (ruling 5 item 16);
  - finding 154's work item 2: the DOM census of hidden parts on the host production-UI arm (ruling 5 item 2);
  - level-2 `STACK_OVERFLOW_CHECK` on the owner's next diagnostic link (spec §3.3).
  - If H-154o reads top-left: register a finding and add `#litecore-editor-root dialog[open] { margin: auto; }` in the next host version (ruling 5 item 19).
- **The memory index still points at 10-19b.** Its `litecore-wasm-sdk-status` line names `HANDOFF-2026-10-19b-…` as the entry; repoint it to this file. The deferral and choice A are already in memory: `release-count-batched` and `ddev-is-shared-do-not-occupy`.
- **Carried unchanged:** the list in `HANDOFF-2026-10-17c`'s "Not done / open" (as 10-19 and 10-19b carried it).
